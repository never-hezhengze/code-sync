#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2（单一车型，全部装完且车辆最少）
模式生成 + 最少车辆枚举/分支定界

思路：
1. 先用快速单车装箱器生成一批“单车可行装载模式”；
2. 再在模式层面求解：用最少的车辆（模式）覆盖全部货物需求；
3. 最后对每辆车输出逐件坐标与姿态。

说明：
- 这是工程化近似算法，目标是稳定、可运行、可解释；
- 单车模式生成器采用轻量 DBLF + 三空间分割 + 空间合并；
- 模式主问题采用分支定界 DFS，而不是重型 SA / GA；
- 更适合本题“货物类型少（5类）、数量大、固定车型”的 1.2 场景。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter, defaultdict
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
    max_support_pressure: float = 500.0
    top_clearance: int = 3

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def density(self) -> float:
        return self.weight / self.volume


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


@dataclass(frozen=True)
class Pattern:
    pattern_id: int
    counts: Tuple[int, int, int, int, int]
    used_volume: int
    used_weight: float
    space_util: float
    weight_util: float
    fullness: float


# ============================================================
# 基础数据
# ============================================================

TYPE_ORDER = ("G1", "G2", "G3", "G4", "G5")

TRUCKS: Dict[str, Truck] = {
    "车型1": Truck("车型1", 420, 210, 220, 6000.0, 450.0),
    "车型2": Truck("车型2", 680, 245, 250, 10000.0, 700.0),
}

CARGO_TYPES: Dict[str, CargoType] = {
    "G1": CargoType("G1", "standard", 60, 40, 30, 12.0, 800, True, True, False, False),
    "G2": CargoType("G2", "standard", 50, 35, 25, 8.0, 1000, True, True, False, False),
    "G3": CargoType("G3", "fragile", 70, 50, 40, 15.0, 300, False, True, True, False),
    "G4": CargoType("G4", "oriented", 80, 60, 50, 25.0, 400, True, False, False, True),
    "G5": CargoType("G5", "oriented", 40, 40, 60, 18.0, 500, True, False, False, True),
}


# ============================================================
# 姿态 / 单件展开
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

    uniq: List[Orientation] = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            uniq.append(Orientation(len(uniq) + 1, key, name))
    return tuple(uniq)


ORIENTATIONS = {t: generate_orientations(c) for t, c in CARGO_TYPES.items()}


def expand_items_for_pattern(counts: Dict[str, int]) -> List[CargoItem]:
    items: List[CargoItem] = []
    for t in TYPE_ORDER:
        cargo = CARGO_TYPES[t]
        n = counts.get(t, 0)
        for i in range(1, n + 1):
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
                allowed_orientations=ORIENTATIONS[t],
            ))
    return items


# ============================================================
# 轻量单车装箱器（模式生成/还原共用）
# ============================================================


def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / truck.effective_volume
    wv = used_weight / truck.max_weight
    fullness = 0.72 * sv + 0.28 * wv
    return sv, wv, fullness



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
                (a.x, a.y, a.z, a.length, a.width, a.height) !=
                (b.x, b.y, b.z, b.length, b.width, b.height)
            ):
                contained = True
                break
        if not contained and a.length > 0 and a.width > 0 and a.height > 0:
            result.append(a)
    return result



def try_merge_two_spaces(a: Space, b: Space) -> Optional[Space]:
    same_support = (a.support_item_id == b.support_item_id and a.support_type_id == b.support_type_id)
    if not same_support:
        return None
    if a.y == b.y and a.z == b.z and a.width == b.width and a.height == b.height:
        if a.x + a.length == b.x:
            return Space(a.x, a.y, a.z, a.length + b.length, a.width, a.height, a.support_item_id, a.support_type_id)
        if b.x + b.length == a.x:
            return Space(b.x, b.y, b.z, a.length + b.length, a.width, a.height, a.support_item_id, a.support_type_id)
    if a.x == b.x and a.z == b.z and a.length == b.length and a.height == b.height:
        if a.y + a.width == b.y:
            return Space(a.x, a.y, a.z, a.length, a.width + b.width, a.height, a.support_item_id, a.support_type_id)
        if b.y + b.width == a.y:
            return Space(b.x, b.y, b.z, a.length, a.width + b.width, a.height, a.support_item_id, a.support_type_id)
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



