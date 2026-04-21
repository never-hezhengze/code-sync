# -*- coding: utf-8 -*-
"""
问题1.2 轻量增强版：
基于 baseline 的“随机化多启动 + 尾车合并压缩”

设计原则：
1. 保留 baseline 的单车物理约束与空间切分逻辑，不引入重型元启发式；
2. 每辆车仍使用“多策略试探”，但增加少量随机扰动策略；
3. 整体做多启动，选择车辆数更少、平均利用率更高的方案；
4. 对尾车做轻量压缩：尝试将最后两辆车合并为一辆，或最后三辆压成两辆。

相比重型 GRASP/Tabu/PR，这版更适合：
- 直接替换 p12_baseline.py 做增强对照
- 运行时间可控
- 结果通常比纯确定性 baseline 更稳一些
"""

from __future__ import annotations

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
)

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]

MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000


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
    support_by: Optional[str] = None
    direct_supported_weight: float = 0.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return (self.length * self.width) / 10000.0


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


def plan_loaded_count(plan) -> int:
    return sum(plan.actual_counts.values())


def solution_key(plans: List["FastTruck"], truck) -> Tuple[int, float, float]:
    """越小越好：先比车辆数，再比平均满载率（取负）"""
    vehicle_count = len(plans)
    avg_sv = sum(p.used_volume for p in plans) / (max(1, vehicle_count) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (max(1, vehicle_count) * truck.max_weight)
    fullness = 0.72 * avg_sv + 0.28 * avg_wv
    return (vehicle_count, -fullness, -avg_sv)


def solution_summary(plans: List["FastTruck"], truck_name: str):
    truck = TRUCKS[truck_name]
    total_cost = len(plans) * truck.cost
    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)
    return {
        "truck": truck_name,
        "vehicle_count": len(plans),
        "total_cost": total_cost,
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "all_loaded": True,
    }


# =========================================================
# 轻量货车类（保留 baseline 物理约束）
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

    def place_item(self, type_id, ori, sp_idx):
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
# 类型顺序与评分
# =========================================================
def build_type_order(strategy: str, rng: random.Random):
    std_types = ["G1", "G2"]
    dir_types = ["G4", "G5"]

    if strategy == "std_first":
        return std_types + dir_types + ["G3"]
    elif strategy == "dir_first":
        return dir_types + std_types + ["G3"]
    elif strategy == "g3_first":
        return ["G3"] + dir_types + std_types
    elif strategy == "mixed":
        arr = ["G1", "G2", "G4", "G5", "G3"]
        rng.shuffle(arr)
        return arr
    elif strategy == "g3_last":
        arr = ["G1", "G2", "G4", "G5"]
        rng.shuffle(arr)
        return arr + ["G3"]
    elif strategy == "fragile_late":
        arr = ["G4", "G5", "G1", "G2"]
        rng.shuffle(arr)
        return arr + ["G3"]
    else:
        arr = TYPE_ORDER_ALL[:]
        rng.shuffle(arr)
        return arr


def eval_candidate(type_id, ori, sp, remaining, truck_obj, rng: random.Random, noise_scale: float = 0.015):
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight:
        return None
    if remaining[type_id] <= 0:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    remain_bonus = remaining[type_id] / max(1, CARGO_TYPES[type_id].quantity)
    support_penalty = 0.02 if sp["z"] > 0 else 0.0
    edge_bonus = 0.015 if (sp["x"] == 0 or sp["y"] == 0) else 0.0

    score = 0.60 * fill_ratio + 0.22 * bottom_bonus + 0.14 * remain_bonus + edge_bonus - support_penalty
    score += rng.uniform(-noise_scale, noise_scale)
    return score


def place_one_rcl(truck_obj, remaining, type_order, rng: random.Random, rcl_size: int = 4):
    candidates = []
    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    for sp_idx, _sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = eval_candidate(type_id, ori, truck_obj.spaces[sp_idx], remaining, truck_obj, rng)
                if val is None:
                    continue
                candidates.append((val, type_id, ori, sp_idx))

    if not candidates:
        return False

    candidates.sort(key=lambda x: x[0], reverse=True)
    rcl = candidates[:max(1, min(rcl_size, len(candidates)))]
    _, type_id, ori, sp_idx = rng.choice(rcl)
    truck_obj.place_item(type_id, ori, sp_idx)
    remaining[type_id] -= 1
    return True


