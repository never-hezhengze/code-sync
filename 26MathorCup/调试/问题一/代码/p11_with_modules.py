#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
MathorCup D题 - 问题1.1 改进版（集成p12模块系统）

目标：单车满载优化 + 灵活的模块选择系统
- 允许使用p12模块（G1/G2支撑+G3顶部），但不强制
- 在模块和单件之间自主选择，获得更优的装箱方案
- 保持单车装运的框架
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

# 参数配置
MAX_SPACES_TO_CHECK = 100
MIN_SPACE_VOLUME = 15000
RANDOM_SEED = 2026
random.seed(RANDOM_SEED)

# 模板生成参数
BASE_PATTERNS = [(1, 2), (2, 1), (2, 2)]
EXT_PATTERNS = [(1, 3), (3, 1), (2, 3), (3, 2)]
MAX_TEMPLATE_KEEP = 25


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


@dataclass(frozen=True)
class ModuleTemplate:
    name: str
    support_type: str
    support_orientation_id: int
    g3_orientation_id: int
    pattern_nx: int
    pattern_ny: int
    layers: int
    support_count: int
    g3_count: int
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
    source_kind: str = "base"


@dataclass
class VehicleResult:
    vehicle_id: str
    placed: List[PlacedCargo]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int
    strategy: str
    module_count: int = 0

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


def template_score(truck, base_L, base_W, total_h, total_wt, gl, gw, g3_count, kind: str):
    platform_area = base_L * base_W
    g3_area = g3_count * gl * gw
    height_util = total_h / truck.effective_height
    top_cover = g3_area / max(1, platform_area)
    weight_util = total_wt / truck.max_weight
    area_redundancy = (platform_area - g3_area) / max(1, platform_area)

    g3_bonus = 0.08 if g3_count == 2 else 0.0
    lift_bonus = 0.03 if kind == "lifted" else 0.0
    ext_bonus = 0.02 if kind == "ext" else 0.0

    return (
        0.30 * height_util
        + 0.24 * top_cover
        + 0.14 * (1.0 - weight_util)
        + 0.12 * (1.0 - area_redundancy)
        + g3_bonus + lift_bonus + ext_bonus
    )


def feasible_g3_count_on_platform(base_L: int, base_W: int, gl: int, gw: int) -> int:
    if gl <= base_L and gw <= base_W:
        if 2 * gl <= base_L and gw <= base_W:
            return 2
        if gl <= base_L and 2 * gw <= base_W:
            return 2
        return 1
    return 0


