#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
MathorCup D题 - 问题1.1（基于问题1.2思路的单车满载优化版）

核心思想：
1. 不再先搜索数量组合，而是直接采用“空间驱动”的单车装箱框架；
2. 每一步从 候选空间 × 货物类型 × 合法姿态 中选择当前最优放置；
3. 通过多策略试探避免单一路径贪心；
4. 目标函数改成最大化单车综合满载率（空间利用率 + 载重利用率）；
5. 输出车辆汇总与逐件装箱明细 CSV。
"""

import argparse
import csv
import os
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from mathorcup_d_common import (
    CARGO_TYPES,
    TRUCKS,
    ORIENTATIONS,
    Truck,
    Orientation,
    truck_score,
)

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]

MAX_SPACES_TO_CHECK = 120
MIN_SPACE_VOLUME = 15000
RANDOM_SEED = 2026
random.seed(RANDOM_SEED)


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
    placed: List[PlacedCargo]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int
    strategy: str

    @property
    def item_count(self) -> int:
        return sum(self.actual_counts.values())


def space_volume(sp: Dict[str, int]) -> int:
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces: List[Dict[str, int]]) -> List[Dict[str, int]]:
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (-space_volume(s), s["z"], s["y"], s["x"]))
    return spaces


def fullness_score(truck: Truck, used_volume: int, used_weight: float) -> float:
    _, _, fs = truck_score(truck, used_volume, used_weight)
    return fs


class FastTruck:
    def __init__(self, truck: Truck, vehicle_id: str):
        self.truck = truck
        self.vehicle_id = vehicle_id
        self.L = truck.length
        self.W = truck.width
        self.H = truck.effective_height
        self.max_weight = truck.max_weight

        self.spaces = [{
            "x": 0, "y": 0, "z": 0,
            "l": self.L, "w": self.W, "h": self.H
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

        right = {
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": w,
            "h": h,
        }
        front = {
            "x": sp["x"],
            "y": sp["y"] + w,
            "z": sp["z"],
            "l": sp["l"],
            "w": sp["w"] - w,
            "h": h,
        }
        upper = {
            "x": sp["x"],
            "y": sp["y"],
            "z": sp["z"] + h,
            "l": sp["l"],
            "w": sp["w"],
            "h": sp["h"] - h,
        }

        self.spaces.pop(sp_idx)
        self.spaces.extend([right, front, upper])
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


def build_type_order(strategy: str) -> List[str]:
    std_types = ["G1", "G2"]
    dir_types = ["G4", "G5"]

    if strategy == "std_first":
        return std_types + dir_types + ["G3"]
    elif strategy == "dir_first":
        return dir_types + std_types + ["G3"]
    elif strategy == "g3_first":
        return ["G3"] + dir_types + std_types
    elif strategy == "heavy_first":
        return sorted(TYPE_ORDER_ALL, key=lambda t: CARGO_TYPES[t].weight, reverse=True)
    elif strategy == "bulky_first":
        return sorted(TYPE_ORDER_ALL, key=lambda t: CARGO_TYPES[t].volume, reverse=True)
    else:
        arr = TYPE_ORDER_ALL[:]
        random.shuffle(arr)
        return arr


def eval_candidate(type_id: str, ori: Orientation, sp: Dict[str, int], remaining: Dict[str, int], truck_obj: FastTruck) -> Optional[float]:
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if remaining[type_id] <= 0:
        return None
    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight:
        return None

    item_vol = l * w * h
    fill_ratio = item_vol / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    vol_gain = item_vol / max(1, truck_obj.truck.effective_volume)
    wt_gain = cargo.weight / max(1.0, truck_obj.truck.max_weight)

    old_fs = fullness_score(truck_obj.truck, truck_obj.used_volume, truck_obj.used_weight)
    new_fs = fullness_score(
        truck_obj.truck,
        truck_obj.used_volume + item_vol,
        truck_obj.used_weight + cargo.weight,
    )
    fs_gain = new_fs - old_fs
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    fragile_bonus = 0.02 if type_id == "G3" else 0.0

    score = (
        0.34 * vol_gain
        + 0.26 * wt_gain
        + 0.20 * fill_ratio
        + 0.12 * fs_gain * 10.0
        + 0.05 * bottom_bonus
        + 0.02 * remain_bonus
        + fragile_bonus
    )
    return score


def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], type_order: List[str]) -> bool:
    best = None
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


def load_one_truck(truck: Truck, remaining: Dict[str, int], strategy: str, vehicle_idx: int) -> FastTruck:
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)

    while True:
        ok = place_one_best(truck_obj, remaining, type_order)
        if not ok:
            break

    return truck_obj


def build_one_vehicle_best(truck: Truck, vehicle_idx: int) -> VehicleResult:
    initial_remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}
    strategies = [
        "std_first",
        "dir_first",
        "mixed",
        "g3_first",
        "heavy_first",
        "bulky_first",
    ]

    best_plan = None
    best_key = None

    for st in strategies:
        rem_copy = deepcopy(initial_remaining)
        plan = load_one_truck(truck, rem_copy, st, vehicle_idx)

        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue

        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
        key = (
            round(fs, 8),
            plan.used_volume,
            plan.used_weight,
            loaded_cnt,
        )
        if best_plan is None or key > best_key:
            best_plan = VehicleResult(
                vehicle_id=plan.vehicle_id,
                placed=plan.placed,
                actual_counts=dict(plan.actual_counts),
                used_weight=plan.used_weight,
                used_volume=plan.used_volume,
                strategy=st,
            )
            best_key = key

    if best_plan is None:
        raise RuntimeError(f"{truck.name} 单车求解失败：未能装入任何货物。")

    return best_plan


def write_vehicle_summary_csv(path: str, plans: List[VehicleResult], truck: Truck) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_count", "loaded_weight_kg", "loaded_volume_cm3", "strategy"
        ])
        for plan in plans:
            sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
            w.writerow([
                plan.vehicle_id,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                dict(plan.actual_counts),
                plan.item_count,
                round(plan.used_weight, 3),
                plan.used_volume,
                plan.strategy,
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
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id,
            ])


def solve_problem_11_greedy(truck_name: str) -> Tuple[List[VehicleResult], Dict[str, object]]:
    truck = TRUCKS[truck_name]
    best_plan = build_one_vehicle_best(truck, vehicle_idx=1)
    plans = [best_plan]

    sv, wv, fs = truck_score(truck, best_plan.used_volume, best_plan.used_weight)
    print(
        f"[{truck_name}] 单车装载结果："
        f"装入 {best_plan.item_count} 件，"
        f"空间利用率={sv:.4f}，"
        f"载重利用率={wv:.4f}，"
        f"fullness_score={fs:.4f}，"
        f"策略={best_plan.strategy}"
    )

    summary = {
        "truck": truck_name,
        "vehicle_count": 1,
        "loaded_count": best_plan.item_count,
        "total_cost": truck.cost,
        "space_utilization": round(sv, 6),
        "weight_utilization": round(wv, 6),
        "fullness_score": round(fs, 6),
        "all_loaded": False,
    }
    return plans, summary


def solve_for_truck(truck_name: str, outdir: str) -> Dict[str, object]:
    truck = TRUCKS[truck_name]
    plans, summary = solve_problem_11_greedy(truck_name)
    truck_dir = os.path.join(outdir, truck_name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), plans, truck)
    for plan in plans:
        write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan.placed)
    summary["output_dir"] = truck_dir
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.1（基于问题1.2思路的单车满载优化版）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="output_p11_greedy_like_p12", help="输出目录")
    return parser.parse_args()


def main():
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for truck_name in truck_list:
        print("=" * 64)
        print(f"开始求解问题1.1（基于问题1.2思路）：{truck_name}")
        print("=" * 64)
        summary = solve_for_truck(truck_name, args.outdir)
        print(summary)
        print()


if __name__ == "__main__":
    main()
