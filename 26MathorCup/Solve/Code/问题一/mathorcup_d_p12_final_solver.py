
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2（单一车型、车辆数最少）
最终推荐版：分层分配 + 单车增强装箱 + 轻量LNS修复

说明：
1. 外层从理论下界开始试探车辆数 K；
2. 在固定 K 下，先做“分层分配”：
   - G3（易碎件）优先按底面积资源均匀分配；
   - G4/G5（大件/定向件）优先按体积与载重分配；
   - G1/G2 用于填补剩余体积与重量；
3. 每辆车调用轻量版“单车增强装箱器”：
   beam search + DBLF + 三空间分割 + 空间合并；
4. 若仍有未装货物，则进行轻量LNS跨车修复，再重新验证；
5. 第一次全部可行的 K 作为近似最少车辆数解。

注意：
- 这是工程化近似算法，不是严格精确最优算法；
- 相比“SA + 重型逐车验证”更适合本地运行；
- 相比“模式生成 + 覆盖主问题”更能体现三维可装性的影响。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
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
    max_support_pressure: float = 500.0  # kg/m^2
    top_clearance: int = 3

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def density(self) -> float:
        return self.weight / self.volume


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
    truck_id: str
    target_counts: Dict[str, int]
    state: LayoutState
    actual_counts: Dict[str, int]
    feasible_full_pack: bool


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

TYPE_ORDER = ["G1", "G2", "G3", "G4", "G5"]
DIFFICULT_TYPES = ["G3", "G4", "G5", "G1", "G2"]


# ============================================================
# 姿态与展开
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
    if cargo.category == "fragile":
        dims = [(l, w, h, "LWH"), (w, l, h, "WLH")]
    elif cargo.category == "oriented":
        dims = [(l, w, h, "LWH")]

    uniq: List[Orientation] = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            uniq.append(Orientation(len(uniq), key, name))
    return tuple(uniq)


def expand_items(counts: Dict[str, int]) -> List[CargoItem]:
    items: List[CargoItem] = []
    for t in TYPE_ORDER:
        cargo = CARGO_TYPES[t]
        oris = generate_orientations(cargo)
        for i in range(1, counts.get(t, 0) + 1):
            items.append(CargoItem(
                item_id=f"{t}_{i:04d}",
                type_id=t,
                category=cargo.category,
                original_size=(cargo.length, cargo.width, cargo.height),
                weight=cargo.weight,
                volume=cargo.volume,
                stackable=cargo.stackable,
                fragile=cargo.fragile,
                oriented=cargo.oriented,
                allowed_orientations=oris,
            ))
    return items


# ============================================================
# 单车装箱：轻量增强版
# ============================================================

