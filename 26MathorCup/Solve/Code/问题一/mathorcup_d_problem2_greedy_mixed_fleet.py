#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（重构版）
混合车型：基于“快速贪心单车装载器”的逐车构造算法

特点：
1. 不再使用原问题2中的枚举车队结构 + SA/GA/LNS；
2. 直接复用问题1.2当前这版“按货类计数 + 候选空间限制”的快速装车思想；
3. 每一步同时试装一辆车型1和一辆车型2，再根据目标选择更优车辆加入车队；
4. 支持两个目标：
   - min_vehicle：车辆数最少
   - min_cost：运输成本最低
5. 输出：
   - 车辆汇总.csv
   - 每辆车装箱明细.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Tuple

from mathorcup_d_p12_stable_solver import (
    CARGO_TYPES,
    TRUCKS,
    ORIENTATIONS,
    Truck,
    CargoType,
    Orientation,
)

# =========================================================
# 参数区：你后续可以只调这里
# =========================================================
MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000
RANDOM_SEED = 2026

random.seed(RANDOM_SEED)

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]


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


# =========================================================
# 工具函数
# =========================================================
def total_remaining_items(remaining: Dict[str, int]) -> int:
    return sum(remaining[t] for t in TYPE_ORDER_ALL)


def total_remaining_volume(remaining: Dict[str, int]) -> int:
    return sum(CARGO_TYPES[t].volume * remaining[t] for t in TYPE_ORDER_ALL)


def total_remaining_weight(remaining: Dict[str, int]) -> float:
    return sum(CARGO_TYPES[t].weight * remaining[t] for t in TYPE_ORDER_ALL)


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


# =========================================================
# 快速装载车对象
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

    def can_load_weight(self, type_id: str) -> bool:
        return self.used_weight + CARGO_TYPES[type_id].weight <= self.truck.max_weight

    def place_item(self, type_id: str, ori: Orientation, sp_idx: int) -> None:
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
            orientation_id=ori.orient_id,
            rotation=ori.rotation,
            truck_id=self.vehicle_id,
        )
        self.placed.append(placed)
        self.used_weight += cargo.weight
        self.used_volume += placed.volume
        self.actual_counts[type_id] += 1

        # 三切分
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
# 策略与评分
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


def eval_candidate(type_id: str, ori: Orientation, sp: Dict[str, int], remaining: Dict[str, int], truck_obj: FastTruck) -> float | None:
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

    # 对G3略做偏置，但不走复杂双通道建模
    if type_id == "G3":
        fragile_bonus = 0.08
    else:
        fragile_bonus = 0.0

    score = 0.62 * fill_ratio + 0.23 * bottom_bonus + 0.15 * remain_bonus + fragile_bonus
    return score


def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], type_order: List[str]) -> bool:
    best = None  # (score, type_id, ori, sp_idx)

    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    for sp_idx, sp in enumerate(candidate_spaces):
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


# =========================================================
# 单车装载：多策略试装
# =========================================================
def load_one_truck_with_strategy(truck: Truck, remaining: Dict[str, int], vehicle_index: int, strategy: str) -> VehicleResult:
    vehicle_id = f"{truck.name}_{vehicle_index:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)

    fail_count = 0
    while True:
        ok = place_one_best(truck_obj, remaining, type_order)
        if ok:
            fail_count = 0
        else:
            fail_count += 1
            if fail_count >= 1:
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


def build_one_vehicle_best(truck: Truck, remaining: Dict[str, int], vehicle_index: int) -> VehicleResult:
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
        plan = load_one_truck_with_strategy(truck, rem_copy, vehicle_index, st)

        loaded_cnt = plan.item_count
        if loaded_cnt == 0:
            continue

        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)

        key = (
            loaded_cnt,
            round(fs, 6),
            plan.used_volume,
            -plan.used_weight,
        )
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key

    if best_plan is None:
        raise RuntimeError(f"{truck.name} 第 {vehicle_index} 辆车未能装入任何货物。")

    return best_plan