def generate_templates_by_patterns(truck_name: str, patterns: List[Tuple[int, int]], kind: str) -> List[ModuleTemplate]:
    truck = TRUCKS[truck_name]
    g3 = CARGO_TYPES["G3"]
    templates: List[ModuleTemplate] = []

    for support_type in ("G1", "G2"):
        support_cargo = CARGO_TYPES[support_type]

        for s_ori in ORIENTATIONS[support_type]:
            sl, sw, sh = s_ori.size

            for nx, ny in patterns:
                base_L = nx * sl
                base_W = ny * sw

                if base_L > truck.length or base_W > truck.width:
                    continue

                for g3_ori in ORIENTATIONS["G3"]:
                    gl, gw, gh = g3_ori.size
                    max_g3 = feasible_g3_count_on_platform(base_L, base_W, gl, gw)
                    if max_g3 <= 0:
                        continue

                    max_layers = max(0, (truck.effective_height - gh) // sh)
                    if max_layers <= 0:
                        continue

                    for layers in range(1, min(max_layers, 4) + 1):
                        total_h = layers * sh + gh
                        if total_h > truck.effective_height:
                            continue

                        support_count = nx * ny * layers

                        for g3_count in (1, 2):
                            if g3_count > max_g3:
                                continue

                            total_wt = support_count * support_cargo.weight + g3_count * g3.weight
                            if total_wt > truck.max_weight:
                                continue

                            bbox_vol = base_L * base_W * total_h
                            score = template_score(
                                truck, base_L, base_W, total_h, total_wt, gl, gw, g3_count, kind
                            )

                            templates.append(
                                ModuleTemplate(
                                    name=f"TPL_{kind}_{support_type}_{nx}x{ny}_L{layers}_G{g3_count}",
                                    support_type=support_type,
                                    support_orientation_id=s_ori.orient_id,
                                    g3_orientation_id=g3_ori.orient_id,
                                    pattern_nx=nx,
                                    pattern_ny=ny,
                                    layers=layers,
                                    support_count=support_count,
                                    g3_count=g3_count,
                                    length=base_L,
                                    width=base_W,
                                    height=total_h,
                                    weight=total_wt,
                                    support_length=sl,
                                    support_width=sw,
                                    support_height=sh,
                                    g3_length=gl,
                                    g3_width=gw,
                                    g3_height=gh,
                                    volume_bbox=bbox_vol,
                                    score=score,
                                    source_kind=kind,
                                )
                            )

    return templates


def dedupe_templates(templates: List[ModuleTemplate]) -> List[ModuleTemplate]:
    best_map = {}
    for tpl in templates:
        key = (
            tpl.support_type,
            tpl.support_orientation_id,
            tpl.g3_orientation_id,
            tpl.pattern_nx,
            tpl.pattern_ny,
            tpl.layers,
            tpl.g3_count,
            tpl.length,
            tpl.width,
            tpl.height,
        )
        if key not in best_map or tpl.score > best_map[key].score:
            best_map[key] = tpl
    return list(best_map.values())


def build_template_library(truck_name: str) -> List[ModuleTemplate]:
    """生成模板库：base + ext"""
    base_templates = generate_templates_by_patterns(truck_name, BASE_PATTERNS, "base")
    base_templates = dedupe_templates(base_templates)
    base_templates.sort(key=lambda t: (-t.score, -t.g3_count, -t.volume_bbox, t.weight))

    ext_templates = generate_templates_by_patterns(truck_name, EXT_PATTERNS, "ext")
    ext_templates = dedupe_templates(ext_templates)
    ext_templates.sort(key=lambda t: (-t.score, -t.g3_count, -t.volume_bbox, t.weight))

    mixed = (base_templates + ext_templates)
    mixed = dedupe_templates(mixed)
    mixed.sort(key=lambda t: (-t.score, -t.g3_count, -t.height, -t.volume_bbox, t.weight))
    return mixed[:MAX_TEMPLATE_KEEP]


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
        self.module_counter = 0

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

    def can_place_module(self, tpl: ModuleTemplate, sp_idx: int) -> bool:
        sp = self.spaces[sp_idx]
        if sp["z"] != 0:
            return False
        if tpl.length > sp["l"] or tpl.width > sp["w"] or tpl.height > sp["h"]:
            return False
        if self.used_weight + tpl.weight > self.max_weight:
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

    def place_module(self, tpl: ModuleTemplate, sp_idx: int) -> None:
        """展开并放置模块"""
        sp = self.spaces[sp_idx]
        support_ori = next(ori for ori in ORIENTATIONS[tpl.support_type] if ori.orient_id == tpl.support_orientation_id)
        g3_ori = next(ori for ori in ORIENTATIONS["G3"] if ori.orient_id == tpl.g3_orientation_id)
        sl, sw, sh = support_ori.size
        gl, gw, gh = g3_ori.size

        # 放置支撑件（通常是G1/G2）
        lower_map: Dict[Tuple[int, int, int], str] = {}
        for layer in range(tpl.layers):
            z0 = sp["z"] + layer * sh
            for ix in range(tpl.pattern_nx):
                x0 = sp["x"] + ix * sl
                for iy in range(tpl.pattern_ny):
                    y0 = sp["y"] + iy * sw
                    support_by = None if layer == 0 else lower_map[(layer - 1, ix, iy)]
                    self.serial_counter[tpl.support_type] += 1
                    item_id = f"{tpl.support_type}_{self.vehicle_id}_{self.serial_counter[tpl.support_type]:04d}"
                    placed = PlacedCargo(
                        item_id=item_id,
                        type_id=tpl.support_type,
                        category=CARGO_TYPES[tpl.support_type].category,
                        x=x0, y=y0, z=z0,
                        length=sl, width=sw, height=sh,
                        weight=CARGO_TYPES[tpl.support_type].weight,
                        rotation=support_ori.rotation,
                        orientation_id=support_ori.orient_id,
                        truck_id=self.vehicle_id,
                        support_by=support_by,
                    )
                    self.placed.append(placed)
                    self.placed_map[item_id] = placed
                    self.used_weight += placed.weight
                    self.used_volume += placed.volume
                    self.actual_counts[tpl.support_type] += 1
                    lower_map[(layer, ix, iy)] = item_id
                    if support_by is not None and support_by in self.placed_map:
                        self.placed_map[support_by].direct_supported_weight += placed.weight

        # 放置G3（易碎件）在顶部
        top_z = sp["z"] + tpl.layers * sh
        g3_positions: List[Tuple[int, int]] = []
        if tpl.g3_count == 1:
            g3_positions.append((sp["x"], sp["y"]))
        else:
            if 2 * gl <= tpl.length:
                g3_positions.extend([(sp["x"], sp["y"]), (sp["x"] + gl, sp["y"])])
            elif 2 * gw <= tpl.width:
                g3_positions.extend([(sp["x"], sp["y"]), (sp["x"], sp["y"] + gw)])

        for x0, y0 in g3_positions:
            self.serial_counter["G3"] += 1
            item_id = f"G3_{self.vehicle_id}_{self.serial_counter['G3']:04d}"
            placed = PlacedCargo(
                item_id=item_id,
                type_id="G3",
                category=CARGO_TYPES["G3"].category,
                x=x0, y=y0, z=top_z,
                length=gl, width=gw, height=gh,
                weight=CARGO_TYPES["G3"].weight,
                rotation=g3_ori.rotation,
                orientation_id=g3_ori.orient_id,
                truck_id=self.vehicle_id,
                support_by=str([lower_map[(tpl.layers - 1, ix, iy)] for ix in range(tpl.pattern_nx) for iy in range(tpl.pattern_ny)]),
            )
            self.placed.append(placed)
            self.placed_map[item_id] = placed
            self.used_weight += placed.weight
            self.used_volume += placed.volume
            self.actual_counts["G3"] += 1

        # 更新空间
        l, w = tpl.length, tpl.width
        right = {
            "x": sp["x"] + l, "y": sp["y"], "z": sp["z"],
            "l": sp["l"] - l, "w": sp["w"], "h": sp["h"],
            "support_item_id": None,
            "support_type_id": None,
            "support_length": self.L,
            "support_width": self.W,
        }
        front = {
            "x": sp["x"], "y": sp["y"] + w, "z": sp["z"],
            "l": l, "w": sp["w"] - w, "h": sp["h"],
            "support_item_id": None,
            "support_type_id": None,
            "support_length": self.L,
            "support_width": self.W,
        }
        self.spaces.pop(sp_idx)
        self.spaces.extend([right, front])
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]
        self.module_counter += 1


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