def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    space_util = used_volume / truck.effective_volume
    weight_util = used_weight / truck.max_weight
    fullness = 0.68 * space_util + 0.32 * weight_util
    return space_util, weight_util, fullness


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
    same_support = (
        a.support_item_id == b.support_item_id and
        a.support_type_id == b.support_type_id and
        a.support_length == b.support_length and
        a.support_width == b.support_width
    )
    if not same_support:
        return None

    # x merge
    if a.y == b.y and a.z == b.z and a.width == b.width and a.height == b.height:
        if a.x + a.length == b.x:
            return Space(a.x, a.y, a.z, a.length + b.length, a.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.x + b.length == a.x:
            return Space(b.x, b.y, b.z, a.length + b.length, a.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
    # y merge
    if a.x == b.x and a.z == b.z and a.length == b.length and a.height == b.height:
        if a.y + a.width == b.y:
            return Space(a.x, a.y, a.z, a.length, a.width + b.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.y + b.width == a.y:
            return Space(a.x, b.y, b.z, a.length, a.width + b.width, a.height,
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


def build_item_orders(items: List[CargoItem], policy: int) -> List[CargoItem]:
    def max_base(item: CargoItem) -> int:
        return max(o.size[0] * o.size[1] for o in item.allowed_orientations)
    if policy == 0:
        return sorted(items, key=lambda it: (it.fragile, it.category == "oriented", -it.volume, -it.weight, it.item_id))
    if policy == 1:
        return sorted(items, key=lambda it: (-max_base(it), -it.volume, it.fragile, it.item_id))
    return sorted(items, key=lambda it: (it.category != "standard", it.fragile, -it.weight / it.volume, -it.volume, it.item_id))


def can_place_in_space(item: CargoItem, ori: Orientation, space: Space, placed_map: Dict[str, PlacedCargo], truck: Truck, used_weight: float) -> bool:
    l, w, h = ori.size
    if l > space.length or w > space.width or h > space.height:
        return False
    if used_weight + item.weight > truck.max_weight + 1e-9:
        return False
    if space.z + h > truck.effective_height:
        return False

    # fragile constraints
    if item.fragile:
        if space.z > 0 and space.support_type_id not in ("G1", "G2"):
            return False

    if space.z > 0:
        if space.support_item_id is None:
            return False
        support = placed_map.get(space.support_item_id)
        if support is None:
            return False
        if support.category == "fragile":
            return False
        if l > support.length or w > support.width:
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
    used_volume = state.used_volume + item.volume
    used_weight = state.used_weight + item.weight
    sv, wv, full = truck_score(truck, used_volume, used_weight)
    support_bonus = 0.08 if space.z > 0 else 0.0
    hard_bonus = 0.06 if item.type_id in ("G3", "G4", "G5") else 0.0
    return full + 0.10 * fill_ratio + 0.03 * low_z_bonus + 0.02 * tight_bonus + support_bonus + hard_bonus + 0.01 * sv + 0.005 * wv


def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []
    if space.length > placed.length:
        new_spaces.append(Space(space.x + placed.length, space.y, space.z,
                                space.length - placed.length, space.width, space.height,
                                space.support_item_id, space.support_type_id, space.support_length, space.support_width))
    if space.width > placed.width:
        new_spaces.append(Space(space.x, space.y + placed.width, space.z,
                                placed.length, space.width - placed.width, space.height,
                                space.support_item_id, space.support_type_id, space.support_length, space.support_width))
    if space.height > placed.height and placed.category != "fragile":
        new_spaces.append(Space(space.x, space.y, space.z + placed.height,
                                placed.length, placed.width, space.height - placed.height,
                                placed.item_id, placed.type_id, placed.length, placed.width))
    return [s for s in new_spaces if s.length > 0 and s.width > 0 and s.height > 0]


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
        truck_id=truck.name
    )
    new_placed = list(state.placed)
    new_placed.append(placed)

    if space.support_item_id is not None:
        for p in new_placed:
            if p.item_id == space.support_item_id:
                p.direct_supported_weight += item.weight
                break

    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))
    new_spaces = sort_spaces_dblf(merge_spaces(new_spaces))

    new_remaining = state.remaining[:item_idx] + state.remaining[item_idx + 1:]
    used_weight = state.used_weight + item.weight
    used_volume = state.used_volume + item.volume
    sv, wv, full = truck_score(truck, used_volume, used_weight)
    packed_ratio = len(new_placed) / max(1, len(new_placed) + len(new_remaining))

    return LayoutState(
        spaces=new_spaces,
        placed=new_placed,
        remaining=new_remaining,
        used_weight=used_weight,
        used_volume=used_volume,
        score=full + 0.02 * packed_ratio + 0.01 * sv + 0.005 * wv,
        packed_ratio=packed_ratio,
    )


def pack_with_beam_search(truck: Truck, items: List[CargoItem], beam_width: int = 3, policy: int = 0) -> LayoutState:
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
    beam = [init]
    best = init

    while beam:
        next_beam: List[LayoutState] = []
        expanded_any = False

        for state in beam:
            if (state.used_volume, state.used_weight, state.score) > (best.used_volume, best.used_weight, best.score):
                best = state
            if not state.remaining or not state.spaces:
                next_beam.append(state)
                continue

            placed_map = {p.item_id: p for p in state.placed}
            item_candidates = state.remaining[: min(6, len(state.remaining))]
            move_pool: List[Tuple[float, int, Orientation, int]] = []

            for item_idx, item in enumerate(item_candidates):
                for space_idx, space in enumerate(state.spaces[: min(15, len(state.spaces))]):
                    for ori in item.allowed_orientations:
                        if can_place_in_space(item, ori, space, placed_map, truck, state.used_weight):
                            gain = placement_gain(truck, state, item, ori, space)
                            move_pool.append((gain, item_idx, ori, space_idx))

            move_pool.sort(key=lambda x: x[0], reverse=True)
            move_pool = move_pool[: 8]

            if not move_pool:
                next_beam.append(state)
                continue

            expanded_any = True
            for _, item_idx, ori, space_idx in move_pool:
                child = apply_placement(truck, state, item_idx, ori, space_idx)
                next_beam.append(child)

        if not expanded_any:
            break

        next_beam.sort(key=lambda st: (st.score, st.used_volume, st.used_weight, len(st.placed)), reverse=True)
        beam = next_beam[:beam_width]
        if beam and (beam[0].used_volume, beam[0].used_weight) > (best.used_volume, best.used_weight):
            best = beam[0]

    return best


def solve_single_vehicle_load(truck: Truck, counts: Dict[str, int], truck_id: str, beam_width: int = 3) -> VehiclePlan:
    items = expand_items(counts)
    best_state: Optional[LayoutState] = None
    for policy in range(3):
        state = pack_with_beam_search(truck, items, beam_width=beam_width, policy=policy)
        if best_state is None or (state.used_volume, state.used_weight) > (best_state.used_volume, best_state.used_weight):
            best_state = state
    assert best_state is not None
    actual_counts = dict(Counter(p.type_id for p in best_state.placed))
    feasible = all(actual_counts.get(t, 0) == counts.get(t, 0) for t in TYPE_ORDER)
    return VehiclePlan(
        truck_id=truck_id,
        target_counts=counts.copy(),
        state=best_state,
        actual_counts=actual_counts,
        feasible_full_pack=feasible,
    )


# ============================================================
# 问题1.2：分层分配
# ============================================================

def lower_bound_vehicle_count(truck: Truck) -> int:
    total_volume = sum(c.quantity * c.volume for c in CARGO_TYPES.values())
    total_weight = sum(c.quantity * c.weight for c in CARGO_TYPES.values())
    by_volume = math.ceil(total_volume / truck.effective_volume)
    by_weight = math.ceil(total_weight / truck.max_weight)
    return max(by_volume, by_weight)


def best_grid_count(truck: Truck, cargo: CargoType) -> int:
    best = 0
    for ori in generate_orientations(cargo):
        l, w, h = ori.size
        nx = truck.length // l
        ny = truck.width // w
        nz = 1 if cargo.fragile else truck.effective_height // h
        best = max(best, nx * ny * nz)
    return best


def per_vehicle_rough_cap(truck: Truck, t: str) -> int:
    cargo = CARGO_TYPES[t]
    by_vol = truck.effective_volume // cargo.volume
    by_wt = int(truck.max_weight // cargo.weight)
    by_grid = best_grid_count(truck, cargo)
    return max(0, min(cargo.quantity, by_vol, by_wt, by_grid))


def quota_metrics(counts: Dict[str, int]) -> Tuple[float, int]:
    wt = sum(counts[t] * CARGO_TYPES[t].weight for t in TYPE_ORDER)
    vol = sum(counts[t] * CARGO_TYPES[t].volume for t in TYPE_ORDER)
    return wt, vol


def residual_score_for_type(truck: Truck, counts: Dict[str, int], t: str) -> float:
    wt, vol = quota_metrics(counts)
    cargo = CARGO_TYPES[t]
    if wt + cargo.weight > truck.max_weight + 1e-9:
        return -1e18
    if vol + cargo.volume > truck.effective_volume:
        return -1e18

    after_w = wt + cargo.weight
    after_v = vol + cargo.volume
    wr = after_w / truck.max_weight
    vr = after_v / truck.effective_volume

    rough_cap = per_vehicle_rough_cap(truck, t)
    overflow_pen = max(0.0, (counts.get(t, 0) + 1) / max(1, rough_cap) - 1.0)
    hard_bonus = 0.06 if t in ("G3", "G4", "G5") else 0.0
    balance = -0.05 * abs(vr - wr)
    return 0.66 * vr + 0.34 * wr + hard_bonus + balance - 0.12 * overflow_pen


def allocate_uniform(total: int, K: int) -> List[int]:
    base = total // K
    rem = total % K
    return [base + (1 if i < rem else 0) for i in range(K)]


def layered_initial_allocation(truck: Truck, K: int) -> List[Dict[str, int]]:
    quotas: List[Dict[str, int]] = [{t: 0 for t in TYPE_ORDER} for _ in range(K)]

    # 第一层：G3 易碎件按底面积资源均匀分散
    g3_total = CARGO_TYPES["G3"].quantity
    g3_rough_cap = max(1, per_vehicle_rough_cap(truck, "G3"))
    remaining = g3_total
    order = list(range(K))
    # 先均匀分，单车不超过rough cap附近
    for idx in order:
        take = min(g3_rough_cap, math.ceil(remaining / max(1, K - idx)))
        quotas[idx]["G3"] += min(take, remaining)
        remaining -= min(take, remaining)
        if remaining <= 0:
            break
    # 若还有剩余，轮转分
    idx = 0
    while remaining > 0:
        add = min(g3_rough_cap // 3 + 1, remaining)
        quotas[idx % K]["G3"] += add
        remaining -= add
        idx += 1

    # 第二层：G4/G5 大件优先均匀分到当前已占用较少、体积较空的车
    for t in ["G4", "G5"]:
        total = CARGO_TYPES[t].quantity
        for _ in range(total):
            best_j = max(range(K), key=lambda j: residual_score_for_type(truck, quotas[j], t))
            quotas[best_j][t] += 1

    # 第三层：G1/G2 用于填补剩余容重
    # 优先 G1 再 G2 的混装平衡
    for t in ["G1", "G2"]:
        total = CARGO_TYPES[t].quantity
        for _ in range(total):
            best_j = max(range(K), key=lambda j: residual_score_for_type(truck, quotas[j], t))
            if residual_score_for_type(truck, quotas[best_j], t) <= -1e17:
                # 若无法继续加，优先加到最空车做软超配，后续 LNS 修复
                best_j = min(range(K), key=lambda j: quota_metrics(quotas[j])[1])
            quotas[best_j][t] += 1

    return quotas


# ============================================================
# LNS 修复
# ============================================================

def collect_unpacked(plans: List[VehiclePlan]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER}
    for vp in plans:
        for t in TYPE_ORDER:
            missing[t] += max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))
    return missing


def residual_capacity_counts(truck: Truck, vp: VehiclePlan) -> Dict[str, int]:
    # 基于实际装入结果的剩余容重，给出各类货物的粗补装数量上界
    res_w = truck.max_weight - vp.state.used_weight
    res_v = truck.effective_volume - vp.state.used_volume
    caps: Dict[str, int] = {}
    for t in TYPE_ORDER:
        c = CARGO_TYPES[t]
        by_w = int(max(0.0, res_w) // c.weight)
        by_v = int(max(0, res_v) // c.volume)
        caps[t] = max(0, min(by_w, by_v))
    return caps


def vehicle_stress(vp: VehiclePlan) -> float:
    target_total = sum(vp.target_counts.values())
    actual_total = len(vp.state.placed)
    if target_total <= 0:
        return 0.0
    packed_ratio = actual_total / target_total
    sv, wv, full = truck_score(TRUCKS[vp.truck_id.split("_")[0] if "_" in vp.truck_id else vp.truck_id] if vp.truck_id in TRUCKS else TRUCKS["车型1"], vp.state.used_volume, vp.state.used_weight)
    return (1.0 - packed_ratio) + 0.2 * (1.0 - full)


def choose_receiver(truck: Truck, quotas: List[Dict[str, int]], plans: List[VehiclePlan], t: str) -> int:
    caps = [residual_capacity_counts(truck, vp).get(t, 0) for vp in plans]
    best = max(range(len(plans)), key=lambda j: (caps[j], -sum(quotas[j].values())))
    return best


def lightweight_lns_repair(truck: Truck, quotas: List[Dict[str, int]], beam_width: int = 3, max_rounds: int = 6, rng_seed: int = 2026) -> Tuple[List[VehiclePlan], bool]:
    rng = random.Random(rng_seed)
    plans = [solve_single_vehicle_load(truck, quotas[j], f"{truck.name}_{j+1}", beam_width=beam_width) for j in range(len(quotas))]

    if all(vp.feasible_full_pack for vp in plans):
        return plans, True

    for rd in range(max_rounds):
        missing = collect_unpacked(plans)
        print(f"[{truck.name}] LNS 第 {rd+1}/{max_rounds} 轮，未装货: {missing}", flush=True)

        if all(v == 0 for v in missing.values()):
            return plans, True

        improved = False

        # 1) 先把难货往更空、粗容量更足的车挪
        for t in DIFFICULT_TYPES:
            need = missing[t]
            if need <= 0:
                continue

            # 找最差的车作为释放源
            failing = sorted(
                [j for j, vp in enumerate(plans) if vp.target_counts.get(t, 0) > vp.actual_counts.get(t, 0)],
                key=lambda j: (vp_shortfall(plans[j], t), sum(quotas[j].values())),
                reverse=True
            )
            for src in failing:
                movable = min(need, max(1, vp_shortfall(plans[src], t)))
                if movable <= 0 or quotas[src][t] <= 0:
                    continue

                for _ in range(movable):
                    dst = choose_receiver(truck, quotas, plans, t)
                    if dst == src:
                        break
                    quotas[src][t] -= 1
                    quotas[dst][t] += 1
                    need -= 1
                    improved = True
                    if need <= 0:
                        break
                if need <= 0:
                    break

        # 2) 若仍不改进，做“难货换轻货”释放底面/大件空间
        if not improved:
            worst = max(range(len(plans)), key=lambda j: packed_shortage_ratio(plans[j]))
            best = min(range(len(plans)), key=lambda j: packed_shortage_ratio(plans[j]))
            for hard in ["G3", "G4", "G5"]:
                if quotas[worst][hard] > 0:
                    quotas[worst][hard] -= 1
                    quotas[best][hard] += 1
                    # 用轻货回填，保持平衡
                    for soft in ["G1", "G2"]:
                        if quotas[best][soft] > 0:
                            quotas[best][soft] -= 1
                            quotas[worst][soft] += 1
                            break
                    improved = True
                    break

        # 3) 仍无改进则随机交换少量货类
        if not improved:
            a, b = rng.sample(range(len(quotas)), 2)
            ta = rng.choice(TYPE_ORDER)
            tb = rng.choice(TYPE_ORDER)
            if quotas[a][ta] > 0:
                quotas[a][ta] -= 1
                quotas[b][ta] += 1
            if quotas[b][tb] > 0:
                quotas[b][tb] -= 1
                quotas[a][tb] += 1

        plans = [solve_single_vehicle_load(truck, quotas[j], f"{truck.name}_{j+1}", beam_width=beam_width) for j in range(len(quotas))]
        if all(vp.feasible_full_pack for vp in plans):
            return plans, True

    return plans, all(vp.feasible_full_pack for vp in plans)


def vp_shortfall(vp: VehiclePlan, t: str) -> int:
    return max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))


def packed_shortage_ratio(vp: VehiclePlan) -> float:
    tgt = sum(vp.target_counts.values())
    if tgt <= 0:
        return 0.0
    return 1.0 - len(vp.state.placed) / tgt


# ============================================================
# 问题1.2主流程
# ============================================================

def solve_problem_12_fixed_truck(truck: Truck, beam_width: int = 3, lns_rounds: int = 6, max_extra_k: int = 8) -> Tuple[int, List[VehiclePlan], Dict[str, object]]:
    lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb}", flush=True)

    for extra in range(max_extra_k + 1):
        K = lb + extra
        print(f"[{truck.name}] 正在尝试 K = {K} ...", flush=True)

        quotas = layered_initial_allocation(truck, K)
        plans, ok = lightweight_lns_repair(
            truck,
            quotas,
            beam_width=beam_width,
            max_rounds=lns_rounds,
            rng_seed=2026 + K,
        )

        print(f"[{truck.name}] K = {K} 可行性结果: {ok}", flush=True)
        if ok:
            avg_sv = sum(vp.state.used_volume for vp in plans) / (K * truck.effective_volume)
            avg_wv = sum(vp.state.used_weight for vp in plans) / (K * truck.max_weight)
            summary = {
                "truck": truck.name,
                "vehicle_count": K,
                "lower_bound": lb,
                "avg_space_utilization": round(avg_sv, 6),
                "avg_weight_utilization": round(avg_wv, 6),
                "total_cost": round(K * truck.cost, 2),
                "all_loaded": True,
            }
            return K, plans, summary

    raise RuntimeError(f"{truck.name} 在 K <= {lb + max_extra_k} 范围内未找到可行方案。")


