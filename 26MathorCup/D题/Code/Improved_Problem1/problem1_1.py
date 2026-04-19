from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Optional

import numpy as np

RANDOM_SEED = 20260417
TOP_CLEARANCE = 3
SUPPORT_LIMIT_PER_CM2 = 500 / 10000


@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str


@dataclass(frozen=True)
class CargoType:
    type_id: str
    category: str
    length: int
    width: int
    height: int
    weight: float
    quantity: int
    stackable: bool
    can_rotate: bool
    fragile: bool
    oriented: bool


@dataclass(frozen=True)
class CargoItem:
    item_id: str
    type_id: str
    category: str
    original_size: Tuple[int, int, int]
    weight: float
    volume: int
    stackable: bool
    fragile: bool
    oriented: bool
    allowed_orientations: Tuple[Orientation, ...]


@dataclass(frozen=True)
class TruckType:
    truck_id: int
    name: str
    length: int
    width: int
    height: int
    max_weight: float
    trip_cost: float

    @property
    def usable_height(self) -> int:
        return self.height - TOP_CLEARANCE

    @property
    def volume(self) -> int:
        return self.length * self.width * self.usable_height


@dataclass
class PlacedCargo:
    item_id: str
    type_id: str
    category: str
    x: int
    y: int
    z: int
    length: int
    width: int
    height: int
    weight: float
    orientation_id: int
    rotation: str
    support_by: str | None = None
    support_capacity: float = 0.0
    direct_supported_weight: float = 0.0

    @property
    def top(self) -> int:
        return self.z + self.height

    @property
    def bounds(self) -> Tuple[int, int, int, int, int, int]:
        """返回边界框，用于 numpy 快速计算"""
        return (self.x, self.y, self.z, 
                self.x + self.length, self.y + self.width, self.z + self.height)


@dataclass
class PackingResult:
    truck: TruckType
    placed: List[PlacedCargo]
    unplaced: List[CargoItem]
    utilized_volume: int
    utilized_weight: float
    score: float

    @property
    def volume_utilization(self) -> float:
        return self.utilized_volume / self.truck.volume if self.truck.volume else 0.0

    @property
    def weight_utilization(self) -> float:
        return self.utilized_weight / self.truck.max_weight if self.truck.max_weight else 0.0


def load_truck_types() -> Dict[int, TruckType]:
    return {
        1: TruckType(1, "车型1", 420, 210, 220, 6000, 450),
        2: TruckType(2, "车型2", 680, 245, 250, 10000, 700),
    }


def load_cargo_types() -> Dict[str, CargoType]:
    return {
        "G1": CargoType("G1", "standard", 60, 40, 30, 12, 800, True, True, False, False),
        "G2": CargoType("G2", "standard", 50, 35, 25, 8, 1000, True, True, False, False),
        "G3": CargoType("G3", "fragile", 70, 50, 40, 15, 300, False, True, True, False),
        "G4": CargoType("G4", "oriented", 80, 60, 50, 25, 400, True, False, False, True),
        "G5": CargoType("G5", "oriented", 40, 40, 60, 18, 500, True, False, False, True),
    }


def unique_orientations(size: Tuple[int, int, int], category: str) -> Tuple[Orientation, ...]:
    l, w, h = size
    perms = {
        "standard": [((l, w, h), "LWH"), ((l, h, w), "LHW"), ((w, l, h), "WLH"), 
                     ((w, h, l), "WHL"), ((h, l, w), "HLW"), ((h, w, l), "HWL")],
        "fragile": [((l, w, h), "LWH"), ((w, l, h), "WLH")],
        "oriented": [((l, w, h), "LWH")],
    }[category]
    seen, ans = set(), []
    for i, (dims, name) in enumerate(perms, 1):
        if dims in seen:
            continue
        seen.add(dims)
        ans.append(Orientation(i, dims, name))
    return tuple(ans)


def expand_cargo_items(cargo_types: Dict[str, CargoType]) -> List[CargoItem]:
    items = []
    for cargo in cargo_types.values():
        size = (cargo.length, cargo.width, cargo.height)
        orientations = unique_orientations(size, cargo.category)
        volume = cargo.length * cargo.width * cargo.height
        for idx in range(1, cargo.quantity + 1):
            items.append(CargoItem(f"{cargo.type_id}_{idx:03d}", cargo.type_id, cargo.category, 
                                   size, cargo.weight, volume, cargo.stackable, cargo.fragile, 
                                   cargo.oriented, orientations))
    return items