def eval_module_candidate(tpl: ModuleTemplate, sp, truck_obj) -> Optional[float]:
    if tpl.length > sp["l"] or tpl.width > sp["w"] or tpl.height > sp["h"]:
        return None
    if sp["z"] != 0:
        return None
    if truck_obj.used_weight + tpl.weight > truck_obj.max_weight:
        return None

    fill_ratio = tpl.volume_bbox / max(1, sp["l"] * sp["w"] * sp["h"])
    height_bonus = tpl.height / max(1, truck_obj.H)
    edge_bonus = 0.02 if (sp["x"] == 0 or sp["y"] == 0) else 0.0
    g3_bonus = 0.06 if tpl.g3_count == 2 else 0.0

    return 0.56 * fill_ratio + 0.20 * height_bonus + 0.10 * edge_bonus + g3_bonus


def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], type_order: List[str], module_templates: List[ModuleTemplate]) -> bool:
    """混合装箱：在模块和单件之间选择"""
    best = None
    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    # 尝试放置模块（仅在底层）
    if remaining.get("G3", 0) > 0:
        for sp_idx, sp in enumerate(candidate_spaces):
            for tpl in module_templates:
                if remaining.get(tpl.support_type, 0) < tpl.support_count:
                    continue
                if remaining.get("G3", 0) < tpl.g3_count:
                    continue
                if not truck_obj.can_place_module(tpl, sp_idx):
                    continue
                val = eval_module_candidate(tpl, sp, truck_obj)
                if val is None:
                    continue
                if best is None or val > best[0]:
                    best = (val, "module", tpl, sp_idx)

    # 尝试放置单件
    for sp_idx, sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = eval_candidate(type_id, ori, sp, remaining, truck_obj)
                if val is None:
                    continue
                # 模块相比单件有slight preference，但不强制
                threshold = best[0] + 0.01 if best else 0
                if best is None or val > threshold:
                    best = (val, "item", (type_id, ori), sp_idx)

    if best is None:
        return False

    _, kind, obj, sp_idx = best
    if kind == "module":
        tpl = obj
        truck_obj.place_module(tpl, sp_idx)
        remaining[tpl.support_type] -= tpl.support_count
        remaining["G3"] -= tpl.g3_count
    else:
        type_id, ori = obj
        truck_obj.place_item(type_id, ori, sp_idx)
        remaining[type_id] -= 1

    return True


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
        return sorted(["G1", "G2", "G3", "G4", "G5"], key=lambda t: CARGO_TYPES[t].weight, reverse=True)
    elif strategy == "bulky_first":
        return sorted(["G1", "G2", "G3", "G4", "G5"], key=lambda t: CARGO_TYPES[t].volume, reverse=True)
    else:
        arr = ["G3", "G4", "G5", "G1", "G2"]
        random.shuffle(arr)
        return arr