def load_one_truck(truck, remaining, type_order, vehicle_idx, rng: random.Random, rcl_size: int = 4):
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    while True:
        ok = place_one_rcl(truck_obj, remaining, type_order, rng=rng, rcl_size=rcl_size)
        if not ok:
            break
    return truck_obj


def build_one_vehicle_best(truck, remaining, vehicle_idx, rng: random.Random, extra_random_trials: int = 3, rcl_size: int = 4):
    strategies = ["std_first", "dir_first", "mixed", "g3_first", "g3_last", "fragile_late"]
    best_plan = None
    best_key = None

    # 固定策略
    for st in strategies:
        rem_copy = deepcopy(remaining)
        type_order = build_type_order(st, rng)
        local_rng = random.Random(rng.randint(1, 10**9))
        plan = load_one_truck(truck, rem_copy, type_order, vehicle_idx, local_rng, rcl_size=rcl_size)
        loaded_cnt = plan_loaded_count(plan)
        if loaded_cnt == 0:
            continue
        key = (loaded_cnt, plan.used_volume, -plan.used_weight)
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key

    # 少量随机策略
    for _ in range(extra_random_trials):
        rem_copy = deepcopy(remaining)
        type_order = build_type_order("random", rng)
        local_rng = random.Random(rng.randint(1, 10**9))
        plan = load_one_truck(truck, rem_copy, type_order, vehicle_idx, local_rng, rcl_size=rcl_size)
        loaded_cnt = plan_loaded_count(plan)
        if loaded_cnt == 0:
            continue
        key = (loaded_cnt, plan.used_volume, -plan.used_weight)
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key

    return best_plan


# =========================================================
# 轻量尾车压缩
# =========================================================
def counts_from_plan(plan: FastTruck) -> Dict[str, int]:
    return {k: int(v) for k, v in plan.actual_counts.items()}


def add_counts(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    out = Counter()
    out.update(a)
    out.update(b)
    return dict(out)


def subtract_counts(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    out = Counter(a)
    for k, v in b.items():
        out[k] -= v
    return {k: int(v) for k, v in out.items() if v > 0}


def can_fully_pack_counts_in_n_vehicles(truck, counts: Dict[str, int], n_vehicles: int, seed: int, rcl_size: int = 4):
    rng = random.Random(seed)
    remaining = {k: int(counts.get(k, 0)) for k in CARGO_TYPES.keys()}
    plans = []

    for idx in range(1, n_vehicles + 1):
        if sum(remaining.values()) <= 0:
            break
        plan = build_one_vehicle_best(truck, remaining, idx, rng, extra_random_trials=2, rcl_size=rcl_size)
        if plan is None or plan_loaded_count(plan) == 0:
            return None
        for t, c in plan.actual_counts.items():
            remaining[t] -= c
        plans.append(plan)

    if sum(remaining.values()) == 0:
        return plans
    return None


def tail_merge_improve(plans: List[FastTruck], truck, seed: int, rcl_size: int = 4):
    if len(plans) < 2:
        return plans

    improved = plans[:]
    changed = True
    while changed:
        changed = False

        # 先尝试最后两辆压成一辆
        if len(improved) >= 2:
            c12 = add_counts(counts_from_plan(improved[-2]), counts_from_plan(improved[-1]))
            packed = can_fully_pack_counts_in_n_vehicles(truck, c12, 1, seed=seed + len(improved), rcl_size=rcl_size)
            if packed is not None:
                base = improved[:-2]
                # 重命名车辆编号保持连续
                new_vehicle_idx = len(base) + 1
                packed[0].vehicle_id = f"{truck.name}_{new_vehicle_idx:03d}"
                improved = base + packed
                changed = True
                continue

        # 再尝试最后三辆压成两辆
        if len(improved) >= 3:
            c123 = add_counts(add_counts(counts_from_plan(improved[-3]), counts_from_plan(improved[-2])), counts_from_plan(improved[-1]))
            packed = can_fully_pack_counts_in_n_vehicles(truck, c123, 2, seed=seed + 1000 + len(improved), rcl_size=rcl_size)
            if packed is not None:
                base = improved[:-3]
                for i, p in enumerate(packed, start=1):
                    p.vehicle_id = f"{truck.name}_{len(base) + i:03d}"
                improved = base + packed
                changed = True
                continue

    return improved


# =========================================================
# 求解主流程：多启动 + 尾车压缩
# =========================================================
def solve_one_truck_type_multistart(truck_name: str, starts: int, seed: int, rcl_size: int, extra_random_trials: int, show_progress: bool):
    truck = TRUCKS[truck_name]
    global_best_plans = None
    global_best_key = None

    for st in range(1, starts + 1):
        rng = random.Random(seed + 10007 * st)
        remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}
        plans = []
        vehicle_idx = 1

        while sum(remaining.values()) > 0:
            plan = build_one_vehicle_best(
                truck=truck,
                remaining=remaining,
                vehicle_idx=vehicle_idx,
                rng=rng,
                extra_random_trials=extra_random_trials,
                rcl_size=rcl_size,
            )
            if plan is None or plan_loaded_count(plan) == 0:
                raise RuntimeError(f"{truck_name} 在 start={st}, vehicle={vehicle_idx} 未能装入任何货物，算法停止。")

            for t, c in plan.actual_counts.items():
                remaining[t] -= c
            plans.append(plan)
            vehicle_idx += 1

        # 轻量尾车压缩
        plans = tail_merge_improve(plans, truck, seed=seed + 777 * st, rcl_size=rcl_size)

        key = solution_key(plans, truck)
        if global_best_plans is None or key < global_best_key:
            global_best_plans = plans
            global_best_key = key

        if show_progress:
            summary = solution_summary(plans, truck_name)
            print(
                f"[{truck_name}] start={st:02d} | vehicles={summary['vehicle_count']} "
                f"| avg_sv={summary['avg_space_utilization']:.4f} "
                f"| avg_wv={summary['avg_weight_utilization']:.4f}"
            )

    summary = solution_summary(global_best_plans, truck_name)
    return global_best_plans, summary


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
            "support_by", "direct_supported_weight"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id,
                p.support_by or "",
                round(p.direct_supported_weight, 6),
            ])


