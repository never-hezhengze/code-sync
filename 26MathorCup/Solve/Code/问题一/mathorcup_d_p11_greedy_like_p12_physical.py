#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
MathorCup D题 - 问题1.1（基于问题1.2思路的单车满载优化版，补全物理约束）

系统性加入以下物理约束：
1. G3（易碎件）上方禁放：G3 放置后不生成其上方可用空间；
2. 支撑完整性：非底板放置必须完整落在单个支撑面上；
3. 承压约束：若货物放在某支撑物上，检查该支撑物的累计直接承重是否超过上限；
4. G3 支撑约束：G3 仅允许放在底板或 G1/G2 顶面上；
5. 定向件姿态约束仍通过公共 ORIENTATIONS 保持。
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
    support_by: Optional[str] = None
    direct_supported_weight: float = 0.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return (self.length * self.width) / 10000.0

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
    spaces.sort(key=lambda s: (s["z"], -space_volume(s), s["y"], s["x"]))
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

    def can_place_with_physics(self, type_id: str, ori: Orientation, sp_idx: int) -> bool:
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

    def place_item(self, type_id: str, ori: Orientation, sp_idx: int) -> None:
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]
        self.serial_counter[type_id] += 1
        item_id = f"{type_id}_{self.vehicle_id}_{self.serial_counter[type_id]:04d}"
        support_by = sp.get("support_item_id")
        placed = PlacedCargo(
            item_id=item_id,
            type_id=type_id,
            category=cargo.category,
            x=sp["x"], y=sp["y"], z=sp["z"],
            length=l, width=w, height=h,
            weight=cargo.weight,
            orientation_id=ori.orient_id,
            rotation=ori.rotation,
            truck_id=self.vehicle_id,
            support_by=support_by,
        )
        self.placed.append(placed)
        self.placed_map[item_id] = placed
        self.used_weight += cargo.weight
        self.used_volume += placed.volume
        self.actual_counts[type_id] += 1
        if support_by is not None and support_by in self.placed_map:
            self.placed_map[support_by].direct_supported_weight += cargo.weight
        right = {
            "x": sp["x"] + l, "y": sp["y"], "z": sp["z"],
            "l": sp["l"] - l, "w": sp["w"], "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
            "support_length": sp.get("support_length"),
            "support_width": sp.get("support_width"),
        }
        front = {
            "x": sp["x"], "y": sp["y"] + w, "z": sp["z"],
            "l": l, "w": sp["w"] - w, "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
            "support_length": sp.get("support_length"),
            "support_width": sp.get("support_width"),
        }
        new_spaces = [right, front]
        if cargo.category != "fragile":
            upper = {
                "x": sp["x"], "y": sp["y"], "z": sp["z"] + h,
                "l": l, "w": w, "h": sp["h"] - h,
                "support_item_id": item_id,
                "support_type_id": type_id,
                "support_length": l,
                "support_width": w,
            }
            new_spaces.append(upper)
        self.spaces.pop(sp_idx)
        self.spaces.extend(new_spaces)
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
    item_vol = l * w * h
    fill_ratio = item_vol / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    vol_gain = item_vol / max(1, truck_obj.truck.effective_volume)
    wt_gain = cargo.weight / max(1.0, truck_obj.truck.max_weight)
    old_fs = fullness_score(truck_obj.truck, truck_obj.used_volume, truck_obj.used_weight)
    new_fs = fullness_score(truck_obj.truck, truck_obj.used_volume + item_vol, truck_obj.used_weight + cargo.weight)
    fs_gain = new_fs - old_fs
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    support_penalty = 0.02 if sp["z"] > 0 else 0.0
    score = (
        0.34 * vol_gain + 0.26 * wt_gain + 0.20 * fill_ratio +
        0.12 * fs_gain * 10.0 + 0.05 * bottom_bonus +
        0.02 * remain_bonus - support_penalty
    )
    return score

def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], type_order: List[str]) -> bool:
    best = None
    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]
    for sp_idx, _sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = eval_candidate(type_id, ori, truck_obj.spaces[sp_idx], remaining, truck_obj)
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
    strategies = ["std_first", "dir_first", "mixed", "g3_first", "heavy_first", "bulky_first"]
    best_plan = None
    best_key = None
    for st in strategies:
        rem_copy = deepcopy(initial_remaining)
        plan = load_one_truck(truck, rem_copy, st, vehicle_idx)
        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue
        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
        key = (round(fs, 8), plan.used_volume, plan.used_weight, loaded_cnt)
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
        w.writerow(["vehicle_id", "space_utilization", "weight_utilization", "fullness_score", "actual_counts", "loaded_count", "loaded_weight_kg", "loaded_volume_cm3", "strategy"])
        for plan in plans:
            sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
            w.writerow([plan.vehicle_id, round(sv, 6), round(wv, 6), round(fs, 6), dict(plan.actual_counts), plan.item_count, round(plan.used_weight, 3), plan.used_volume, plan.strategy])

def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "type_id", "category", "x", "y", "z", "length", "width", "height", "weight", "orientation_id", "rotation", "truck_id", "support_by", "direct_supported_weight"])
        for p in placed:
            w.writerow([p.item_id, p.type_id, p.category, p.x, p.y, p.z, p.length, p.width, p.height, p.weight, p.orientation_id, p.rotation, p.truck_id, p.support_by or '', round(p.direct_supported_weight, 6)])

def solve_problem_11_greedy(truck_name: str) -> Tuple[List[VehicleResult], Dict[str, object]]:
    truck = TRUCKS[truck_name]
    best_plan = build_one_vehicle_best(truck, vehicle_idx=1)
    plans = [best_plan]
    sv, wv, fs = truck_score(truck, best_plan.used_volume, best_plan.used_weight)
    print(f"[{truck_name}] 单车装载结果：装入 {best_plan.item_count} 件，空间利用率={sv:.4f}，载重利用率={wv:.4f}，fullness_score={fs:.4f}，策略={best_plan.strategy}")
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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.1（基于问题1.2思路 + 物理约束补全版）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="output_p11_greedy_like_p12_physical", help="输出目录")
    return parser.parse_args()

def main():
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for truck_name in truck_list:
        print("=" * 72)
        print(f"开始求解问题1.1（基于问题1.2思路 + 物理约束补全）：{truck_name}")
        print("=" * 72)
        summary = solve_for_truck(truck_name, args.outdir)
        print(summary)
        print()

if __name__ == "__main__":
    main()