def can_place(item: CargoItem, ori: Orientation, space: Space, placed_map: Dict[str, PlacedCargo], state: LayoutState, truck: Truck) -> bool:
    l, w, h = ori.size
    if l > space.length or w > space.width or h > space.height:
        return False
    if state.used_weight + item.weight > truck.max_weight + 1e-9:
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



def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []
    if space.length > placed.length:
        new_spaces.append(Space(space.x + placed.length, space.y, space.z,
                                space.length - placed.length, space.width, space.height,
                                space.support_item_id, space.support_type_id))
    if space.width > placed.width:
        new_spaces.append(Space(space.x, space.y + placed.width, space.z,
                                placed.length, space.width - placed.width, space.height,
                                space.support_item_id, space.support_type_id))
    if space.height > placed.height and placed.category != "fragile":
        new_spaces.append(Space(space.x, space.y, space.z + placed.height,
                                placed.length, placed.width, space.height - placed.height,
                                placed.item_id, placed.type_id))
    return [s for s in new_spaces if s.length > 0 and s.width > 0 and s.height > 0]



def order_items(items: List[CargoItem], policy: int) -> List[CargoItem]:
    if policy == 0:
        return sorted(items, key=lambda x: (-x.volume, -x.weight, x.type_id, x.item_id))
    if policy == 1:
        return sorted(items, key=lambda x: (x.fragile, -x.weight / x.volume, -x.volume, x.item_id))
    if policy == 2:
        return sorted(items, key=lambda x: (x.category == "oriented", x.fragile, -x.volume, -x.weight, x.item_id))
    return sorted(items, key=lambda x: (-x.weight, -x.volume, x.item_id))



def quick_single_vehicle_pack(truck: Truck, counts: Dict[str, int], truck_id: str, policy: int = 0) -> LayoutState:
    items = order_items(expand_items_for_pattern(counts), policy)
    state = LayoutState(
        spaces=[Space(0, 0, 0, truck.length, truck.width, truck.effective_height, None, None)],
        placed=[],
        remaining=items,
        used_weight=0.0,
        used_volume=0,
    )

    while state.remaining and state.spaces:
        spaces = sort_spaces_dblf(state.spaces[:40])
        placed_map = {p.item_id: p for p in state.placed}
        best_move = None
        best_score = -1e18

        for item_idx, item in enumerate(state.remaining[:10]):
            for space_idx, space in enumerate(spaces[:18]):
                real_space_idx = state.spaces.index(space)
                for ori in item.allowed_orientations:
                    if not can_place(item, ori, space, placed_map, state, truck):
                        continue
                    l, w, h = ori.size
                    fill = (l * w * h) / max(1, space.length * space.width * space.height)
                    tight = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
                    support_bonus = 0.12 if space.z > 0 else 0.03
                    sv, wv, fullness = truck_score(truck, state.used_volume + item.volume, state.used_weight + item.weight)
                    score = fullness + 0.10 * fill + 0.03 * tight + support_bonus + 0.01 * sv + 0.005 * wv
                    if item.fragile and space.z > 0:
                        score -= 0.10
                    if score > best_score:
                        best_score = score
                        best_move = (item_idx, real_space_idx, ori)

        if best_move is None:
            break

        item_idx, space_idx, ori = best_move
        item = state.remaining[item_idx]
        space = state.spaces[space_idx]
        l, w, h = ori.size
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
            support_by=space.support_item_id,
            truck_id=truck_id,
        )
        new_placed = state.placed + [placed]
        if space.support_item_id is not None:
            for p in new_placed:
                if p.item_id == space.support_item_id:
                    p.direct_supported_weight += item.weight
                    break
        new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
        new_spaces.extend(split_space(space, placed))
        new_spaces = merge_spaces(new_spaces)
        state = LayoutState(
            spaces=new_spaces,
            placed=new_placed,
            remaining=state.remaining[:item_idx] + state.remaining[item_idx + 1:],
            used_weight=state.used_weight + item.weight,
            used_volume=state.used_volume + item.volume,
        )
    return state


