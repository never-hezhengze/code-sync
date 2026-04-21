# -*- coding: utf-8 -*-
"""
问题1.2 增强版：随机化贪心构造 + 局部搜索 + Elite池 + 路径重连

相对 p12_baseline.py 的主要增强：
1. 随机化贪心构造（GRASP 风格 RCL）；
2. 全局解表示为“货物实例优先级序列”，便于后续局部搜索；
3. 局部搜索：交换 / 插入 / 小块扰动；
4. Elite 池：保存多样化高质量解；
5. 路径重连：在 elite 解之间做强化搜索；
6. 仍复用 baseline 的物理约束检查与结果输出格式。

说明：
- 该版本仍属于工程化元启发式，不保证全局最优；
- 目标采用字典序：先最少车辆数，再更高装载质量；
- 代码尽量保持与 mathorcup_d_common / baseline 风格兼容。
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import time
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from mathorcup_d_common import CARGO_TYPES, TRUCKS, ORIENTATIONS

# =========================================================
# 参数
# =========================================================
MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ---- GRASP / LS / PR 参数 ----
DEFAULT_ITERATIONS = 36           # GRASP 主迭代次数
DEFAULT_RCL_SIZE = 6              # 限制候选列表大小
DEFAULT_PRIORITY_WINDOW = 80      # 每次仅扫描序列前若干个尚未使用的货物实例
DEFAULT_LS_ITER = 18              # 每轮局部搜索步数
DEFAULT_ELITE_SIZE = 8            # elite 池大小
DEFAULT_PR_PAIRS = 8              # 路径重连对数上限
MAX_VEHICLES_GUARD = 200          # 防止异常死循环


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

    # 基础顺序：难装/方向受限/易碎优先，给后续局部搜索留空间
    if strategy == "fragile_first":
        order = ["G3", "G4", "G5", "G1", "G2"]
    elif strategy == "regular_first":
        order = ["G1", "G2", "G4", "G5", "G3"]
    else:
        order = ["G3", "G4", "G5", "G1", "G2"]

    seq = []
    for type_id in order:
        arr = tokens_by_type[type_id][:]
        if strategy == "hybrid":
            random.shuffle(arr)
        seq.extend(arr)

    # 再做少量分块扰动，避免完全按类型团簇
    if strategy == "hybrid":
        for _ in range(max(5, len(seq) // 80)):
            i = random.randint(0, len(seq) - 2)
            j = random.randint(i + 1, min(len(seq) - 1, i + 20))
            seq[i:j] = reversed(seq[i:j])

    return seq


def sequence_signature(sequence: List[str], block: int = 24) -> Tuple[str, ...]:
    # 用前若干位置的类型序列作为轻量特征，避免 elite 池全是同构解
    head = sequence[:block]
    return tuple(cargo_type_from_token(x) for x in head)


# =========================================================
# 货车类（保留 baseline 的物理约束逻辑）
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
    fragile_bonus = 0.06 if type_id == "G3" and sp["z"] == 0 else 0.0
    support_penalty = 0.02 if sp["z"] > 0 else 0.0
    priority_bonus = 1.0 - priority_rank / max(1, scan_limit)

    score = (
        0.46 * fill_ratio
        + 0.18 * bottom_bonus
        + 0.12 * low_center_bonus
        + 0.10 * tight_fit_bonus
        + 0.08 * priority_bonus
        + fragile_bonus
        - support_penalty
    )
    return score


# =========================================================
# 随机化构造：基于全局序列构建整解
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
            # 理论上不该发生；若发生，说明剩余货物即使新车也无法装入
            raise RuntimeError(f"{truck.name} 第 {vehicle_idx} 辆车无法装入任何货物。")

        plans.append(truck_obj)
        vehicle_idx += 1

    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)
    avg_fs = 0.0
    for p in plans:
        _, _, fs = local_truck_score(p.used_volume, p.used_weight, truck)
        avg_fs += fs
    avg_fs /= len(plans)

    # 字典序目标：车辆数最少 > 满载率高 > 前车更满(通过平均满载率体现)
    score_key = (
        -len(plans),
        round(avg_fs, 8),
        round(avg_sv, 8),
        round(avg_wv, 8),
        -sum(1 for p in plans if sum(p.actual_counts.values()) <= 2),
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
# 解比较与 elite 池
# =========================================================
def better(sol_a: Solution, sol_b: Optional[Solution]) -> bool:
    if sol_b is None:
        return True
    return sol_a.score_key > sol_b.score_key


def sequence_distance(seq_a: List[str], seq_b: List[str], head: int = 60) -> int:
    n = min(head, len(seq_a), len(seq_b))
    return sum(1 for i in range(n) if seq_a[i] != seq_b[i])


def update_elite_pool(elite_pool: List[Solution], candidate: Solution, max_size: int = DEFAULT_ELITE_SIZE):
    if not elite_pool:
        elite_pool.append(candidate)
        return

    # 多样性过滤：太像且不更优则不收
    for i, ex in enumerate(elite_pool):
        if sequence_distance(candidate.sequence, ex.sequence, head=80) <= 6:
            if better(candidate, ex):
                elite_pool[i] = candidate
            return

    elite_pool.append(candidate)
    elite_pool.sort(key=lambda s: s.score_key, reverse=True)
    if len(elite_pool) > max_size:
        elite_pool.pop()


# =========================================================
# 局部搜索（在优先级序列上操作）
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


def local_search(
    truck,
    base_solution: Solution,
    ls_iter: int = DEFAULT_LS_ITER,
    rcl_size: int = DEFAULT_RCL_SIZE,
    priority_window: int = DEFAULT_PRIORITY_WINDOW,
    seed: Optional[int] = None,
) -> Solution:
    rng = random.Random(seed)
    best = base_solution
    current = base_solution
    n = len(current.sequence)

    for step in range(ls_iter):
        mode = step % 3
        cand_seq = current.sequence[:]

        if mode == 0:
            # 让前部关键货物顺序更容易变化
            i = rng.randint(0, min(n - 2, max(10, n // 5)))
            j = rng.randint(i + 1, min(n - 1, i + 25))
            cand_seq = move_token(cand_seq, j, i)
        elif mode == 1:
            i = rng.randint(0, min(n - 2, max(15, n // 4)))
            j = rng.randint(i + 1, min(n - 1, i + 35))
            cand_seq = swap_token(cand_seq, i, j)
        else:
            i = rng.randint(0, max(1, n - 8))
            j = min(n, i + rng.randint(3, 10))
            cand_seq = reverse_block(cand_seq, i, j)

        cand_sol = build_solution_from_sequence(
            truck,
            cand_seq,
            rcl_size=rcl_size,
            priority_window=priority_window,
            randomize=False,
        )

        if better(cand_sol, current):
            current = cand_sol
            if better(current, best):
                best = current
        else:
            # 轻微接受非改进步，帮助跳局部最优
            if rng.random() < 0.12:
                current = cand_sol

    return best


# =========================================================
# 路径重连
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

    # 逐步把 current 序列向 target 序列对齐
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

        # 不必每一步都重建，可隔几步强化一次；这里为了稳妥直接重建
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
def solve_one_truck_type_enhanced(
    truck_name: str,
    iterations: int = DEFAULT_ITERATIONS,
    rcl_size: int = DEFAULT_RCL_SIZE,
    priority_window: int = DEFAULT_PRIORITY_WINDOW,
    ls_iter: int = DEFAULT_LS_ITER,
    elite_size: int = DEFAULT_ELITE_SIZE,
    pr_pairs: int = DEFAULT_PR_PAIRS,
    seed: int = RANDOM_SEED,
    verbose: bool = True,
):
    truck = TRUCKS[truck_name]
    rng = random.Random(seed)

    base_seq = build_initial_sequence("hybrid")
    base_sol = build_solution_from_sequence(
        truck,
        base_seq,
        rcl_size=rcl_size,
        priority_window=priority_window,
        randomize=False,
    )

    best_solution = base_sol
    elite_pool: List[Solution] = []
    update_elite_pool(elite_pool, base_sol, max_size=elite_size)

    if verbose:
        print(f"[{truck_name}] baseline：车辆数={base_sol.vehicle_count}, avg_fs={base_sol.avg_fullness_score:.4f}, avg_sv={base_sol.avg_space_utilization:.4f}, avg_wv={base_sol.avg_weight_utilization:.4f}")

    for it in range(1, iterations + 1):
        # ---- 随机化构造 ----
        if it == 1:
            seq = build_initial_sequence("hybrid")
        else:
            seq = best_solution.sequence[:]
            # 对当前好解做扰动，生成新的构造顺序
            for _ in range(rng.randint(2, 5)):
                i = rng.randint(0, len(seq) - 2)
                j = rng.randint(i + 1, min(len(seq) - 1, i + 40))
                if rng.random() < 0.5:
                    seq = swap_token(seq, i, j)
                else:
                    seq = move_token(seq, j, i)

        constructed = build_solution_from_sequence(
            truck,
            seq,
            rcl_size=rcl_size,
            priority_window=priority_window,
            randomize=True,
            seed=seed + 1000 * it,
        )

        # ---- 局部搜索 ----
        improved = local_search(
            truck,
            constructed,
            ls_iter=ls_iter,
            rcl_size=rcl_size,
            priority_window=priority_window,
            seed=seed + 2000 * it,
        )

        if better(improved, best_solution):
            best_solution = improved

        update_elite_pool(elite_pool, improved, max_size=elite_size)

        if verbose:
            print(
                f"[{truck_name}] iter={it:03d} 车辆数={improved.vehicle_count} "
                f"avg_fs={improved.avg_fullness_score:.4f} avg_sv={improved.avg_space_utilization:.4f} "
                f"elite={len(elite_pool)} best_vehicle={best_solution.vehicle_count}"
            )

    # ---- 路径重连 ----
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
                if better(pr_sol, best_solution):
                    best_solution = pr_sol
                update_elite_pool(elite_pool, pr_sol, max_size=elite_size)
                tried += 1
                if verbose:
                    print(
                        f"[{truck_name}] PR {tried:02d}：车辆数={pr_sol.vehicle_count} "
                        f"avg_fs={pr_sol.avg_fullness_score:.4f} best_vehicle={best_solution.vehicle_count}"
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
    ls_iter,
    elite_size,
    pr_pairs,
    seed,
):
    truck = TRUCKS[truck_name]
    best_solution, summary = solve_one_truck_type_enhanced(
        truck_name=truck_name,
        iterations=iterations,
        rcl_size=rcl_size,
        priority_window=priority_window,
        ls_iter=ls_iter,
        elite_size=elite_size,
        pr_pairs=pr_pairs,
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
    parser = argparse.ArgumentParser(description="问题1.2 GRASP + Local Search + Elite Pool + Path Relinking")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2_GRASP_PR", help="输出目录")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--rcl-size", type=int, default=DEFAULT_RCL_SIZE)
    parser.add_argument("--priority-window", type=int, default=DEFAULT_PRIORITY_WINDOW)
    parser.add_argument("--ls-iter", type=int, default=DEFAULT_LS_ITER)
    parser.add_argument("--elite-size", type=int, default=DEFAULT_ELITE_SIZE)
    parser.add_argument("--pr-pairs", type=int, default=DEFAULT_PR_PAIRS)
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
            ls_iter=args.ls_iter,
            elite_size=args.elite_size,
            pr_pairs=args.pr_pairs,
            seed=args.seed,
        )
        print(summary)
        print()

    print(f"总耗时：{time.time() - start_time:.2f} 秒")


if __name__ == "__main__":
    main()
