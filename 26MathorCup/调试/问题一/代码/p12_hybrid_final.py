#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
MathorCup D题 - 问题1.2 终极修正版
保留 p12_final.py 的 GA + SA/LNS 外层框架，
将内层单车装箱器替换为基于 p11_final.py 思路的“物理约束 + 空间切分 + beam search”版本。

修正目标：
1. 消除原 p12_final.py 中由分层/分行构造带来的悬空问题；
2. 用真实可用空间集合替代“整层推进”，减少成片大空隙；
3. 保留原问题1.2的：quota、GA 单车策略搜索、外层减车、SA/LNS 压缩框架。
"""

import argparse
import csv
import math
import os
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from mathorcup_d_common import (
    Orientation,
    Truck,
    CARGO_TYPES,
    TRUCKS,
    generate_orientations,
    truck_score,
)
ORI_CACHE = {k: generate_orientations(v) for k, v in CARGO_TYPES.items()}
TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]
TYPE_ORDER_MAIN = ["G4", "G5", "G1", "G2"]
RANDOM_SEED = 2026
random.seed(RANDOM_SEED)


# ============================================================
# 数据结构
# ============================================================

@dataclass(frozen=True)
class CargoItem:
    item_id: str
    type_id: str
    category: str
    original_size: Tuple[int, int, int]
    weight: float
    volume: int
    stackable: bool
    fragile: bool
    oriented: bool
    allowed_orientations: Tuple[Orientation, ...]


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
class Space:
    x: int
    y: int
    z: int
    length: int
    width: int
    height: int
    support_item_id: Optional[str] = None
    support_type_id: Optional[str] = None
    support_length: Optional[int] = None
    support_width: Optional[int] = None

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass
class LayoutState:
    spaces: List[Space]
    placed: List[PlacedCargo]
    remaining: List[CargoItem]
    used_weight: float
    used_volume: int
    score: float = 0.0
    packed_ratio: float = 0.0


@dataclass
class VehicleResult:
    vehicle_id: str
    placed: List[PlacedCargo]
    target_counts: Dict[str, int]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int
    policy_desc: str = ""

    @property
    def feasible_full_pack(self) -> bool:
        return all(self.actual_counts.get(t, 0) == self.target_counts.get(t, 0) for t in TYPE_ORDER_ALL)


@dataclass(frozen=True)
class PackingPolicy:
    g3_ratio: float
    main_order: Tuple[str, ...]
    w_fill: float
    w_remain: float
    w_volume: float
    row_mode: int
    layer_height_relax: int

    def desc(self) -> str:
        return (
            f"g3_ratio={self.g3_ratio:.2f};order={'-'.join(self.main_order)};"
            f"wf={self.w_fill:.2f};wr={self.w_remain:.2f};wv={self.w_volume:.2f};"
            f"row={self.row_mode};relax={self.layer_height_relax}"
        )


# ============================================================
# 基础工具
# ============================================================


def lower_bound_vehicle_count(truck: Truck) -> Tuple[int, int, int]:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    basic = max(math.ceil(total_volume / truck.effective_volume), math.ceil(total_weight / truck.max_weight))

    g3_best = 0
    for ori in generate_orientations(CARGO_TYPES["G3"]):
        l, w, h = ori.size
        if h <= truck.effective_height:
            g3_best = max(g3_best, (truck.length // l) * (truck.width // w))
    g3_lb = math.ceil(CARGO_TYPES["G3"].quantity / max(1, g3_best))
    return max(basic, g3_lb), basic, g3_lb


def quota_total_volume(quota: Dict[str, int]) -> int:
    return sum(CARGO_TYPES[t].volume * quota.get(t, 0) for t in TYPE_ORDER_ALL)


def quota_total_weight(quota: Dict[str, int]) -> float:
    return sum(CARGO_TYPES[t].weight * quota.get(t, 0) for t in TYPE_ORDER_ALL)


def residual_volume(truck: Truck, quota: Dict[str, int]) -> int:
    return truck.effective_volume - quota_total_volume(quota)


def residual_weight(truck: Truck, quota: Dict[str, int]) -> float:
    return truck.max_weight - quota_total_weight(quota)


def quota_size(quota: Dict[str, int]) -> int:
    return sum(quota.get(t, 0) for t in TYPE_ORDER_ALL)


def default_policy() -> PackingPolicy:
    return PackingPolicy(
        g3_ratio=0.60,
        main_order=("G4", "G5", "G1", "G2"),
        w_fill=0.60,
        w_remain=0.20,
        w_volume=0.20,
        row_mode=0,
        layer_height_relax=0,
    )


# ============================================================
# 内层：物理约束 + 空间切分 + beam search
# ============================================================


def expand_quota_to_items(quota: Dict[str, int], vehicle_index: int) -> List[CargoItem]:
    items: List[CargoItem] = []
    for type_id in TYPE_ORDER_ALL:
        cargo = CARGO_TYPES[type_id]
        cnt = int(quota.get(type_id, 0))
        if cnt <= 0:
            continue
        oris = generate_orientations(cargo)
        for i in range(1, cnt + 1):
            items.append(
                CargoItem(
                    item_id=f"{type_id}_{vehicle_index:03d}_{i:04d}",
                    type_id=type_id,
                    category=cargo.category,
                    original_size=(cargo.length, cargo.width, cargo.height),
                    weight=cargo.weight,
                    volume=cargo.volume,
                    stackable=cargo.stackable,
                    fragile=cargo.fragile,
                    oriented=cargo.oriented,
                    allowed_orientations=oris,
                )
            )
    return items


def sort_spaces_dblf(spaces: Sequence[Space]) -> List[Space]:
    spaces = [s for s in spaces if s.length > 0 and s.width > 0 and s.height > 0]
    return sorted(spaces, key=lambda s: (s.z, s.y, s.x, -s.volume))


def remove_contained_spaces(spaces: List[Space]) -> List[Space]:
    out: List[Space] = []
    for i, a in enumerate(spaces):
        contained = False
        for j, b in enumerate(spaces):
            if i == j:
                continue
            if (
                a.x >= b.x and a.y >= b.y and a.z >= b.z and
                a.x + a.length <= b.x + b.length and
                a.y + a.width <= b.y + b.width and
                a.z + a.height <= b.z + b.height and
                (a.x, a.y, a.z, a.length, a.width, a.height) != (b.x, b.y, b.z, b.length, b.width, b.height)
            ):
                contained = True
                break
        if not contained:
            out.append(a)
    return out


def try_merge_two_spaces(a: Space, b: Space) -> Optional[Space]:
    support_same = (
        a.support_item_id == b.support_item_id and
        a.support_type_id == b.support_type_id and
        a.support_length == b.support_length and
        a.support_width == b.support_width
    )
    if not support_same:
        return None

    if a.y == b.y and a.z == b.z and a.width == b.width and a.height == b.height:
        if a.x + a.length == b.x:
            return Space(a.x, a.y, a.z, a.length + b.length, a.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.x + b.length == a.x:
            return Space(b.x, b.y, b.z, a.length + b.length, a.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)

    if a.x == b.x and a.z == b.z and a.length == b.length and a.height == b.height:
        if a.y + a.width == b.y:
            return Space(a.x, a.y, a.z, a.length, a.width + b.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.y + b.width == a.y:
            return Space(b.x, b.y, b.z, a.length, a.width + b.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)

    if a.x == b.x and a.y == b.y and a.length == b.length and a.width == b.width:
        if a.z + a.height == b.z:
            return Space(a.x, a.y, a.z, a.length, a.width, a.height + b.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.z + b.height == a.z:
            return Space(b.x, b.y, b.z, a.length, a.width, a.height + b.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
    return None


def merge_spaces(spaces: List[Space]) -> List[Space]:
    spaces = remove_contained_spaces(spaces)
    changed = True
    while changed:
        changed = False
        n = len(spaces)
        for i in range(n):
            merged = False
            for j in range(i + 1, n):
                m = try_merge_two_spaces(spaces[i], spaces[j])
                if m is not None:
                    spaces = [spaces[k] for k in range(n) if k not in (i, j)] + [m]
                    spaces = remove_contained_spaces(spaces)
                    changed = True
                    merged = True
                    break
            if merged:
                break
    return spaces


def build_item_orders(items: List[CargoItem], policy: PackingPolicy) -> List[CargoItem]:
    order_rank = {t: i for i, t in enumerate(policy.main_order)}

    def ori_height(item: CargoItem) -> int:
        return max(o.size[2] for o in item.allowed_orientations)

    def base_area(item: CargoItem) -> int:
        return max(o.size[0] * o.size[1] for o in item.allowed_orientations)

    def key_mode_0(item: CargoItem):
        group = 0 if item.type_id == "G3" else 1 + order_rank.get(item.type_id, 9)
        return (group, -base_area(item), -ori_height(item), -item.volume, item.item_id)

    def key_mode_1(item: CargoItem):
        group = 0 if item.type_id == "G3" else 1 + order_rank.get(item.type_id, 9)
        return (group, -item.weight / max(1, item.volume), -item.volume, item.item_id)

    def key_mode_2(item: CargoItem):
        group = 0 if item.type_id == "G3" else 1 + order_rank.get(item.type_id, 9)
        return (group, item.fragile, -base_area(item), -item.weight, item.item_id)

    if policy.row_mode == 0:
        return sorted(items, key=key_mode_0)
    if policy.row_mode == 1:
        return sorted(items, key=key_mode_1)
    return sorted(items, key=key_mode_2)


def can_place_in_space(item: CargoItem, ori: Orientation, space: Space, placed_map: Dict[str, PlacedCargo], used_weight: float, truck: Truck) -> bool:
    l, w, h = ori.size
    if l > space.length or w > space.width or h > space.height:
        return False
    if used_weight + item.weight > truck.max_weight + 1e-9:
        return False

    if item.fragile and space.z > 0:
        if space.support_type_id not in ("G1", "G2"):
            return False

    if space.z > 0:
        if space.support_item_id is None:
            return False
        support = placed_map.get(space.support_item_id)
        if support is None:
            return False
        if l > support.length or w > support.width:
            return False
        if support.category == "fragile":
            return False
        projected_pressure = (support.direct_supported_weight + item.weight) / max(1e-9, support.top_area_m2)
        if projected_pressure > CARGO_TYPES[support.type_id].max_support_pressure + 1e-9:
            return False
    return True


def placement_gain(truck: Truck, state: LayoutState, item: CargoItem, ori: Orientation, space: Space, policy: PackingPolicy) -> float:
    l, w, h = ori.size
    fill_ratio = (l * w * h) / max(1, space.length * space.width * space.height)
    low_z_bonus = 1.0 / (1.0 + space.z)
    tight_bonus = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
    support_bonus = 0.10 if space.z > 0 else 0.0
    dense_bonus = (item.weight / max(1, item.volume)) / max(c.density for c in CARGO_TYPES.values())
    sv0, wv0, fs0 = truck_score(truck, state.used_volume, state.used_weight)
    sv1, wv1, fs1 = truck_score(truck, state.used_volume + item.volume, state.used_weight + item.weight)
    fs_gain = fs1 - fs0
    remain_same_type = sum(1 for x in state.remaining if x.type_id == item.type_id)
    remain_bonus = remain_same_type / max(1, CARGO_TYPES[item.type_id].quantity)
    main_order_bonus = 0.0
    if item.type_id in policy.main_order:
        main_order_bonus = 0.04 * (len(policy.main_order) - policy.main_order.index(item.type_id))
    if item.type_id == "G3":
        main_order_bonus += 0.08 * policy.g3_ratio

    return (
        policy.w_fill * fill_ratio +
        policy.w_remain * remain_bonus +
        policy.w_volume * (item.volume / max(1, truck.effective_volume)) +
        0.20 * low_z_bonus +
        0.16 * tight_bonus +
        0.10 * support_bonus +
        0.08 * dense_bonus +
        0.25 * fs_gain +
        main_order_bonus +
        0.02 * (wv1 - wv0) + 0.02 * (sv1 - sv0)
    )


def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    out: List[Space] = []
    if space.length > placed.length:
        out.append(Space(
            x=space.x + placed.length,
            y=space.y,
            z=space.z,
            length=space.length - placed.length,
            width=space.width,
            height=space.height,
            support_item_id=space.support_item_id,
            support_type_id=space.support_type_id,
            support_length=space.support_length,
            support_width=space.support_width,
        ))
    if space.width > placed.width:
        out.append(Space(
            x=space.x,
            y=space.y + placed.width,
            z=space.z,
            length=placed.length,
            width=space.width - placed.width,
            height=space.height,
            support_item_id=space.support_item_id,
            support_type_id=space.support_type_id,
            support_length=space.support_length,
            support_width=space.support_width,
        ))
    if space.height > placed.height and placed.category != "fragile":
        out.append(Space(
            x=space.x,
            y=space.y,
            z=space.z + placed.height,
            length=placed.length,
            width=placed.width,
            height=space.height - placed.height,
            support_item_id=placed.item_id,
            support_type_id=placed.type_id,
            support_length=placed.length,
            support_width=placed.width,
        ))
    return out


def apply_placement(truck: Truck, state: LayoutState, item_idx: int, ori: Orientation, space_idx: int, vehicle_id: str) -> LayoutState:
    item = state.remaining[item_idx]
    space = state.spaces[space_idx]
    l, w, h = ori.size
    support_by = space.support_item_id

    placed = PlacedCargo(
        item_id=item.item_id,
        type_id=item.type_id,
        category=item.category,
        x=space.x,
        y=space.y,
        z=space.z,
        length=l,
        width=w,
        height=h,
        weight=item.weight,
        orientation_id=ori.orient_id,
        rotation=ori.rotation,
        truck_id=vehicle_id,
        support_by=support_by,
    )

    new_placed = [p for p in state.placed]
    new_placed.append(placed)

    if support_by is not None:
        for p in new_placed:
            if p.item_id == support_by:
                p.direct_supported_weight += item.weight
                break

    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))
    new_spaces = merge_spaces(new_spaces)
    new_spaces = sort_spaces_dblf(new_spaces)

    new_remaining = state.remaining[:item_idx] + state.remaining[item_idx + 1:]
    used_weight = state.used_weight + item.weight
    used_volume = state.used_volume + item.volume
    sv, wv, fs = truck_score(truck, used_volume, used_weight)
    packed_ratio = len(new_placed) / max(1, len(new_placed) + len(new_remaining))

    return LayoutState(
        spaces=new_spaces,
        placed=new_placed,
        remaining=new_remaining,
        used_weight=used_weight,
        used_volume=used_volume,
        score=fs + 0.04 * packed_ratio + 0.02 * sv + 0.01 * wv,
        packed_ratio=packed_ratio,
    )


def pack_with_beam_search(
    truck: Truck,
    items: List[CargoItem],
    vehicle_id: str,
    policy: PackingPolicy,
) -> LayoutState:
    ordered = build_item_orders(items, policy)
    init = LayoutState(
        spaces=[Space(0, 0, 0, truck.length, truck.width, truck.effective_height, None, None, truck.length, truck.width)],
        placed=[],
        remaining=ordered,
        used_weight=0.0,
        used_volume=0,
        score=0.0,
        packed_ratio=0.0,
    )

    beam_width = 7 + (1 if policy.layer_height_relax else 0)
    candidate_items_each_step = 7 if policy.row_mode != 2 else 8
    candidate_moves_each_state = 12 if policy.w_fill >= 0.45 else 10
    spaces_to_scan = 22 if policy.row_mode == 0 else 18

    beam: List[LayoutState] = [init]
    best = init

    while beam:
        next_beam: List[LayoutState] = []
        expanded_any = False

        for state in beam:
            if state.score > best.score or state.used_volume > best.used_volume or len(state.placed) > len(best.placed):
                best = state
            if not state.remaining or not state.spaces:
                next_beam.append(state)
                continue

            placed_map = {p.item_id: p for p in state.placed}
            item_candidates = state.remaining[:min(candidate_items_each_step, len(state.remaining))]
            move_pool: List[Tuple[float, int, Orientation, int]] = []

            for item_idx, item in enumerate(item_candidates):
                for space_idx, space in enumerate(state.spaces[:min(spaces_to_scan, len(state.spaces))]):
                    for ori in item.allowed_orientations:
                        if can_place_in_space(item, ori, space, placed_map, state.used_weight, truck):
                            gain = placement_gain(truck, state, item, ori, space, policy)
                            move_pool.append((gain, item_idx, ori, space_idx))

            move_pool.sort(key=lambda x: x[0], reverse=True)
            move_pool = move_pool[:candidate_moves_each_state]

            if not move_pool:
                next_beam.append(state)
                continue

            expanded_any = True
            for _, item_idx, ori, space_idx in move_pool:
                next_beam.append(apply_placement(truck, state, item_idx, ori, space_idx, vehicle_id))

        if not expanded_any:
            break

        next_beam.sort(key=lambda st: (st.score, st.used_volume, st.used_weight, len(st.placed)), reverse=True)
        beam = next_beam[:beam_width]
        if beam and (beam[0].score > best.score or beam[0].used_volume > best.used_volume):
            best = beam[0]

    return best


def pack_one_vehicle_with_policy(truck: Truck, target_quota: Dict[str, int], vehicle_index: int, policy: PackingPolicy) -> VehicleResult:
    quota = {t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL}
    vehicle_id = f"{truck.name}_{vehicle_index:03d}"
    items = expand_quota_to_items(quota, vehicle_index)
    state = pack_with_beam_search(truck, items, vehicle_id, policy)
    actual_counts = dict(Counter(p.type_id for p in state.placed))
    return VehicleResult(
        vehicle_id=vehicle_id,
        placed=state.placed,
        target_counts=quota,
        actual_counts=actual_counts,
        used_weight=state.used_weight,
        used_volume=state.used_volume,
        policy_desc=policy.desc(),
    )




# ============================================================
# baseline 初始解生成器：复用 p12_baseline.py 的快速多策略单车构造思想
# 作用：先用更快的 baseline 风格生成较优初始 quotas，再交给 fixed 外层继续压缩
# ============================================================

BASELINE_MAX_SPACES_TO_CHECK = 80
BASELINE_MIN_SPACE_VOLUME = 20000


def baseline_space_volume(sp: Dict[str, int]) -> int:
    return sp["l"] * sp["w"] * sp["h"]


def baseline_sort_spaces(spaces: List[Dict[str, int]]) -> List[Dict[str, int]]:
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if baseline_space_volume(sp) >= BASELINE_MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (s["z"], -baseline_space_volume(s), s["y"], s["x"]))
    return spaces


class BaselineFastTruck:
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
        self.spaces = baseline_sort_spaces(self.spaces)
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
        if self.used_weight + cargo.weight > self.max_weight + 1e-9:
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
            support_by=sp.get("support_item_id"),
        )

        self.placed.append(placed)
        self.placed_map[item_id] = placed
        self.used_weight += cargo.weight
        self.used_volume += placed.volume
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
        self.spaces = baseline_sort_spaces(self.spaces)[:BASELINE_MAX_SPACES_TO_CHECK]


def baseline_build_type_order(strategy: str) -> List[str]:
    std_types = ["G1", "G2"]
    dir_types = ["G4", "G5"]
    if strategy == "std_first":
        return std_types + dir_types + ["G3"]
    if strategy == "dir_first":
        return dir_types + std_types + ["G3"]
    if strategy == "g3_first":
        return ["G3"] + dir_types + std_types
    if strategy == "heavy_first":
        return sorted(TYPE_ORDER_ALL, key=lambda t: CARGO_TYPES[t].weight, reverse=True)
    if strategy == "bulky_first":
        return sorted(TYPE_ORDER_ALL, key=lambda t: CARGO_TYPES[t].volume, reverse=True)
    arr = TYPE_ORDER_ALL[:]
    random.shuffle(arr)
    return arr


def baseline_eval_candidate(type_id: str, ori: Orientation, sp: Dict[str, int], remaining: Dict[str, int], truck_obj: BaselineFastTruck) -> Optional[float]:
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]
    if remaining[type_id] <= 0:
        return None

    item_vol = l * w * h
    fill_ratio = item_vol / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    vol_gain = item_vol / max(1, truck_obj.truck.effective_volume)
    wt_gain = cargo.weight / max(1.0, truck_obj.truck.max_weight)
    old_fs = truck_score(truck_obj.truck, truck_obj.used_volume, truck_obj.used_weight)[2]
    new_fs = truck_score(truck_obj.truck, truck_obj.used_volume + item_vol, truck_obj.used_weight + cargo.weight)[2]
    fs_gain = new_fs - old_fs
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    support_penalty = 0.02 if sp["z"] > 0 else 0.0
    score = (
        0.34 * vol_gain + 0.26 * wt_gain + 0.20 * fill_ratio +
        0.12 * fs_gain * 10.0 + 0.05 * bottom_bonus +
        0.02 * remain_bonus - support_penalty
    )
    return score


def baseline_place_one_best(truck_obj: BaselineFastTruck, remaining: Dict[str, int], type_order: List[str]) -> bool:
    best = None
    candidate_spaces = truck_obj.spaces[:BASELINE_MAX_SPACES_TO_CHECK]
    for sp_idx, _sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in generate_orientations(CARGO_TYPES[type_id]):
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = baseline_eval_candidate(type_id, ori, truck_obj.spaces[sp_idx], remaining, truck_obj)
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


def baseline_load_one_truck(truck: Truck, remaining: Dict[str, int], strategy: str, vehicle_idx: int) -> BaselineFastTruck:
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = BaselineFastTruck(truck, vehicle_id)
    type_order = baseline_build_type_order(strategy)
    while True:
        ok = baseline_place_one_best(truck_obj, remaining, type_order)
        if not ok:
            break
    return truck_obj


def baseline_build_one_vehicle_best(truck: Truck, remaining: Dict[str, int], vehicle_idx: int) -> Optional[BaselineFastTruck]:
    strategies = ["std_first", "dir_first", "mixed", "g3_first", "heavy_first", "bulky_first"]
    best_plan = None
    best_key = None
    for st in strategies:
        rem_copy = deepcopy(remaining)
        plan = baseline_load_one_truck(truck, rem_copy, st, vehicle_idx)
        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue
        key = (loaded_cnt, plan.used_volume, -plan.used_weight)
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key
    return best_plan


def baseline_initial_solution(truck: Truck) -> Tuple[List[VehicleResult], List[Dict[str, int]]]:
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER_ALL}
    plans: List[VehicleResult] = []
    quotas: List[Dict[str, int]] = []
    vehicle_idx = 1

    while sum(remaining.values()) > 0:
        plan = baseline_build_one_vehicle_best(truck, remaining, vehicle_idx)
        if plan is None:
            raise RuntimeError(f"{truck.name} baseline 初始解构造失败：第 {vehicle_idx} 辆车无法生成。")

        loaded_now = sum(plan.actual_counts.values())
        if loaded_now == 0:
            raise RuntimeError(f"{truck.name} baseline 初始解构造失败：第 {vehicle_idx} 辆车装载数为0。")

        actual = {t: int(plan.actual_counts.get(t, 0)) for t in TYPE_ORDER_ALL}
        for t, c in actual.items():
            remaining[t] -= c

        sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
        print(
            f"[{truck.name}] baseline seed 第 {vehicle_idx} 辆车："
            f"装入 {loaded_now} 件，空间利用率={sv:.4f}，载重利用率={wv:.4f}，"
            f"fullness_score={fs:.4f}，剩余={sum(remaining.values())}",
            flush=True,
        )

        vr = VehicleResult(
            vehicle_id=plan.vehicle_id,
            placed=plan.placed,
            target_counts=actual.copy(),
            actual_counts=actual.copy(),
            used_weight=plan.used_weight,
            used_volume=plan.used_volume,
            policy_desc="baseline_seed",
        )
        plans.append(vr)
        quotas.append(actual.copy())
        vehicle_idx += 1

    return plans, quotas

# ============================================================
# 轻量 GA：优化单车装箱策略（保留外层接口）
# ============================================================

_POLICY_CACHE: Dict[Tuple[str, Tuple[Tuple[str, int], ...]], PackingPolicy] = {}


def quota_signature(quota: Dict[str, int]) -> Tuple[Tuple[str, int], ...]:
    return tuple((t, int(quota.get(t, 0))) for t in TYPE_ORDER_ALL)


def random_policy(rng: random.Random) -> PackingPolicy:
    order = TYPE_ORDER_MAIN[:]
    rng.shuffle(order)
    a, b, c = rng.random(), rng.random(), rng.random()
    s = a + b + c
    return PackingPolicy(
        g3_ratio=rng.uniform(0.25, 1.00),
        main_order=tuple(order),
        w_fill=a / s,
        w_remain=b / s,
        w_volume=c / s,
        row_mode=rng.choice([0, 1, 2]),
        layer_height_relax=rng.choice([0, 1]),
    )


def mutate_policy(p: PackingPolicy, rng: random.Random) -> PackingPolicy:
    order = list(p.main_order)
    if rng.random() < 0.5:
        i, j = rng.sample(range(len(order)), 2)
        order[i], order[j] = order[j], order[i]
    wf = max(0.05, p.w_fill + rng.uniform(-0.12, 0.12))
    wr = max(0.05, p.w_remain + rng.uniform(-0.12, 0.12))
    wv = max(0.05, p.w_volume + rng.uniform(-0.12, 0.12))
    s = wf + wr + wv
    return PackingPolicy(
        g3_ratio=min(1.0, max(0.1, p.g3_ratio + rng.uniform(-0.15, 0.15))),
        main_order=tuple(order),
        w_fill=wf / s,
        w_remain=wr / s,
        w_volume=wv / s,
        row_mode=p.row_mode if rng.random() < 0.6 else rng.choice([0, 1, 2]),
        layer_height_relax=p.layer_height_relax if rng.random() < 0.7 else 1 - p.layer_height_relax,
    )


def crossover_policy(a: PackingPolicy, b: PackingPolicy, rng: random.Random) -> PackingPolicy:
    prefix_len = rng.randint(1, len(TYPE_ORDER_MAIN) - 1)
    prefix = list(a.main_order[:prefix_len])
    rest = [x for x in b.main_order if x not in prefix]
    order = tuple(prefix + rest)
    wf = (a.w_fill + b.w_fill) / 2
    wr = (a.w_remain + b.w_remain) / 2
    wv = (a.w_volume + b.w_volume) / 2
    s = wf + wr + wv
    child = PackingPolicy(
        g3_ratio=(a.g3_ratio + b.g3_ratio) / 2,
        main_order=order,
        w_fill=wf / s,
        w_remain=wr / s,
        w_volume=wv / s,
        row_mode=a.row_mode if rng.random() < 0.5 else b.row_mode,
        layer_height_relax=a.layer_height_relax if rng.random() < 0.5 else b.layer_height_relax,
    )
    if rng.random() < 0.45:
        child = mutate_policy(child, rng)
    return child


def vehicle_policy_fitness(truck: Truck, quota: Dict[str, int], plan: VehicleResult) -> float:
    missing = 0
    weighted_missing = 0
    for t in TYPE_ORDER_ALL:
        d = max(0, quota.get(t, 0) - plan.actual_counts.get(t, 0))
        missing += d
        if t == "G3":
            weighted_missing += 15 * d
        elif t in ("G4", "G5"):
            weighted_missing += 8 * d
        else:
            weighted_missing += 3 * d
    sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
    placed_supportive = sum(1 for p in plan.placed if p.support_by is not None)
    return -2000 * missing - 120 * weighted_missing + 300 * sv + 120 * wv + 60 * fs + 0.2 * placed_supportive


def ga_optimize_vehicle_policy(
    truck: Truck,
    quota: Dict[str, int],
    vehicle_index: int,
    seed: int = 2026,
    pop_size: int = 10,
    generations: int = 6,
) -> Tuple[VehicleResult, PackingPolicy]:
    sig = (truck.name, quota_signature(quota))
    if sig in _POLICY_CACHE:
        best_policy = _POLICY_CACHE[sig]
        best_plan = pack_one_vehicle_with_policy(truck, quota, vehicle_index, best_policy)
        return best_plan, best_policy

    rng = random.Random(seed + vehicle_index + sum(quota.values()))
    population: List[PackingPolicy] = [default_policy()]
    while len(population) < pop_size:
        population.append(random_policy(rng))

    best_policy = population[0]
    best_plan = pack_one_vehicle_with_policy(truck, quota, vehicle_index, best_policy)
    best_fit = vehicle_policy_fitness(truck, quota, best_plan)

    for _ in range(generations):
        scored = []
        for p in population:
            plan = pack_one_vehicle_with_policy(truck, quota, vehicle_index, p)
            fit = vehicle_policy_fitness(truck, quota, plan)
            scored.append((fit, p, plan))
            if fit > best_fit:
                best_fit, best_policy, best_plan = fit, p, plan

        scored.sort(key=lambda x: x[0], reverse=True)
        elites = [x[1] for x in scored[:max(2, pop_size // 3)]]
        new_pop = elites[:]
        while len(new_pop) < pop_size:
            if rng.random() < 0.55 and len(elites) >= 2:
                a, b = rng.sample(elites, 2)
                child = crossover_policy(a, b, rng)
            else:
                child = mutate_policy(rng.choice(elites), rng)
            new_pop.append(child)
        population = new_pop
        if best_plan.feasible_full_pack:
            break

    _POLICY_CACHE[sig] = best_policy
    return best_plan, best_policy


def revalidate_all(truck: Truck, quotas: List[Dict[str, int]]) -> List[VehicleResult]:
    return [ga_optimize_vehicle_policy(truck, q, i)[0] for i, q in enumerate(quotas, 1)]


def collect_missing(plans: List[VehicleResult]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER_ALL}
    for vp in plans:
        for t in TYPE_ORDER_ALL:
            missing[t] += max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))
    return missing


def all_feasible(plans: List[VehicleResult]) -> bool:
    return all(vp.feasible_full_pack for vp in plans)


# ============================================================
# 初始可行解：逐车装入“剩余货物集合”的最大可行子集
# ============================================================


def pack_one_vehicle_greedy_from_remaining(truck: Truck, remaining: Dict[str, int], vehicle_index: int) -> VehicleResult:
    policy = default_policy()
    quota = {t: int(remaining.get(t, 0)) for t in TYPE_ORDER_ALL}
    plan = pack_one_vehicle_with_policy(truck, quota, vehicle_index, policy)
    actual = {t: plan.actual_counts.get(t, 0) for t in TYPE_ORDER_ALL}
    for t in TYPE_ORDER_ALL:
        remaining[t] -= actual[t]
    return VehicleResult(
        vehicle_id=plan.vehicle_id,
        placed=plan.placed,
        target_counts=actual.copy(),
        actual_counts=actual.copy(),
        used_weight=plan.used_weight,
        used_volume=plan.used_volume,
        policy_desc=plan.policy_desc,
    )


def greedy_initial_solution(truck: Truck) -> Tuple[List[VehicleResult], List[Dict[str, int]]]:
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER_ALL}
    plans: List[VehicleResult] = []
    quotas: List[Dict[str, int]] = []
    vehicle_index = 1
    prev_total = sum(remaining.values())

    while sum(remaining.values()) > 0:
        plan = pack_one_vehicle_greedy_from_remaining(truck, remaining, vehicle_index)
        loaded = sum(plan.actual_counts.values())
        if loaded == 0:
            raise RuntimeError(f"{truck.name} greedy 初始解构造失败：第 {vehicle_index} 辆车未能装入任何货物。")
        plans.append(plan)
        quotas.append(plan.target_counts.copy())
        after_total = sum(remaining.values())
        if after_total >= prev_total:
            raise RuntimeError(f"{truck.name} greedy 初始解构造未减少剩余货物。")
        prev_total = after_total
        vehicle_index += 1
    return plans, quotas


# ============================================================
# 外层压缩初始化 / SA / LNS（保留 p12_final 主体）
# ============================================================


def compress_quotas_from_feasible(truck: Truck, feasible_quotas: List[Dict[str, int]], target_k: int) -> List[Dict[str, int]]:
    if target_k >= len(feasible_quotas):
        return [q.copy() for q in feasible_quotas[:target_k]]

    kept = [q.copy() for q in feasible_quotas[:target_k]]
    tails = feasible_quotas[target_k:]
    leftover = {t: 0 for t in TYPE_ORDER_ALL}
    for q in tails:
        for t in TYPE_ORDER_ALL:
            leftover[t] += q.get(t, 0)

    for t in ["G4", "G5", "G1", "G2"]:
        qty = leftover[t]
        c = CARGO_TYPES[t]
        while qty > 0:
            candidates = []
            for i in range(target_k):
                rv = residual_volume(truck, kept[i])
                rw = residual_weight(truck, kept[i])
                if rv >= c.volume and rw >= c.weight:
                    sv, wv, _ = truck_score(truck, quota_total_volume(kept[i]), quota_total_weight(kept[i]))
                    slack = (1 - sv) + (1 - wv)
                    candidates.append((slack, i))
            if not candidates:
                break
            candidates.sort(reverse=True)
            i = candidates[0][1]
            kept[i][t] += 1
            qty -= 1
        leftover[t] = qty

    qty = leftover["G3"]
    while qty > 0:
        caps = []
        for i in range(target_k):
            cur = kept[i]["G3"]
            best_floor = 0
            for ori in generate_orientations(CARGO_TYPES["G3"]):
                l, w, h = ori.size
                if h <= truck.effective_height:
                    best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
            slack = max(0, best_floor - cur)
            if slack > 0:
                caps.append((slack, i))
        if not caps:
            break
        caps.sort(reverse=True)
        move = min(qty, max(1, caps[0][0] // 2))
        kept[caps[0][1]]["G3"] += move
        qty -= move
    leftover["G3"] = qty

    rng = random.Random(2026 + target_k)
    for t in TYPE_ORDER_ALL:
        while leftover[t] > 0:
            i = rng.randrange(target_k)
            kept[i][t] += 1
            leftover[t] -= 1
    return kept


def solution_energy(truck: Truck, quotas: List[Dict[str, int]], plans: List[VehicleResult], K: int) -> float:
    missing = collect_missing(plans)
    miss_cnt = sum(missing.values())
    miss_weighted = 35 * missing["G3"] + 16 * missing["G4"] + 12 * missing["G5"] + 5 * missing["G1"] + 4 * missing["G2"]
    used_vol = sum(vp.used_volume for vp in plans)
    used_w = sum(vp.used_weight for vp in plans)
    avg_sv = used_vol / (K * truck.effective_volume)
    avg_wv = used_w / (K * truck.max_weight)
    tail_bad = sum(1 for vp in plans if vp.used_volume / truck.effective_volume < 0.18)
    return 5000 * miss_cnt + 50 * miss_weighted + 120 * K + 40 * tail_bad - 600 * avg_sv - 220 * avg_wv


def block_move_neighbor(quotas: List[Dict[str, int]], rng: random.Random) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    a, b = rng.sample(range(len(child)), 2)
    t = rng.choice(TYPE_ORDER_ALL)
    if child[a][t] <= 0:
        return child
    mv = min(child[a][t], rng.randint(1, 8))
    child[a][t] -= mv
    child[b][t] += mv
    return child


def swap_neighbor(quotas: List[Dict[str, int]], rng: random.Random) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    a, b = rng.sample(range(len(child)), 2)
    ta_choices = [t for t in TYPE_ORDER_ALL if child[a][t] > 0]
    tb_choices = [t for t in TYPE_ORDER_ALL if child[b][t] > 0]
    if not ta_choices or not tb_choices:
        return child
    ta = rng.choice(ta_choices)
    tb = rng.choice(tb_choices)
    if ta == tb:
        return child
    da = min(child[a][ta], rng.randint(1, 4))
    db = min(child[b][tb], rng.randint(1, 4))
    child[a][ta] -= da
    child[b][tb] -= db
    child[a][tb] += db
    child[b][ta] += da
    return child


def rebalance_g3_neighbor(quotas: List[Dict[str, int]], plans: List[VehicleResult], truck: Truck) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    missing = collect_missing(plans)
    if missing["G3"] == 0:
        return child
    deficits, receivers = [], []
    for i, vp in enumerate(plans):
        target = vp.target_counts.get("G3", 0)
        actual = vp.actual_counts.get("G3", 0)
        if target > actual:
            deficits.append((target - actual, i))
        else:
            best_floor = 0
            for ori in generate_orientations(CARGO_TYPES["G3"]):
                l, w, h = ori.size
                if h <= truck.effective_height:
                    best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
            slack = max(0, best_floor - target)
            if slack > 0:
                receivers.append((slack, i))
    deficits.sort(reverse=True)
    receivers.sort(reverse=True)
    for deficit, d in deficits:
        for idx, (slack, r) in enumerate(receivers):
            if r == d or slack <= 0 or child[d]["G3"] <= 0:
                continue
            mv = min(deficit, slack, child[d]["G3"], 6)
            child[d]["G3"] -= mv
            child[r]["G3"] += mv
            receivers[idx] = (slack - mv, r)
            break
    return child


def targeted_lns_repair(quotas: List[Dict[str, int]], plans: List[VehicleResult], truck: Truck) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    missing = collect_missing(plans)
    types_by_need = sorted(TYPE_ORDER_ALL, key=lambda t: missing[t], reverse=True)
    for t in types_by_need:
        if missing[t] <= 0:
            continue
        donors, receivers = [], []
        for i, vp in enumerate(plans):
            target = vp.target_counts.get(t, 0)
            actual = vp.actual_counts.get(t, 0)
            if target > actual and child[i][t] > 0:
                donors.append((target - actual, i))
            else:
                receivers.append(i)
        donors.sort(reverse=True)
        c = CARGO_TYPES[t]
        for deficit, d in donors:
            for r in receivers:
                if r == d:
                    continue
                if residual_volume(truck, child[r]) >= c.volume and residual_weight(truck, child[r]) >= c.weight:
                    mv = min(deficit, child[d][t], 3 if t in ("G4", "G5") else 10)
                    if mv <= 0:
                        continue
                    child[d][t] -= mv
                    child[r][t] += mv
                    break
    return child


def make_neighbor(quotas: List[Dict[str, int]], plans: List[VehicleResult], truck: Truck, rng: random.Random) -> List[Dict[str, int]]:
    op = rng.choice(["block", "swap", "g3", "lns", "block", "lns"])
    if op == "block":
        return block_move_neighbor(quotas, rng)
    if op == "swap":
        return swap_neighbor(quotas, rng)
    if op == "g3":
        return rebalance_g3_neighbor(quotas, plans, truck)
    return targeted_lns_repair(quotas, plans, truck)


def simulated_annealing_optimize(
    truck: Truck,
    init_quotas: List[Dict[str, int]],
    iterations: int = 140,
    seed: int = 2026,
) -> Tuple[List[Dict[str, int]], List[VehicleResult], float]:
    rng = random.Random(seed + len(init_quotas))
    current = [q.copy() for q in init_quotas]
    current_plans = revalidate_all(truck, current)
    current_energy = solution_energy(truck, current, current_plans, len(current))

    best = [q.copy() for q in current]
    best_plans = current_plans
    best_energy = current_energy

    init_temp = 80.0
    final_temp = 0.8
    print(f"[{truck.name}] SA 初始能量 = {current_energy:.2f}", flush=True)

    for it in range(1, iterations + 1):
        ratio = (it - 1) / max(1, iterations - 1)
        temp = init_temp * ((final_temp / init_temp) ** ratio)
        cand = make_neighbor(current, current_plans, truck, rng)
        cand_plans = revalidate_all(truck, cand)
        cand_energy = solution_energy(truck, cand, cand_plans, len(cand))
        delta = cand_energy - current_energy
        accept = delta <= 0 or rng.random() < math.exp(-delta / max(temp, 1e-9))
        if accept:
            current, current_plans, current_energy = cand, cand_plans, cand_energy
        if cand_energy < best_energy:
            best, best_plans, best_energy = [q.copy() for q in cand], cand_plans, cand_energy
        if it == 1 or it % 10 == 0 or it == iterations:
            print(f"[{truck.name}] SA iter={it:03d}/{iterations} temp={temp:.2f} bestE={best_energy:.2f} missing={collect_missing(best_plans)}", flush=True)
        if all_feasible(best_plans):
            break
    return best, best_plans, best_energy


# ============================================================
# 总流程 / 输出
# ============================================================


def solve_problem_12_ultimate_ga(truck: Truck, sa_iterations: int = 140, min_extra_over_lb: int = 0) -> Tuple[int, List[VehicleResult], Dict[str, object]]:
    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)
    greedy_plans, greedy_quotas = baseline_initial_solution(truck)
    greedy_k = len(greedy_plans)
    print(f"[{truck.name}] baseline 初始可行车辆数 = {greedy_k}", flush=True)

    best_feasible_k = greedy_k
    best_feasible_plans = greedy_plans
    best_feasible_quotas = greedy_quotas

    lower_search = lb + min_extra_over_lb
    current_k = greedy_k - 1
    while current_k >= lower_search:
        print(f"[{truck.name}] 尝试压缩到 K = {current_k} ...", flush=True)
        init_quotas = compress_quotas_from_feasible(truck, best_feasible_quotas, current_k)
        quotas, plans, _ = simulated_annealing_optimize(truck, init_quotas, iterations=sa_iterations, seed=2026 + current_k)
        ok = all_feasible(plans)
        print(f"[{truck.name}] K = {current_k} 可行性结果: {ok}", flush=True)
        if ok:
            best_feasible_k, best_feasible_plans, best_feasible_quotas = current_k, plans, quotas
            current_k -= 1
        else:
            break

    K = best_feasible_k
    plans = best_feasible_plans
    avg_sv = sum(vp.used_volume for vp in plans) / (K * truck.effective_volume)
    avg_wv = sum(vp.used_weight for vp in plans) / (K * truck.max_weight)
    summary = {
        "truck": truck.name,
        "vehicle_count": K,
        "lower_bound": lb,
        "lower_bound_basic": basic_lb,
        "lower_bound_g3": g3_lb,
        "greedy_vehicle_count": greedy_k,
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "total_cost": round(K * truck.cost, 2),
        "all_loaded": True,
    }
    return K, plans, summary


def write_vehicle_summary_csv(path: str, plans: List[VehicleResult], truck: Truck) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "target_counts", "actual_counts", "loaded_weight_kg", "loaded_volume_cm3",
            "feasible_full_pack", "policy_desc"
        ])
        for vp in plans:
            sv, wv, fs = truck_score(truck, vp.used_volume, vp.used_weight)
            w.writerow([
                vp.vehicle_id, round(sv, 6), round(wv, 6), round(fs, 6),
                vp.target_counts, vp.actual_counts, round(vp.used_weight, 3), vp.used_volume,
                vp.feasible_full_pack, vp.policy_desc,
            ])


def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id", "support_by", "direct_supported_weight"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id, p.support_by, round(p.direct_supported_weight, 6)
            ])


def solve_for_truck(truck: Truck, outdir: str, sa_iterations: int) -> Dict[str, object]:
    K, plans, summary = solve_problem_12_ultimate_ga(truck, sa_iterations=sa_iterations)
    truck_dir = os.path.join(outdir, truck.name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck.name}_车辆汇总.csv"), plans, truck)
    for vp in plans:
        write_items_csv(os.path.join(truck_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp.placed)
    summary["output_dir"] = truck_dir
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 baseline+fixed 混合压缩终极版")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2(hybrid_final)", help="输出目录")
    parser.add_argument("--sa-iterations", type=int, default=140, help="每轮压缩的 SA 迭代次数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for name in truck_list:
        truck = TRUCKS[name]
        print("\n" + "=" * 68)
        print(f"开始求解问题1.2（fixed）：{truck.name}")
        print("=" * 68)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        summary = solve_for_truck(truck, outdir, args.sa_iterations)
        print(summary)


if __name__ == "__main__":
    main()
