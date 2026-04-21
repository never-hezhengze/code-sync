# -*- coding: utf-8 -*-
"""
问题1.2 最终严格复现整合版
文件名建议：p12_final_best_combo_v2.py

严格复现策略
------------
- 车型1：严格采用 hybrid 版模板逻辑
- 车型2：严格采用基础 platform 版模板逻辑

说明
----
本文件不再尝试“统一重写一套模板评分/筛选体系”。
而是直接在同一文件中保留两套已验证有效的构造逻辑：

1) solve_truck1_hybrid(...)
   - 对应此前把车型1做到 25 辆的 hybrid 思路
   - 模板库 = base + ext + lifted

2) solve_truck2_base(...)
   - 对应此前把车型2做到 13 辆的基础平台模板思路
   - 模板库 = base only

这样做的目标不是代码最简，而是结果最稳、最接近你已经实验验证的最优组合。
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

# hybrid（车型1）参数
HYBRID_KEEP_BASE = 18
HYBRID_KEEP_EXT = 14
HYBRID_KEEP_LIFTED = 18
LIFT_HEIGHT_RATIO = 0.75

# base-only（车型2）参数
BASE_ONLY_KEEP = 20  # 尝试更接近早期平台版规模


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
    source_kind: str = "base"  # base / ext / lifted


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


def feasible_g3_count_on_platform(base_L: int, base_W: int, gl: int, gw: int) -> int:
    if gl <= base_L and gw <= base_W:
        if 2 * gl <= base_L and gw <= base_W:
            return 2
        if gl <= base_L and 2 * gw <= base_W:
            return 2
        return 1
    return 0


def template_score(truck, base_L, base_W, total_h, total_wt, gl, gw, g3_count, kind: str):
    platform_area = base_L * base_W
    g3_area = g3_count * gl * gw
    height_util = total_h / truck.effective_height
    top_cover = g3_area / max(1, platform_area)
    weight_util = total_wt / truck.max_weight
    area_redundancy = (platform_area - g3_area) / max(1, platform_area)

    g3_bonus = 0.08 if g3_count == 2 else 0.0
    lift_bonus = 0.05 if kind == "lifted" and height_util >= LIFT_HEIGHT_RATIO else 0.0
    ext_bonus = 0.03 if kind == "ext" else 0.0

    return (
        0.30 * height_util
        + 0.24 * top_cover
        + 0.14 * (1.0 - weight_util)
        + 0.12 * (1.0 - area_redundancy)
        + g3_bonus + lift_bonus + ext_bonus
    )


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

                    # 对基础平台版和历史平台版保持 1~4 层
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
                                    name=f"MPV2_{kind}_{support_type}_{nx}x{ny}_L{layers}_S{s_ori.orient_id}_G3{g3_ori.orient_id}_K{g3_count}",
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


def generate_lifted_templates(truck_name: str, seed_templates: List[ModuleTemplate]) -> List[ModuleTemplate]:
    truck = TRUCKS[truck_name]
    lifted: List[ModuleTemplate] = []

    for tpl in seed_templates:
        sh = tpl.support_height
        max_layers = max(0, (truck.effective_height - tpl.g3_height) // sh)
        if max_layers <= tpl.layers:
            continue

        for new_layers in range(tpl.layers + 1, max_layers + 1):
            total_h = new_layers * sh + tpl.g3_height
            if total_h > truck.effective_height:
                continue

            height_util = total_h / truck.effective_height
            if height_util < LIFT_HEIGHT_RATIO:
                continue

            support_count = tpl.pattern_nx * tpl.pattern_ny * new_layers
            total_wt = support_count * CARGO_TYPES[tpl.support_type].weight + tpl.g3_count * CARGO_TYPES["G3"].weight
            if total_wt > truck.max_weight:
                continue

            bbox_vol = tpl.length * tpl.width * total_h
            score = template_score(
                truck, tpl.length, tpl.width, total_h, total_wt,
                tpl.g3_length, tpl.g3_width, tpl.g3_count, "lifted"
            )

            lifted.append(
                ModuleTemplate(
                    name=f"{tpl.name}_UP{new_layers}",
                    support_type=tpl.support_type,
                    support_orientation_id=tpl.support_orientation_id,
                    g3_orientation_id=tpl.g3_orientation_id,
                    pattern_nx=tpl.pattern_nx,
                    pattern_ny=tpl.pattern_ny,
                    layers=new_layers,
                    support_count=support_count,
                    g3_count=tpl.g3_count,
                    length=tpl.length,
                    width=tpl.width,
                    height=total_h,
                    weight=total_wt,
                    support_length=tpl.support_length,
                    support_width=tpl.support_width,
                    support_height=tpl.support_height,
                    g3_length=tpl.g3_length,
                    g3_width=tpl.g3_width,
                    g3_height=tpl.g3_height,
                    volume_bbox=bbox_vol,
                    score=score,
                    source_kind="lifted",
                )
            )

    return lifted


# =========================================================
# 严格复现：车型2 基础平台模板逻辑
# =========================================================
def build_templates_base_only_for_truck2() -> List[ModuleTemplate]:
    truck_name = "车型2"
    base_patterns = [(1, 2), (2, 1), (2, 2)]
    base_templates = generate_templates_by_patterns(truck_name, base_patterns, "base")
    base_templates = dedupe_templates(base_templates)
    # 尽量贴近早期基础平台版：按 score / 体积 / 重量排序后截断
    base_templates.sort(key=lambda t: (-t.score, -t.volume_bbox, t.weight))
    return base_templates[:BASE_ONLY_KEEP]


# =========================================================
# 严格复现：车型1 hybrid 模板逻辑
# =========================================================
def build_templates_hybrid_for_truck1() -> List[ModuleTemplate]:
    truck_name = "车型1"
    base_patterns = [(1, 2), (2, 1), (2, 2)]
    ext_patterns = [(1, 3), (3, 1), (2, 3), (3, 2)]

    base_templates = generate_templates_by_patterns(truck_name, base_patterns, "base")
    base_templates = dedupe_templates(base_templates)
    base_templates.sort(key=lambda t: (-t.score, -t.g3_count, -t.volume_bbox, t.weight))

    ext_templates = generate_templates_by_patterns(truck_name, ext_patterns, "ext")
    ext_templates = dedupe_templates(ext_templates)
    ext_templates.sort(key=lambda t: (-t.score, -t.g3_count, -t.volume_bbox, t.weight))

    lifted_seed = base_templates + ext_templates
    lifted_templates = generate_lifted_templates(truck_name, lifted_seed)
    lifted_templates = dedupe_templates(lifted_templates)
    lifted_templates.sort(key=lambda t: (-t.score, -t.height, -t.g3_count, -t.volume_bbox, t.weight))

    mixed = (
        base_templates[:HYBRID_KEEP_BASE]
        + ext_templates[:HYBRID_KEEP_EXT]
        + lifted_templates[:HYBRID_KEEP_LIFTED]
    )
    mixed = dedupe_templates(mixed)
    mixed.sort(key=lambda t: (-t.score, -t.g3_count, -t.height, -t.volume_bbox, t.weight))
    return mixed


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
        self.module_history: List[str] = []

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
            x=sp["x"], y=sp["y"], z=sp["z"],
            length=l, width=w, height=h,
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
        self.actual_counts["G3"] += tpl.g3_count

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


def eval_module_candidate(tpl: ModuleTemplate, sp, truck_obj, truck_name: str):
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

    kind_bonus = 0.0
    if truck_name == "车型1":
        if tpl.source_kind == "lifted":
            kind_bonus = 0.04
        elif tpl.source_kind == "ext":
            kind_bonus = 0.025

    return 0.56 * fill_ratio + 0.20 * height_bonus + 0.10 * edge_bonus + g3_bonus + kind_bonus


def place_one_best_with_modules(truck_obj, remaining, type_order, module_templates, module_quota_left, truck_name: str):
    best = None
    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    if remaining.get("G3", 0) > 0:
        for sp_idx, _sp in enumerate(candidate_spaces):
            for tpl in module_templates:
                if module_quota_left.get(tpl.name, 0) <= 0:
                    continue
                if remaining.get(tpl.support_type, 0) < tpl.support_count:
                    continue
                if remaining.get("G3", 0) < tpl.g3_count:
                    continue
                if not truck_obj.can_place_module(tpl, sp_idx):
                    continue

                val = eval_module_candidate(tpl, truck_obj.spaces[sp_idx], truck_obj, truck_name)
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
        remaining["G3"] -= tpl.g3_count
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


def init_module_quota(module_templates: List[ModuleTemplate], remaining: Dict[str, int], truck_name: str):
    total_g3 = remaining.get("G3", 0)
    target_mod_g3 = int(0.75 * total_g3) if truck_name == "车型1" else int(0.70 * total_g3)

    if not module_templates or target_mod_g3 <= 0:
        return {}

    quotas = {}
    denom = sum(max(1, tpl.g3_count) for tpl in module_templates)
    unit = max(1, target_mod_g3 // denom)

    for tpl in module_templates:
        max_by_support = remaining.get(tpl.support_type, 0) // max(1, tpl.support_count)
        max_by_g3 = total_g3 // max(1, tpl.g3_count)
        base_quota = max(1, unit * tpl.g3_count)

        if truck_name == "车型1":
            if tpl.source_kind == "lifted":
                base_quota += 1
            elif tpl.source_kind == "ext":
                base_quota += 1

        quotas[tpl.name] = min(base_quota, max_by_support, max_by_g3)

    return quotas


def load_one_truck_with_modules(truck, remaining, strategy, vehicle_idx, module_templates, module_quota_left, truck_name: str):
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)

    while True:
        ok = place_one_best_with_modules(
            truck_obj=truck_obj,
            remaining=remaining,
            type_order=type_order,
            module_templates=module_templates,
            module_quota_left=module_quota_left,
            truck_name=truck_name,
        )
        if not ok:
            break

    return truck_obj


def build_one_vehicle_best_with_modules(truck, remaining, vehicle_idx, module_templates, module_quota_left, truck_name: str):
    strategies = ["std_first", "dir_first", "mixed", "g3_first"]

    best_plan = None
    best_key = None
    best_quota_after = None

    for st in strategies:
        rem_copy = deepcopy(remaining)
        quota_copy = deepcopy(module_quota_left)
        plan = load_one_truck_with_modules(truck, rem_copy, st, vehicle_idx, module_templates, quota_copy, truck_name)

        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue

        key = (loaded_cnt, plan.used_volume, -plan.used_weight)
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key
            best_quota_after = quota_copy

    return best_plan, best_quota_after


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
                len(getattr(plan, "module_history", [])),
            ])


def write_items_csv(path, plan: FastTruck):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id",
            "support_by", "direct_supported_weight"
        ])

        for p in plan.placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id,
                p.support_by or "",
                round(p.direct_supported_weight, 6),
            ])


def write_templates_csv(path, templates: List[ModuleTemplate]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "template_name",
            "support_type", "support_orientation_id", "g3_orientation_id",
            "pattern_nx", "pattern_ny", "layers", "support_count", "g3_count",
            "length", "width", "height", "weight",
            "support_length", "support_width", "support_height",
            "g3_length", "g3_width", "g3_height",
            "volume_bbox", "score", "source_kind"
        ])
        for t in templates:
            w.writerow([
                t.name,
                t.support_type, t.support_orientation_id, t.g3_orientation_id,
                t.pattern_nx, t.pattern_ny, t.layers, t.support_count, t.g3_count,
                t.length, t.width, t.height, round(t.weight, 6),
                t.support_length, t.support_width, t.support_height,
                t.g3_length, t.g3_width, t.g3_height,
                t.volume_bbox, round(t.score, 6), t.source_kind
            ])


def solve_one_truck_type(truck_name: str):
    truck = TRUCKS[truck_name]
    remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}

    if truck_name == "车型1":
        module_templates = build_templates_hybrid_for_truck1()
    else:
        module_templates = build_templates_base_only_for_truck2()

    module_quota_left = init_module_quota(module_templates, remaining, truck_name)

    plans = []
    vehicle_idx = 1

    base_n = sum(1 for t in module_templates if t.source_kind == "base")
    ext_n = sum(1 for t in module_templates if t.source_kind == "ext")
    lift_n = sum(1 for t in module_templates if t.source_kind == "lifted")
    print(f"[{truck_name}] 严格复现模板库总数: {len(module_templates)}（base={base_n}, ext={ext_n}, lifted={lift_n}）")

    while sum(remaining.values()) > 0:
        plan, quota_after = build_one_vehicle_best_with_modules(
            truck=truck,
            remaining=remaining,
            vehicle_idx=vehicle_idx,
            module_templates=module_templates,
            module_quota_left=module_quota_left,
            truck_name=truck_name,
        )
        if plan is None or sum(plan.actual_counts.values()) == 0:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车未能装入任何货物，算法停止。")

        errors = validate_truck_plan(plan, truck)
        if errors:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车校验失败：" + " | ".join(errors[:8]))

        for t, c in plan.actual_counts.items():
            remaining[t] -= c
        module_quota_left = quota_after
        plans.append(plan)

        sv = plan.used_volume / (truck.length * truck.width * truck.effective_height)
        wv = plan.used_weight / truck.max_weight
        fs = 0.72 * sv + 0.28 * wv
        print(
            f"[{truck_name}] 第 {vehicle_idx} 辆车："
            f"装入 {sum(plan.actual_counts.values())} 件（模块 {len(getattr(plan, 'module_history', []))} 个），"
            f"空间利用率={sv:.4f}，载重利用率={wv:.4f}，fullness_score={fs:.4f}，"
            f"剩余={sum(remaining.values())}"
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
    plans, summary, module_templates = solve_one_truck_type(truck_name)

    truck_dir = os.path.join(outdir, truck_name)
    write_templates_csv(os.path.join(truck_dir, f"{truck_name}_最终严格复现模板库.csv"), module_templates)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), plans, truck)
    for plan in plans:
        write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan)

    summary["output_dir"] = truck_dir
    return summary



# =========================================================
# 模块展开校验补丁：模块逐件落地 + 全车复核
# =========================================================
def _patch_next_item_id(self, type_id: str) -> str:
    self.serial_counter[type_id] += 1
    return f"{type_id}_{self.vehicle_id}_{self.serial_counter[type_id]:04d}"


def _patch_append_placed_cargo(self, placed: PlacedCargo):
    self.placed.append(placed)
    self.placed_map[placed.item_id] = placed
    self.used_weight += placed.weight
    self.used_volume += placed.volume
    self.actual_counts[placed.type_id] += 1


def _patch_overlap_len(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def _patch_build_module_items(self, tpl: ModuleTemplate, sp_idx: int) -> List[PlacedCargo]:
    sp = self.spaces[sp_idx]
    support_ori = next(ori for ori in ORIENTATIONS[tpl.support_type] if ori.orient_id == tpl.support_orientation_id)
    g3_ori = next(ori for ori in ORIENTATIONS["G3"] if ori.orient_id == tpl.g3_orientation_id)
    sl, sw, sh = support_ori.size
    gl, gw, gh = g3_ori.size

    items: List[PlacedCargo] = []
    lower_map: Dict[Tuple[int, int, int], str] = {}

    for layer in range(tpl.layers):
        z0 = sp["z"] + layer * sh
        for ix in range(tpl.pattern_nx):
            x0 = sp["x"] + ix * sl
            for iy in range(tpl.pattern_ny):
                y0 = sp["y"] + iy * sw
                support_by = None if layer == 0 else lower_map[(layer - 1, ix, iy)]
                item_id = self._next_item_id(tpl.support_type)
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
                items.append(placed)
                lower_map[(layer, ix, iy)] = item_id

    top_z = sp["z"] + tpl.layers * sh
    g3_positions: List[Tuple[int, int]] = []
    if tpl.g3_count == 1:
        g3_positions.append((sp["x"], sp["y"]))
    else:
        if 2 * gl <= tpl.length:
            g3_positions.extend([(sp["x"], sp["y"]), (sp["x"] + gl, sp["y"])])
        elif 2 * gw <= tpl.width:
            g3_positions.extend([(sp["x"], sp["y"]), (sp["x"], sp["y"] + gw)])
        else:
            raise RuntimeError(f"模板 {tpl.name} 无法为 2 个 G3 生成合法顶层布局。")

    top_support_ids = [lower_map[(tpl.layers - 1, ix, iy)] for ix in range(tpl.pattern_nx) for iy in range(tpl.pattern_ny)]
    support_by_str = ";".join(top_support_ids)
    for x0, y0 in g3_positions:
        item_id = self._next_item_id("G3")
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
            support_by=support_by_str,
        )
        items.append(placed)

    return items


def _patch_validate_module_items(self, items: List[PlacedCargo], base_z: int):
    direct_load = Counter()
    top_map: Dict[int, List[PlacedCargo]] = {}
    for it in items:
        top_map.setdefault(it.z + it.height, []).append(it)

    for i, a in enumerate(items):
        if a.x < 0 or a.y < 0 or a.z < 0:
            raise RuntimeError(f"模块展开出现负坐标: {a.item_id}")
        if a.x + a.length > self.L or a.y + a.width > self.W or a.z + a.height > self.H:
            raise RuntimeError(f"模块展开越界: {a.item_id}")
        for b in items[i + 1:]:
            if (_patch_overlap_len(a.x, a.x + a.length, b.x, b.x + b.length) > 0
                    and _patch_overlap_len(a.y, a.y + a.width, b.y, b.y + b.width) > 0
                    and _patch_overlap_len(a.z, a.z + a.height, b.z, b.z + b.height) > 0):
                raise RuntimeError(f"模块内部货物重叠: {a.item_id} 与 {b.item_id}")
        for b in self.placed:
            if (_patch_overlap_len(a.x, a.x + a.length, b.x, b.x + b.length) > 0
                    and _patch_overlap_len(a.y, a.y + a.width, b.y, b.y + b.width) > 0
                    and _patch_overlap_len(a.z, a.z + a.height, b.z, b.z + b.height) > 0):
                raise RuntimeError(f"模块与已有货物重叠: {a.item_id} 与 {b.item_id}")

    id_map = {it.item_id: it for it in items}
    for it in items:
        if it.z == base_z:
            continue
        supporters = []
        area_sum = 0
        for sup in top_map.get(it.z, []):
            ox = _patch_overlap_len(it.x, it.x + it.length, sup.x, sup.x + sup.length)
            oy = _patch_overlap_len(it.y, it.y + it.width, sup.y, sup.y + sup.width)
            if ox > 0 and oy > 0:
                area = ox * oy
                supporters.append((sup, area))
                area_sum += area
        if area_sum + 1e-9 < it.length * it.width:
            raise RuntimeError(f"模块展开存在支撑不足: {it.item_id}")
        for sup, area in supporters:
            if sup.category == "fragile":
                raise RuntimeError(f"易碎件被用作支撑: {sup.item_id}")
            if it.type_id == "G3" and sup.type_id not in ("G1", "G2"):
                raise RuntimeError(f"G3 非法支撑: {it.item_id} supported by {sup.item_id}")
            direct_load[sup.item_id] += it.weight * (area / (it.length * it.width))

    for sup_id, wt in direct_load.items():
        sup = id_map[sup_id]
        limit = CARGO_TYPES[sup.type_id].max_support_pressure
        pressure = wt / max(1e-9, sup.top_area_m2)
        if pressure > limit + 1e-9:
            raise RuntimeError(f"模块展开承压超限: {sup_id}, {pressure:.6f} > {limit:.6f}")


def _patch_place_module(self, tpl: ModuleTemplate, sp_idx: int):
    sp = self.spaces[sp_idx]
    items = self._build_module_items(tpl, sp_idx)
    self._validate_module_items(items, sp["z"])

    direct_load = Counter()
    top_map: Dict[int, List[PlacedCargo]] = {}
    for it in items:
        top_map.setdefault(it.z + it.height, []).append(it)

    for it in items:
        if it.z == sp["z"]:
            continue
        for sup in top_map.get(it.z, []):
            ox = _patch_overlap_len(it.x, it.x + it.length, sup.x, sup.x + sup.length)
            oy = _patch_overlap_len(it.y, it.y + it.width, sup.y, sup.y + sup.width)
            if ox > 0 and oy > 0:
                direct_load[sup.item_id] += it.weight * ((ox * oy) / (it.length * it.width))

    for it in items:
        self._append_placed_cargo(it)
    for sup_id, wt in direct_load.items():
        self.placed_map[sup_id].direct_supported_weight += wt

    self.module_history.append(tpl.name)

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


def validate_truck_plan(plan: FastTruck, truck) -> List[str]:
    errors: List[str] = []
    items = plan.placed
    top_map: Dict[int, List[PlacedCargo]] = {}

    for it in items:
        top_map.setdefault(it.z + it.height, []).append(it)

    for i, a in enumerate(items):
        if a.x < 0 or a.y < 0 or a.z < 0:
            errors.append(f"负坐标: {a.item_id}")
        if a.x + a.length > truck.length or a.y + a.width > truck.width or a.z + a.height > truck.effective_height:
            errors.append(f"越界: {a.item_id}")
        for b in items[i + 1:]:
            if (_patch_overlap_len(a.x, a.x + a.length, b.x, b.x + b.length) > 0
                    and _patch_overlap_len(a.y, a.y + a.width, b.y, b.y + b.width) > 0
                    and _patch_overlap_len(a.z, a.z + a.height, b.z, b.z + b.height) > 0):
                errors.append(f"重叠: {a.item_id} 与 {b.item_id}")

    total_weight = sum(p.weight for p in items)
    if abs(total_weight - plan.used_weight) > 1e-6:
        errors.append(f"used_weight 与逐件重量不一致: {plan.used_weight:.6f} vs {total_weight:.6f}")
    total_volume = sum(p.volume for p in items)
    if total_volume != plan.used_volume:
        errors.append(f"used_volume 与逐件体积不一致: {plan.used_volume} vs {total_volume}")
    if plan.used_weight > truck.max_weight + 1e-9:
        errors.append(f"总重量超限: {plan.used_weight:.6f} > {truck.max_weight:.6f}")

    direct_load = Counter()
    for it in items:
        if it.z == 0:
            continue
        supporters = []
        area_sum = 0
        for sup in top_map.get(it.z, []):
            ox = _patch_overlap_len(it.x, it.x + it.length, sup.x, sup.x + sup.length)
            oy = _patch_overlap_len(it.y, it.y + it.width, sup.y, sup.y + sup.width)
            if ox > 0 and oy > 0:
                area = ox * oy
                supporters.append((sup, area))
                area_sum += area
        if area_sum + 1e-9 < it.length * it.width:
            errors.append(f"支撑不足: {it.item_id}")
            continue
        for sup, area in supporters:
            if sup.category == "fragile":
                errors.append(f"易碎件作为支撑: {sup.item_id} -> {it.item_id}")
            if it.type_id == "G3" and sup.type_id not in ("G1", "G2"):
                errors.append(f"G3 非法支撑: {sup.item_id} -> {it.item_id}")
            direct_load[sup.item_id] += it.weight * (area / (it.length * it.width))

    for sup_id, wt in direct_load.items():
        sup = plan.placed_map[sup_id]
        limit = CARGO_TYPES[sup.type_id].max_support_pressure
        pressure = wt / max(1e-9, sup.top_area_m2)
        if pressure > limit + 1e-9:
            errors.append(f"承压超限: {sup_id}, {pressure:.6f} > {limit:.6f}")

    for frag in (it for it in items if it.category == "fragile"):
        for other in items:
            if other.item_id == frag.item_id:
                continue
            if other.z >= frag.z + frag.height:
                ox = _patch_overlap_len(frag.x, frag.x + frag.length, other.x, other.x + other.length)
                oy = _patch_overlap_len(frag.y, frag.y + frag.width, other.y, other.y + other.width)
                if ox > 0 and oy > 0:
                    errors.append(f"G3 上方禁放被破坏: {frag.item_id} 与 {other.item_id}")

    return errors


FastTruck._next_item_id = _patch_next_item_id
FastTruck._append_placed_cargo = _patch_append_placed_cargo
FastTruck._build_module_items = _patch_build_module_items
FastTruck._validate_module_items = _patch_validate_module_items
FastTruck.place_module = _patch_place_module


def parse_args():
    parser = argparse.ArgumentParser(description="问题1.2 最终严格复现整合版")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2(final)", help="输出目录")
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
