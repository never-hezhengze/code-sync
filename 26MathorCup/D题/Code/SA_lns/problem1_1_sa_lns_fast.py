from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

RANDOM_SEED = 20261016
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


# =========================
# 数据读取
# =========================
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
        "standard": [
            ((l, w, h), "LWH"),
            ((l, h, w), "LHW"),
            ((w, l, h), "WLH"),
            ((w, h, l), "WHL"),
            ((h, l, w), "HLW"),
            ((h, w, l), "HWL"),
        ],
        "fragile": [
            ((l, w, h), "LWH"),
            ((w, l, h), "WLH"),
        ],
        "oriented": [
            ((l, w, h), "LWH"),
        ],
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
            items.append(
                CargoItem(
                    f"{cargo.type_id}_{idx:03d}",
                    cargo.type_id,
                    cargo.category,
                    size,
                    cargo.weight,
                    volume,
                    cargo.stackable,
                    cargo.fragile,
                    cargo.oriented,
                    orientations,
                )
            )
    return items


# =========================
# 几何与支撑判断
# =========================
def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def boxes_overlap(x: int, y: int, z: int, dims: Tuple[int, int, int], p: PlacedCargo) -> bool:
    l, w, h = dims
    return (
        overlap(x, x + l, p.x, p.x + p.length)
        and overlap(y, y + w, p.y, p.y + p.width)
        and overlap(z, z + h, p.z, p.z + p.height)
    )


def point_inside_box(point: Tuple[int, int, int], p: PlacedCargo) -> bool:
    x, y, z = point
    return p.x <= x < p.x + p.length and p.y <= y < p.y + p.width and p.z <= z < p.z + p.height


def supporter_for(item: CargoItem, x: int, y: int, z: int, dims: Tuple[int, int, int], placed: List[PlacedCargo]):
    if z == 0:
        return None, None

    l, w, _ = dims
    for c in placed:
        if c.top != z:
            continue
        if not (c.x <= x and x + l <= c.x + c.length and c.y <= y and y + w <= c.y + c.width):
            continue
        if item.fragile and c.category != "standard":
            continue
        if c.category == "fragile":
            continue
        return c.item_id, c
    return None, None


def can_place(
    item: CargoItem,
    ori: Orientation,
    point: Tuple[int, int, int],
    truck: TruckType,
    placed: List[PlacedCargo],
    current_weight: float,
):
    x, y, z = point
    l, w, h = ori.size

    if x + l > truck.length or y + w > truck.width or z + h > truck.usable_height:
        return False, None, 0.0
    if current_weight + item.weight > truck.max_weight:
        return False, None, 0.0

    for p in placed:
        if boxes_overlap(x, y, z, ori.size, p):
            return False, None, 0.0

    support_id, supporter = supporter_for(item, x, y, z, ori.size, placed)
    if z > 0 and supporter is None:
        return False, None, 0.0

    if supporter is None:
        return True, None, 0.0

    cap = SUPPORT_LIMIT_PER_CM2 * supporter.length * supporter.width
    if supporter.direct_supported_weight + item.weight > cap + 1e-9:
        return False, None, 0.0

    if item.category == "oriented":
        cx, cy = x + l / 2, y + w / 2
        if not (supporter.x <= cx <= supporter.x + supporter.length and supporter.y <= cy <= supporter.y + supporter.width):
            return False, None, 0.0

    return True, support_id, cap


# =========================
# 极点与评分
# =========================
def candidate_points(placed: List[PlacedCargo], truck: TruckType) -> List[Tuple[int, int, int]]:
    pts = {(0, 0, 0)}
    for p in placed:
        x0, y0, z0 = p.x, p.y, p.z
        x1, y1, z1 = p.x + p.length, p.y + p.width, p.z + p.height

        pts.update({
            (x1, y0, z0),
            (x0, y1, z0),
            (x0, y0, z1),
            (x1, y1, z0),
            (x1, y0, z1),
            (x0, y1, z1),
            (x1, y1, z1),
            (x1, y0, 0),
            (x0, y1, 0),
            (x1, 0, z0),
            (0, y1, z0),
        })

    filtered = []
    for pt in pts:
        x, y, z = pt
        if x < 0 or y < 0 or z < 0:
            continue
        if x > truck.length or y > truck.width or z > truck.usable_height:
            continue
        if any(point_inside_box(pt, p) for p in placed):
            continue
        filtered.append(pt)

    return sorted(set(filtered), key=lambda t: (t[2], t[0] + t[1], t[0], t[1]))