# ============================================================
# 输出
# ============================================================

def write_vehicle_summary_csv(path: str, plans: List[VehiclePlan]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "truck_id", "placed_item_count", "space_utilization", "weight_utilization",
            "fullness_score", "loaded_weight_kg", "loaded_volume_cm3",
            "target_counts", "actual_counts", "feasible_full_pack"
        ])
        for vp in plans:
            sv, wv, full = truck_score(TRUCKS[vp.truck_id.split("_")[0]], vp.state.used_volume, vp.state.used_weight)
            writer.writerow([
                vp.truck_id,
                len(vp.state.placed),
                round(sv, 6),
                round(wv, 6),
                round(full, 6),
                round(vp.state.used_weight, 3),
                vp.state.used_volume,
                vp.target_counts,
                vp.actual_counts,
                vp.feasible_full_pack,
            ])


def write_items_csv(path: str, placed: Sequence[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "type_id", "category", "truck_id",
            "x", "y", "z",
            "length", "width", "height",
            "weight", "orientation_id", "rotation", "support_by"
        ])
        for p in placed:
            writer.writerow([
                p.item_id, p.type_id, p.category, p.truck_id,
                p.x, p.y, p.z,
                p.length, p.width, p.height,
                p.weight, p.orientation_id, p.rotation,
                p.support_by or ""
            ])


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 单一车型最少车辆数（分层分配 + 单车增强装箱 + 轻量LNS修复）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all", help="选择车型")
    parser.add_argument("--beam-width", type=int, default=3, help="单车装箱阶段 beam width")
    parser.add_argument("--lns-rounds", type=int, default=6, help="轻量LNS修复轮数")
    parser.add_argument("--max-extra-k", type=int, default=8, help="在理论下界基础上最多额外尝试的车辆数")
    parser.add_argument("--outdir", type=str, default="output_p12_final", help="输出目录")
    return parser.parse_args()


def solve_for_truck(truck: Truck, beam_width: int, lns_rounds: int, max_extra_k: int, out_root: str) -> Dict[str, object]:
    print("\n" + "=" * 56)
    print(f"开始求解问题1.2：{truck.name}")
    print("=" * 56)

    K, plans, summary = solve_problem_12_fixed_truck(
        truck=truck,
        beam_width=beam_width,
        lns_rounds=lns_rounds,
        max_extra_k=max_extra_k,
    )

    truck_dir = os.path.join(out_root, truck.name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck.name}_车辆汇总.csv"), plans)
    for idx, vp in enumerate(plans, start=1):
        write_items_csv(os.path.join(truck_dir, f"{truck.name}_{idx:03d}_装箱明细.csv"), vp.state.placed)

    summary["output_dir"] = truck_dir
    return summary


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for truck_name in truck_list:
        summary = solve_for_truck(
            TRUCKS[truck_name],
            beam_width=args.beam_width,
            lns_rounds=args.lns_rounds,
            max_extra_k=args.max_extra_k,
            out_root=args.outdir,
        )
        print(summary)


if __name__ == "__main__":
    main()