def solve_for_truck(truck_name, outdir, starts: int, seed: int, rcl_size: int, extra_random_trials: int, show_progress: bool):
    truck = TRUCKS[truck_name]
    plans, summary = solve_one_truck_type_multistart(
        truck_name=truck_name,
        starts=starts,
        seed=seed,
        rcl_size=rcl_size,
        extra_random_trials=extra_random_trials,
        show_progress=show_progress,
    )
    truck_dir = os.path.join(outdir, truck_name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), plans, truck)
    for plan in plans:
        write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan.placed)
    summary["output_dir"] = truck_dir
    return plans, summary


# =========================================================
# CLI
# =========================================================
def parse_args():
    parser = argparse.ArgumentParser(description="问题1.2 轻量增强版：随机化多启动 + 尾车合并压缩")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2_multistart_tailmerge", help="输出目录")
    parser.add_argument("--starts", type=int, default=8, help="多启动次数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--rcl-size", type=int, default=4, help="RCL 候选集大小")
    parser.add_argument("--extra-random-trials", type=int, default=3, help="每辆车额外随机策略次数")
    parser.add_argument("--show-progress", action="store_true", help="打印每次启动的汇总进度")
    return parser.parse_args()


# =========================================================
# 主程序
# =========================================================
def main():
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for truck_name in truck_list:
        print(f"===== {truck_name} =====")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        plans, summary = solve_for_truck(
            truck_name=truck_name,
            outdir=outdir,
            starts=args.starts,
            seed=args.seed,
            rcl_size=args.rcl_size,
            extra_random_trials=args.extra_random_trials,
            show_progress=args.show_progress,
        )
        # 打印最佳解逐车汇总
        truck = TRUCKS[truck_name]
        for i, plan in enumerate(plans, start=1):
            sv, wv, fs = local_truck_score(plan.used_volume, plan.used_weight, truck)
            print(
                f"[{truck_name}] 第 {i} 辆车："
                f"装入 {plan_loaded_count(plan)} 件，"
                f"空间利用率={sv:.4f}，"
                f"载重利用率={wv:.4f}，"
                f"fullness_score={fs:.4f}"
            )
        print(summary)
        print()


if __name__ == "__main__":
    main()