def difficulty_rank(item: CargoItem) -> int:
    return {"fragile": 3, "oriented": 2, "standard": 1}[item.category]


def initial_sequence(items: Sequence[CargoItem], rng: random.Random) -> List[CargoItem]:
    seq = list(items)
    seq.sort(
        key=lambda item: (
            -difficulty_rank(item),
            -item.volume,
            -item.weight,
            -item.weight / max(item.volume, 1),
            item.type_id,
            item.item_id,
        )
    )

    block = max(6, len(seq) // 15)
    for start in range(0, len(seq), block):
        end = min(len(seq), start + block)
        chunk = seq[start:end]
        rng.shuffle(chunk)
        seq[start:end] = chunk

    return seq


def estimate_fragmentation(point: Tuple[int, int, int], ori: Orientation, truck: TruckType) -> float:
    x, y, z = point
    l, w, h = ori.size
    gap_x = min(x, max(0, truck.length - (x + l)))
    gap_y = min(y, max(0, truck.width - (y + w)))
    gap_z = min(z, max(0, truck.usable_height - (z + h)))
    return 0.000015 * (gap_x * gap_y + gap_x * gap_z + gap_y * gap_z)


def placement_score(item: CargoItem, ori: Orientation, point: Tuple[int, int, int], truck: TruckType, alpha: float, beta: float) -> float:
    x, y, z = point
    l, w, h = ori.size

    volume_ratio = (l * w * h) / truck.volume
    weight_ratio = item.weight / truck.max_weight

    boundary_bonus = 0.03 if (x == 0 or y == 0 or z == 0) else 0.0
    floor_bonus = 0.015 if z == 0 else 0.0
    footprint_bonus = 0.012 * (l * w) / (truck.length * truck.width)
    difficulty_bonus = {"fragile": 0.035, "oriented": 0.020, "standard": 0.0}[item.category]

    compact_penalty = 0.00035 * (z + 0.30 * x + 0.18 * y)
    frag_penalty = estimate_fragmentation(point, ori, truck)

    return (
        alpha * volume_ratio
        + beta * weight_ratio
        + boundary_bonus
        + floor_bonus
        + footprint_bonus
        + difficulty_bonus
        - compact_penalty
        - frag_penalty
    )


# =========================
# 单车装箱器
# =========================
def pack_single_truck(sequence: Sequence[CargoItem], truck: TruckType, alpha: float = 0.5, beta: float = 0.5) -> PackingResult:
    placed: List[PlacedCargo] = []
    unplaced: List[CargoItem] = []
    current_weight = 0.0
    current_volume = 0

    for item in sequence:
        best = None
        points = candidate_points(placed, truck)

        for point in points:
            for ori in item.allowed_orientations:
                feasible, support_id, cap = can_place(item, ori, point, truck, placed, current_weight)
                if not feasible:
                    continue
                score = placement_score(item, ori, point, truck, alpha, beta)
                if best is None or score > best[0]:
                    best = (score, point, ori, support_id, cap)

        if best is None:
            unplaced.append(item)
            continue

        _, (x, y, z), ori, support_id, cap = best
        placed_item = PlacedCargo(
            item.item_id,
            item.type_id,
            item.category,
            x,
            y,
            z,
            ori.size[0],
            ori.size[1],
            ori.size[2],
            item.weight,
            ori.orient_id,
            ori.rotation,
            support_id,
            cap,
        )
        placed.append(placed_item)
        current_weight += item.weight
        current_volume += item.volume

        if support_id is not None:
            for p in placed:
                if p.item_id == support_id:
                    p.direct_supported_weight += item.weight
                    break

    score = alpha * (current_volume / truck.volume) + beta * (current_weight / truck.max_weight)
    return PackingResult(truck, placed, unplaced, current_volume, current_weight, score)


# =========================
# SA + LNS 评价与邻域
# =========================
def better_result(a: PackingResult, b: PackingResult) -> bool:
    if len(a.placed) != len(b.placed):
        return len(a.placed) > len(b.placed)
    if abs(a.score - b.score) > 1e-12:
        return a.score > b.score
    return a.volume_utilization > b.volume_utilization


def scalar_energy(result: PackingResult) -> float:
    return (
        1000.0 * len(result.placed)
        + 100.0 * result.score
        + 10.0 * result.volume_utilization
        + 5.0 * result.weight_utilization
    )


def make_sa_neighbor(sequence: List[CargoItem], rng: random.Random, current_result: PackingResult) -> List[CargoItem]:
    child = sequence[:]
    n = len(child)
    if n < 2:
        return child

    move = rng.choice(["swap", "insert", "block_reverse", "block_shuffle", "promote_unplaced"])

    if move == "swap":
        i, j = rng.sample(range(n), 2)
        child[i], child[j] = child[j], child[i]

    elif move == "insert":
        i, j = rng.sample(range(n), 2)
        item = child.pop(i)
        child.insert(j, item)

    elif move == "block_reverse":
        l, r = sorted(rng.sample(range(n), 2))
        child[l:r + 1] = reversed(child[l:r + 1])

    elif move == "block_shuffle":
        l = rng.randint(0, max(0, n - 2))
        r = rng.randint(l + 1, min(n - 1, l + 6))
        block = child[l:r + 1]
        rng.shuffle(block)
        child[l:r + 1] = block

    elif move == "promote_unplaced":
        if current_result.unplaced:
            promote = rng.sample(current_result.unplaced, k=min(len(current_result.unplaced), rng.randint(1, 3)))
            promote_ids = {x.item_id for x in promote}
            chosen = [x for x in child if x.item_id in promote_ids]
            others = [x for x in child if x.item_id not in promote_ids]
            pos = rng.randint(0, min(10, len(others)))
            child = others[:pos] + chosen + others[pos:]

    return child


# =========================
# LNS destroy / repair
# =========================
def destroy_sequence(
    sequence: List[CargoItem],
    result: PackingResult,
    rng: random.Random,
    ratio: float = 0.08,
) -> Tuple[List[CargoItem], List[CargoItem]]:
    """
    更快版 destroy：
    移除比例更低，只选少量关键货物
    """
    n = len(sequence)
    remove_count = max(2, min(12, int(n * ratio)))
    item_map = {item.item_id: item for item in sequence}

    candidate_ids = set()

    # 1. 未装入货物优先
    for item in result.unplaced[: max(4, remove_count)]:
        candidate_ids.add(item.item_id)

    # 2. 难装货 / 大件优先
    hard_sorted = sorted(
        sequence,
        key=lambda item: (difficulty_rank(item), item.volume, item.weight),
        reverse=True,
    )
    for item in hard_sorted[: max(remove_count * 2, 8)]:
        candidate_ids.add(item.item_id)

    candidate_list = list(candidate_ids)
    rng.shuffle(candidate_list)

    if len(candidate_list) < remove_count:
        remain = [item.item_id for item in sequence if item.item_id not in candidate_ids]
        rng.shuffle(remain)
        candidate_list.extend(remain[: remove_count - len(candidate_list)])

    remove_ids = set(candidate_list[:remove_count])

    remain_seq = [item for item in sequence if item.item_id not in remove_ids]
    removed_items = [item_map[iid] for iid in remove_ids]

    return remain_seq, removed_items


def candidate_insert_positions(seq_len: int, max_positions: int = 10) -> List[int]:
    positions = list(range(seq_len + 1))
    if len(positions) <= max_positions:
        return positions

    step = max(1, len(positions) // (max_positions - 1))
    sampled = positions[::step]
    if positions[-1] not in sampled:
        sampled.append(positions[-1])

    return sorted(set(sampled[:max_positions] + [positions[-1]]))


def greedy_repair_sequence(
    partial_seq: List[CargoItem],
    removed_items: List[CargoItem],
    truck: TruckType,
    alpha: float,
    beta: float,
    verbose: bool = True,
    max_insert_positions: int = 10,
) -> List[CargoItem]:
    seq = partial_seq[:]
    removed_items = sorted(
        removed_items,
        key=lambda item: (
            -difficulty_rank(item),
            -item.volume,
            -item.weight,
            item.item_id,
        )
    )

    total = len(removed_items)
    for idx, item in enumerate(removed_items, 1):
        if verbose:
            print(f"    [repair] {idx}/{total} -> {item.item_id}", flush=True)

        best_seq = None
        best_result = None

        for pos in candidate_insert_positions(len(seq), max_insert_positions=max_insert_positions):
            trial = seq[:pos] + [item] + seq[pos:]
            result = pack_single_truck(trial, truck, alpha, beta)
            if best_result is None or better_result(result, best_result):
                best_result = result
                best_seq = trial

        seq = best_seq if best_seq is not None else (seq + [item])

    return seq


# =========================
# 主算法：SA + LNS（快版）
# =========================
def sa_lns_optimize_single_truck(
    items: Sequence[CargoItem],
    truck: TruckType,
    alpha: float = 0.5,
    beta: float = 0.5,
    seed: int = RANDOM_SEED,
    init_temp: float = 10.0,
    final_temp: float = 0.12,
    cooling_rate: float = 0.90,
    iters_per_temp: int = 10,
    lns_every: int = 10,
    destroy_ratio: float = 0.08,
    max_insert_positions: int = 10,
) -> PackingResult:
    rng = random.Random(seed + truck.truck_id)

    current_seq = initial_sequence(items, rng)
    current_result = pack_single_truck(current_seq, truck, alpha, beta)

    best_seq = current_seq[:]
    best_result = current_result
    current_energy = scalar_energy(current_result)

    temp = init_temp
    temp_round = 0
    step = 0

    print(
        f"[{truck.name}] SA+LNS开始："
        f" loaded={len(best_result.placed)}"
        f" score={best_result.score:.6f}"
        f" vol={best_result.volume_utilization:.4%}"
        f" wt={best_result.weight_utilization:.4%}",
        flush=True,
    )

    while temp > final_temp:
        temp_round += 1
        print(
            f"[{truck.name}] === 温度轮次 {temp_round} | T={temp:.4f} | "
            f"current_loaded={len(current_result.placed)} | "
            f"best_loaded={len(best_result.placed)} | "
            f"best_score={best_result.score:.6f} ===",
            flush=True,
        )

        # ---------- SA阶段 ----------
        for inner in range(1, iters_per_temp + 1):
            step += 1
            candidate_seq = make_sa_neighbor(current_seq, rng, current_result)
            candidate_result = pack_single_truck(candidate_seq, truck, alpha, beta)

            candidate_energy = scalar_energy(candidate_result)
            delta = candidate_energy - current_energy

            accept = False
            if delta >= 0:
                accept = True
            else:
                prob = math.exp(delta / max(temp, 1e-9))
                if rng.random() < prob:
                    accept = True

            if accept:
                current_seq = candidate_seq
                current_result = candidate_result
                current_energy = candidate_energy

            if better_result(candidate_result, best_result):
                best_seq = candidate_seq[:]
                best_result = candidate_result
                print(
                    f"[{truck.name}] SA更新 "
                    f"round={temp_round} "
                    f"inner={inner}/{iters_per_temp} "
                    f"step={step} "
                    f"T={temp:.4f} "
                    f"loaded={len(best_result.placed)} "
                    f"score={best_result.score:.6f} "
                    f"vol={best_result.volume_utilization:.4%} "
                    f"wt={best_result.weight_utilization:.4%}",
                    flush=True,
                )

        # ---------- LNS阶段 ----------
        if temp_round % lns_every == 0:
            print(f"[{truck.name}] >>> 进入LNS阶段 T={temp:.4f}", flush=True)

            partial_seq, removed_items = destroy_sequence(
                current_seq,
                current_result,
                rng,
                ratio=destroy_ratio,
            )
            print(
                f"[{truck.name}] LNS destroy完成，移除货物数={len(removed_items)}，剩余序列长度={len(partial_seq)}",
                flush=True,
            )

            repaired_seq = greedy_repair_sequence(
                partial_seq,
                removed_items,
                truck,
                alpha,
                beta,
                verbose=True,
                max_insert_positions=max_insert_positions,
            )

            print(f"[{truck.name}] LNS repair完成，开始评估", flush=True)
            repaired_result = pack_single_truck(repaired_seq, truck, alpha, beta)
            print(
                f"[{truck.name}] LNS评估完成 "
                f"loaded={len(repaired_result.placed)} "
                f"score={repaired_result.score:.6f}",
                flush=True,
            )

            repaired_energy = scalar_energy(repaired_result)
            delta = repaired_energy - current_energy

            accept = False
            if delta >= 0:
                accept = True
            else:
                prob = math.exp(delta / max(temp, 1e-9))
                if rng.random() < prob * 0.5:
                    accept = True

            if accept:
                current_seq = repaired_seq
                current_result = repaired_result
                current_energy = repaired_energy
                print(f"[{truck.name}] LNS结果被接受", flush=True)
            else:
                print(f"[{truck.name}] LNS结果未被接受", flush=True)

            if better_result(repaired_result, best_result):
                best_seq = repaired_seq[:]
                best_result = repaired_result
                print(
                    f"[{truck.name}] LNS更新 "
                    f"T={temp:.4f} "
                    f"loaded={len(best_result.placed)} "
                    f"score={best_result.score:.6f} "
                    f"vol={best_result.volume_utilization:.4%} "
                    f"wt={best_result.weight_utilization:.4%}",
                    flush=True,
                )

        temp *= cooling_rate

    print(
        f"[{truck.name}] SA+LNS结束："
        f" best_loaded={len(best_result.placed)}"
        f" best_score={best_result.score:.6f}"
        f" best_vol={best_result.volume_utilization:.4%}"
        f" best_wt={best_result.weight_utilization:.4%}",
        flush=True,
    )

    return best_result


# =========================
# 输出
# =========================
def result_to_dict(result: PackingResult) -> Dict[str, object]:
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


def solve_problem_1_1_sa_lns_fast(alpha: float = 0.5, beta: float = 0.5) -> Dict[int, PackingResult]:
    items = expand_cargo_items(load_cargo_types())
    results = {}

    for truck_id, truck in load_truck_types().items():
        print(f"开始使用 SA + LNS（快版）求解 {truck.name} ...", flush=True)
        results[truck_id] = sa_lns_optimize_single_truck(
            items,
            truck,
            alpha=alpha,
            beta=beta,
            seed=RANDOM_SEED,
            init_temp=10.0,
            final_temp=0.12,
            cooling_rate=0.90,
            iters_per_temp=10,
            lns_every=10,
            destroy_ratio=0.08,
            max_insert_positions=10,
        )
    return results


def save_problem_1_1_sa_lns_fast_results(results: Dict[int, PackingResult], output_dir: Path | None = None) -> None:
    output_dir = output_dir or Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {}
    for truck_id, result in results.items():
        data = result_to_dict(result)
        summary[truck_id] = data["summary"]
        (output_dir / f"problem1_1_sa_lns_fast_truck_{truck_id}_solution.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    (output_dir / "problem1_1_sa_lns_fast_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_problem_1_1_sa_lns_fast_summary(results: Dict[int, PackingResult], elapsed: float) -> None:
    print("问题1.1 单车满载率最大化（SA + LNS 快版）求解结果")
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
    start = time.time()
    results = solve_problem_1_1_sa_lns_fast()
    save_problem_1_1_sa_lns_fast_results(results)
    print_problem_1_1_sa_lns_fast_summary(results, time.time() - start)