def load_one_truck(truck: Truck, remaining: Dict[str, int], strategy: str, vehicle_idx: int, module_templates: List[ModuleTemplate]) -> FastTruck:
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)
    while True:
        ok = place_one_best(truck_obj, remaining, type_order, module_templates)
        if not ok:
            break
    return truck_obj


def build_one_vehicle_best(truck: Truck, vehicle_idx: int, module_templates: List[ModuleTemplate]) -> VehicleResult:
    """尝试多个策略，选择最优结果"""
    initial_remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}
    strategies = ["std_first", "dir_first", "mixed", "g3_first", "heavy_first", "bulky_first"]
    best_plan = None
    best_key = None
    best_module_count = 0
    
    for st in strategies:
        rem_copy = deepcopy(initial_remaining)
        plan = load_one_truck(truck, rem_copy, st, vehicle_idx, module_templates)
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
                module_count=plan.module_counter,
            )
            best_key = key
            best_module_count = plan.module_counter
    
    if best_plan is None:
        raise RuntimeError(f"{truck.name} 单车求解失败：未能装入任何货物。")
    return best_plan


def write_vehicle_summary_csv(path: str, plan: VehicleResult, truck: Truck) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["vehicle_id", "space_utilization", "weight_utilization", "fullness_score", "actual_counts", "loaded_count", "loaded_weight_kg", "loaded_volume_cm3", "strategy", "module_count"])
        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
        w.writerow([plan.vehicle_id, round(sv, 6), round(wv, 6), round(fs, 6), dict(plan.actual_counts), plan.item_count, round(plan.used_weight, 3), plan.used_volume, plan.strategy, plan.module_count])


def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "type_id", "category", "x", "y", "z", "length", "width", "height", "weight", "orientation_id", "rotation", "truck_id", "support_by", "direct_supported_weight"])
        for p in placed:
            w.writerow([p.item_id, p.type_id, p.category, p.x, p.y, p.z, p.length, p.width, p.height, p.weight, p.orientation_id, p.rotation, p.truck_id, p.support_by or '', round(p.direct_supported_weight, 6)])


def solve_problem_11_with_modules(truck_name: str, module_templates: List[ModuleTemplate]) -> Tuple[VehicleResult, Dict[str, object]]:
    truck = TRUCKS[truck_name]
    best_plan = build_one_vehicle_best(truck, vehicle_idx=1, module_templates=module_templates)
    sv, wv, fs = truck_score(truck, best_plan.used_volume, best_plan.used_weight)
    print(f"[{truck_name}] 单车装载结果：装入 {best_plan.item_count} 件（模块 {best_plan.module_count} 个），空间利用率={sv:.4f}，载重利用率={wv:.4f}，fullness_score={fs:.4f}，策略={best_plan.strategy}")
    summary = {
        "truck": truck_name,
        "vehicle_count": 1,
        "loaded_count": best_plan.item_count,
        "module_count": best_plan.module_count,
        "total_cost": truck.cost,
        "space_utilization": round(sv, 6),
        "weight_utilization": round(wv, 6),
        "fullness_score": round(fs, 6),
        "all_loaded": False,
    }
    return best_plan, summary


def solve_for_truck(truck_name: str, outdir: str) -> Dict[str, object]:
    truck = TRUCKS[truck_name]
    module_templates = build_template_library(truck_name)
    print(f"  生成模板库：{len(module_templates)} 个")
    plan, summary = solve_problem_11_with_modules(truck_name, module_templates)
    truck_dir = os.path.join(outdir, truck_name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), plan, truck)
    write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan.placed)
    summary["output_dir"] = truck_dir
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.1 改进版（集成p12模块系统）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.1(final)", help="输出目录")
    return parser.parse_args()


def main():
    random.seed(RANDOM_SEED)
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for truck_name in truck_list:
        print("=" * 72)
        print(f"开始求解问题1.1（改进版 + 模块系统）：{truck_name}")
        print("=" * 72)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        summary = solve_for_truck(truck_name, outdir)
        print(summary)
        print()


if __name__ == "__main__":
    main()
