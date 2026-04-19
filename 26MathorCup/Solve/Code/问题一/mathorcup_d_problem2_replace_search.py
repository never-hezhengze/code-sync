#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（重构版）
基准解 + 局部车型替换 搜索算法

思路：
1. 先分别求全车型1、全车型2的单车型解；
2. 选取一个基准解：
   - min_vehicle: 先选车辆数更少者；若相同，选成本更低者
   - min_cost:    先选成本更低者；若相同，选车辆数更少者
3. 在当前解上做局部替换：
   - 抽取若干辆车（通常优先抽利用率低的尾车）
   - 汇总其所装货物
   - 尝试用其他车型组合重装
   - 若目标改进，则接受
4. 输出车辆汇总和每车装箱明细

特点：
- 完全不使用原问题2中的枚举车队结构 / SA / GA / LNS
- 复用问题1.2快速装车思想
- 真正做“车队结构”优化，而不是“每轮二选一”
"""

from __future__ import annotations

import argparse
import csv
import os
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from itertools import count
from typing import Dict, List, Tuple, Optional

from mathorcup_d_p12_stable_solver import (
    CARGO_TYPES,
    TRUCKS,
    ORIENTATIONS,
    Truck,
    Orientation,
)

# =========================================================
# 参数区
# =========================================================
MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000
RANDOM_SEED = 2026
TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]

random.seed(RANDOM_SEED)
_PLAN_ID_GEN = count(1)


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
    orientation_id: int
    rotation: str
    truck_id: str

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass
class VehicleResult:
    vehicle_id: str
    truck_name: str
    placed: List[PlacedCargo]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int
    strategy: str

    @property
    def item_count(self) -> int:
        return sum(self.actual_counts.values())

    @property
    def truck(self) -> Truck:
        return TRUCKS[self.truck_name]


# =========================================================
# 基础工具
# =========================================================
def space_volume(sp: Dict[str, int]) -> int:
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces: List[Dict[str, int]]) -> List[Dict[str, int]]:
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (-space_volume(s), s["z"], s["y"], s["x"]))
    return spaces


def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / truck.effective_volume
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def solution_stats(plans: List[VehicleResult]) -> Dict[str, object]:
    n1 = sum(1 for p in plans if p.truck_name == "车型1")
    n2 = sum(1 for p in plans if p.truck_name == "车型2")
    total_cost = n1 * TRUCKS["车型1"].cost + n2 * TRUCKS["车型2"].cost
    used_volume = sum(p.used_volume for p in plans)
    used_weight = sum(p.used_weight for p in plans)
    total_volume = sum(TRUCKS[p.truck_name].effective_volume for p in plans)
    total_weight_cap = sum(TRUCKS[p.truck_name].max_weight for p in plans)

    return {
        "fleet_structure": {"车型1": n1, "车型2": n2},
        "vehicle_count": len(plans),
        "total_cost": round(total_cost, 2),
        "avg_space_utilization": round(used_volume / max(1, total_volume), 6),
        "avg_weight_utilization": round(used_weight / max(1.0, total_weight_cap), 6),
        "all_loaded": True,
    }


def is_better_solution(a: List[VehicleResult], b: List[VehicleResult], objective: str) -> bool:
    """
    a 是否优于 b
    """
    sa = solution_stats(a)
    sb = solution_stats(b)

    if objective == "min_vehicle":
        key_a = (sa["vehicle_count"], sa["total_cost"], -sa["avg_space_utilization"])
        key_b = (sb["vehicle_count"], sb["total_cost"], -sb["avg_space_utilization"])
        return key_a < key_b
    else:
        key_a = (sa["total_cost"], sa["vehicle_count"], -sa["avg_space_utilization"])
        key_b = (sb["total_cost"], sb["vehicle_count"], -sb["avg_space_utilization"])
        return key_a < key_b


def vehicle_fill_score(vp: VehicleResult) -> float:
    sv, wv, fs = truck_score(TRUCKS[vp.truck_name], vp.used_volume, vp.used_weight)
    return fs


def count_to_zero(quota: Dict[str, int]) -> bool:
    return all(quota[t] == 0 for t in TYPE_ORDER_ALL)


# =========================================================
# 快速装车器
# =========================================================
class FastTruck:
    def __init__(self, truck: Truck, vehicle_id: str):
        self.truck = truck
        self.vehicle_id = vehicle_id
        self.spaces = [{
            "x": 0, "y": 0, "z": 0,
            "l": truck.length,
            "w": truck.width,
            "h": truck.effective_height
        }]
        self.spaces = sort_spaces(self.spaces)
        self.placed: List[PlacedCargo] = []
        self.used_weight = 0.0
        self.used_volume = 0
        self.actual_counts = Counter()
        self.serial_counter = Counter()

    def place_item(self, type_id: str, ori: Orientation, sp_idx: int) -> None:
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        self.serial_counter[type_id] += 1
        item_id = f"{type_id}_{self.vehicle_id}_{self.serial_counter[type_id]:04d}"

        pc = PlacedCargo(
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
            orientation_id=ori.orient_id,
            rotation=ori.rotation,
            truck_id=self.vehicle_id,
        )
        self.placed.append(pc)
        self.used_weight += cargo.weight
        self.used_volume += pc.volume
        self.actual_counts[type_id] += 1

        right = {
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": w,
            "h": h
        }
        front = {
            "x": sp["x"],
            "y": sp["y"] + w,
            "z": sp["z"],
            "l": sp["l"],
            "w": sp["w"] - w,
            "h": h
        }
        upper = {
            "x": sp["x"],
            "y": sp["y"],
            "z": sp["z"] + h,
            "l": sp["l"],
            "w": sp["w"],
            "h": sp["h"] - h
        }

        self.spaces.pop(sp_idx)
        self.spaces.extend([right, front, upper])
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


# =========================================================
# 单车装载策略
# =========================================================
def build_type_order(strategy: str) -> List[str]:
    std_types = ["G1", "G2"]
    dir_types = ["G4", "G5"]

    if strategy == "std_first":
        return std_types + dir_types + ["G3"]
    elif strategy == "dir_first":
        return dir_types + std_types + ["G3"]
    elif strategy == "g3_first":
        return ["G3"] + dir_types + std_types
    elif strategy == "std_g3_dir":
        return std_types + ["G3"] + dir_types
    elif strategy == "dir_g3_std":
        return dir_types + ["G3"] + std_types
    else:
        arr = ["G1", "G2", "G4", "G5", "G3"]
        random.shuffle(arr)
        return arr


def eval_candidate(type_id: str, ori: Orientation, sp: Dict[str, int], remaining: Dict[str, int], truck_obj: FastTruck) -> Optional[float]:
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if remaining[type_id] <= 0:
        return None
    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.truck.max_weight:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    fragile_bonus = 0.08 if type_id == "G3" else 0.0

    return 0.62 * fill_ratio + 0.23 * bottom_bonus + 0.15 * remain_bonus + fragile_bonus


def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], type_order: List[str]) -> bool:
    best = None  # (score, type_id, ori, sp_idx)

    for sp_idx, sp in enumerate(truck_obj.spaces[:MAX_SPACES_TO_CHECK]):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                val = eval_candidate(type_id, ori, sp, remaining, truck_obj)
                if val is None:
                    continue
                if best is None or val > best[0]:
                    best = (val, type_id, ori, sp_idx)

    if best is None:
        return False

    _, type_id, ori, sp_idx = best
    truck_obj.place_item(type_id, ori, sp_idx)
    remaining[type_id] -= 1
    return True


def load_one_truck_with_strategy(truck: Truck, remaining: Dict[str, int], strategy: str) -> VehicleResult:
    plan_id = next(_PLAN_ID_GEN)
    vehicle_id = f"{truck.name}_{plan_id:04d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)

    while True:
        ok = place_one_best(truck_obj, remaining, type_order)
        if not ok:
            break

    return VehicleResult(
        vehicle_id=vehicle_id,
        truck_name=truck.name,
        placed=truck_obj.placed,
        actual_counts=dict(truck_obj.actual_counts),
        used_weight=truck_obj.used_weight,
        used_volume=truck_obj.used_volume,
        strategy=strategy,
    )


def build_one_vehicle_best(truck: Truck, remaining: Dict[str, int]) -> VehicleResult:
    strategies = [
        "std_first",
        "dir_first",
        "mixed",
        "g3_first",
        "std_g3_dir",
        "dir_g3_std",
    ]
    best_plan = None
    best_key = None

    for st in strategies:
        rem_copy = deepcopy(remaining)
        plan = load_one_truck_with_strategy(truck, rem_copy, st)
        if plan.item_count == 0:
            continue

        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
        key = (
            plan.item_count,
            round(fs, 6),
            plan.used_volume,
            -plan.used_weight,
        )
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key

    if best_plan is None:
        raise RuntimeError(f"{truck.name} 无法装入任何货物。")
    return best_plan


# =========================================================
# 单车型基准解
# =========================================================
def solve_single_type(truck_name: str) -> List[VehicleResult]:
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER_ALL}
    plans: List[VehicleResult] = []
    truck = TRUCKS[truck_name]

    while not count_to_zero(remaining):
        plan = build_one_vehicle_best(truck, remaining)
        if plan.item_count == 0:
            raise RuntimeError(f"{truck_name} 单车型求解失败：出现空车。")

        for t, c in plan.actual_counts.items():
            remaining[t] -= c
            if remaining[t] < 0:
                raise RuntimeError(f"{truck_name} 扣减后 {t} 为负数。")

        plans.append(plan)

        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
        print(
            f"[基准-{truck_name}] {plan.vehicle_id}："
            f"装入 {plan.item_count} 件，"
            f"空间利用率={sv:.4f}，载重利用率={wv:.4f}，fullness_score={fs:.4f}，"
            f"剩余={sum(remaining.values())}"
        )

    return plans


def choose_baseline(plans1: List[VehicleResult], plans2: List[VehicleResult], objective: str) -> List[VehicleResult]:
    return plans1 if is_better_solution(plans1, plans2, objective) else plans2


# =========================================================
# 局部换车：将若干辆车上的货重新打包到新车队
# =========================================================
def collect_quota_from_plans(plans: List[VehicleResult]) -> Dict[str, int]:
    quota = {t: 0 for t in TYPE_ORDER_ALL}
    for vp in plans:
        for t, c in vp.actual_counts.items():
            quota[t] += c
    return quota


def repack_quota_into_fleet(quota: Dict[str, int], fleet_types: List[str]) -> Optional[List[VehicleResult]]:
    """
    将 quota 用给定 fleet_types 重装。
    若能全部装完，则返回对应新 plans；否则返回 None。
    """
    remaining = deepcopy(quota)
    new_plans: List[VehicleResult] = []

    for truck_name in fleet_types:
        if count_to_zero(remaining):
            break
        plan = build_one_vehicle_best(TRUCKS[truck_name], remaining)
        if plan.item_count == 0:
            break
        for t, c in plan.actual_counts.items():
            remaining[t] -= c
            if remaining[t] < 0:
                return None
        new_plans.append(plan)

    if count_to_zero(remaining):
        return new_plans
    return None


def replacement_patterns(objective: str) -> List[Tuple[Tuple[str, ...], Tuple[str, ...]]]:
    """
    (原组合, 新组合)
    这里只给最有实际意义的几种局部替换模式。
    """
    if objective == "min_vehicle":
        return [
            (("车型2",), ("车型2",)),              # 仅重装，不变车种，修尾车
            (("车型1", "车型1"), ("车型2",)),      # 2辆小车 -> 1辆大车
            (("车型1", "车型1", "车型1"), ("车型2", "车型1")),  # 3小 -> 1大1小（降1辆）
            (("车型2", "车型1"), ("车型2",)),      # 大+小 -> 大（降1辆）
        ]
    else:
        return [
            (("车型2",), ("车型1", "车型1")),      # 1大 -> 2小，成本 700 -> 900（一般不会优，但允许验证）
            (("车型2",), ("车型1",)),              # 1大 -> 1小，只有在局部货不多时才可能
            (("车型2", "车型2"), ("车型1", "车型1", "车型1")),  # 2大 -> 3小，1400 -> 1350
            (("车型2", "车型2"), ("车型1", "车型1", "车型1", "车型1")),  # 2大 -> 4小，1400 -> 1800，多数不优但留作探索
            (("车型2", "车型1"), ("车型1", "车型1")),  # 1大1小 -> 2小
            (("车型1", "车型1"), ("车型2",)),      # 2小 -> 1大，有时成本不降但利于结构调整
        ]


def find_candidate_groups(plans: List[VehicleResult], source_pattern: Tuple[str, ...], max_groups: int = 8) -> List[List[int]]:
    """
    从当前解中找到若干可尝试替换的车辆组。
    按利用率低的车优先。
    """
    pattern_counter = Counter(source_pattern)
    indices_by_type = {
        "车型1": [i for i, p in enumerate(plans) if p.truck_name == "车型1"],
        "车型2": [i for i, p in enumerate(plans) if p.truck_name == "车型2"],
    }

    for k in indices_by_type:
        indices_by_type[k].sort(key=lambda i: vehicle_fill_score(plans[i]))  # 低利用率优先

    results: List[List[int]] = []

    if len(pattern_counter) == 1:
        t = next(iter(pattern_counter))
        need = pattern_counter[t]
        arr = indices_by_type[t]
        for start in range(0, max(0, len(arr) - need + 1)):
            group = arr[start:start + need]
            if len(group) == need:
                results.append(group)
                if len(results) >= max_groups:
                    break
        return results

    # 混合 pattern 的简单组合
    arr1 = indices_by_type["车型1"]
    arr2 = indices_by_type["车型2"]
    need1 = pattern_counter["车型1"]
    need2 = pattern_counter["车型2"]

    cands1 = [arr1[i:i + need1] for i in range(0, max(0, len(arr1) - need1 + 1))] if need1 > 0 else [[]]
    cands2 = [arr2[i:i + need2] for i in range(0, max(0, len(arr2) - need2 + 1))] if need2 > 0 else [[]]

    for g1 in cands1[:max_groups]:
        for g2 in cands2[:max_groups]:
            group = g1 + g2
            if len(group) == need1 + need2 and len(set(group)) == len(group):
                results.append(sorted(group))
                if len(results) >= max_groups:
                    return results

    return results


def try_one_replacement(
    plans: List[VehicleResult],
    source_group_idx: List[int],
    target_pattern: Tuple[str, ...],
) -> Optional[List[VehicleResult]]:
    source_plans = [plans[i] for i in source_group_idx]
    quota = collect_quota_from_plans(source_plans)
    new_local = repack_quota_into_fleet(quota, list(target_pattern))
    if new_local is None:
        return None

    keep = [p for i, p in enumerate(plans) if i not in set(source_group_idx)]
    candidate = keep + new_local
    return candidate


def local_replacement_search(initial_plans: List[VehicleResult], objective: str, max_rounds: int = 20) -> List[VehicleResult]:
    current = initial_plans[:]

    for rd in range(1, max_rounds + 1):
        improved = False
        best_neighbor = None

        for source_pattern, target_pattern in replacement_patterns(objective):
            groups = find_candidate_groups(current, source_pattern, max_groups=8)
            for group_idx in groups:
                candidate = try_one_replacement(current, group_idx, target_pattern)
                if candidate is None:
                    continue

                if is_better_solution(candidate, current, objective):
                    if best_neighbor is None or is_better_solution(candidate, best_neighbor, objective):
                        best_neighbor = candidate

        if best_neighbor is not None:
            before = solution_stats(current)
            after = solution_stats(best_neighbor)
            print(
                f"[局部替换-{objective}] 第 {rd} 轮接受改进："
                f"车辆数 {before['vehicle_count']} -> {after['vehicle_count']}，"
                f"成本 {before['total_cost']} -> {after['total_cost']}"
            )
            current = best_neighbor
            improved = True

        if not improved:
            break

    return current


# =========================================================
# 输出
# =========================================================
def write_vehicle_summary_csv(path: str, plans: List[VehicleResult]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "truck_name", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_weight_kg", "loaded_volume_cm3", "strategy"
        ])
        for vp in plans:
            tr = TRUCKS[vp.truck_name]
            sv, wv, fs = truck_score(tr, vp.used_volume, vp.used_weight)
            w.writerow([
                vp.vehicle_id,
                vp.truck_name,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                vp.actual_counts,
                round(vp.used_weight, 3),
                vp.used_volume,
                vp.strategy,
            ])


def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category,
                p.x, p.y, p.z,
                p.length, p.width, p.height,
                p.weight, p.orientation_id, p.rotation, p.truck_id
            ])


def export_solution(base_dir: str, plans: List[VehicleResult]) -> None:
    os.makedirs(base_dir, exist_ok=True)
    write_vehicle_summary_csv(os.path.join(base_dir, "车辆汇总.csv"), plans)
    for vp in plans:
        write_items_csv(os.path.join(base_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp.placed)


# =========================================================
# 主求解
# =========================================================
def solve_problem2_replacement(objective: str) -> Tuple[List[VehicleResult], Dict[str, object]]:
    print("=" * 72)
    print(f"开始生成单车型基准解，目标 = {objective}")
    print("=" * 72)

    plans_type1 = solve_single_type("车型1")
    plans_type2 = solve_single_type("车型2")

    stats1 = solution_stats(plans_type1)
    stats2 = solution_stats(plans_type2)

    print(f"[基准-车型1] {stats1}")
    print(f"[基准-车型2] {stats2}")

    current = choose_baseline(plans_type1, plans_type2, objective)
    base_stats = solution_stats(current)
    print(f"[选定基准] {base_stats}")

    improved = local_replacement_search(current, objective, max_rounds=20)
    final_stats = solution_stats(improved)
    final_stats["objective"] = objective
    return improved, final_stats


# =========================================================
# CLI
# =========================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（基准解 + 局部车型替换）")
    parser.add_argument("--objective", choices=["min_vehicle", "min_cost", "both"], default="both")
    parser.add_argument("--outdir", type=str, default="output_problem2_replace_search")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    objectives = ["min_vehicle", "min_cost"] if args.objective == "both" else [args.objective]

    for obj in objectives:
        print("\n" + "=" * 72)
        print(f"开始求解问题二（基准解 + 局部车型替换），目标 = {obj}")
        print("=" * 72)

        plans, summary = solve_problem2_replacement(obj)
        outdir = os.path.join(args.outdir, obj)
        export_solution(outdir, plans)
        summary["output_dir"] = outdir
        print(summary)


if __name__ == "__main__":
    main()