# =========================================================
# 问题2：比较两种车型当前轮表现，逐车加入
# =========================================================
def choose_vehicle_for_objective(
    plan1: VehicleResult,
    plan2: VehicleResult,
    objective: str,
) -> VehicleResult:
    tr1 = TRUCKS["车型1"]
    tr2 = TRUCKS["车型2"]

    sv1, wv1, fs1 = truck_score(tr1, plan1.used_volume, plan1.used_weight)
    sv2, wv2, fs2 = truck_score(tr2, plan2.used_volume, plan2.used_weight)

    if objective == "min_vehicle":
        key1 = (
            plan1.item_count,
            round(fs1, 6),
            plan1.used_volume,
            -tr1.cost,
        )
        key2 = (
            plan2.item_count,
            round(fs2, 6),
            plan2.used_volume,
            -tr2.cost,
        )
        return plan1 if key1 >= key2 else plan2

    # min_cost：看“每单位成本换来多少有效装载”
    value1 = (
        1.2 * plan1.item_count
        + 0.00002 * plan1.used_volume
        + 12.0 * fs1
    ) / tr1.cost

    value2 = (
        1.2 * plan2.item_count
        + 0.00002 * plan2.used_volume
        + 12.0 * fs2
    ) / tr2.cost

    if value1 > value2:
        return plan1
    elif value2 > value1:
        return plan2
    else:
        # 打平时，优先成本更低；再优先装得更多
        key1 = (-tr1.cost, plan1.item_count, plan1.used_volume)
        key2 = (-tr2.cost, plan2.item_count, plan2.used_volume)
        return plan1 if key1 >= key2 else plan2


def apply_plan_to_remaining(remaining: Dict[str, int], plan: VehicleResult) -> None:
    for t, c in plan.actual_counts.items():
        remaining[t] -= c
        if remaining[t] < 0:
            raise RuntimeError(f"剩余货物 {t} 被扣成负数，请检查算法。")


def solve_mixed_fleet_greedy(objective: str) -> Tuple[List[VehicleResult], Dict[str, object]]:
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER_ALL}
    plans: List[VehicleResult] = []

    vehicle_index_1 = 1
    vehicle_index_2 = 1

    while total_remaining_items(remaining) > 0:
        plan1 = build_one_vehicle_best(TRUCKS["车型1"], remaining, vehicle_index_1)
        plan2 = build_one_vehicle_best(TRUCKS["车型2"], remaining, vehicle_index_2)

        chosen = choose_vehicle_for_objective(plan1, plan2, objective)

        if chosen.item_count <= 0:
            raise RuntimeError("当前轮两种车型都无法装入货物，算法停止。")

        apply_plan_to_remaining(remaining, chosen)
        plans.append(chosen)

        if chosen.truck_name == "车型1":
            vehicle_index_1 += 1
            n1 = sum(1 for p in plans if p.truck_name == "车型1")
            n2 = sum(1 for p in plans if p.truck_name == "车型2")
        else:
            vehicle_index_2 += 1
            n1 = sum(1 for p in plans if p.truck_name == "车型1")
            n2 = sum(1 for p in plans if p.truck_name == "车型2")

        tr = TRUCKS[chosen.truck_name]
        sv, wv, fs = truck_score(tr, chosen.used_volume, chosen.used_weight)

        print(
            f"[{objective}] 选择 {chosen.truck_name} -> {chosen.vehicle_id}："
            f"装入 {chosen.item_count} 件，"
            f"空间利用率={sv:.4f}，"
            f"载重利用率={wv:.4f}，"
            f"fullness_score={fs:.4f}，"
            f"当前车队=(车型1:{n1}, 车型2:{n2})，"
            f"剩余={total_remaining_items(remaining)}"
        )

    n1 = sum(1 for p in plans if p.truck_name == "车型1")
    n2 = sum(1 for p in plans if p.truck_name == "车型2")
    total_cost = n1 * TRUCKS["车型1"].cost + n2 * TRUCKS["车型2"].cost
    total_volume = sum(TRUCKS[p.truck_name].effective_volume for p in plans)
    total_weight_cap = sum(TRUCKS[p.truck_name].max_weight for p in plans)
    used_volume = sum(p.used_volume for p in plans)
    used_weight = sum(p.used_weight for p in plans)

    summary = {
        "objective": objective,
        "fleet_structure": {"车型1": n1, "车型2": n2},
        "vehicle_count": len(plans),
        "total_cost": round(total_cost, 2),
        "avg_space_utilization": round(used_volume / max(1, total_volume), 6),
        "avg_weight_utilization": round(used_weight / max(1.0, total_weight_cap), 6),
        "all_loaded": True,
    }
    return plans, summary


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
# CLI
# =========================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（重构版：快速贪心混合车型）")
    parser.add_argument("--objective", choices=["min_vehicle", "min_cost", "both"], default="both")
    parser.add_argument("--outdir", type=str, default="output_problem2_greedy_mixed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    objectives = ["min_vehicle", "min_cost"] if args.objective == "both" else [args.objective]

    for obj in objectives:
        print("=" * 72)
        print(f"开始求解问题二（重构版），目标 = {obj}")
        print("=" * 72)

        plans, summary = solve_mixed_fleet_greedy(obj)
        obj_dir = os.path.join(args.outdir, obj)
        export_solution(obj_dir, plans)
        summary["output_dir"] = obj_dir
        print(summary)


if __name__ == "__main__":
    main()