class FastPacker:
    """优化版装箱器，使用 numpy 加速空间检查"""
    
    def __init__(self, truck: TruckType, alpha: float = 0.5, beta: float = 0.5):
        self.truck = truck
        self.alpha = alpha
        self.beta = beta
        self.candidate_limit = 30  # 候选点数量限制
        
    def pack(self, items: Sequence[CargoItem]) -> PackingResult:
        """打包单个序列"""
        placed: List[PlacedCargo] = []
        unplaced: List[CargoItem] = []
        current_weight = 0.0
        current_volume = 0
        
        # 用于 numpy 快速检查的数组
        placed_bounds = np.empty((0, 6), dtype=np.int32)
        
        for item in items:
            best = None
            # 获取候选点
            points = self._get_candidate_points(placed, placed_bounds)
            
            for point in points:
                for ori in item.allowed_orientations:
                    feasible, support_id, cap = self._can_place_fast(
                        item, ori, point, placed, placed_bounds, current_weight
                    )
                    if not feasible:
                        continue
                    score = self._placement_score(item, ori, point)
                    if best is None or score > best[0]:
                        best = (score, point, ori, support_id, cap)
            
            if best is None:
                unplaced.append(item)
                continue
                
            _, (x, y, z), ori, support_id, cap = best
            placed_item = PlacedCargo(
                item.item_id, item.type_id, item.category,
                x, y, z, ori.size[0], ori.size[1], ori.size[2],
                item.weight, ori.orient_id, ori.rotation,
                support_id, cap
            )
            placed.append(placed_item)
            # 更新 numpy 数组
            placed_bounds = np.vstack([placed_bounds, [placed_item.bounds]])
            current_weight += item.weight
            current_volume += item.volume
            
            if support_id is not None:
                for p in placed:
                    if p.item_id == support_id:
                        p.direct_supported_weight += item.weight
                        break
        
        score = self.alpha * (current_volume / self.truck.volume) + \
                self.beta * (current_weight / self.truck.max_weight)
        return PackingResult(self.truck, placed, unplaced, current_volume, current_weight, score)
    
    def _get_candidate_points(self, placed: List[PlacedCargo], 
                               placed_bounds: np.ndarray) -> List[Tuple[int, int, int]]:
        """获取候选放置点，使用缓存减少重复计算"""
        if not placed:
            return [(0, 0, 0)]
        
        pts = {(0, 0, 0)}
        for p in placed:
            pts.add((p.x + p.length, p.y, p.z))
            pts.add((p.x, p.y + p.width, p.z))
            pts.add((p.x, p.y, p.z + p.height))
        
        # 过滤掉已被占用的点
        if len(placed_bounds) > 0:
            valid_pts = []
            for pt in pts:
                if not self._point_inside_any_fast(pt, placed_bounds):
                    valid_pts.append(pt)
        else:
            valid_pts = list(pts)
        
        # 排序并限制数量
        valid_pts.sort(key=lambda t: (t[2], t[0] + t[1], t[0], t[1]))
        return valid_pts[:self.candidate_limit]
    
    def _point_inside_any_fast(self, point: Tuple[int, int, int], 
                                bounds: np.ndarray) -> bool:
        """numpy 加速的点是否在任意盒子内检查"""
        if len(bounds) == 0:
            return False
        x, y, z = point
        # 向量化检查
        inside = (x >= bounds[:, 0]) & (x < bounds[:, 3]) & \
                 (y >= bounds[:, 1]) & (y < bounds[:, 4]) & \
                 (z >= bounds[:, 2]) & (z < bounds[:, 5])
        return np.any(inside)
    
    def _boxes_overlap_fast(self, x: int, y: int, z: int, l: int, w: int, h: int,
                             bounds: np.ndarray) -> bool:
        """numpy 加速的盒子重叠检查"""
        if len(bounds) == 0:
            return False
        # 向量化重叠检查
        overlap = (x < bounds[:, 3]) & (x + l > bounds[:, 0]) & \
                  (y < bounds[:, 4]) & (y + w > bounds[:, 1]) & \
                  (z < bounds[:, 5]) & (z + h > bounds[:, 2])
        return np.any(overlap)
    
    def _can_place_fast(self, item: CargoItem, ori: Orientation, 
                         point: Tuple[int, int, int], placed: List[PlacedCargo],
                         placed_bounds: np.ndarray, current_weight: float):
        """快速检查是否可以放置"""
        x, y, z = point
        l, w, h = ori.size
        
        # 边界检查
        if x + l > self.truck.length or y + w > self.truck.width or \
           z + h > self.truck.usable_height:
            return False, None, 0.0
        
        # 重量检查
        if current_weight + item.weight > self.truck.max_weight + 1e-9:
            return False, None, 0.0
        
        # 重叠检查（numpy 加速）
        if self._boxes_overlap_fast(x, y, z, l, w, h, placed_bounds):
            return False, None, 0.0
        
        # 支撑检查
        if z == 0:
            return True, None, 0.0
        
        support_id, supporter = self._find_supporter_fast(
            item, x, y, z, l, w, placed, placed_bounds
        )
        if supporter is None:
            return False, None, 0.0
        
        cap = SUPPORT_LIMIT_PER_CM2 * supporter.length * supporter.width
        if supporter.direct_supported_weight + item.weight > cap + 1e-9:
            return False, None, 0.0
        
        if item.category == "oriented":
            cx, cy = x + l / 2, y + w / 2
            if not (supporter.x <= cx <= supporter.x + supporter.length and
                    supporter.y <= cy <= supporter.y + supporter.width):
                return False, None, 0.0
        
        return True, support_id, cap
    
    def _find_supporter_fast(self, item: CargoItem, x: int, y: int, z: int,
                              l: int, w: int, placed: List[PlacedCargo],
                              placed_bounds: np.ndarray):
        """快速查找支撑物"""
        # 先快速筛选可能支撑的货物（在 z 高度）
        if len(placed_bounds) == 0:
            return None, None
        
        # 找出 top == z 的货物
        for i, p in enumerate(placed):
            if p.top != z:
                continue
            # 检查是否完全支撑
            if not (p.x <= x and x + l <= p.x + p.length and
                    p.y <= y and y + w <= p.y + p.width):
                continue
            # 易碎品和支撑物限制
            if item.fragile and p.category != "standard":
                continue
            if p.category == "fragile":
                continue
            return p.item_id, p
        
        return None, None
    
    def _placement_score(self, item: CargoItem, ori: Orientation,
                          point: Tuple[int, int, int]) -> float:
        """计算放置得分"""
        x, y, z = point
        l, w, h = ori.size
        volume_ratio = (l * w * h) / self.truck.volume
        weight_ratio = item.weight / self.truck.max_weight
        compact_penalty = 0.0004 * (z + 0.35 * x + 0.2 * y)
        boundary_bonus = 0.02 if (x == 0 or y == 0 or z == 0) else 0.0
        footprint_bonus = 0.005 * (l * w) / (self.truck.length * self.truck.width)
        return self.alpha * volume_ratio + self.beta * weight_ratio + \
               boundary_bonus + footprint_bonus - compact_penalty


