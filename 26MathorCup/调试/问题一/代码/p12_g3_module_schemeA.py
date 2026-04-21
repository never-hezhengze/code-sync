# -*- coding: utf-8 -*-
"""
问题1.2：方案A —— G3 支撑模块模板 + 主装箱

核心思想
--------
1. 预先为 G3 构造少量“支撑模块模板”：
   - 模块 = n 个同规格 G1/G2 竖向堆叠 + 1 个 G3 放在最上方
   - 模块总高度不超过对应车型有效高度
   - 模块顶面必须能完整支撑 G3
   - 模块内部视为已验证可行的复合装载单元

2. 主装箱时优先尝试这些 G3 模块，再装普通货物：
   - 模块只允许放在地板上（z=0），避免外部再叠放导致复杂性激增
   - 模块上方不再生成可用空间
   - 普通货物仍沿用 baseline 的空间切分与物理约束检查思路
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

from mathorcup_d_common import CARGO_TYPES, TRUCKS, ORIENTATIONS

MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000
RANDOM_SEED = 42
MAX_TEMPLATES_PER_TRUCK = 8


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


@dataclass(frozen=True)
class ModuleTemplate:
    name: str
    support_type: str
    support_count: int
    support_orientation_id: int
    g3_orientation_id: int
    length: int
    width: int
    height: int
    weight: float
    support_length: int
    support_width: int
    support_height: int
    g3_length: int
    g3_width: int
    g3_height: int
    volume_bbox: int
    score: float


@dataclass
class PlacedModule:
    module_id: str
    template_name: str
    x: int
    y: int
    z: int
    length: int
    width: int
    height: int
    weight: float
    truck_id: str

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


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


def build_g3_module_templates_for_truck(truck_name: str) -> List[ModuleTemplate]:
    truck = TRUCKS[truck_name]
    g3 = CARGO_TYPES["G3"]
    templates: List[ModuleTemplate] = []

    for support_type in ("G1", "G2"):
        support_cargo = CARGO_TYPES[support_type]

        for s_ori in ORIENTATIONS[support_type]:
            sl, sw, sh = s_ori.size

            for g3_ori in ORIENTATIONS["G3"]:
                gl, gw, gh = g3_ori.size
                if gl > sl or gw > sw:
                    continue

                max_n = max(0, (truck.effective_height - gh) // sh)
                if max_n <= 0:
                    continue

                for n in range(1, max_n + 1):
                    total_h = n * sh + gh
                    if total_h > truck.effective_height:
                        continue

                    total_wt = n * support_cargo.weight + g3.weight
                    L, W, H = sl, sw, total_h
                    bbox_vol = L * W * H
                    height_util = total_h / truck.effective_height
                    top_cover = (gl * gw) / max(1, sl * sw)
                    weight_util = total_wt / truck.max_weight
                    score = 0.56 * height_util + 0.24 * top_cover + 0.20 * (1.0 - weight_util)

                    templates.append(
                        ModuleTemplate(
                            name=f"M_{support_type}_n{n}_S{s_ori.orient_id}_G3{g3_ori.orient_id}",
                            support_type=support_type,
                            support_count=n,
                            support_orientation_id=s_ori.orient_id,
                            g3_orientation_id=g3_ori.orient_id,
                            length=L,
                            width=W,
                            height=H,
                            weight=total_wt,
                            support_length=sl,
                            support_width=sw,
                            support_height=sh,
                            g3_length=gl,
                            g3_width=gw,
                            g3_height=gh,
                            volume_bbox=bbox_vol,
                            score=score,
                        )
                    )

    best_map = {}
    for tpl in templates:
        key = (
            tpl.support_type, tpl.support_count, tpl.length, tpl.width,
            tpl.height, tpl.support_orientation_id, tpl.g3_orientation_id
        )
        if key not in best_map or tpl.score > best_map[key].score:
            best_map[key] = tpl

    templates = list(best_map.values())
    templates.sort(key=lambda t: (-t.score, -t.volume_bbox, t.weight))
    return templates[:MAX_TEMPLATES_PER_TRUCK]


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
        self.placed_modules: List[PlacedModule] = []
        self.used_weight = 0.0
        self.used_volume = 0
        self.actual_counts = Counter()
        self.serial_counter = Counter()
        self.module_counter = 0

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

    def can_place_module(self, tpl: ModuleTemplate, sp_idx: int):
        sp = self.spaces[sp_idx]
        if sp["z"] != 0:
            return False
        if tpl.length > sp["l"] or tpl.width > sp["w"] or tpl.height > sp["h"]:
            return False
        if self.used_weight + tpl.weight > self.max_weight:
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

    def place_module(self, tpl: ModuleTemplate, sp_idx: int):
        sp = self.spaces[sp_idx]
        self.module_counter += 1
        module_id = f"MODULE_{self.vehicle_id}_{self.module_counter:04d}"

        placed = PlacedModule(
            module_id=module_id,
            template_name=tpl.name,
            x=sp["x"], y=sp["y"], z=sp["z"],
            length=tpl.length, width=tpl.width, height=tpl.height,
            weight=tpl.weight, truck_id=self.vehicle_id,
        )
        self.placed_modules.append(placed)
        self.used_weight += tpl.weight
        self.used_volume += tpl.volume_bbox
        self.actual_counts[tpl.support_type] += tpl.support_count
        self.actual_counts["G3"] += 1

        l, w = tpl.length, tpl.width
        right = {
            "x": sp["x"] + l, "y": sp["y"], "z": sp["z"],
            "l": sp["l"] - l, "w": sp["w"], "h": sp["h"],
            "support_item_id": None, "support_type_id": None,
            "support_length": self.L, "support_width": self.W,
        }
        front = {
            "x": sp["x"], "y": sp["y"] + w, "z": sp["z"],
            "l": l, "w": sp["w"] - w, "h": sp["h"],
            "support_item_id": None, "support_type_id": None,
            "support_length": self.L, "support_width": self.W,
        }

        self.spaces.pop(sp_idx)
        self.spaces.extend([right, front])
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


def eval_item_candidate(type_id, ori, sp, remaining, truck_obj):
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
    return 0.62 * fill_ratio + 0.23 * bottom_bonus + 0.15 * remain_bonus - support_penalty


def eval_module_candidate(tpl: ModuleTemplate, sp, truck_obj):
    if tpl.length > sp["l"] or tpl.width > sp["w"] or tpl.height > sp["h"]:
        return None
    if sp["z"] != 0:
        return None
    if truck_obj.used_weight + tpl.weight > truck_obj.max_weight:
        return None

    fill_ratio = tpl.volume_bbox / max(1, sp["l"] * sp["w"] * sp["h"])
    height_bonus = tpl.height / max(1, truck_obj.H)
    edge_bonus = 0.02 if (sp["x"] == 0 or sp["y"] == 0) else 0.0
    return 0.68 * fill_ratio + 0.22 * height_bonus + 0.10 * edge_bonus


def place_one_best_with_modules(truck_obj, remaining, type_order, module_templates, module_quota_left):
    best = None
    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    if remaining.get("G3", 0) > 0:
        for sp_idx, _sp in enumerate(candidate_spaces):
            for tpl in module_templates:
                if module_quota_left.get(tpl.name, 0) <= 0:
                    continue
                if remaining.get(tpl.support_type, 0) < tpl.support_count:
                    continue
                if remaining.get("G3", 0) < 1:
                    continue
                if not truck_obj.can_place_module(tpl, sp_idx):
                    continue
                val = eval_module_candidate(tpl, truck_obj.spaces[sp_idx], truck_obj)
                if val is None:
                    continue
                if best is None or val > best[0]:
                    best = (val, "module", tpl, sp_idx)

    for sp_idx, _sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = eval_item_candidate(type_id, ori, truck_obj.spaces[sp_idx], remaining, truck_obj)
                if val is None:
                    continue
                if best is None or val > best[0] + 0.015:
                    best = (val, "item", (type_id, ori), sp_idx)

    if best is None:
        return False

    _, kind, obj, sp_idx = best
    if kind == "module":
        tpl = obj
        truck_obj.place_module(tpl, sp_idx)
        remaining[tpl.support_type] -= tpl.support_count
        remaining["G3"] -= 1
        module_quota_left[tpl.name] -= 1
    else:
        type_id, ori = obj
        truck_obj.place_item(type_id, ori, sp_idx)
        remaining[type_id] -= 1

    return True


def build_type_order(strategy):
    std_types = ["G1", "G2"]
    dir_types = ["G4", "G5"]

    if strategy == "std_first":
        return std_types + dir_types + ["G3"]
    elif strategy == "dir_first":
        return dir_types + std_types + ["G3"]
    elif strategy == "g3_first":
        return ["G3"] + dir_types + std_types
    else:
        arr = ["G1", "G2", "G4", "G5", "G3"]
        random.shuffle(arr)
        return arr


def load_one_truck_with_modules(truck, remaining, strategy, vehicle_idx, module_templates, module_quota_left):
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)

    while True:
        ok = place_one_best_with_modules(truck_obj, remaining, type_order, module_templates, module_quota_left)
        if not ok:
            break

    return truck_obj


def build_one_vehicle_best_with_modules(truck, remaining, vehicle_idx, module_templates, module_quota_left):
    strategies = ["std_first", "dir_first", "mixed", "g3_first"]

    best_plan = None
    best_key = None
    best_quota_after = None

    for st in strategies:
        rem_copy = deepcopy(remaining)
        quota_copy = deepcopy(module_quota_left)
        plan = load_one_truck_with_modules(truck, rem_copy, st, vehicle_idx, module_templates, quota_copy)

        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue

        key = (loaded_cnt, plan.used_volume, -plan.used_weight)
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key
            best_quota_after = quota_copy

    return best_plan, best_quota_after


def init_module_quota(module_templates, remaining):
    total_g3 = remaining.get("G3", 0)
    target_mod_g3 = int(0.70 * total_g3)

    if not module_templates or target_mod_g3 <= 0:
        return {}

    quotas = {}
    each = max(1, target_mod_g3 // len(module_templates))
    for tpl in module_templates:
        max_by_support = remaining.get(tpl.support_type, 0) // max(1, tpl.support_count)
        quotas[tpl.name] = min(each, max_by_support, total_g3)
    return quotas


def write_vehicle_summary_csv(path, plans, truck):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_weight_kg", "loaded_volume_cm3", "module_count"
        ])
        for plan in plans:
            sv, wv, fs = local_truck_score(plan.used_volume, plan.used_weight, truck)
            w.writerow([
                plan.vehicle_id,
                round(sv, 6), round(wv, 6), round(fs, 6),
                dict(plan.actual_counts),
                round(plan.used_weight, 3),
                plan.used_volume,
                len(plan.placed_modules),
            ])


def write_items_csv(path, plan: FastTruck):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "record_type", "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id",
            "support_by", "direct_supported_weight", "template_name"
        ])

        for p in plan.placed:
            w.writerow([
                "item", p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id,
                p.support_by or "", round(p.direct_supported_weight, 6), ""
            ])

        for m in plan.placed_modules:
            w.writerow([
                "module", m.module_id, "MODULE_G3", "composite", m.x, m.y, m.z,
                m.length, m.width, m.height, m.weight,
                "", "", m.truck_id, "", "", m.template_name
            ])


def write_templates_csv(path, templates):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "template_name", "support_type", "support_count",
            "support_orientation_id", "g3_orientation_id",
            "length", "width", "height", "weight",
            "support_length", "support_width", "support_height",
            "g3_length", "g3_width", "g3_height",
            "volume_bbox", "score"
        ])
        for t in templates:
            w.writerow([
                t.name, t.support_type, t.support_count,
                t.support_orientation_id, t.g3_orientation_id,
                t.length, t.width, t.height, round(t.weight, 6),
                t.support_length, t.support_width, t.support_height,
                t.g3_length, t.g3_width, t.g3_height,
                t.volume_bbox, round(t.score, 6)
            ])


def solve_one_truck_type_with_modules(truck_name):
    truck = TRUCKS[truck_name]
    remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}

    module_templates = build_g3_module_templates_for_truck(truck_name)
    module_quota_left = init_module_quota(module_templates, remaining)

    plans = []
    vehicle_idx = 1

    print(f"[{truck_name}] 生成 G3 模块模板数: {len(module_templates)}")
    for tpl in module_templates:
        print(
            f"  模板 {tpl.name}: {tpl.support_count}*{tpl.support_type} + 1*G3, "
            f"尺寸=({tpl.length},{tpl.width},{tpl.height}), "
            f"重量={tpl.weight:.3f}, 配额={module_quota_left.get(tpl.name, 0)}"
        )

    while sum(remaining.values()) > 0:
        plan, quota_after = build_one_vehicle_best_with_modules(
            truck, remaining, vehicle_idx, module_templates, module_quota_left
        )

        if plan is None:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车未能装入任何货物，算法停止。")

        loaded_now = sum(plan.actual_counts.values())
        if loaded_now == 0:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车装载数为0，算法停止。")

        for t, c in plan.actual_counts.items():
            remaining[t] -= c

        module_quota_left = quota_after
        plans.append(plan)

        sv = plan.used_volume / (truck.length * truck.width * truck.effective_height)
        wv = plan.used_weight / truck.max_weight
        fs = 0.72 * sv + 0.28 * wv

        print(
            f"[{truck_name}] 第 {vehicle_idx} 辆车：装入 {loaded_now} 件（模块 {len(plan.placed_modules)} 个），"
            f"空间利用率={sv:.4f}，载重利用率={wv:.4f}，fullness_score={fs:.4f}，剩余={sum(remaining.values())}"
        )

        vehicle_idx += 1

    total_cost = len(plans) * truck.cost
    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)

    summary = {
        "truck": truck_name,
        "vehicle_count": len(plans),
        "total_cost": total_cost,
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "all_loaded": True,
    }
    return plans, summary, module_templates


def solve_for_truck(truck_name, outdir):
    truck = TRUCKS[truck_name]
    plans, summary, module_templates = solve_one_truck_type_with_modules(truck_name)
    truck_dir = os.path.join(outdir, truck_name)
    write_templates_csv(os.path.join(truck_dir, f"{truck_name}_G3模块模板.csv"), module_templates)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), plans, truck)
    for plan in plans:
        write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan)
    summary["output_dir"] = truck_dir
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="问题1.2：G3 支撑模块模板 + 主装箱（方案A）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2_G3模块方案A", help="输出目录")
    return parser.parse_args()


def main():
    random.seed(RANDOM_SEED)
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for truck_name in truck_list:
        print(f"===== {truck_name} =====")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        summary = solve_for_truck(truck_name, outdir)
        print(summary)
        print()


if __name__ == "__main__":
    main()
