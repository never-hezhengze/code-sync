#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二 最终版
混合车型 + 贪心初始化 + 局部搜索

算法结构：
1. 将全部货物展开为逐件货物；
2. 外层使用贪心逐件插入，决定：
   - 每件货分配到哪辆车
   - 每辆车使用车型1还是车型2
3. 内层对每辆车调用 beam-search + DBLF + 三空间分割做单车可行装箱；
4. 局部搜索改进：
   - 删车重构
   - 单件搬移
   - 车型切换

支持目标：
- min_trucks : 问题2.1 车辆总数最少
- min_cost   : 问题2.2 总运输成本最低

说明：
- 这是工程化高质量启发式，不是严格精确全局最优；
- 内层装箱逻辑沿用问题1.1风格；
- 支撑/承压仍采用工程近似。
"""

from __future__ import annotations

import argparse
import csv
import os
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# =========================
# 数据结构
# =========================

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

    @property
    def capacity_density(self) -> float:
        return self.max_weight / self.effective_volume


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
class TruckLoad:
    truck_id: str
    truck: Truck
    assigned_items: List[CargoItem] = field(default_factory=list)
    layout: Optional[LayoutState] = None
    feasible: bool = False

    @property
    def used_weight(self) -> float:
        return 0.0 if self.layout is None else self.layout.used_weight

    @property
    def used_volume(self) -> int:
        return 0 if self.layout is None else self.layout.used_volume

    @property
    def item_count(self) -> int:
        return len(self.assigned_items)

    @property
    def space_utilization(self) -> float:
        return self.used_volume / self.truck.effective_volume if self.truck.effective_volume > 0 else 0.0

    @property
    def weight_utilization(self) -> float:
        return self.used_weight / self.truck.max_weight if self.truck.max_weight > 0 else 0.0


@dataclass
class FleetSolution:
    trucks: List[TruckLoad] = field(default_factory=list)
    objective: str = "min_trucks"
    objective_value: float = float("inf")

    def clone(self) -> "FleetSolution":
        new_trucks: List[TruckLoad] = []
        for tl in self.trucks:
            copied_layout = None
            if tl.layout is not None:
                copied_layout = LayoutState(
                    spaces=[
                        Space(
                            s.x, s.y, s.z, s.length, s.width, s.height,
                            s.support_item_id, s.support_type_id, s.support_length, s.support_width
                        )
                        for s in tl.layout.spaces
                    ],
                    placed=[
                        PlacedCargo(
                            p.item_id, p.type_id, p.category,
                            p.x, p.y, p.z,
                            p.length, p.width, p.height,
                            p.weight, p.orientation_id, p.rotation,
                            p.support_by, p.truck_id, p.direct_supported_weight
                        )
                        for p in tl.layout.placed
                    ],
                    remaining=list(tl.layout.remaining),
                    used_weight=tl.layout.used_weight,
                    used_volume=tl.layout.used_volume,
                    score=tl.layout.score,
                    packed_ratio=tl.layout.packed_ratio,
                )

            new_trucks.append(
                TruckLoad(
                    truck_id=tl.truck_id,
                    truck=tl.truck,
                    assigned_items=list(tl.assigned_items),
                    layout=copied_layout,
                    feasible=tl.feasible,
                )
            )
        return FleetSolution(
            trucks=new_trucks,
            objective=self.objective,
            objective_value=self.objective_value,
        )


# =========================
# 基础数据
# =========================

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


# =========================
# 姿态与展开
# =========================

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
        dims = [
            (l, w, h, "LWH"),
            (w, l, h, "WLH"),
        ]
    elif cargo.category == "oriented":
        dims = [(l, w, h, "LWH")]

    uniq: List[Orientation] = []
    seen = set()
    for _, (a, b, c, name) in enumerate(dims):
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            uniq.append(Orientation(len(uniq), key, name))
    return tuple(uniq)


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
# 单车装箱评分与空间管理
# =========================

def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    space_util = used_volume / truck.effective_volume
    weight_util = used_weight / truck.max_weight
    fullness = 0.72 * space_util + 0.28 * weight_util
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


# =========================
# 单车装箱核心
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

    if item.fragile and space.z > 0:
        if space.support_type_id != "G1" and space.support_type_id != "G2":
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
    support_bonus = 0.10 if space.z > 0 else 0.0
    dense_bonus = 0.03 * (item.weight / item.volume) / max(c.density for c in CARGO_TYPES.values())

    used_volume = state.used_volume + item.volume
    used_weight = state.used_weight + item.weight
    space_util, weight_util, fullness = truck_score(truck, used_volume, used_weight)
    return fullness + 0.10 * fill_ratio + 0.03 * low_z_bonus + 0.02 * tight_bonus + support_bonus + dense_bonus + 0.02 * space_util + 0.01 * weight_util


def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    new_spaces: List[Space] = []

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

    if support_by is not None:
        for p in new_placed:
            if p.item_id == support_by:
                p.direct_supported_weight += item.weight
                break

    new_spaces = [s for idx, s in enumerate(state.spaces) if idx != space_idx]
    new_spaces.extend(split_space(space, placed))

    # 关键优化：不再做重型 merge_spaces
    new_spaces = remove_contained_spaces(new_spaces)
    new_spaces = sort_spaces_dblf(new_spaces)

    # 限制空间数量，防止状态爆炸
    if len(new_spaces) > 60:
        new_spaces = new_spaces[:60]

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
    candidate_moves_each_state: int = 12,
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


def repack_assigned_items(
    truck: Truck,
    items: List[CargoItem],
    beam_width: int = 6,
) -> Tuple[bool, Optional[LayoutState]]:
    """
    给定一组已分配给某辆车的货物，尝试重装。
    只要能全部装下，就认为该车当前分配可行。
    """

    if not items:
        empty_layout = LayoutState(
            spaces=[Space(0, 0, 0, truck.length, truck.width, truck.effective_height, None, None, truck.length, truck.width)],
            placed=[],
            remaining=[],
            used_weight=0.0,
            used_volume=0,
            score=0.0,
            packed_ratio=1.0,
        )
        return True, empty_layout

    # 先做快速重量筛选
    total_weight = sum(it.weight for it in items)
    if total_weight > truck.max_weight + 1e-9:
        return False, None

    best_state: Optional[LayoutState] = None

    # 关键优化：少跑几种排序策略
    for policy in (0, 2):
        state = pack_with_beam_search(
            truck=truck,
            items=items,
            beam_width=beam_width,
            candidate_items_each_step=4,
            candidate_moves_each_state=6,
            policy=policy,
        )
        if best_state is None:
            best_state = state
        else:
            old_key = (len(best_state.placed), best_state.used_volume, best_state.used_weight)
            new_key = (len(state.placed), state.used_volume, state.used_weight)
            if new_key > old_key:
                best_state = state

    assert best_state is not None
    feasible = len(best_state.placed) == len(items)
    return feasible, best_state
# parser.add_argument

# =========================
# 问题二外层：解评价
# =========================

def evaluate_fleet_solution(solution: FleetSolution) -> float:
    if any(not t.feasible for t in solution.trucks):
        return float("inf")

    num_trucks = len(solution.trucks)
    total_cost = sum(t.truck.cost for t in solution.trucks)
    avg_space_util = sum(t.space_utilization for t in solution.trucks) / num_trucks if num_trucks else 0.0
    avg_weight_util = sum(t.weight_utilization for t in solution.trucks) / num_trucks if num_trucks else 0.0

    if solution.objective == "min_trucks":
        value = num_trucks - 0.01 * avg_space_util - 0.005 * avg_weight_util
    elif solution.objective == "min_cost":
        value = total_cost - 5.0 * avg_space_util - 2.0 * avg_weight_util
    else:
        raise ValueError(f"未知目标类型: {solution.objective}")

    solution.objective_value = value
    return value


def better_solution(a: FleetSolution, b: Optional[FleetSolution]) -> bool:
    if b is None:
        return True
    return evaluate_fleet_solution(a) + 1e-9 < evaluate_fleet_solution(b)


def get_item_priority(item: CargoItem) -> Tuple[int, int, int, float, str]:
    oriented = 1 if item.oriented else 0
    fragile = 1 if item.fragile else 0
    max_edge = max(item.original_size)
    return (oriented, fragile, item.volume, item.weight, item.item_id)


def sort_all_items(items: List[CargoItem]) -> List[CargoItem]:
    return sorted(items, key=get_item_priority, reverse=True)


# =========================
# 单车重建
# =========================

def rebuild_truckload(truckload: TruckLoad, beam_width: int) -> TruckLoad:
    feasible, layout = repack_assigned_items(truckload.truck, truckload.assigned_items, beam_width=beam_width)
    new_tl = TruckLoad(
        truck_id=truckload.truck_id,
        truck=truckload.truck,
        assigned_items=list(truckload.assigned_items),
        layout=layout,
        feasible=feasible,
    )
    if new_tl.layout is not None:
        for p in new_tl.layout.placed:
            p.truck_id = new_tl.truck_id
    return new_tl


# =========================
# 贪心初始化
# =========================

def greedy_construct(
    all_items: List[CargoItem],
    objective: str,
    beam_width: int,
) -> FleetSolution:
    solution = FleetSolution(trucks=[], objective=objective)
    ordered_items = sort_all_items(all_items)
    next_truck_idx = 1

    for item in ordered_items:
        best_candidate: Optional[FleetSolution] = None

        # 1. 尝试插入已有车辆
        for idx, tl in enumerate(solution.trucks):
            trial = solution.clone()
            trial.trucks[idx].assigned_items.append(item)
            rebuilt = rebuild_truckload(trial.trucks[idx], beam_width)
            if not rebuilt.feasible:
                continue
            trial.trucks[idx] = rebuilt
            if better_solution(trial, best_candidate):
                best_candidate = trial

        # 2. 尝试新开车
        # min_trucks 更偏向先试大车；min_cost 更偏向先试小车
        truck_order = ["车型2", "车型1"] if objective == "min_trucks" else ["车型1", "车型2"]
        for truck_name in truck_order:
            trial = solution.clone()
            new_load = TruckLoad(
                truck_id=f"T{next_truck_idx:03d}",
                truck=TRUCKS[truck_name],
                assigned_items=[item],
            )
            rebuilt = rebuild_truckload(new_load, beam_width)
            if not rebuilt.feasible:
                continue
            trial.trucks.append(rebuilt)
            if better_solution(trial, best_candidate):
                best_candidate = trial

        if best_candidate is None:
            raise RuntimeError(f"货物 {item.item_id} 无法装入任何车辆，构造失败。")

        solution = best_candidate
        next_truck_idx = len(solution.trucks) + 1

    evaluate_fleet_solution(solution)
    return solution


# =========================
# 局部搜索：辅助
# =========================

def sort_trucks_for_removal(solution: FleetSolution) -> List[TruckLoad]:
    return sorted(
        solution.trucks,
        key=lambda t: (t.space_utilization + 0.6 * t.weight_utilization, len(t.assigned_items), -t.truck.cost)
    )


def insert_item_into_existing_best(
    solution: FleetSolution,
    item: CargoItem,
    beam_width: int,
) -> Optional[FleetSolution]:
    best_trial: Optional[FleetSolution] = None

    for idx, tl in enumerate(solution.trucks):
        trial = solution.clone()
        trial.trucks[idx].assigned_items.append(item)
        rebuilt = rebuild_truckload(trial.trucks[idx], beam_width)
        if not rebuilt.feasible:
            continue
        trial.trucks[idx] = rebuilt
        if better_solution(trial, best_trial):
            best_trial = trial

    return best_trial


# =========================
# 局部搜索：删车重构
# =========================

def remove_truck_search(
    solution: FleetSolution,
    beam_width: int,
    max_trials: int = 10,
) -> Optional[FleetSolution]:
    if len(solution.trucks) <= 1:
        return None

    candidates = sort_trucks_for_removal(solution)
    best_sol: Optional[FleetSolution] = None
    tried = 0

    for victim in candidates:
        if tried >= max_trials:
            break
        tried += 1

        trial = solution.clone()
        victim_idx = next((i for i, t in enumerate(trial.trucks) if t.truck_id == victim.truck_id), None)
        if victim_idx is None:
            continue

        removed_items = list(trial.trucks[victim_idx].assigned_items)
        del trial.trucks[victim_idx]

        removed_items = sort_all_items(removed_items)
        feasible_all = True

        for item in removed_items:
            inserted = insert_item_into_existing_best(trial, item, beam_width)
            if inserted is None:
                feasible_all = False
                break
            trial = inserted

        if feasible_all and better_solution(trial, best_sol):
            best_sol = trial

    return best_sol


# =========================
# 局部搜索：单件搬移
# =========================

def relocate_search(
    solution: FleetSolution,
    beam_width: int,
    max_trials: int = 150,
) -> Optional[FleetSolution]:
    if len(solution.trucks) <= 1:
        return None

    best_sol: Optional[FleetSolution] = None
    trials = 0

    source_trucks = sorted(solution.trucks, key=lambda t: (t.space_utilization + 0.5 * t.weight_utilization, len(t.assigned_items)))

    for src in source_trucks:
        src_items = sort_all_items(src.assigned_items)
        for item in src_items:
            for dst in solution.trucks:
                if src.truck_id == dst.truck_id:
                    continue
                if trials >= max_trials:
                    return best_sol
                trials += 1

                trial = solution.clone()
                src_idx = next(i for i, t in enumerate(trial.trucks) if t.truck_id == src.truck_id)
                dst_idx = next(i for i, t in enumerate(trial.trucks) if t.truck_id == dst.truck_id)

                # 删除该货物
                found = False
                for k, it in enumerate(trial.trucks[src_idx].assigned_items):
                    if it.item_id == item.item_id:
                        del trial.trucks[src_idx].assigned_items[k]
                        found = True
                        break
                if not found:
                    continue

                trial.trucks[dst_idx].assigned_items.append(item)

                rebuilt_src = rebuild_truckload(trial.trucks[src_idx], beam_width)
                rebuilt_dst = rebuild_truckload(trial.trucks[dst_idx], beam_width)
                if not rebuilt_src.feasible or not rebuilt_dst.feasible:
                    continue

                trial.trucks[src_idx] = rebuilt_src
                trial.trucks[dst_idx] = rebuilt_dst

                if len(trial.trucks[src_idx].assigned_items) == 0:
                    del trial.trucks[src_idx]

                if better_solution(trial, best_sol):
                    best_sol = trial

    return best_sol


# =========================
# 局部搜索：车型切换
# =========================

def switch_truck_type_search(
    solution: FleetSolution,
    beam_width: int,
    max_trials: int = 20,
) -> Optional[FleetSolution]:
    best_sol: Optional[FleetSolution] = None
    trucks = list(solution.trucks)
    random.shuffle(trucks)

    for idx, tl in enumerate(trucks[:max_trials]):
        other_name = "车型1" if tl.truck.name == "车型2" else "车型2"

        trial = solution.clone()
        true_idx = next(i for i, t in enumerate(trial.trucks) if t.truck_id == tl.truck_id)
        trial.trucks[true_idx].truck = TRUCKS[other_name]
        rebuilt = rebuild_truckload(trial.trucks[true_idx], beam_width)
        if not rebuilt.feasible:
            continue

        trial.trucks[true_idx] = rebuilt
        if better_solution(trial, best_sol):
            best_sol = trial

    return best_sol


# =========================
# 局部搜索主流程
# =========================

def local_search(
    init_solution: FleetSolution,
    beam_width: int,
    max_rounds: int = 30,
) -> FleetSolution:
    current = init_solution.clone()
    improved = True
    rounds = 0

    while improved and rounds < max_rounds:
        improved = False
        rounds += 1

        # 1. 删车重构
        new_sol = remove_truck_search(current, beam_width=beam_width, max_trials=10)
        if new_sol is not None and better_solution(new_sol, current):
            current = new_sol
            improved = True
            continue

        # 2. 单件搬移
        new_sol = relocate_search(current, beam_width=beam_width, max_trials=150)
        if new_sol is not None and better_solution(new_sol, current):
            current = new_sol
            improved = True
            continue

        # 3. 车型切换
        new_sol = switch_truck_type_search(current, beam_width=beam_width, max_trials=20)
        if new_sol is not None and better_solution(new_sol, current):
            current = new_sol
            improved = True
            continue

    evaluate_fleet_solution(current)
    return current


# =========================
# 问题二总入口
# =========================

def solve_problem_2(
    objective: str = "min_trucks",
    beam_width: int = 8,
    local_search_rounds: int = 30,
) -> FleetSolution:
    if objective not in {"min_trucks", "min_cost"}:
        raise ValueError("objective 必须为 min_trucks 或 min_cost")

    full_counts = {k: CARGO_TYPES[k].quantity for k in TYPE_ORDER}
    all_items = expand_items(full_counts)

    # 1. 贪心初始化
    init_solution = greedy_construct(all_items, objective=objective, beam_width=beam_width)

    # 2. 局部搜索
    final_solution = local_search(init_solution, beam_width=beam_width, max_rounds=local_search_rounds)

    evaluate_fleet_solution(final_solution)
    return final_solution


# =========================
# 输出
# =========================

def summarize_solution(solution: FleetSolution) -> Dict[str, object]:
    num_trucks = len(solution.trucks)
    total_cost = sum(t.truck.cost for t in solution.trucks)
    avg_space_util = sum(t.space_utilization for t in solution.trucks) / num_trucks if num_trucks else 0.0
    avg_weight_util = sum(t.weight_utilization for t in solution.trucks) / num_trucks if num_trucks else 0.0
    type_counter = Counter(t.truck.name for t in solution.trucks)

    return {
        "objective": solution.objective,
        "objective_value": round(solution.objective_value, 6),
        "num_trucks": num_trucks,
        "total_cost": round(total_cost, 2),
        "avg_space_utilization": round(avg_space_util, 6),
        "avg_weight_utilization": round(avg_weight_util, 6),
        "truck_type_counts": dict(type_counter),
    }


def print_solution(solution: FleetSolution, title: str):
    summary = summarize_solution(solution)
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(f"目标: {summary['objective']}")
    print(f"目标函数值: {summary['objective_value']}")
    print(f"车辆数: {summary['num_trucks']}")
    print(f"总成本: {summary['total_cost']}")
    print(f"平均空间利用率: {summary['avg_space_utilization']:.4f}")
    print(f"平均载重利用率: {summary['avg_weight_utilization']:.4f}")
    print(f"车型使用统计: {summary['truck_type_counts']}")

    for tl in solution.trucks:
        print("-" * 80)
        print(
            f"{tl.truck_id} | {tl.truck.name} | "
            f"货物数={len(tl.assigned_items)} | "
            f"空间利用率={tl.space_utilization:.4f} | "
            f"载重利用率={tl.weight_utilization:.4f} | "
            f"成本={tl.truck.cost:.2f}"
        )
        type_counts = Counter(it.type_id for it in tl.assigned_items)
        print(f"货类组成: {dict(type_counts)}")


def write_items_csv(path: str, solution: FleetSolution) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    rows: List[PlacedCargo] = []
    for tl in solution.trucks:
        if tl.layout is not None:
            rows.extend(tl.layout.placed)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "truck_id", "truck_type",
            "item_id", "type_id", "category",
            "x", "y", "z",
            "length", "width", "height",
            "weight", "orientation_id", "rotation",
            "support_by"
        ])
        for tl in solution.trucks:
            if tl.layout is None:
                continue
            for p in tl.layout.placed:
                writer.writerow([
                    tl.truck_id, tl.truck.name,
                    p.item_id, p.type_id, p.category,
                    p.x, p.y, p.z,
                    p.length, p.width, p.height,
                    p.weight, p.orientation_id, p.rotation,
                    p.support_by or "",
                ])


def write_summary_csv(path: str, solution: FleetSolution) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "truck_id", "truck_type", "truck_cost",
            "item_count", "used_weight", "used_volume",
            "space_utilization", "weight_utilization",
            "type_counts"
        ])
        for tl in solution.trucks:
            type_counts = Counter(it.type_id for it in tl.assigned_items)
            writer.writerow([
                tl.truck_id,
                tl.truck.name,
                tl.truck.cost,
                len(tl.assigned_items),
                round(tl.used_weight, 3),
                tl.used_volume,
                round(tl.space_utilization, 6),
                round(tl.weight_utilization, 6),
                dict(type_counts),
            ])


# =========================
# 命令行
# =========================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二 贪心 + 局部搜索 最终版")
    parser.add_argument(
        "--objective",
        type=str,
        default="both",
        choices=["min_trucks", "min_cost", "both"],
        help="求解目标：min_trucks / min_cost / both",
    )
    parser.add_argument("--beam-width", type=int, default=6, help="单车装箱 beam width")
    parser.add_argument("--local-rounds", type=int, default=10, help="局部搜索轮数上限")
    parser.add_argument("--seed", type=int, default=2026, help="随机种子")
    parser.add_argument("--outdir", type=str, default="output_problem2", help="输出目录")
    return parser.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)

    objectives = ["min_trucks", "min_cost"] if args.objective == "both" else [args.objective]

    for obj in objectives:
        title = "问题2.1：车辆总数最少" if obj == "min_trucks" else "问题2.2：总运输成本最低"
        solution = solve_problem_2(
            objective=obj,
            beam_width=args.beam_width,
            local_search_rounds=args.local_rounds,
        )

        print_solution(solution, title=title)

        detail_csv = os.path.join(args.outdir, f"{obj}_装箱明细.csv")
        summary_csv = os.path.join(args.outdir, f"{obj}_车辆汇总.csv")
        write_items_csv(detail_csv, solution)
        write_summary_csv(summary_csv, solution)

        print(f"\n装箱明细已写入: {detail_csv}")
        print(f"车辆汇总已写入: {summary_csv}")


if __name__ == "__main__":
    main()