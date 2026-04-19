#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2 最终版（G3主导下界 + 分层分配 + 单车增强装箱 + 轻量LNS修复）

说明：
1. 固定一种车型，目标为装完附件1全部货物且车辆数尽量少；
2. 先计算体积/重量下界，再叠加 G3（易碎件单层）底面积下界；
3. 对固定车辆数 K，先做 G3 优先分配，再分配 G4/G5，最后用 G1/G2 填充；
4. 每辆车调用轻量单车增强装箱器（beam search + DBLF + 三空间分割 + 空间合并）；
5. 若仍有未装货物，则做轻量 LNS 修复，重点修复 G3/G4/G5。

这是工程化近似算法，强调稳定可运行和结果可解释性。
"""
# raise RuntimeError(...)
from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# ============================================================
# 数据结构
# ============================================================

@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str


@dataclass(frozen=True)
class CargoType:
    type_id: str
    category: str  # standard / fragile / oriented
    length: int
    width: int
    height: int
    weight: float
    quantity: int
    stackable: bool
    can_rotate: bool
    fragile: bool
    oriented: bool
    max_support_pressure: float = 500.0  # kg / m^2
    top_clearance: int = 3

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def density(self) -> float:
        return self.weight / max(1, self.volume)


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
    support_by: Optional[str] = None
    truck_id: Optional[str] = None
    direct_supported_weight: float = 0.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return (self.length * self.width) / 10000.0


@dataclass(frozen=True)
class Truck:
    name: str
    length: int
    width: int
    height: int
    max_weight: float
    cost: float
    top_clearance: int = 3

    @property
    def effective_height(self) -> int:
        return self.height - self.top_clearance

    @property
    def effective_volume(self) -> int:
        return self.length * self.width * self.effective_height


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
class VehiclePlan:
    truck_name: str
    vehicle_index: int
    target_counts: Dict[str, int]
    state: LayoutState
    feasible_full_pack: bool
    actual_counts: Dict[str, int]


# ============================================================
# 基础数据
# ============================================================

TRUCKS: Dict[str, Truck] = {
    "车型1": Truck("车型1", 420, 210, 220, 6000.0, 450.0),
    "车型2": Truck("车型2", 680, 245, 250, 10000.0, 700.0),
}

CARGO_TYPES: Dict[str, CargoType] = {
    "G1": CargoType("G1", "standard", 60, 40, 30, 12, 800, True, True, False, False),
    "G2": CargoType("G2", "standard", 50, 35, 25, 8, 1000, True, True, False, False),
    "G3": CargoType("G3", "fragile", 70, 50, 40, 15, 300, False, True, True, False),
    "G4": CargoType("G4", "oriented", 80, 60, 50, 25, 400, True, False, False, True),
    "G5": CargoType("G5", "oriented", 40, 40, 60, 18, 500, True, False, False, True),
}

TYPE_ORDER = ["G3", "G4", "G5", "G1", "G2"]  # 1.2 中优先难装货物


# ============================================================
# 姿态与单件展开
# ============================================================

def generate_orientations(cargo: CargoType) -> Tuple[Orientation, ...]:
    l, w, h = cargo.length, cargo.width, cargo.height
    dims = [
        (l, w, h, "LWH"),
        (l, h, w, "LHW"),
        (w, l, h, "WLH"),
        (w, h, l, "WHL"),
        (h, l, w, "HLW"),
        (h, w, l, "HWL"),
    ]
    if cargo.fragile:
        dims = [(l, w, h, "LWH"), (w, l, h, "WLH")]
    elif cargo.oriented:
        dims = [(l, w, h, "LWH")]

    out: List[Orientation] = []
    seen = set()
    for _, (a, b, c, name) in enumerate(dims):
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            out.append(Orientation(len(out) + 1, key, name))
    return tuple(out)


def expand_items(counts: Dict[str, int]) -> List[CargoItem]:
    items: List[CargoItem] = []
    for type_id in TYPE_ORDER:
        cargo = CARGO_TYPES[type_id]
        n = counts.get(type_id, 0)
        if n <= 0:
            continue
        oris = generate_orientations(cargo)
        for i in range(1, n + 1):
            items.append(
                CargoItem(
                    item_id=f"{type_id}_{i:04d}",
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


# ============================================================
# 基础评价
# ============================================================

def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    space_util = used_volume / truck.effective_volume
    weight_util = used_weight / truck.max_weight
    fullness = 0.72 * space_util + 0.28 * weight_util
    return space_util, weight_util, fullness


def floor_capacity_for_type(truck: Truck, type_id: str) -> int:
    cargo = CARGO_TYPES[type_id]
    best = 0
    for ori in generate_orientations(cargo):
        l, w, h = ori.size
        if h > truck.effective_height:
            continue
        best = max(best, (truck.length // l) * (truck.width // w))
    return best


# ============================================================
# 空间工具
# ============================================================

def sort_spaces_dblf(spaces: Sequence[Space]) -> List[Space]:
    return sorted(spaces, key=lambda s: (s.z, s.y, s.x, s.volume))


def remove_contained_spaces(spaces: List[Space]) -> List[Space]:
    result: List[Space] = []
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
        if not contained and a.length > 0 and a.width > 0 and a.height > 0:
            result.append(a)
    return result


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
                    new_spaces = [spaces[k] for k in range(n) if k not in (i, j)]
                    new_spaces.append(m)
                    spaces = remove_contained_spaces(new_spaces)
                    changed = True
                    merged = True
                    break
            if merged:
                break
    return spaces


# ============================================================
# 单车增强装箱器
# ============================================================

def build_item_orders(items: List[CargoItem], policy: int) -> List[CargoItem]:
    def base_area(item: CargoItem) -> int:
        return max(o.size[0] * o.size[1] for o in item.allowed_orientations)

    # 1.2 强化：优先 G3，其次大件 G4/G5，再用 G1/G2 填缝
    if policy == 0:
        return sorted(items, key=lambda it: (it.type_id != "G3", it.type_id not in ("G4", "G5"), -base_area(it), -it.volume, it.item_id))
    if policy == 1:
        return sorted(items, key=lambda it: (it.fragile is False, it.oriented is False, -it.weight, -it.volume, it.item_id))
    if policy == 2:
        return sorted(items, key=lambda it: (it.type_id not in ("G4", "G5"), it.type_id != "G3", -base_area(it), -it.weight, it.item_id))
    return sorted(items, key=lambda it: (it.type_id != "G3", -it.volume, -it.weight, it.item_id))


def can_place_in_space(item: CargoItem, ori: Orientation, space: Space, placed_map: Dict[str, PlacedCargo]) -> bool:
    l, w, h = ori.size
    if l > space.length or w > space.width or h > space.height:
        return False

    if item.fragile:
        # G3 优先保证单层：这里只允许放底板；这样更贴近 1.2 的瓶颈结构
        if space.z > 0:
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


def placement_gain(truck: Truck, state: LayoutState, item: CargoItem, ori: Orientation, space: Space) -> float:
    l, w, h = ori.size
    fill_ratio = (l * w * h) / max(1, space.length * space.width * space.height)
    low_z_bonus = 1.0 / (1.0 + space.z)
    tight_bonus = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
    g3_floor_bonus = 0.18 if (item.type_id == "G3" and space.z == 0) else 0.0
    big_bonus = 0.08 if item.type_id in ("G4", "G5") and space.z == 0 else 0.0
    used_volume = state.used_volume + item.volume
    used_weight = state.used_weight + item.weight
    _, _, fullness = truck_score(truck, used_volume, used_weight)
    return fullness + 0.10 * fill_ratio + 0.03 * low_z_bonus + 0.02 * tight_bonus + g3_floor_bonus + big_bonus


def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []
    if space.length > placed.length:
        new_spaces.append(Space(space.x + placed.length, space.y, space.z, space.length - placed.length, space.width, space.height,
                                space.support_item_id, space.support_type_id, space.support_length, space.support_width))
    if space.width > placed.width:
        new_spaces.append(Space(space.x, space.y + placed.width, space.z, placed.length, space.width - placed.width, space.height,
                                space.support_item_id, space.support_type_id, space.support_length, space.support_width))
    if space.height > placed.height and placed.category != "fragile":
        new_spaces.append(Space(space.x, space.y, space.z + placed.height, placed.length, placed.width, space.height - placed.height,
                                placed.item_id, placed.type_id, placed.length, placed.width))
    return new_spaces


def apply_placement(truck: Truck, state: LayoutState, item_idx: int, ori: Orientation, space_idx: int) -> LayoutState:
    item = state.remaining[item_idx]
    space = state.spaces[space_idx]
    l, w, h = ori.size
    placed = PlacedCargo(
        item_id=item.item_id,
        type_id=item.type_id,
        category=item.category,
        x=space.x, y=space.y, z=space.z,
        length=l, width=w, height=h,
        weight=item.weight,
        orientation_id=ori.orient_id,
        rotation=ori.rotation,
        support_by=space.support_item_id,
        truck_id=truck.name,
    )
    new_placed = [p for p in state.placed]
    new_placed.append(placed)
    if placed.support_by is not None:
        for p in new_placed:
            if p.item_id == placed.support_by:
                p.direct_supported_weight += item.weight
                break
    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))
    new_spaces = sort_spaces_dblf(merge_spaces(new_spaces))
    new_remaining = state.remaining[:item_idx] + state.remaining[item_idx + 1:]
    used_weight = state.used_weight + item.weight
    used_volume = state.used_volume + item.volume
    space_util, weight_util, fullness = truck_score(truck, used_volume, used_weight)
    packed_ratio = len(new_placed) / max(1, len(new_placed) + len(new_remaining))
    return LayoutState(new_spaces, new_placed, new_remaining, used_weight, used_volume,
                      score=fullness + 0.02 * packed_ratio + 0.01 * space_util + 0.005 * weight_util,
                      packed_ratio=packed_ratio)


def pack_with_beam_search(truck: Truck, items: List[CargoItem], beam_width: int = 3, policy: int = 0) -> LayoutState:
    ordered = build_item_orders(items, policy)
    init = LayoutState(
        spaces=[Space(0, 0, 0, truck.length, truck.width, truck.effective_height, None, None, truck.length, truck.width)],
        placed=[], remaining=ordered, used_weight=0.0, used_volume=0, score=0.0, packed_ratio=0.0
    )
    beam = [init]
    best = init
    while beam:
        next_beam: List[LayoutState] = []
        expanded_any = False
        for state in beam:
            if state.score > best.score or state.used_volume > best.used_volume:
                best = state
            if not state.remaining or not state.spaces:
                next_beam.append(state)
                continue
            placed_map = {p.item_id: p for p in state.placed}
            item_candidates = state.remaining[:min(6, len(state.remaining))]
            move_pool: List[Tuple[float, int, Orientation, int]] = []
            for item_idx, item in enumerate(item_candidates):
                for space_idx, space in enumerate(state.spaces[:min(18, len(state.spaces))]):
                    for ori in item.allowed_orientations:
                        if can_place_in_space(item, ori, space, placed_map):
                            gain = placement_gain(truck, state, item, ori, space)
                            move_pool.append((gain, item_idx, ori, space_idx))
            move_pool.sort(key=lambda x: x[0], reverse=True)
            move_pool = move_pool[:10]
            if not move_pool:
                next_beam.append(state)
                continue
            expanded_any = True
            for _, item_idx, ori, space_idx in move_pool:
                next_beam.append(apply_placement(truck, state, item_idx, ori, space_idx))
        if not expanded_any:
            break
        next_beam.sort(key=lambda st: (st.score, st.used_volume, st.used_weight, len(st.placed)), reverse=True)
        beam = next_beam[:beam_width]
        if beam and (beam[0].score > best.score or beam[0].used_volume > best.used_volume):
            best = beam[0]
    return best


def solve_single_vehicle_load(truck: Truck, counts: Dict[str, int], vehicle_index: int, beam_width: int = 3) -> VehiclePlan:
    items = expand_items(counts)
    best_state: Optional[LayoutState] = None
    best_policy = None
    for policy in range(4):
        state = pack_with_beam_search(truck, items, beam_width=beam_width, policy=policy)
        if best_state is None or state.used_volume > best_state.used_volume or (
            state.used_volume == best_state.used_volume and state.used_weight > best_state.used_weight
        ):
            best_state = state
            best_policy = policy
    assert best_state is not None
    actual_counts = dict(Counter(p.type_id for p in best_state.placed))
    feasible = sum(actual_counts.values()) == sum(counts.values())
    return VehiclePlan(truck.name, vehicle_index, counts.copy(), best_state, feasible, actual_counts)


# ============================================================
# 下界与分层分配
# ============================================================

def lower_bound_vehicle_count_basic(truck: Truck) -> int:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    return max(math.ceil(total_volume / truck.effective_volume), math.ceil(total_weight / truck.max_weight))


def lower_bound_vehicle_count_g3(truck: Truck) -> int:
    g3_cap = floor_capacity_for_type(truck, "G3")
    if g3_cap <= 0:
        return 10**9
    return math.ceil(CARGO_TYPES["G3"].quantity / g3_cap)


def lower_bound_vehicle_count(truck: Truck) -> Tuple[int, int, int]:
    basic = lower_bound_vehicle_count_basic(truck)
    g3_lb = lower_bound_vehicle_count_g3(truck)
    return max(basic, g3_lb), basic, g3_lb


def empty_quota_list(K: int) -> List[Dict[str, int]]:
    return [{t: 0 for t in TYPE_ORDER} for _ in range(K)]


def quota_weight(q: Dict[str, int]) -> float:
    return sum(q[t] * CARGO_TYPES[t].weight for t in TYPE_ORDER)


def quota_volume(q: Dict[str, int]) -> int:
    return sum(q[t] * CARGO_TYPES[t].volume for t in TYPE_ORDER)


def residual_weight(truck: Truck, q: Dict[str, int]) -> float:
    return truck.max_weight - quota_weight(q)


def residual_volume(truck: Truck, q: Dict[str, int]) -> int:
    return truck.effective_volume - quota_volume(q)


def initial_quota_split_g3_aware(truck: Truck, K: int) -> List[Dict[str, int]]:
    quotas = empty_quota_list(K)

    # 1) G3 先分，按单层底面积容量约束分散到各车
    g3_cap = floor_capacity_for_type(truck, "G3")
    remaining_g3 = CARGO_TYPES["G3"].quantity
    i = 0
    while remaining_g3 > 0:
        add = min(g3_cap, remaining_g3)
        quotas[i]["G3"] += add
        remaining_g3 -= add
        i = (i + 1) % K
    # 若 K 远大于 G3下界，则尽量均匀打散
    flat_total = CARGO_TYPES["G3"].quantity
    base = flat_total // K
    extra = flat_total % K
    if base > 0:
        quotas = empty_quota_list(K)
        for j in range(K):
            quotas[j]["G3"] = base + (1 if j < extra else 0)
            quotas[j]["G3"] = min(quotas[j]["G3"], g3_cap)
        # 若截断后不足，补到有余量的车辆
        assigned = sum(q["G3"] for q in quotas)
        remaining = flat_total - assigned
        idx = 0
        while remaining > 0:
            if quotas[idx]["G3"] < g3_cap:
                quotas[idx]["G3"] += 1
                remaining -= 1
            idx = (idx + 1) % K

    # 2) G4/G5 其次分，大件优先给当前 G3 少、剩余体积/重量大的车
    for t in ["G4", "G5"]:
        remaining = CARGO_TYPES[t].quantity
        while remaining > 0:
            best_idx = max(
                range(K),
                key=lambda j: (
                    residual_volume(truck, quotas[j]) >= CARGO_TYPES[t].volume,
                    residual_weight(truck, quotas[j]) >= CARGO_TYPES[t].weight,
                    -quotas[j]["G3"],
                    residual_volume(truck, quotas[j]),
                    residual_weight(truck, quotas[j]),
                    -(quotas[j]["G4"] + quotas[j]["G5"]),
                )
            )
            if residual_volume(truck, quotas[best_idx]) < CARGO_TYPES[t].volume or residual_weight(truck, quotas[best_idx]) < CARGO_TYPES[t].weight:
                # 硬塞到当前最优车，后面交给LNS与K扩展解决
                quotas[best_idx][t] += 1
            else:
                quotas[best_idx][t] += 1
            remaining -= 1

    # 3) G1/G2 最后按容重平衡填充
    for t in ["G1", "G2"]:
        remaining = CARGO_TYPES[t].quantity
        while remaining > 0:
            best_idx = max(
                range(K),
                key=lambda j: (
                    residual_volume(truck, quotas[j]) >= CARGO_TYPES[t].volume,
                    residual_weight(truck, quotas[j]) >= CARGO_TYPES[t].weight,
                    min(residual_volume(truck, quotas[j]) / max(1, CARGO_TYPES[t].volume), residual_weight(truck, quotas[j]) / max(1, CARGO_TYPES[t].weight)),
                    residual_volume(truck, quotas[j]),
                )
            )
            quotas[best_idx][t] += 1
            remaining -= 1

    return quotas


# ============================================================
# 轻量LNS修复
# ============================================================

def collect_unpacked(plans: List[VehiclePlan]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER}
    for vp in plans:
        for t in TYPE_ORDER:
            missing[t] += vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0)
    return missing


def vehicle_g3_slack(truck: Truck, plan: VehiclePlan) -> int:
    cap = floor_capacity_for_type(truck, "G3")
    used = plan.actual_counts.get("G3", 0)
    return max(0, cap - used)


def residual_capacity_counts(truck: Truck, plan: VehiclePlan) -> Dict[str, int]:
    out = {t: 0 for t in TYPE_ORDER}
    rw = truck.max_weight - plan.state.used_weight
    rv = truck.effective_volume - plan.state.used_volume
    for t in TYPE_ORDER:
        c = CARGO_TYPES[t]
        out[t] = min(int(rw // c.weight) if c.weight > 0 else 0, rv // c.volume if c.volume > 0 else 0)
    out["G3"] = min(out["G3"], vehicle_g3_slack(truck, plan))
    return out


def revalidate_all(truck: Truck, quotas: List[Dict[str, int]], beam_width: int) -> List[VehiclePlan]:
    return [solve_single_vehicle_load(truck, quotas[j], j + 1, beam_width=beam_width) for j in range(len(quotas))]


def repair_with_lns(truck: Truck, quotas: List[Dict[str, int]], beam_width: int = 3, max_rounds: int = 6, rng_seed: int = 2026) -> Tuple[List[VehiclePlan], bool]:
    rng = random.Random(rng_seed)
    plans = revalidate_all(truck, quotas, beam_width)
    if all(vp.feasible_full_pack for vp in plans):
        return plans, True

    for rd in range(max_rounds):
        missing = collect_unpacked(plans)
        print(f"[{truck.name}] LNS 第 {rd+1}/{max_rounds} 轮，未装货: {missing}", flush=True)
        if all(v == 0 for v in missing.values()):
            return plans, True

        # 1) 优先修复 G3：往有 G3 底面积余量的车挪，同时从这些车中挪走一些 G1/G2/G4/G5
        if missing["G3"] > 0:
            order = sorted(range(len(plans)), key=lambda j: (vehicle_g3_slack(truck, plans[j]), residual_capacity_counts(truck, plans[j]).get("G3", 0)), reverse=True)
            for j in order:
                slack = vehicle_g3_slack(truck, plans[j])
                if slack <= 0:
                    continue
                # 先腾空间：优先移走 G1/G2，再移大件
                for t in ["G1", "G2", "G5", "G4"]:
                    while slack > 0 and quotas[j][t] > 0 and residual_weight(truck, quotas[j]) < CARGO_TYPES["G3"].weight:
                        quotas[j][t] -= 1
                    while slack > 0 and quotas[j][t] > 0 and residual_volume(truck, quotas[j]) < CARGO_TYPES["G3"].volume:
                        quotas[j][t] -= 1
                add = min(missing["G3"], slack)
                while add > 0 and residual_weight(truck, quotas[j]) >= CARGO_TYPES["G3"].weight and residual_volume(truck, quotas[j]) >= CARGO_TYPES["G3"].volume:
                    quotas[j]["G3"] += 1
                    missing["G3"] -= 1
                    add -= 1

        # 2) 修复 G4/G5：把大件往当前大件较少、剩余体积更大的车移动
        for t in ["G4", "G5"]:
            need = missing[t]
            if need <= 0:
                continue
            order = sorted(range(len(plans)), key=lambda j: (quotas[j]["G4"] + quotas[j]["G5"], residual_volume(truck, quotas[j]), residual_weight(truck, quotas[j])))
            for j in order:
                while need > 0 and residual_weight(truck, quotas[j]) >= CARGO_TYPES[t].weight and residual_volume(truck, quotas[j]) >= CARGO_TYPES[t].volume:
                    quotas[j][t] += 1
                    need -= 1
            missing[t] = need

        # 3) 小件填缝修复
        for t in ["G1", "G2"]:
            need = missing[t]
            if need <= 0:
                continue
            order = sorted(range(len(plans)), key=lambda j: residual_volume(truck, quotas[j]), reverse=True)
            for j in order:
                while need > 0 and residual_weight(truck, quotas[j]) >= CARGO_TYPES[t].weight and residual_volume(truck, quotas[j]) >= CARGO_TYPES[t].volume:
                    quotas[j][t] += 1
                    need -= 1
            missing[t] = need

        # 4) 随机交换，防止停滞
        a, b = rng.sample(range(len(quotas)), 2)
        ta = rng.choice(TYPE_ORDER)
        tb = rng.choice(TYPE_ORDER)
        if quotas[a][ta] > 0:
            delta = 1 if ta in ("G3", "G4", "G5") else 3
            delta = min(delta, quotas[a][ta])
            quotas[a][ta] -= delta
            quotas[b][ta] += delta
        if quotas[b][tb] > 0:
            delta = 1 if tb in ("G3", "G4", "G5") else 3
            delta = min(delta, quotas[b][tb])
            quotas[b][tb] -= delta
            quotas[a][tb] += delta

        plans = revalidate_all(truck, quotas, beam_width)
        if all(vp.feasible_full_pack for vp in plans):
            return plans, True

    return plans, all(vp.feasible_full_pack for vp in plans)


# ============================================================
# 问题1.2求解
# ============================================================

def solve_problem_12_fixed_truck(truck: Truck, beam_width: int = 3, lns_rounds: int = 6, max_extra_k: int = 8) -> Tuple[int, List[VehiclePlan], Dict[str, object]]:
    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)

    for extra in range(max_extra_k + 1):
        K = lb + extra
        print(f"[{truck.name}] 正在尝试 K = {K} ...", flush=True)
        quotas = initial_quota_split_g3_aware(truck, K)
        plans, ok = repair_with_lns(truck, quotas, beam_width=beam_width, max_rounds=lns_rounds, rng_seed=2026 + K)
        print(f"[{truck.name}] K = {K} 可行性结果: {ok}", flush=True)
        if ok:
            avg_sv = sum(vp.state.used_volume for vp in plans) / (K * truck.effective_volume)
            avg_wv = sum(vp.state.used_weight for vp in plans) / (K * truck.max_weight)
            summary = {
                "truck": truck.name,
                "vehicle_count": K,
                "lower_bound": lb,
                "lower_bound_basic": basic_lb,
                "lower_bound_g3": g3_lb,
                "avg_space_utilization": round(avg_sv, 6),
                "avg_weight_utilization": round(avg_wv, 6),
                "total_cost": round(K * truck.cost, 2),
                "all_loaded": True,
            }
            return K, plans, summary

    print(f"{truck.name} 在当前范围未找到解，自动扩大搜索范围...")

    return solve_problem_12_fixed_truck(
        truck,
        beam_width=beam_width,
        lns_rounds=lns_rounds,
        max_extra_k=max_extra_k + 20
    )


def write_vehicle_summary_csv(path: str, plans: List[VehiclePlan]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "target_counts", "actual_counts", "feasible_full_pack", "loaded_weight_kg", "loaded_volume_cm3"
        ])
        for vp in plans:
            sv, wv, fs = truck_score(TRUCKS[vp.truck_name], vp.state.used_volume, vp.state.used_weight)
            w.writerow([
                f"{vp.truck_name}_{vp.vehicle_index:03d}",
                round(sv, 6), round(wv, 6), round(fs, 6),
                vp.target_counts, vp.actual_counts, vp.feasible_full_pack,
                round(vp.state.used_weight, 3), vp.state.used_volume,
            ])


def write_items_csv(path: str, placed: Sequence[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z", "length", "width", "height",
            "weight", "orientation_id", "rotation", "support_by", "truck_id"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z, p.length, p.width, p.height,
                p.weight, p.orientation_id, p.rotation, p.support_by or "", p.truck_id or ""
            ])


def solve_for_truck(truck: Truck, beam_width: int, lns_rounds: int, max_extra_k: int, outdir: str) -> Dict[str, object]:
    K, plans, summary = solve_problem_12_fixed_truck(truck, beam_width=beam_width, lns_rounds=lns_rounds, max_extra_k=max_extra_k)
    truck_dir = os.path.join(outdir, truck.name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck.name}_车辆汇总.csv"), plans)
    for vp in plans:
        write_items_csv(os.path.join(truck_dir, f"{truck.name}_{vp.vehicle_index:03d}_装箱明细.csv"), vp.state.placed)
    summary["output_dir"] = truck_dir
    return summary


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 最终版（G3主导 + 分层分配 + 单车增强装箱 + 轻量LNS）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--beam-width", type=int, default=3, help="单车增强装箱 beam width")
    parser.add_argument("--lns-rounds", type=int, default=6, help="轻量LNS轮数")
    parser.add_argument("--max-extra-k", type=int, default=8, help="在理论下界基础上最多额外尝试的车辆数")
    parser.add_argument("--outdir", type=str, default="output_p12_final_g3aware", help="输出目录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for name in truck_list:
        truck = TRUCKS[name]
        print("\n" + "=" * 56)
        print(f"开始求解问题1.2：{truck.name}")
        print("=" * 56)
        summary = solve_for_truck(truck, args.beam_width, args.lns_rounds, args.max_extra_k, args.outdir)
        print(summary)


if __name__ == "__main__":
    main()
