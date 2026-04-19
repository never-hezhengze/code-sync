#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.1 单车满载率最大化（增强版）

算法结构：
1. 计数优化：不展开全部附件数量，只在 G1~G5 的数量空间中搜索候选组合；
2. 精细布局验证：对候选组合做 beam-search + DBLF + 三空间分割验证，并输出逐件坐标与姿态。

特点：
- 只针对问题1.1；
- 支持车型1/车型2；
- 兼容标准件 / 易碎件 / 定向件；
- 输出每件货物坐标、姿态、支撑来源；
- 默认写入当前目录 output/ 下的 csv。

说明：
- 这是高质量近似算法，不是严格全局最优精确算法；
- 承压和支撑采用工程化近似：要求上层货物完整落在单个支撑面上，
  并按直接支撑累计载荷近似检查 500 kg/m^2。
"""
import argparse
import csv
import math
import os
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from mathorcup_d_common import (
    Orientation,
    CargoType,
    Truck,
    CARGO_TYPES,
    TRUCKS,
    generate_orientations,
    truck_score,
)



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


# =========================
# 基础数据
# =========================



TYPE_ORDER = ["G1", "G2", "G3", "G4", "G5"]




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
                    item_id=f"{type_id}_{i:03d}",
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


# =========================
# 工具函数
# =========================



def count_score(truck: Truck, counts: Dict[str, int]) -> float:
    total_volume = sum(CARGO_TYPES[k].volume * v for k, v in counts.items())
    total_weight = sum(CARGO_TYPES[k].weight * v for k, v in counts.items())
    space_util, weight_util, fullness = truck_score(truck, total_volume, total_weight)
    if total_volume == 0:
        return -1e18

    avg_density = total_weight / total_volume
    densest = max(c.density for c in CARGO_TYPES.values())
    density_score = avg_density / densest

    vol_share = []
    for k in TYPE_ORDER:
        v = counts.get(k, 0) * CARGO_TYPES[k].volume
        if v > 0:
            vol_share.append(v / total_volume)
    concentration = sum(p * p for p in vol_share) if vol_share else 1.0

    return (
        0.72 * space_util
        + 0.28 * weight_util
        + 0.08 * density_score
        - 0.03 * concentration
    )



def sort_spaces_dblf(spaces: Sequence[Space]) -> List[Space]:
    # 采用低 z、低 y、低 x 优先的底-后-左放置顺序。
    return sorted(spaces, key=lambda s: (s.z, s.y, s.x, s.volume))



def remove_contained_spaces(spaces: List[Space]) -> List[Space]:
    result: List[Space] = []
    for i, a in enumerate(spaces):
        contained = False
        for j, b in enumerate(spaces):
            if i == j:
                continue
            if (
                a.x >= b.x
                and a.y >= b.y
                and a.z >= b.z
                and a.x + a.length <= b.x + b.length
                and a.y + a.width <= b.y + b.width
                and a.z + a.height <= b.z + b.height
                and (a.x, a.y, a.z, a.length, a.width, a.height) != (b.x, b.y, b.z, b.length, b.width, b.height)
            ):
                contained = True
                break
        if not contained and a.length > 0 and a.width > 0 and a.height > 0:
            result.append(a)
    return result



def try_merge_two_spaces(a: Space, b: Space) -> Optional[Space]:
    support_same = (
        a.support_item_id == b.support_item_id
        and a.support_type_id == b.support_type_id
        and a.support_length == b.support_length
        and a.support_width == b.support_width
    )
    if not support_same:
        return None

    # x向合并
    if a.y == b.y and a.z == b.z and a.width == b.width and a.height == b.height:
        if a.x + a.length == b.x:
            return Space(a.x, a.y, a.z, a.length + b.length, a.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.x + b.length == a.x:
            return Space(b.x, b.y, b.z, a.length + b.length, a.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
    # y向合并
    if a.x == b.x and a.z == b.z and a.length == b.length and a.height == b.height:
        if a.y + a.width == b.y:
            return Space(a.x, a.y, a.z, a.length, a.width + b.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
        if b.y + b.width == a.y:
            return Space(b.x, b.y, b.z, a.length, a.width + b.width, a.height,
                         a.support_item_id, a.support_type_id, a.support_length, a.support_width)
    # z向合并（仅相同支撑下）
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


# =========================
# 粗几何上界与计数组合生成
# =========================


def best_grid_count(truck: Truck, cargo: CargoType) -> int:
    """单一货类规则堆码的粗几何上界。"""
    best = 0
    for ori in generate_orientations(cargo):
        l, w, h = ori.size
        nx = truck.length // l
        ny = truck.width // w
        if cargo.fragile:
            nz = 1 if h <= truck.effective_height else 0
        else:
            nz = truck.effective_height // h
        best = max(best, nx * ny * nz)
    return best



def compute_upper_bounds(truck: Truck) -> Dict[str, int]:
    bounds: Dict[str, int] = {}
    floor_area = truck.length * truck.width
    for type_id, cargo in CARGO_TYPES.items():
        by_volume = truck.effective_volume // cargo.volume
        by_weight = int(truck.max_weight // cargo.weight)
        by_grid = best_grid_count(truck, cargo)
        ub = min(cargo.quantity, by_volume, by_weight, by_grid)
        if cargo.fragile:
            # 易碎件单层，附加地板面积限制。
            best_floor = 0
            for ori in generate_orientations(cargo):
                l, w, h = ori.size
                if h <= truck.effective_height:
                    best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
            ub = min(ub, best_floor)
        bounds[type_id] = max(0, ub)
    return bounds



def rough_geometry_penalty(truck: Truck, counts: Dict[str, int]) -> float:
    """对明显不利的底面积和单层易碎件使用情况给出粗罚分。"""
    floor_area = truck.length * truck.width
    fragile_floor_need = counts.get("G3", 0) * min(a * b for a, b, _ in [ori.size for ori in generate_orientations(CARGO_TYPES["G3"])])
    fragile_penalty = max(0.0, fragile_floor_need / floor_area - 1.0)

    bulky = counts.get("G4", 0) + counts.get("G5", 0)
    bulky_penalty = 0.0
    if bulky > 0:
        # 大件比例太高时给一点惩罚，避免上层碎空间太多。
        bulky_penalty = max(0.0, bulky / 220.0 - 1.0)
    return 0.08 * fragile_penalty + 0.04 * bulky_penalty



def generate_count_candidates(
    truck: Truck,
    upper_bounds: Dict[str, int],
    trials: int = 1200,
    keep: int = 80,
    seed: int = 2026,
) -> List[Dict[str, int]]:
    rng = random.Random(seed)
    seen = set()
    pool: List[Tuple[float, Dict[str, int]]] = []
    densest = sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].density, reverse=True)

    for trial in range(trials):
        counts = {t: 0 for t in TYPE_ORDER}
        used_weight = 0.0
        used_volume = 0
        attempts = 0
        while attempts < 5000:
            feasible: List[Tuple[float, str]] = []
            for t in TYPE_ORDER:
                if counts[t] >= upper_bounds[t]:
                    continue
                c = CARGO_TYPES[t]
                if used_weight + c.weight > truck.max_weight:
                    continue
                if used_volume + c.volume > truck.effective_volume:
                    continue
                new_counts = counts.copy()
                new_counts[t] += 1
                score = count_score(truck, new_counts) - rough_geometry_penalty(truck, new_counts)
                # 少量随机扰动，增强多样性。
                score += rng.uniform(-0.01, 0.01)
                feasible.append((score, t))
            if not feasible:
                break

            feasible.sort(reverse=True)
            rcl_size = 2 + (trial % 4)
            chosen = rng.choice(feasible[: min(rcl_size, len(feasible))])[1]
            counts[chosen] += 1
            used_weight += CARGO_TYPES[chosen].weight
            used_volume += CARGO_TYPES[chosen].volume
            attempts += 1

            # 偶尔偏向高密度货物，防止全塞轻货。
            if rng.random() < 0.10:
                t = rng.choice(densest[:3])
                c = CARGO_TYPES[t]
                if (
                    counts[t] < upper_bounds[t]
                    and used_weight + c.weight <= truck.max_weight
                    and used_volume + c.volume <= truck.effective_volume
                ):
                    counts[t] += 1
                    used_weight += c.weight
                    used_volume += c.volume

        # 邻域微调：增1、减1、换1
        best_counts = counts.copy()
        best_score = count_score(truck, best_counts) - rough_geometry_penalty(truck, best_counts)
        for _ in range(80):
            cand = best_counts.copy()
            move = rng.choice(["add", "remove", "swap"])
            if move == "add":
                t = rng.choice(TYPE_ORDER)
                c = CARGO_TYPES[t]
                if (
                    cand[t] < upper_bounds[t]
                    and sum(CARGO_TYPES[k].weight * cand[k] for k in TYPE_ORDER) + c.weight <= truck.max_weight
                    and sum(CARGO_TYPES[k].volume * cand[k] for k in TYPE_ORDER) + c.volume <= truck.effective_volume
                ):
                    cand[t] += 1
            elif move == "remove":
                nz = [t for t in TYPE_ORDER if cand[t] > 0]
                if nz:
                    cand[rng.choice(nz)] -= 1
            else:
                srcs = [t for t in TYPE_ORDER if cand[t] > 0]
                if srcs:
                    src = rng.choice(srcs)
                    dst = rng.choice(TYPE_ORDER)
                    if src != dst and cand[dst] < upper_bounds[dst]:
                        cand[src] -= 1
                        after_w = sum(CARGO_TYPES[k].weight * cand[k] for k in TYPE_ORDER) + CARGO_TYPES[dst].weight
                        after_v = sum(CARGO_TYPES[k].volume * cand[k] for k in TYPE_ORDER) + CARGO_TYPES[dst].volume
                        if after_w <= truck.max_weight and after_v <= truck.effective_volume:
                            cand[dst] += 1
                        else:
                            cand[src] += 1

            s = count_score(truck, cand) - rough_geometry_penalty(truck, cand)
            if s > best_score:
                best_score, best_counts = s, cand

        key = tuple(best_counts[t] for t in TYPE_ORDER)
        if key not in seen and sum(best_counts.values()) > 0:
            seen.add(key)
            pool.append((best_score, best_counts))

    pool.sort(key=lambda x: x[0], reverse=True)
    return [counts for _, counts in pool[:keep]]


# =========================
# 布局验证：beam search + DBLF + 三空间分割
# =========================


def build_item_orders(items: List[CargoItem], policy: int) -> List[CargoItem]:
    def ori_height(item: CargoItem) -> int:
        return max(o.size[2] for o in item.allowed_orientations)

    def base_area(item: CargoItem) -> int:
        return max(o.size[0] * o.size[1] for o in item.allowed_orientations)

    if policy == 0:
        return sorted(items, key=lambda it: (-it.volume, -it.weight, it.type_id, it.item_id))
    if policy == 1:
        return sorted(items, key=lambda it: (it.fragile, -it.weight / it.volume, -it.volume, it.item_id))
    if policy == 2:
        return sorted(items, key=lambda it: (-base_area(it), -ori_height(it), -it.volume, it.item_id))
    if policy == 3:
        return sorted(items, key=lambda it: (it.category == "oriented", it.fragile, -it.volume, -it.weight, it.item_id))
    return sorted(items, key=lambda it: (-it.weight, -it.volume, it.item_id))



def can_place_in_space(
    item: CargoItem,
    ori: Orientation,
    space: Space,
    placed_map: Dict[str, PlacedCargo],
) -> bool:
    l, w, h = ori.size
    if l > space.length or w > space.width or h > space.height:
        return False

    # 易碎件只能放在地板或标准件顶面。
    if item.fragile and space.z > 0:
        if space.support_type_id != "G1" and space.support_type_id != "G2":
            return False

    # 非地板上的放置要求完整落在单个支撑面上。
    if space.z > 0:
        if space.support_item_id is None:
            return False
        support = placed_map.get(space.support_item_id)
        if support is None:
            return False
        if l > support.length or w > support.width:
            return False
        # 下层易碎件不可作为支撑物
        if support.category == "fragile":
            return False
        # 直接承压近似检查
        projected_pressure = (support.direct_supported_weight + item.weight) / max(1e-9, support.top_area_m2)
        if projected_pressure > CARGO_TYPES[support.type_id].max_support_pressure + 1e-9:
            return False
    return True



def placement_gain(truck: Truck, state: LayoutState, item: CargoItem, ori: Orientation, space: Space) -> float:
    l, w, h = ori.size
    fill_ratio = (l * w * h) / max(1, space.length * space.width * space.height)
    low_z_bonus = 1.0 / (1.0 + space.z)
    tight_bonus = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
    support_bonus = 0.10 if space.z > 0 else 0.0
    dense_bonus = 0.03 * (item.weight / item.volume) / max(c.density for c in CARGO_TYPES.values())

    used_volume = state.used_volume + item.volume
    used_weight = state.used_weight + item.weight
    space_util, weight_util, fullness = truck_score(truck, used_volume, used_weight)
    return fullness + 0.10 * fill_ratio + 0.03 * low_z_bonus + 0.02 * tight_bonus + support_bonus + dense_bonus + 0.02 * space_util + 0.01 * weight_util



def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []
    # 右侧空间
    if space.length > placed.length:
        new_spaces.append(
            Space(
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
            )
        )
    # 前方空间
    if space.width > placed.width:
        new_spaces.append(
            Space(
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
            )
        )
    # 上方空间：易碎件上方不生成空间
    if space.height > placed.height and placed.category != "fragile":
        new_spaces.append(
            Space(
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
            )
        )
    return new_spaces



def apply_placement(
    truck: Truck,
    state: LayoutState,
    item_idx: int,
    ori: Orientation,
    space_idx: int,
) -> LayoutState:
    item = state.remaining[item_idx]
    space = state.spaces[space_idx]
    support_by = space.support_item_id
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
        support_by=support_by,
        truck_id=truck.name,
    )

    new_placed = [p for p in state.placed]
    new_placed.append(placed)

    # 更新直接支撑载荷
    if support_by is not None:
        for p in new_placed:
            if p.item_id == support_by:
                p.direct_supported_weight += item.weight
                break

    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))
    new_spaces = merge_spaces(new_spaces)
    new_spaces = sort_spaces_dblf(new_spaces)

    new_remaining = state.remaining[:item_idx] + state.remaining[item_idx + 1 :]
    used_weight = state.used_weight + item.weight
    used_volume = state.used_volume + item.volume
    space_util, weight_util, fullness = truck_score(truck, used_volume, used_weight)
    packed_ratio = len(new_placed) / max(1, len(new_placed) + len(new_remaining))

    return LayoutState(
        spaces=new_spaces,
        placed=new_placed,
        remaining=new_remaining,
        used_weight=used_weight,
        used_volume=used_volume,
        score=fullness + 0.02 * packed_ratio + 0.01 * space_util + 0.005 * weight_util,
        packed_ratio=packed_ratio,
    )



def pack_with_beam_search(
    truck: Truck,
    items: List[CargoItem],
    beam_width: int = 8,
    candidate_items_each_step: int = 6,
    candidate_moves_each_state: int = 10,
    policy: int = 0,
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

    beam: List[LayoutState] = [init]
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
            item_candidates = state.remaining[: min(candidate_items_each_step, len(state.remaining))]
            move_pool: List[Tuple[float, int, Orientation, int]] = []

            for item_idx, item in enumerate(item_candidates):
                for space_idx, space in enumerate(state.spaces[: min(18, len(state.spaces))]):
                    for ori in item.allowed_orientations:
                        if can_place_in_space(item, ori, space, placed_map):
                            gain = placement_gain(truck, state, item, ori, space)
                            move_pool.append((gain, item_idx, ori, space_idx))

            move_pool.sort(key=lambda x: x[0], reverse=True)
            move_pool = move_pool[:candidate_moves_each_state]

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
        if beam and (beam[0].score > best.score or beam[0].used_volume > best.used_volume):
            best = beam[0]

    return best


# =========================
# 总流程
# =========================


def evaluate_candidate(
    truck: Truck,
    counts: Dict[str, int],
    beam_width: int,
) -> Tuple[LayoutState, Dict[str, object]]:
    items = expand_items(counts)
    best_state: Optional[LayoutState] = None
    best_meta: Dict[str, object] = {}

    for policy in range(5):
        state = pack_with_beam_search(
            truck=truck,
            items=items,
            beam_width=beam_width,
            candidate_items_each_step=6,
            candidate_moves_each_state=12,
            policy=policy,
        )
        if best_state is None or state.used_volume > best_state.used_volume or (
            state.used_volume == best_state.used_volume and state.used_weight > best_state.used_weight
        ):
            best_state = state
            best_meta = {"policy_index": policy}

    assert best_state is not None
    actual_counts = Counter(p.type_id for p in best_state.placed)
    target_counts = {k: v for k, v in counts.items() if v > 0}
    feasible_full_pack = sum(actual_counts.values()) == sum(target_counts.values())
    space_util, weight_util, fullness = truck_score(truck, best_state.used_volume, best_state.used_weight)
    packed_ratio = sum(actual_counts.values()) / max(1, sum(target_counts.values()))

    meta = {
        "truck": truck.name,
        "space_utilization": round(space_util, 6),
        "weight_utilization": round(weight_util, 6),
        "fullness_score": round(fullness, 6),
        "loaded_weight_kg": round(best_state.used_weight, 3),
        "loaded_volume_cm3": int(best_state.used_volume),
        "target_counts": target_counts,
        "actual_counts": dict(actual_counts),
        "placed_item_count": len(best_state.placed),
        "feasible_full_pack": feasible_full_pack,
        "packed_ratio": round(packed_ratio, 6),
        **best_meta,
    }
    return best_state, meta



def solve_problem_11(
    truck: Truck,
    topk: int,
    beam_width: int,
    trials: int,
    seed: int,
) -> Tuple[LayoutState, Dict[str, object], Dict[str, int]]:
    upper_bounds = compute_upper_bounds(truck)
    candidates = generate_count_candidates(truck, upper_bounds, trials=trials, keep=max(topk * 4, 40), seed=seed)

    best_state: Optional[LayoutState] = None
    best_meta: Dict[str, object] = {}
    best_counts: Dict[str, int] = {}

    for idx, counts in enumerate(candidates[:topk]):
        state, meta = evaluate_candidate(truck, counts, beam_width=beam_width)
        meta["candidate_index"] = idx
        if best_state is None:
            best_state, best_meta, best_counts = state, meta, counts
            continue

        old = (best_state.used_volume, best_state.used_weight, best_meta.get("packed_ratio", 0.0))
        new = (state.used_volume, state.used_weight, meta.get("packed_ratio", 0.0))
        if new > old:
            best_state, best_meta, best_counts = state, meta, counts

    assert best_state is not None
    return best_state, best_meta, upper_bounds


# =========================
# 输出
# =========================


def write_items_csv(path: str, placed: Sequence[PlacedCargo]) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item_id", "type_id", "category",
            "x", "y", "z",
            "length", "width", "height",
            "weight", "orientation_id", "rotation",
            "support_by", "truck_id"
        ])
        for p in placed:
            writer.writerow([
                p.item_id, p.type_id, p.category,
                p.x, p.y, p.z,
                p.length, p.width, p.height,
                p.weight, p.orientation_id, p.rotation,
                p.support_by or "", p.truck_id or ""
            ])


# =========================
# 命令行入口
# =========================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.1 单车满载率最大化（增强版）")

    parser.add_argument("--truck", type=str, default="all",
                        choices=["车型1", "车型2", "all"],
                        help="选择车型")

    parser.add_argument("--topk", type=int, default=18)
    parser.add_argument("--beam-width", type=int, default=8)
    parser.add_argument("--trials", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=2026)

    parser.add_argument("--outdir", type=str, default="../结果展示/output1.1(对照）")

    return parser.parse_args()


def main():
    args = parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.normpath(os.path.join(base_dir, args.outdir))

    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for truck_name in truck_list:
        print("\n==============================")
        print(f"开始求解：{truck_name}")
        print("==============================")

        truck = TRUCKS[truck_name]

        state, meta, upper_bounds = solve_problem_11(
            truck=truck,
            topk=args.topk,
            beam_width=args.beam_width,
            trials=args.trials,
            seed=args.seed,
        )

        print(f"[{truck.name}] 单车上界: {upper_bounds}")
        print(meta)

        out_csv = os.path.join(
            outdir,
            f"{truck.name}_问题1_1_增强版装箱明细.csv"
        )

        write_items_csv(out_csv, state.placed)
        print(f"装箱明细已写入: {out_csv}")

if __name__ == "__main__":
    main()
