# -*- coding: utf-8 -*-
"""
问题1.2 专用增强版：GRASP + Tabu Search + Elite Pool + Path Relinking

相对 baseline / 上一版 GRASP-PR 的主要升级：
1. GRASP：随机化贪心构造（RCL）；
2. Tabu Search：在“货物实例优先级序列”上做禁忌强化；
3. Elite Pool：维护一组高质量且有差异的解；
4. Path Relinking：在 elite 解之间做路径重连；
5. PR 后再做一次 Tabu 精修；
6. 保留 baseline 中的物理约束检查与输出格式。

设计思想：
- 全局解表示为货物实例 token 的优先级序列；
- 给定序列后，调用单车快速装载构造整个多车解；
- 通过“序列扰动 -> 重建装载”的方式搜索更优解；
- 目标采用字典序：先最少车辆数，再更高平均满载率。

说明：
- 这是一版工程化元启发式代码，不保证全局最优；
- 由于 Tabu 会多次重建整解，时间开销会高于 baseline；
- 建议先从中等参数开始跑，再逐步增大迭代次数。
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import time
from collections import Counter, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

from mathorcup_d_common import CARGO_TYPES, TRUCKS, ORIENTATIONS

# =========================================================
# 全局参数
# =========================================================
MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ---- GRASP / Tabu / PR 默认参数 ----
DEFAULT_ITERATIONS = 24
DEFAULT_RCL_SIZE = 6
DEFAULT_PRIORITY_WINDOW = 80
DEFAULT_ELITE_SIZE = 8
DEFAULT_PR_PAIRS = 8

DEFAULT_TABU_ITER = 20
DEFAULT_TABU_TENURE = 7
DEFAULT_TABU_CANDIDATES = 14

MAX_VEHICLES_GUARD = 200

# =========================================================
# 数据结构
# =========================================================
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
    rotation: str
    orientation_id: int
    truck_id: str
    source_token: str
    support_by: Optional[str] = None
    direct_supported_weight: float = 0.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return (self.length * self.width) / 10000.0


@dataclass
class Solution:
    sequence: List[str]
    plans: List["FastTruck"]
    vehicle_count: int
    avg_space_utilization: float
    avg_weight_utilization: float
    avg_fullness_score: float
    total_loaded: int
    score_key: Tuple[float, ...]


# =========================================================
# 工具函数
# =========================================================
def space_volume(sp):
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces):
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (s["z"], -space_volume(s), s["y"], s["x"]))
    return spaces


def local_truck_score(used_volume, used_weight, truck):
    sv = used_volume / (truck.length * truck.width * truck.effective_height)
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def cargo_type_from_token(token: str) -> str:
    return token.split("#", 1)[0]


def build_item_tokens() -> List[str]:
    tokens = []
    for type_id, cargo in CARGO_TYPES.items():
        for i in range(1, cargo.quantity + 1):
            tokens.append(f"{type_id}#{i:04d}")
    return tokens


def build_initial_sequence(strategy: str = "hybrid") -> List[str]:
    tokens_by_type = {
        type_id: [f"{type_id}#{i:04d}" for i in range(1, cargo.quantity + 1)]
        for type_id, cargo in CARGO_TYPES.items()
    }

    if strategy == "fragile_first":
        order = ["G3", "G4", "G5", "G1", "G2"]
    elif strategy == "regular_first":
        order = ["G1", "G2", "G4", "G5", "G3"]
    elif strategy == "direct_first":
        order = ["G4", "G5", "G3", "G1", "G2"]
    else:
        order = ["G3", "G4", "G5", "G1", "G2"]

    seq = []
    for type_id in order:
        arr = tokens_by_type[type_id][:]
        random.shuffle(arr)
        seq.extend(arr)

    for _ in range(max(8, len(seq) // 60)):
        i = random.randint(0, len(seq) - 2)
        j = random.randint(i + 1, min(len(seq) - 1, i + 30))
        if random.random() < 0.5:
            seq[i:j] = reversed(seq[i:j])
        else:
            seq[i], seq[j] = seq[j], seq[i]
    return seq


def sequence_distance(seq_a: List[str], seq_b: List[str], head: int = 80) -> int:
    n = min(head, len(seq_a), len(seq_b))
    return sum(1 for i in range(n) if seq_a[i] != seq_b[i])


# =========================================================
# 货车类（保留 baseline 物理约束）
# =========================================================
class FastTruck:
    def __init__(self, truck, vehicle_id):
        self.truck = truck
        self.vehicle_id = vehicle_id
        self.L = truck.length
        self.W = truck.width
        self.H = truck.effective_height
        self.max_weight = truck.max_weight

        self.spaces = [{
            "x": 0, "y": 0, "z": 0,
            "l": self.L, "w": self.W, "h": self.H,
            "support_item_id": None,
            "support_type_id": None,
            "support_length": self.L,
            "support_width": self.W,
        }]
        self.spaces = sort_spaces(self.spaces)

        self.placed: List[PlacedCargo] = []
        self.placed_map: Dict[str, PlacedCargo] = {}
        self.used_weight = 0.0
        self.used_volume = 0
        self.actual_counts = Counter()
        self.serial_counter = Counter()

    def can_place_with_physics(self, type_id, ori, sp_idx):
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        if l > sp["l"] or w > sp["w"] or h > sp["h"]:
            return False
        if self.used_weight + cargo.weight > self.max_weight:
            return False

        if sp["z"] > 0:
            support_item_id = sp.get("support_item_id")
            support_type_id = sp.get("support_type_id")
            if support_item_id is None or support_item_id not in self.placed_map:
                return False

            support = self.placed_map[support_item_id]
            if l > support.length or w > support.width:
                return False
            if support.category == "fragile":
                return False
            if type_id == "G3" and support_type_id not in ("G1", "G2"):
                return False

            support_limit = CARGO_TYPES[support.type_id].max_support_pressure
            projected_pressure = (support.direct_supported_weight + cargo.weight) / max(1e-9, support.top_area_m2)
            if projected_pressure > support_limit + 1e-9:
                return False

        return True

    def place_item(self, type_id, ori, sp_idx, source_token: str):
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        self.serial_counter[type_id] += 1
        item_id = f"{type_id}_{self.vehicle_id}_{self.serial_counter[type_id]:04d}"

        placed = PlacedCargo(
            item_id=item_id,
            type_id=type_id,
            category=cargo.category,
            x=sp["x"],
            y=sp["y"],
            z=sp["z"],
            length=l,
            width=w,
            height=h,
            weight=cargo.weight,
            rotation=ori.rotation,
            orientation_id=ori.orient_id,
            truck_id=self.vehicle_id,
            source_token=source_token,
            support_by=sp.get("support_item_id"),
        )

        self.placed.append(placed)
        self.placed_map[item_id] = placed
        self.used_weight += cargo.weight
        self.used_volume += l * w * h
        self.actual_counts[type_id] += 1

        support_by = sp.get("support_item_id")
        if support_by is not None and support_by in self.placed_map:
            self.placed_map[support_by].direct_supported_weight += cargo.weight

        right = {
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": sp["w"],
            "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
            "support_length": sp.get("support_length"),
            "support_width": sp.get("support_width"),
        }

        front = {
            "x": sp["x"],
            "y": sp["y"] + w,
            "z": sp["z"],
            "l": l,
            "w": sp["w"] - w,
            "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
            "support_length": sp.get("support_length"),
            "support_width": sp.get("support_width"),
        }

        new_spaces = [right, front]
        if cargo.category != "fragile":
            upper = {
                "x": sp["x"],
                "y": sp["y"],
                "z": sp["z"] + h,
                "l": l,
                "w": w,
                "h": sp["h"] - h,
                "support_item_id": item_id,
                "support_type_id": type_id,
                "support_length": l,
                "support_width": w,
            }
            new_spaces.append(upper)

        self.spaces.pop(sp_idx)
        self.spaces.extend(new_spaces)
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


# =========================================================
# 候选评分
# =========================================================
def eval_candidate(type_id, ori, sp, truck_obj, priority_rank: int, scan_limit: int):
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    low_center_bonus = 1.0 / (1.0 + sp["z"] + 0.35 * h)
    tight_fit_bonus = 1.0 - (
        (sp["l"] - l) * (sp["w"] - w) * max(1, sp["h"] - h) / max(1, sp["l"] * sp["w"] * sp["h"])
    )
    priority_bonus = 1.0 - priority_rank / max(1, scan_limit)
    fragile_bonus = 0.08 if type_id == "G3" and sp["z"] == 0 else 0.0
    upper_penalty = 0.02 if sp["z"] > 0 else 0.0

    score = (
        0.46 * fill_ratio
        + 0.18 * bottom_bonus
        + 0.12 * low_center_bonus
        + 0.10 * tight_fit_bonus
        + 0.08 * priority_bonus
        + fragile_bonus
        - upper_penalty
    )
    return score


# =========================================================
# 给定序列构造整解
# =========================================================
def build_solution_from_sequence(
    truck,
    sequence: List[str],
    rcl_size: int = DEFAULT_RCL_SIZE,
    priority_window: int = DEFAULT_PRIORITY_WINDOW,
    randomize: bool = True,
    seed: Optional[int] = None,
) -> Solution:
    rng = random.Random(seed)
    remaining_tokens = sequence[:]
    plans: List[FastTruck] = []
    vehicle_idx = 1
    total_loaded = 0

    while remaining_tokens:
        if vehicle_idx > MAX_VEHICLES_GUARD:
            raise RuntimeError("车辆数异常增长，请检查构造逻辑。")

        truck_obj = FastTruck(truck, f"{truck.name}_{vehicle_idx:03d}")
        loaded_this_vehicle = 0

        while True:
            scan_tokens = remaining_tokens[:priority_window]
            candidate_pool = []

            for rank, token in enumerate(scan_tokens):
                type_id = cargo_type_from_token(token)
                for sp_idx, _sp in enumerate(truck_obj.spaces[:MAX_SPACES_TO_CHECK]):
                    for ori in ORIENTATIONS[type_id]:
                        if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                            continue
                        val = eval_candidate(type_id, ori, truck_obj.spaces[sp_idx], truck_obj, rank, len(scan_tokens))
                        if val is None:
                            continue
                        candidate_pool.append((val, token, type_id, ori, sp_idx, rank))

            if not candidate_pool:
                break

            candidate_pool.sort(key=lambda x: (-x[0], x[5]))
            rcl = candidate_pool[:max(1, min(rcl_size, len(candidate_pool)))]
            choice = rng.choice(rcl) if randomize and len(rcl) > 1 else rcl[0]
            _, token, type_id, ori, sp_idx, _rank = choice

            truck_obj.place_item(type_id, ori, sp_idx, source_token=token)
            remaining_tokens.remove(token)
            loaded_this_vehicle += 1
            total_loaded += 1

        if loaded_this_vehicle == 0:
            raise RuntimeError(f"{truck.name} 第 {vehicle_idx} 辆车无法装入任何货物。")

        plans.append(truck_obj)
        vehicle_idx += 1

    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)
    avg_fs = 0.0
    singletons = 0
    for p in plans:
        _, _, fs = local_truck_score(p.used_volume, p.used_weight, truck)
        avg_fs += fs
        if sum(p.actual_counts.values()) <= 2:
            singletons += 1
    avg_fs /= len(plans)

    # 字典序目标：
    # 1) 车辆数最少
    # 2) 平均综合满载率更高
    # 3) 空间利用率更高
    # 4) 载重利用率更高
    # 5) 极不饱满车辆更少
    score_key = (
        -len(plans),
        round(avg_fs, 8),
        round(avg_sv, 8),
        round(avg_wv, 8),
        -singletons,
    )

    return Solution(
        sequence=sequence[:],
        plans=plans,
        vehicle_count=len(plans),
        avg_space_utilization=avg_sv,
        avg_weight_utilization=avg_wv,
        avg_fullness_score=avg_fs,
        total_loaded=total_loaded,
        score_key=score_key,
    )


# =========================================================
# 解比较 / elite 池
# =========================================================
def better(sol_a: Solution, sol_b: Optional[Solution]) -> bool:
    if sol_b is None:
        return True
    return sol_a.score_key > sol_b.score_key


def update_elite_pool(elite_pool: List[Solution], candidate: Solution, max_size: int = DEFAULT_ELITE_SIZE):
    if not elite_pool:
        elite_pool.append(candidate)
        return

    for i, ex in enumerate(elite_pool):
        if sequence_distance(candidate.sequence, ex.sequence, head=100) <= 8:
            if better(candidate, ex):
                elite_pool[i] = candidate
            return

    elite_pool.append(candidate)
    elite_pool.sort(key=lambda s: s.score_key, reverse=True)
    if len(elite_pool) > max_size:
        elite_pool.pop()


# =========================================================
# 序列邻域操作
# =========================================================
def move_token(seq: List[str], i: int, j: int) -> List[str]:
    arr = seq[:]
    token = arr.pop(i)
    arr.insert(j, token)
    return arr


def swap_token(seq: List[str], i: int, j: int) -> List[str]:
    arr = seq[:]
    arr[i], arr[j] = arr[j], arr[i]
    return arr


def reverse_block(seq: List[str], i: int, j: int) -> List[str]:
    arr = seq[:]
    arr[i:j] = reversed(arr[i:j])
    return arr


def perturb_sequence(seq: List[str], rng: random.Random) -> List[str]:
    arr = seq[:]
    n = len(arr)
    for _ in range(rng.randint(2, 5)):
        i = rng.randint(0, n - 2)
        j = rng.randint(i + 1, min(n - 1, i + 40))
        p = rng.random()
        if p < 0.4:
            arr = swap_token(arr, i, j)
        elif p < 0.8:
            arr = move_token(arr, j, i)
        else:
            arr = reverse_block(arr, i, j)
    return arr


# =========================================================
# Tabu Search
# =========================================================
def encode_move(move_type: str, i: int, j: int, seq: List[str]) -> Tuple[str, str, str]:
    a = seq[i]
    b = seq[j] if 0 <= j < len(seq) else "NA"
    return move_type, a, b


def generate_tabu_neighbors(seq: List[str], rng: random.Random, max_candidates: int) -> List[Tuple[List[str], Tuple[str, str, str]]]:
    n = len(seq)
    neighbors = []
    seen = set()

    while len(neighbors) < max_candidates:
        i = rng.randint(0, n - 2)
        if rng.random() < 0.7:
            # 更偏向前部，因为前部优先级更影响装车结果
            j = rng.randint(i + 1, min(n - 1, i + rng.randint(8, 45)))
        else:
            j = rng.randint(i + 1, n - 1)

        mode_p = rng.random()
        if mode_p < 0.45:
            move = encode_move("swap", i, j, seq)
            if move in seen:
                continue
            seen.add(move)
            neighbors.append((swap_token(seq, i, j), move))
        elif mode_p < 0.80:
            move = encode_move("move", i, j, seq)
            if move in seen:
                continue
            seen.add(move)
            neighbors.append((move_token(seq, j, i), move))
        else:
            move = encode_move("reverse", i, j, seq)
            if move in seen:
                continue
            seen.add(move)
            neighbors.append((reverse_block(seq, i, j), move))

    return neighbors


def tabu_search(
    truck,
    base_solution: Solution,
    tabu_iter: int = DEFAULT_TABU_ITER,
    tabu_tenure: int = DEFAULT_TABU_TENURE,
    tabu_candidates: int = DEFAULT_TABU_CANDIDATES,
    rcl_size: int = DEFAULT_RCL_SIZE,
    priority_window: int = DEFAULT_PRIORITY_WINDOW,
    seed: Optional[int] = None,
) -> Solution:
    rng = random.Random(seed)

    current = base_solution
    best = base_solution

    tabu_set = set()
    tabu_queue: Deque[Tuple[str, str, str]] = deque()

    for _ in range(tabu_iter):
        neighbors = generate_tabu_neighbors(current.sequence, rng, max_candidates=tabu_candidates)
        best_candidate = None
        best_move = None

        for cand_seq, move in neighbors:
            cand_sol = build_solution_from_sequence(
                truck,
                cand_seq,
                rcl_size=rcl_size,
                priority_window=priority_window,
                randomize=False,
            )

            is_tabu = move in tabu_set
            aspiration = better(cand_sol, best)

            if is_tabu and not aspiration:
                continue

            if best_candidate is None or better(cand_sol, best_candidate):
                best_candidate = cand_sol
                best_move = move

        if best_candidate is None:
            break

        current = best_candidate
        if better(current, best):
            best = current

        if best_move is not None:
            tabu_queue.append(best_move)
            tabu_set.add(best_move)
            while len(tabu_queue) > tabu_tenure:
                old = tabu_queue.popleft()
                if old in tabu_set:
                    tabu_set.remove(old)

    return best


# =========================================================
# Path Relinking
# =========================================================
def path_relink(
    truck,
    source: Solution,
    target: Solution,
    rcl_size: int = DEFAULT_RCL_SIZE,
    priority_window: int = DEFAULT_PRIORITY_WINDOW,
) -> Solution:
    current_seq = source.sequence[:]
    best = source if better(source, target) else target
    n = len(current_seq)

    for pos in range(n):
        if current_seq[pos] == target.sequence[pos]:
            continue

        wanted = target.sequence[pos]
        try:
            j = current_seq.index(wanted, pos + 1)
        except ValueError:
            continue

        token = current_seq.pop(j)
        current_seq.insert(pos, token)

        cand = build_solution_from_sequence(
            truck,
            current_seq,
            rcl_size=rcl_size,
            priority_window=priority_window,
            randomize=False,
        )
        if better(cand, best):
            best = cand

    return best


# =========================================================
# 主求解器
# =========================================================
def solve_one_truck_type_gttp(
    truck_name: str,
    iterations: int = DEFAULT_ITERATIONS,
    rcl_size: int = DEFAULT_RCL_SIZE,
    priority_window: int = DEFAULT_PRIORITY_WINDOW,
    elite_size: int = DEFAULT_ELITE_SIZE,
    pr_pairs: int = DEFAULT_PR_PAIRS,
    tabu_iter: int = DEFAULT_TABU_ITER,
    tabu_tenure: int = DEFAULT_TABU_TENURE,
    tabu_candidates: int = DEFAULT_TABU_CANDIDATES,
    seed: int = RANDOM_SEED,
    verbose: bool = True,
):
    truck = TRUCKS[truck_name]
    rng = random.Random(seed)

    strategies = ["hybrid", "fragile_first", "regular_first", "direct_first"]
    best_solution = None
    elite_pool: List[Solution] = []

    # 初始多种构造种子
    for idx, st in enumerate(strategies):
        seq = build_initial_sequence(st)
        sol = build_solution_from_sequence(
            truck,
            seq,
            rcl_size=rcl_size,
            priority_window=priority_window,
            randomize=False,
            seed=seed + idx,
        )
        if better(sol, best_solution):
            best_solution = sol
        update_elite_pool(elite_pool, sol, max_size=elite_size)

    assert best_solution is not None

    if verbose:
        print(
            f"[{truck_name}] initial：车辆数={best_solution.vehicle_count}, "
            f"avg_fs={best_solution.avg_fullness_score:.4f}, "
            f"avg_sv={best_solution.avg_space_utilization:.4f}, "
            f"avg_wv={best_solution.avg_weight_utilization:.4f}"
        )

    # ===== 主循环：GRASP + Tabu =====
    for it in range(1, iterations + 1):
        if it <= len(strategies):
            base_seq = build_initial_sequence(strategies[(it - 1) % len(strategies)])
        else:
            anchor = elite_pool[rng.randint(0, len(elite_pool) - 1)] if elite_pool else best_solution
            base_seq = perturb_sequence(anchor.sequence, rng)

        constructed = build_solution_from_sequence(
            truck,
            base_seq,
            rcl_size=rcl_size,
            priority_window=priority_window,
            randomize=True,
            seed=seed + 1000 * it,
        )

        improved = tabu_search(
            truck,
            constructed,
            tabu_iter=tabu_iter,
            tabu_tenure=tabu_tenure,
            tabu_candidates=tabu_candidates,
            rcl_size=rcl_size,
            priority_window=priority_window,
            seed=seed + 2000 * it,
        )

        if better(improved, best_solution):
            best_solution = improved
        update_elite_pool(elite_pool, improved, max_size=elite_size)

        if verbose:
            print(
                f"[{truck_name}] iter={it:03d} "
                f"构造车数={constructed.vehicle_count} -> tabu车数={improved.vehicle_count} "
                f"avg_fs={improved.avg_fullness_score:.4f} elite={len(elite_pool)} "
                f"best_vehicle={best_solution.vehicle_count}"
            )

    # ===== 路径重连 + 再 Tabu =====
    if len(elite_pool) >= 2 and pr_pairs > 0:
        tried = 0
        for i in range(len(elite_pool)):
            for j in range(i + 1, len(elite_pool)):
                pr_sol = path_relink(
                    truck,
                    elite_pool[i],
                    elite_pool[j],
                    rcl_size=rcl_size,
                    priority_window=priority_window,
                )
                pr_refined = tabu_search(
                    truck,
                    pr_sol,
                    tabu_iter=max(6, tabu_iter // 2),
                    tabu_tenure=tabu_tenure,
                    tabu_candidates=max(8, tabu_candidates // 2),
                    rcl_size=rcl_size,
                    priority_window=priority_window,
                    seed=seed + 30000 + tried,
                )
                if better(pr_refined, best_solution):
                    best_solution = pr_refined
                update_elite_pool(elite_pool, pr_refined, max_size=elite_size)
                tried += 1

                if verbose:
                    print(
                        f"[{truck_name}] PR={tried:02d} 车数={pr_refined.vehicle_count} "
                        f"avg_fs={pr_refined.avg_fullness_score:.4f} best_vehicle={best_solution.vehicle_count}"
                    )

                if tried >= pr_pairs:
                    break
            if tried >= pr_pairs:
                break

    total_cost = best_solution.vehicle_count * truck.cost
    summary = {
        "truck": truck_name,
        "vehicle_count": best_solution.vehicle_count,
        "total_cost": total_cost,
        "avg_space_utilization": round(best_solution.avg_space_utilization, 6),
        "avg_weight_utilization": round(best_solution.avg_weight_utilization, 6),
        "avg_fullness_score": round(best_solution.avg_fullness_score, 6),
        "all_loaded": best_solution.total_loaded == sum(v.quantity for v in CARGO_TYPES.values()),
    }
    return best_solution, summary


# =========================================================
# 输出
# =========================================================
def write_vehicle_summary_csv(path, plans, truck):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_weight_kg", "loaded_volume_cm3"
        ])
        for plan in plans:
            sv, wv, fs = local_truck_score(plan.used_volume, plan.used_weight, truck)
            w.writerow([
                plan.vehicle_id,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                dict(plan.actual_counts),
                round(plan.used_weight, 3),
                plan.used_volume,
            ])


def write_items_csv(path, placed):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id",
            "source_token", "support_by", "direct_supported_weight"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id,
                p.source_token,
                p.support_by or "",
                round(p.direct_supported_weight, 6),
            ])


def solve_for_truck(
    truck_name,
    outdir,
    iterations,
    rcl_size,
    priority_window,
    elite_size,
    pr_pairs,
    tabu_iter,
    tabu_tenure,
    tabu_candidates,
    seed,
):
    truck = TRUCKS[truck_name]
    best_solution, summary = solve_one_truck_type_gttp(
        truck_name=truck_name,
        iterations=iterations,
        rcl_size=rcl_size,
        priority_window=priority_window,
        elite_size=elite_size,
        pr_pairs=pr_pairs,
        tabu_iter=tabu_iter,
        tabu_tenure=tabu_tenure,
        tabu_candidates=tabu_candidates,
        seed=seed,
        verbose=True,
    )

    truck_dir = os.path.join(outdir, truck_name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), best_solution.plans, truck)
    for plan in best_solution.plans:
        write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan.placed)
    summary["output_dir"] = truck_dir
    return summary


# =========================================================
# CLI
# =========================================================
def parse_args():
    parser = argparse.ArgumentParser(description="问题1.2 专用：GRASP + Tabu + Path Relinking")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2_GRASP_TABU_PR", help="输出目录")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--rcl-size", type=int, default=DEFAULT_RCL_SIZE)
    parser.add_argument("--priority-window", type=int, default=DEFAULT_PRIORITY_WINDOW)
    parser.add_argument("--elite-size", type=int, default=DEFAULT_ELITE_SIZE)
    parser.add_argument("--pr-pairs", type=int, default=DEFAULT_PR_PAIRS)
    parser.add_argument("--tabu-iter", type=int, default=DEFAULT_TABU_ITER)
    parser.add_argument("--tabu-tenure", type=int, default=DEFAULT_TABU_TENURE)
    parser.add_argument("--tabu-candidates", type=int, default=DEFAULT_TABU_CANDIDATES)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


# =========================================================
# 主程序
# =========================================================
def main():
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    start_time = time.time()
    for truck_name in truck_list:
        print(f"===== {truck_name} =====")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        summary = solve_for_truck(
            truck_name=truck_name,
            outdir=outdir,
            iterations=args.iterations,
            rcl_size=args.rcl_size,
            priority_window=args.priority_window,
            elite_size=args.elite_size,
            pr_pairs=args.pr_pairs,
            tabu_iter=args.tabu_iter,
            tabu_tenure=args.tabu_tenure,
            tabu_candidates=args.tabu_candidates,
            seed=args.seed,
        )
        print(summary)
        print()

    print(f"总耗时：{time.time() - start_time:.2f} 秒")


if __name__ == "__main__":
    main()