def initial_sequence(items: Sequence[CargoItem], rng: random.Random) -> List[CargoItem]:
    """生成初始序列"""
    seq = list(items)
    seq.sort(key=lambda item: (item.fragile, -item.weight / item.volume, 
                                -item.volume, -item.weight, item.type_id, item.item_id))
    for _ in range(min(len(seq) // 10, 12)):
        i, j = rng.sample(range(len(seq)), 2)
        seq[i], seq[j] = seq[j], seq[i]
    return seq


def mutate(sequence: List[CargoItem], rng: random.Random, swaps: int = 3) -> List[CargoItem]:
    """变异操作"""
    child = sequence[:]
    if len(child) < 2:
        return child
    for _ in range(swaps):
        i, j = rng.sample(range(len(child)), 2)
        child[i], child[j] = child[j], child[i]
    return child


def order_crossover(parent1: Sequence[CargoItem], parent2: Sequence[CargoItem], 
                     rng: random.Random) -> List[CargoItem]:
    """顺序交叉"""
    n = len(parent1)
    if n < 2:
        return list(parent1)
    left, right = sorted(rng.sample(range(n), 2))
    child: List[CargoItem | None] = [None] * n
    child[left:right + 1] = list(parent1[left:right + 1])
    used = {item.item_id for item in parent1[left:right + 1]}
    fill = [item for item in parent2 if item.item_id not in used]
    ptr = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[ptr]
            ptr += 1
    return [item for item in child if item is not None]


def tournament_select(population: Sequence[List[CargoItem]], scores: Sequence[float], 
                       rng: random.Random, k: int = 3) -> List[CargoItem]:
    """锦标赛选择"""
    cand = rng.sample(range(len(population)), k)
    return population[max(cand, key=lambda idx: scores[idx])]


def evaluate_individual(args: Tuple) -> Tuple[float, PackingResult, List[CargoItem]]:
    """评估单个个体（用于多进程）"""
    seq, truck, alpha, beta = args
    packer = FastPacker(truck, alpha, beta)
    result = packer.pack(seq)
    return (result.score, result, seq)


def genetic_optimize_single_truck(items: Sequence[CargoItem], truck: TruckType,
                                   alpha: float = 0.5, beta: float = 0.5,
                                   population_size: int = 18, generations: int = 24,
                                   seed: int = RANDOM_SEED,
                                   use_parallel: bool = True) -> PackingResult:
    """遗传算法优化（支持多进程并行）"""
    if len(items) <= 1:
        packer = FastPacker(truck, alpha, beta)
        return packer.pack(items)
    
    rng = random.Random(seed + truck.truck_id)
    base = initial_sequence(items, rng)
    population = [base] + [mutate(base, rng, swaps=6) for _ in range(population_size - 1)]
    best = None
    elite_count = max(2, population_size // 6)
    
    for g in range(generations):
        print(f"第{g+1}代开始，种群大小: {len(population)}", end="\r")
        
        # 准备评估参数
        eval_args = [(seq, truck, alpha, beta) for seq in population]
        
        # 多进程并行评估
        if use_parallel and len(population) > 1:
            with Pool(processes=min(cpu_count(), len(population))) as pool:
                scored = pool.map(evaluate_individual, eval_args)
        else:
            scored = [evaluate_individual(args) for args in eval_args]
        
        # 更新最优解
        for score, result, seq in scored:
            if best is None or score > best.score:
                best = result
        
        # 排序
        scored.sort(key=lambda x: x[0], reverse=True)
        elites = [row[2][:] for row in scored[:elite_count]]
        raw_population = [row[2] for row in scored]
        raw_scores = [row[0] for row in scored]
        
        # 生成下一代
        next_population = elites[:]
        while len(next_population) < population_size:
            p1 = tournament_select(raw_population, raw_scores, rng)
            p2 = tournament_select(raw_population, raw_scores, rng)
            child = order_crossover(p1, p2, rng)
            if rng.random() < 0.85:
                child = mutate(child, rng, swaps=rng.randint(2, 6))
            next_population.append(child)
        population = next_population
    
    print()  # 换行
    return best if best is not None else packer.pack(items)


def result_to_dict(result: PackingResult) -> Dict[str, object]:
    """转换结果为字典"""
    return {
        "truck": asdict(result.truck),
        "summary": {
            "loaded_items": len(result.placed),
            "unloaded_items": len(result.unplaced),
            "space_utilization": round(result.volume_utilization, 6),
            "weight_utilization": round(result.weight_utilization, 6),
            "composite_score": round(result.score, 6),
            "used_volume_cm3": result.utilized_volume,
            "used_weight_kg": round(result.utilized_weight, 3),
        },
        "placements": [asdict(item) for item in result.placed],
        "unplaced_items": [item.item_id for item in result.unplaced],
    }


def solve_problem_1_1(alpha: float = 0.5, beta: float = 0.5,
                       use_parallel: bool = True) -> Dict[int, PackingResult]:
    """求解问题1.1"""
    items = expand_cargo_items(load_cargo_types())
    trucks = load_truck_types()
    results = {}
    
    for truck_id, truck in trucks.items():
        print(f"\n正在优化 {truck.name}...")
        results[truck_id] = genetic_optimize_single_truck(
            items, truck, alpha, beta, use_parallel=use_parallel
        )
    
    return results


def save_problem_1_1_results(results: Dict[int, PackingResult], 
                              output_dir: Path | None = None) -> None:
    """保存结果"""
    output_dir = output_dir or Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for truck_id, result in results.items():
        data = result_to_dict(result)
        summary[truck_id] = data["summary"]
        (output_dir / f"problem1_1_truck_{truck_id}_solution.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (output_dir / "problem1_1_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def print_problem_1_1_summary(results: Dict[int, PackingResult], elapsed: float) -> None:
    """打印摘要"""
    print("\n问题1.1 单车满载率最大化求解结果")
    print("=" * 60)
    for result in results.values():
        print(f"{result.truck.name}：")
        print(f"  装入件数：{len(result.placed)}")
        print(f"  剩余件数：{len(result.unplaced)}")
        print(f"  空间利用率：{result.volume_utilization:.4%}")
        print(f"  载重利用率：{result.weight_utilization:.4%}")
        print(f"  综合满载率：{result.score:.4%}")
        print(f"  已用体积：{result.utilized_volume} cm^3")
        print(f"  已用载重：{result.utilized_weight:.2f} kg")
        print("-" * 60)
    print(f"总耗时：{elapsed:.2f} s")


if __name__ == "__main__":
    print("start")
    start = time.time()
    print("开始求解...")
    
    # use_parallel=False 可以禁用多进程（调试用）
    results = solve_problem_1_1(use_parallel=True)
    
    print("求解完成，开始保存结果...")
    save_problem_1_1_results(results)
    print("保存完成，开始打印摘要...")
    print_problem_1_1_summary(results, time.time() - start)
    print("end")