# ============================================================
# 模式生成
# ============================================================


def compute_upper_bounds(truck: Truck) -> Dict[str, int]:
    bounds: Dict[str, int] = {}
    for t, cargo in CARGO_TYPES.items():
        by_v = truck.effective_volume // cargo.volume
        by_w = int(truck.max_weight // cargo.weight)
        if cargo.fragile:
            best_floor = 0
            for ori in ORIENTATIONS[t]:
                l, w, h = ori.size
                if h <= truck.effective_height:
                    best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
            bounds[t] = min(cargo.quantity, by_v, by_w, best_floor)
        else:
            bounds[t] = min(cargo.quantity, by_v, by_w)
    return bounds



def pattern_seed_vectors(truck: Truck, n_random: int, seed: int) -> List[Dict[str, int]]:
    rng = random.Random(seed)
    ub = compute_upper_bounds(truck)
    seeds: List[Dict[str, int]] = []

    def empty_counts() -> Dict[str, int]:
        return {k: 0 for k in TYPE_ORDER}

    # 1) 单类极限模式
    for t in TYPE_ORDER:
        c = empty_counts()
        c[t] = ub[t]
        seeds.append(c)

    # 2) G3优先模式（易碎件单层优先）
    for ratio in (1.0, 0.85, 0.70, 0.55, 0.40):
        c = empty_counts()
        c["G3"] = max(1, int(ub["G3"] * ratio))
        rem_v = truck.effective_volume - c["G3"] * CARGO_TYPES["G3"].volume
        rem_w = truck.max_weight - c["G3"] * CARGO_TYPES["G3"].weight
        for t in ("G1", "G2"):
            cargo = CARGO_TYPES[t]
            add = min(ub[t], int(rem_v // cargo.volume), int(rem_w // cargo.weight))
            add = max(0, add // 4)
            c[t] += add
            rem_v -= add * cargo.volume
            rem_w -= add * cargo.weight
        seeds.append(c)

    # 3) G4/G5优先模式
    for major in ("G4", "G5"):
        for ratio in (1.0, 0.85, 0.70, 0.55):
            c = empty_counts()
            c[major] = max(1, int(ub[major] * ratio))
            rem_v = truck.effective_volume - c[major] * CARGO_TYPES[major].volume
            rem_w = truck.max_weight - c[major] * CARGO_TYPES[major].weight
            other = "G5" if major == "G4" else "G4"
            cargo = CARGO_TYPES[other]
            add = min(ub[other], int(rem_v // cargo.volume), int(rem_w // cargo.weight))
            add = max(0, add // 6)
            c[other] += add
            rem_v -= add * cargo.volume
            rem_w -= add * cargo.weight
            for t in ("G1", "G2"):
                cargo = CARGO_TYPES[t]
                add = min(ub[t], int(rem_v // cargo.volume), int(rem_w // cargo.weight))
                add = max(0, add // 5)
                c[t] += add
                rem_v -= add * cargo.volume
                rem_w -= add * cargo.weight
            seeds.append(c)

    # 4) 平衡混装模式
    hand_patterns = [
        {"G1": int(0.42 * ub["G1"]), "G2": int(0.35 * ub["G2"]), "G3": int(0.20 * ub["G3"]), "G4": int(0.10 * ub["G4"]), "G5": int(0.18 * ub["G5"])},
        {"G1": int(0.30 * ub["G1"]), "G2": int(0.28 * ub["G2"]), "G3": int(0.55 * ub["G3"]), "G4": int(0.08 * ub["G4"]), "G5": int(0.10 * ub["G5"])},
        {"G1": int(0.22 * ub["G1"]), "G2": int(0.22 * ub["G2"]), "G3": int(0.12 * ub["G3"]), "G4": int(0.45 * ub["G4"]), "G5": int(0.35 * ub["G5"])},
        {"G1": int(0.36 * ub["G1"]), "G2": int(0.30 * ub["G2"]), "G3": int(0.35 * ub["G3"]), "G4": 0, "G5": 0},
        {"G1": int(0.25 * ub["G1"]), "G2": int(0.25 * ub["G2"]), "G3": 0, "G4": int(0.28 * ub["G4"]), "G5": int(0.52 * ub["G5"])},
        {"G1": int(0.18 * ub["G1"]), "G2": int(0.20 * ub["G2"]), "G3": int(0.80 * ub["G3"]), "G4": 0, "G5": 0},
    ]
    for c in hand_patterns:
        seeds.append({k: max(0, min(ub[k], c.get(k, 0))) for k in TYPE_ORDER})

    # 5) 随机模式种子
    weights_bank = [
        (1.0, 1.0, 1.0, 1.0, 1.0),
        (1.2, 1.2, 0.4, 0.8, 1.0),
        (0.6, 0.7, 2.1, 0.3, 0.3),
        (0.8, 0.8, 0.5, 1.8, 1.5),
        (0.9, 1.0, 1.6, 0.8, 0.7),
    ]
    for _ in range(n_random):
        w = list(rng.choice(weights_bank))
        w = [x * rng.uniform(0.65, 1.45) for x in w]
        total_w = sum(w)
        counts = empty_counts()
        used_v = 0
        used_w = 0.0
        for idx, t in enumerate(TYPE_ORDER):
            cargo = CARGO_TYPES[t]
            target_share = w[idx] / total_w
            rough = int(target_share * (truck.effective_volume / cargo.volume) * rng.uniform(0.22, 0.82))
            rough = min(rough, ub[t])
            while rough > 0 and (used_v + rough * cargo.volume > truck.effective_volume or used_w + rough * cargo.weight > truck.max_weight):
                rough -= 1
            counts[t] = rough
            used_v += rough * cargo.volume
            used_w += rough * cargo.weight
        seeds.append(counts)

    # 合法化：控制重量/体积，并做去重
    cleaned: List[Dict[str, int]] = []
    seen = set()
    for c in seeds:
        cc = c.copy()
        while True:
            vol = sum(cc[t] * CARGO_TYPES[t].volume for t in TYPE_ORDER)
            wt = sum(cc[t] * CARGO_TYPES[t].weight for t in TYPE_ORDER)
            if vol <= truck.effective_volume and wt <= truck.max_weight:
                break
            for t in ("G4", "G5", "G3", "G1", "G2"):
                if cc[t] > 0:
                    cc[t] -= 1
                    break
        key = tuple(cc[t] for t in TYPE_ORDER)
        if sum(key) > 0 and key not in seen:
            seen.add(key)
            cleaned.append(cc)
    return cleaned


def generate_patterns(truck: Truck, n_random: int = 60, seed: int = 2026) -> List[Pattern]:
    seeds = pattern_seed_vectors(truck, n_random=n_random, seed=seed)
    raw_patterns: Dict[Tuple[int, int, int, int, int], Pattern] = {}
    pid = 1
    for counts in seeds:
        for policy in range(4):
            state = quick_single_vehicle_pack(truck, counts, truck_id="PATTERN", policy=policy)
            actual = Counter(p.type_id for p in state.placed)
            tup = tuple(actual.get(t, 0) for t in TYPE_ORDER)
            if sum(tup) == 0:
                continue
            sv, wv, fullness = truck_score(truck, state.used_volume, state.used_weight)
            p = Pattern(pid, tup, state.used_volume, state.used_weight, sv, wv, fullness)
            old = raw_patterns.get(tup)
            if old is None or (p.fullness, p.used_volume, p.used_weight) > (old.fullness, old.used_volume, old.used_weight):
                raw_patterns[tup] = p
                pid += 1

    pats = list(raw_patterns.values())
    # 去除支配模式
    kept: List[Pattern] = []
    for p in sorted(pats, key=lambda x: (x.fullness, x.used_volume, x.used_weight), reverse=True):
        dominated = False
        for q in kept:
            if all(q.counts[i] >= p.counts[i] for i in range(5)) and (q.counts != p.counts):
                dominated = True
                break
        if not dominated:
            kept.append(p)
    # 按质量排序，保留前若干个
    kept.sort(key=lambda x: (sum(x.counts), x.fullness, x.used_volume, x.used_weight), reverse=True)
    return kept[:80]


# ============================================================
# 模式主问题：最少车辆搜索（DFS + 剪枝）
# ============================================================


def demand_vector() -> Tuple[int, int, int, int, int]:
    return tuple(CARGO_TYPES[t].quantity for t in TYPE_ORDER)



def lower_bound_vehicle_count(truck: Truck) -> int:
    total_v = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_w = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    return max(math.ceil(total_v / truck.effective_volume), math.ceil(total_w / truck.max_weight))



def ceil_div(a: int, b: int) -> int:
    return 0 if a <= 0 else (a + b - 1) // b



def patterns_coverage_upper(patterns: List[Pattern], rem: Tuple[int, int, int, int, int], start_idx: int) -> int:
    # 一个简单的下界：按每类剩余量 / 单车该类最大覆盖量 取最大值
    lb = 0
    for j in range(5):
        mx = max((p.counts[j] for p in patterns[start_idx:]), default=0)
        if rem[j] > 0:
            if mx == 0:
                return 10**9
            lb = max(lb, ceil_div(rem[j], mx))
    return lb



def subtract_pattern(rem: Tuple[int, int, int, int, int], pat: Pattern, times: int = 1) -> Tuple[int, int, int, int, int]:
    return tuple(max(0, rem[i] - times * pat.counts[i]) for i in range(5))



def pattern_coverage_stats(patterns: List[Pattern]) -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    for idx, t in enumerate(TYPE_ORDER):
        mx = max((p.counts[idx] for p in patterns), default=0)
        freq = sum(1 for p in patterns if p.counts[idx] > 0)
        stats[t] = {"max_single_pattern": mx, "pattern_count": freq}
    return stats


def solve_master_min_vehicle(patterns: List[Pattern], truck: Truck, time_node_cap: int = 300000) -> Tuple[int, Dict[int, int]]:
    demand = demand_vector()
    lb = lower_bound_vehicle_count(truck)
    patterns = sorted(patterns, key=lambda p: (sum(p.counts), p.fullness, p.used_volume, p.used_weight), reverse=True)

    stats = pattern_coverage_stats(patterns)
    for j, t in enumerate(TYPE_ORDER):
        if demand[j] > 0 and stats[t]["max_single_pattern"] == 0:
            raise RuntimeError(f"模式集中不存在可覆盖货类 {t} 的模式，请增大模式数或补充种子模式。")

    # 先用贪心构造一个可行上界（若能构造出来）
    rem = list(demand)
    greedy_sol: Dict[int, int] = {}
    used = 0
    while any(x > 0 for x in rem):
        best = None
        best_gain = -1
        for p in patterns:
            gain = sum(min(rem[i], p.counts[i]) for i in range(5))
            if gain > best_gain:
                best_gain = gain
                best = p
        if best is None or best_gain <= 0:
            break
        greedy_sol[best.pattern_id] = greedy_sol.get(best.pattern_id, 0) + 1
        rem = [max(0, rem[i] - best.counts[i]) for i in range(5)]
        used += 1
        if used > lb + 400:
            break

    best_k = used if all(x == 0 for x in rem) else lb + 200
    best_sol: Dict[int, int] = greedy_sol.copy() if best_k < lb + 200 else {}
    nodes = 0

    def dfs(idx: int, rem: Tuple[int, int, int, int, int], used: int, chosen: Dict[int, int]) -> None:
        nonlocal best_k, best_sol, nodes
        nodes += 1
        if nodes > time_node_cap:
            return
        if all(x == 0 for x in rem):
            if used < best_k:
                best_k = used
                best_sol = chosen.copy()
            return
        if idx >= len(patterns):
            return
        if used >= best_k:
            return
        optimistic = patterns_coverage_upper(patterns, rem, idx)
        if used + optimistic >= best_k:
            return

        p = patterns[idx]
        max_use = 0
        for i in range(5):
            if p.counts[i] > 0 and rem[i] > 0:
                max_use = max(max_use, ceil_div(rem[i], p.counts[i]))
        max_use = min(max_use, best_k - used - 1)

        for t in range(max_use, -1, -1):
            new_used = used + t
            if new_used >= best_k:
                continue
            new_rem = subtract_pattern(rem, p, t) if t > 0 else rem
            if t > 0:
                chosen[p.pattern_id] = t
            else:
                chosen.pop(p.pattern_id, None)
            dfs(idx + 1, new_rem, new_used, chosen)
        chosen.pop(p.pattern_id, None)

    dfs(0, demand, 0, {})
    if not best_sol:
        raise RuntimeError("模式主问题未找到可行解。可以尝试增大模式数。")
    return best_k, best_sol


# ============================================================
# 解还原：把选中的模式展开成每辆车逐件装箱方案
# ============================================================


def pattern_counts_to_dict(pattern: Pattern) -> Dict[str, int]:
    return {TYPE_ORDER[i]: pattern.counts[i] for i in range(5)}



def expand_solution_patterns(patterns: List[Pattern], solution: Dict[int, int]) -> List[Pattern]:
    id_map = {p.pattern_id: p for p in patterns}
    used_patterns: List[Pattern] = []
    for pid, num in solution.items():
        used_patterns.extend([id_map[pid]] * num)
    return used_patterns



def assign_global_item_ids(used_patterns: List[Pattern]) -> List[Dict[str, List[str]]]:
    next_id = {t: 1 for t in TYPE_ORDER}
    assignments: List[Dict[str, List[str]]] = []
    for pat in used_patterns:
        pool: Dict[str, List[str]] = {t: [] for t in TYPE_ORDER}
        for i, t in enumerate(TYPE_ORDER):
            cnt = pat.counts[i]
            for _ in range(cnt):
                pool[t].append(f"{t}_{next_id[t]:04d}")
                next_id[t] += 1
        assignments.append(pool)
    return assignments



def rebuild_with_global_ids(truck: Truck, counts: Dict[str, int], truck_id: str, global_pool: Dict[str, List[str]]) -> LayoutState:
    # 先用模式装箱器得到局部放置，再把 item_id 替换成全局编号
    best_state = None
    best_key = None
    for policy in range(4):
        st = quick_single_vehicle_pack(truck, counts, truck_id=truck_id, policy=policy)
        key = (st.used_volume, st.used_weight, len(st.placed))
        if best_state is None or key > best_key:
            best_state = st
            best_key = key
    assert best_state is not None

    local_counter = defaultdict(int)
    new_placed: List[PlacedCargo] = []
    id_map: Dict[str, str] = {}
    for p in best_state.placed:
        t = p.type_id
        local_counter[t] += 1
        gid = global_pool[t][local_counter[t] - 1]
        id_map[p.item_id] = gid
        new_placed.append(PlacedCargo(
            item_id=gid,
            type_id=p.type_id,
            category=p.category,
            x=p.x, y=p.y, z=p.z,
            length=p.length, width=p.width, height=p.height,
            weight=p.weight,
            orientation_id=p.orientation_id,
            rotation=p.rotation,
            support_by=None if p.support_by is None else id_map.get(p.support_by, p.support_by),
            truck_id=truck_id,
            direct_supported_weight=p.direct_supported_weight,
        ))
    return LayoutState(best_state.spaces, new_placed, best_state.remaining, best_state.used_weight, best_state.used_volume)


# ============================================================
# 输出
# ============================================================


def write_vehicle_summary_csv(path: str, rows: List[Dict[str, object]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "truck_id", "space_utilization", "weight_utilization", "fullness_score",
            "loaded_weight_kg", "loaded_volume_cm3", "actual_counts"
        ])
        for r in rows:
            writer.writerow([
                r["truck_id"], r["space_utilization"], r["weight_utilization"], r["fullness_score"],
                r["loaded_weight_kg"], r["loaded_volume_cm3"], r["actual_counts"]
            ])



def write_items_csv(path: str, placed: Sequence[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "type_id", "category", "truck_id", "x", "y", "z",
            "length", "width", "height", "weight", "orientation_id", "rotation", "support_by"
        ])
        for p in placed:
            writer.writerow([
                p.item_id, p.type_id, p.category, p.truck_id, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight, p.orientation_id, p.rotation,
                p.support_by or ""
            ])


# ============================================================
# 总流程
# ============================================================


def solve_problem_12_for_truck(truck: Truck, pattern_random: int, pattern_seed: int, outdir: str) -> Dict[str, object]:
    lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb}", flush=True)

    patterns: List[Pattern] = []
    best_k: Optional[int] = None
    sol: Dict[int, int] = {}

    retry_randoms = [pattern_random, max(pattern_random + 80, int(pattern_random * 1.8)), max(pattern_random + 180, int(pattern_random * 3.0))]
    retry_randoms = list(dict.fromkeys(retry_randoms))
    last_error = None

    for ridx, pr in enumerate(retry_randoms, start=1):
        print(f"[{truck.name}] 第 {ridx}/{len(retry_randoms)} 轮生成单车装载模式，随机种子模式数 = {pr} ...", flush=True)
        patterns = generate_patterns(truck, n_random=pr, seed=pattern_seed + ridx - 1)
        print(f"[{truck.name}] 生成模式数: {len(patterns)}", flush=True)
        if not patterns:
            last_error = RuntimeError("未生成任何有效模式。")
            continue

        stats = pattern_coverage_stats(patterns)
        print(f"[{truck.name}] 模式覆盖检查: {stats}", flush=True)

        try:
            best_k, sol = solve_master_min_vehicle(patterns, truck)
            print(f"[{truck.name}] 模式主问题求得车辆数 = {best_k}", flush=True)
            break
        except RuntimeError as e:
            last_error = e
            print(f"[{truck.name}] 当前模式库无可行解：{e}", flush=True)

    if best_k is None:
        raise RuntimeError(f"模式主问题未找到可行解，自动扩充模式库后仍失败。最后一次错误：{last_error}")

    used_patterns = expand_solution_patterns(patterns, sol)
    global_pools = assign_global_item_ids(used_patterns)

    vehicle_rows: List[Dict[str, object]] = []
    subdir = os.path.join(outdir, truck.name)
    os.makedirs(subdir, exist_ok=True)

    total_counts = Counter()
    for idx, pat in enumerate(used_patterns, start=1):
        counts = pattern_counts_to_dict(pat)
        truck_id = f"{truck.name}_{idx:03d}"
        state = rebuild_with_global_ids(truck, counts, truck_id, global_pools[idx - 1])
        actual_counts = dict(Counter(p.type_id for p in state.placed))
        total_counts.update(actual_counts)
        sv, wv, fullness = truck_score(truck, state.used_volume, state.used_weight)
        row = {
            "truck_id": truck_id,
            "space_utilization": round(sv, 6),
            "weight_utilization": round(wv, 6),
            "fullness_score": round(fullness, 6),
            "loaded_weight_kg": round(state.used_weight, 3),
            "loaded_volume_cm3": state.used_volume,
            "actual_counts": actual_counts,
        }
        vehicle_rows.append(row)
        write_items_csv(os.path.join(subdir, f"{truck_id}_装箱明细.csv"), state.placed)

    demand = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER}
    over_cover = {t: total_counts[t] - demand[t] for t in TYPE_ORDER}

    write_vehicle_summary_csv(os.path.join(subdir, f"{truck.name}_车辆汇总.csv"), vehicle_rows)

    avg_sv = sum(r["space_utilization"] for r in vehicle_rows) / max(1, len(vehicle_rows))
    avg_wv = sum(r["weight_utilization"] for r in vehicle_rows) / max(1, len(vehicle_rows))

    summary = {
        "truck": truck.name,
        "vehicle_count": best_k,
        "lower_bound": lb,
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "total_cost": round(best_k * truck.cost, 2),
        "generated_patterns": len(patterns),
        "over_cover": over_cover,
        "output_dir": subdir,
    }
    return summary


# ============================================================
# CLI
# ============================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2：模式生成 + 最少车辆枚举")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all", help="选择车型")
    parser.add_argument("--pattern-random", type=int, default=120, help="随机模式种子数")
    parser.add_argument("--seed", type=int, default=2026, help="随机种子")
    parser.add_argument("--outdir", type=str, default="output_p12_pattern", help="输出目录")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for tname in truck_list:
        print("\n" + "=" * 56)
        print(f"开始求解问题1.2：{tname}")
        print("=" * 56)
        summary = solve_problem_12_for_truck(TRUCKS[tname], pattern_random=args.pattern_random, pattern_seed=args.seed, outdir=args.outdir)
        print(summary)


if __name__ == "__main__":
    main()
