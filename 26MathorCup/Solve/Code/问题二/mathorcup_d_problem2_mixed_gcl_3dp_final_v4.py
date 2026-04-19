#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题2 最终版
混合车型 GCL-3DP 求解器（Mixed-type GA-driven Channel-aware LNS for 3D Packing）

与前文口径保持一致：
1. 子问题1.1：快速贪心为主，CLB-3DP 为对比；
2. 子问题1.2：GA增强单车策略 + G3第二通道 + 外层减车；
3. 问题2：在 1.2 的基础上增加“混合车型选择”这一层决策，
   同时支持：
   - 问题2.1：总运输车辆数最少；
   - 问题2.2：总运输成本最低。

说明：
- 该程序采用启发式/混合智能算法，不是精确 MILP；
- 仍然保留工程可行的三维装箱物理约束：
  边界、总重、支撑完整性、承压、G3 约束、定向件姿态；
- 输出每辆车的装箱明细、汇总结果与整体方案汇总。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ============================================================
# 基础数据
# ============================================================

RANDOM_SEED = 2026
random.seed(RANDOM_SEED)

MAX_SPACES_TO_CHECK = 48
MIN_SPACE_VOLUME = 22000
CANDIDATE_SPACES_PER_STEP = 18


@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str


@dataclass(frozen=True)
class CargoType:
    type_id: str
    category: str
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

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


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
    def floor_area(self) -> int:
        return self.length * self.width


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

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]
TYPE_ORDER_NON_G3 = ["G4", "G5", "G1", "G2"]


# ============================================================
# 姿态
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
        dims = [
            (l, w, h, "LWH"),
            (w, l, h, "WLH"),
        ]
    elif cargo.oriented:
        dims = [(l, w, h, "LWH")]

    out: List[Orientation] = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            out.append(Orientation(len(out) + 1, key, name))
    return tuple(out)


ORIENTATIONS = {k: generate_orientations(v) for k, v in CARGO_TYPES.items()}


# ============================================================
# 数据结构
# ============================================================

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
    top_area_m2_cache: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.top_area_m2_cache = (self.length * self.width) / 10000.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return self.top_area_m2_cache


@dataclass
class PackingPolicy:
    type_order: Tuple[str, ...]
    w_fill: float
    w_bottom: float
    w_remain: float
    g3_floor_bonus: float
    second_channel_bonus: float

    def desc(self) -> str:
        return (
            f"order={'-'.join(self.type_order)};"
            f"wf={self.w_fill:.2f};wb={self.w_bottom:.2f};wr={self.w_remain:.2f};"
            f"g3f={self.g3_floor_bonus:.2f};g3c={self.second_channel_bonus:.2f}"
        )


@dataclass
class VehicleResult:
    vehicle_id: str
    truck_name: str
    placed: List[PlacedCargo]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int
    policy_desc: str

    @property
    def item_count(self) -> int:
        return sum(self.actual_counts.values())

    @property
    def total_cost(self) -> float:
        return TRUCKS[self.truck_name].cost


@dataclass
class SolutionResult:
    objective: str
    vehicles: List[VehicleResult]
    success: bool
    total_cost: float
    vehicle_count: int
    remaining: Dict[str, int]
    note: str = ""


# ============================================================
# 工具函数
# ============================================================

def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / max(1, truck.effective_volume)
    wv = used_weight / max(1.0, truck.max_weight)
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def total_remaining_items(remaining: Dict[str, int]) -> int:
    return sum(remaining.values())


def total_remaining_volume(remaining: Dict[str, int]) -> int:
    return sum(CARGO_TYPES[t].volume * remaining.get(t, 0) for t in TYPE_ORDER_ALL)


def total_remaining_weight(remaining: Dict[str, int]) -> float:
    return sum(CARGO_TYPES[t].weight * remaining.get(t, 0) for t in TYPE_ORDER_ALL)


def all_loaded(remaining: Dict[str, int]) -> bool:
    return all(v <= 0 for v in remaining.values())


def initial_remaining() -> Dict[str, int]:
    return {k: v.quantity for k, v in CARGO_TYPES.items()}


def clone_remaining(remaining: Dict[str, int]) -> Dict[str, int]:
    return {k: int(v) for k, v in remaining.items()}


def subtract_counts(remaining: Dict[str, int], used: Dict[str, int]) -> None:
    for t, c in used.items():
        remaining[t] = max(0, remaining.get(t, 0) - c)


def add_counts(remaining: Dict[str, int], used: Dict[str, int]) -> None:
    for t, c in used.items():
        remaining[t] = remaining.get(t, 0) + c


def space_volume(sp: Dict[str, int]) -> int:
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces: List[Dict[str, int]]) -> List[Dict[str, int]]:
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (s["z"], -space_volume(s), s["y"], s["x"]))
    return spaces


def default_policy() -> PackingPolicy:
    return PackingPolicy(
        type_order=("G4", "G5", "G1", "G2", "G3"),
        w_fill=0.60,
        w_bottom=0.22,
        w_remain=0.18,
        g3_floor_bonus=0.18,
        second_channel_bonus=0.15,
    )


def random_policy(rng: random.Random) -> PackingPolicy:
    order = TYPE_ORDER_ALL[:]
    rng.shuffle(order)
    return PackingPolicy(
        type_order=tuple(order),
        w_fill=rng.uniform(0.45, 0.75),
        w_bottom=rng.uniform(0.10, 0.30),
        w_remain=rng.uniform(0.08, 0.28),
        g3_floor_bonus=rng.uniform(0.05, 0.30),
        second_channel_bonus=rng.uniform(0.05, 0.25),
    )


def crossover_policy(a: PackingPolicy, b: PackingPolicy, rng: random.Random) -> PackingPolicy:
    order = list(a.type_order[:2])
    for t in b.type_order:
        if t not in order:
            order.append(t)
    for t in TYPE_ORDER_ALL:
        if t not in order:
            order.append(t)
    return PackingPolicy(
        type_order=tuple(order[:5]),
        w_fill=(a.w_fill + b.w_fill) / 2,
        w_bottom=(a.w_bottom + b.w_bottom) / 2,
        w_remain=(a.w_remain + b.w_remain) / 2,
        g3_floor_bonus=(a.g3_floor_bonus + b.g3_floor_bonus) / 2,
        second_channel_bonus=(a.second_channel_bonus + b.second_channel_bonus) / 2,
    )


def mutate_policy(p: PackingPolicy, rng: random.Random) -> PackingPolicy:
    order = list(p.type_order)
    if rng.random() < 0.8:
        i, j = rng.sample(range(len(order)), 2)
        order[i], order[j] = order[j], order[i]

    def clip(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))

    return PackingPolicy(
        type_order=tuple(order),
        w_fill=clip(p.w_fill + rng.uniform(-0.08, 0.08), 0.35, 0.80),
        w_bottom=clip(p.w_bottom + rng.uniform(-0.06, 0.06), 0.05, 0.35),
        w_remain=clip(p.w_remain + rng.uniform(-0.06, 0.06), 0.05, 0.35),
        g3_floor_bonus=clip(p.g3_floor_bonus + rng.uniform(-0.08, 0.08), 0.00, 0.35),
        second_channel_bonus=clip(p.second_channel_bonus + rng.uniform(-0.08, 0.08), 0.00, 0.30),
    )


# ============================================================
# 轻量空间装箱器（保留 1.1 / 1.2 的物理约束口径）
# ============================================================

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

            # 必须完整落在单个支撑顶面内
            if l > support.length or w > support.width:
                return False

            # 易碎件不能作为支撑
            if support.category == "fragile":
                return False

            # G3 仅允许放在底板或 G1/G2 顶面
            if type_id == "G3" and support_type_id not in ("G1", "G2"):
                return False

            # 承压近似
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
            x=sp["x"],
            y=sp["y"],
            z=sp["z"],
            length=l,
            width=w,
            height=h,
            weight=cargo.weight,
            orientation_id=ori.orient_id,
            rotation=ori.rotation,
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

        # G3 上方禁放
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


# ============================================================
# 单车装载评价与 G3 第二通道
# ============================================================

def eval_candidate(type_id: str, ori: Orientation, sp: Dict[str, int], remaining: Dict[str, int], truck_obj: FastTruck, policy: PackingPolicy) -> Optional[float]:
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if remaining.get(type_id, 0) <= 0:
        return None
    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight + 1e-9:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)

    bonus = 0.0
    if type_id == "G3" and sp["z"] == 0:
        bonus += policy.g3_floor_bonus
    if type_id != "G3" and sp["z"] == 0:
        bonus += 0.02
    if sp["z"] > 0:
        bonus -= 0.02

    score = policy.w_fill * fill_ratio + policy.w_bottom * bottom_bonus + policy.w_remain * remain_bonus + bonus
    return score


def choose_type_order(policy: PackingPolicy) -> List[str]:
    order = list(policy.type_order)
    for t in TYPE_ORDER_ALL:
        if t not in order:
            order.append(t)
    return order[:5]


def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], policy: PackingPolicy) -> bool:
    best = None
    best_score = -1e18
    type_order = choose_type_order(policy)
    candidate_spaces = truck_obj.spaces[:CANDIDATE_SPACES_PER_STEP]

    for sp_idx in range(len(candidate_spaces)):
        sp = truck_obj.spaces[sp_idx]
        local_best = None
        local_best_score = -1e18
        for type_id in type_order:
            if remaining.get(type_id, 0) <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = eval_candidate(type_id, ori, sp, remaining, truck_obj, policy)
                if val is None:
                    continue
                if val > local_best_score:
                    local_best_score = val
                    local_best = (type_id, ori, sp_idx)
        if local_best is not None and local_best_score > best_score:
            best_score = local_best_score
            best = (best_score, *local_best)
            # 早停：已经找到足够好的候选，避免每步全扫描
            if best_score >= 0.95:
                break

    if best is None:
        return False

    _, type_id, ori, sp_idx = best
    truck_obj.place_item(type_id, ori, sp_idx)
    remaining[type_id] -= 1
    return True


def add_g3_second_channel(truck_obj: FastTruck, remaining: Dict[str, int], policy: PackingPolicy) -> int:
    """
    在已有 G1/G2 顶面上额外尝试放置 G3。
    这是问题1.2与问题2中保留的“G3第二通道”机制。
    """
    if remaining.get("G3", 0) <= 0:
        return 0

    placed_now = 0
    supports = [p for p in truck_obj.placed if p.type_id in ("G1", "G2")]
    supports.sort(key=lambda p: (p.z, -(p.length * p.width), p.y, p.x))

    for sup in supports:
        if remaining["G3"] <= 0:
            break
        if sup.direct_supported_weight > 1e-9:
            # 顶面上已经承载过东西时仍可继续，但优先用空顶面
            pass

        best = None
        best_key = None
        for ori in ORIENTATIONS["G3"]:
            l, w, h = ori.size
            if sup.z + sup.height + h > truck_obj.truck.effective_height:
                continue
            nx = sup.length // l
            ny = sup.width // w
            cnt = nx * ny
            if cnt <= 0:
                continue
            area_ratio = (cnt * l * w) / max(1, sup.length * sup.width)
            # 优先更多件、覆盖率更高、总高度更低
            key = (-min(cnt, remaining["G3"]), -area_ratio - policy.second_channel_bonus, sup.height + h)
            if best_key is None or key < best_key:
                best_key = key
                best = (ori, nx, ny)

        if best is None:
            continue

        ori, nx, ny = best
        l, w, h = ori.size
        top_z = sup.z + sup.height
        support_limit = CARGO_TYPES[sup.type_id].max_support_pressure

        for j in range(ny):
            for i in range(nx):
                if remaining["G3"] <= 0:
                    break
                projected_pressure = (sup.direct_supported_weight + CARGO_TYPES["G3"].weight) / max(1e-9, sup.top_area_m2)
                if projected_pressure > support_limit + 1e-9:
                    break
                if truck_obj.used_weight + CARGO_TYPES["G3"].weight > truck_obj.max_weight + 1e-9:
                    break

                truck_obj.serial_counter["G3"] += 1
                item_id = f"G3_{truck_obj.vehicle_id}_{truck_obj.serial_counter['G3']:04d}"
                p = PlacedCargo(
                    item_id=item_id,
                    type_id="G3",
                    category="fragile",
                    x=sup.x + i * l,
                    y=sup.y + j * w,
                    z=top_z,
                    length=l,
                    width=w,
                    height=h,
                    weight=CARGO_TYPES["G3"].weight,
                    orientation_id=ori.orient_id,
                    rotation=ori.rotation,
                    truck_id=truck_obj.vehicle_id,
                    support_by=sup.item_id,
                )
                truck_obj.placed.append(p)
                truck_obj.placed_map[item_id] = p
                truck_obj.used_weight += p.weight
                truck_obj.used_volume += p.volume
                truck_obj.actual_counts["G3"] += 1
                sup.direct_supported_weight += p.weight
                remaining["G3"] -= 1
                placed_now += 1

            if remaining["G3"] <= 0:
                break

    return placed_now


def pack_single_vehicle_with_policy(truck: Truck, remaining_source: Dict[str, int], policy: PackingPolicy, vehicle_idx: int) -> VehicleResult:
    remaining = clone_remaining(remaining_source)
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)

    while True:
        ok = place_one_best(truck_obj, remaining, policy)
        if not ok:
            break

    # 第二通道：在 G1/G2 顶面再补放 G3
    add_g3_second_channel(truck_obj, remaining, policy)

    return VehicleResult(
        vehicle_id=vehicle_id,
        truck_name=truck.name,
        placed=truck_obj.placed,
        actual_counts=dict(truck_obj.actual_counts),
        used_weight=truck_obj.used_weight,
        used_volume=truck_obj.used_volume,
        policy_desc=policy.desc(),
    )


def quick_policy_pool() -> List[PackingPolicy]:
    return [
        default_policy(),
        PackingPolicy(("G4", "G5", "G1", "G2", "G3"), 0.58, 0.20, 0.22, 0.25, 0.15),
        PackingPolicy(("G3", "G4", "G5", "G1", "G2"), 0.54, 0.24, 0.22, 0.55, 0.20),
        PackingPolicy(("G1", "G2", "G4", "G5", "G3"), 0.62, 0.20, 0.18, 0.10, 0.12),
    ]


def quick_search_vehicle(truck: Truck, remaining: Dict[str, int], vehicle_idx: int, objective: str) -> VehicleResult:
    best_plan: Optional[VehicleResult] = None
    best_fit: Optional[Tuple[float, float, float, float]] = None
    for policy in quick_policy_pool():
        plan = pack_single_vehicle_with_policy(truck, remaining, policy, vehicle_idx)
        fit = vehicle_fitness(plan, objective)
        if best_plan is None or fit > best_fit:
            best_plan = plan
            best_fit = fit
    assert best_plan is not None
    return best_plan


def choose_truck_candidates_by_screening(
    remaining: Dict[str, int],
    vehicle_idx: int,
    objective: str,
) -> List[str]:
    q1 = quick_search_vehicle(TRUCKS["车型1"], remaining, vehicle_idx, objective)
    q2 = quick_search_vehicle(TRUCKS["车型2"], remaining, vehicle_idx, objective)
    f1 = vehicle_fitness(q1, objective)
    f2 = vehicle_fitness(q2, objective)

    # 问题2规模较大，默认只对粗筛更优的车型做精修；
    # 仅在两者非常接近时才把另一车型作为备选。
    if objective == "min_vehicles":
        primary_gap = abs(f1[0] - f2[0])
        if primary_gap <= 3:
            return [q1.truck_name, q2.truck_name] if f1 >= f2 else [q2.truck_name, q1.truck_name]
        return [q1.truck_name] if f1 >= f2 else [q2.truck_name]

    ratio_gap = abs(f1[0] - f2[0])
    if ratio_gap <= 0.006:
        return [q1.truck_name, q2.truck_name] if f1 >= f2 else [q2.truck_name, q1.truck_name]
    return [q1.truck_name] if f1 >= f2 else [q2.truck_name]


# ============================================================
# GA 单车策略搜索
# ============================================================

def vehicle_fitness(plan: VehicleResult, objective: str) -> Tuple[float, float, float, float]:
    truck = TRUCKS[plan.truck_name]
    sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)

    if objective == "min_vehicles":
        primary = plan.item_count + 120.0 * fs
        secondary = plan.used_volume
        tertiary = plan.used_weight
        quaternary = -truck.cost
    else:
        # 更强调单位成本效率
        eff = (plan.item_count + 80.0 * fs) / max(1.0, truck.cost)
        primary = eff
        secondary = plan.item_count
        tertiary = fs
        quaternary = -truck.cost
    return primary, secondary, tertiary, quaternary


def ga_search_best_vehicle(
    truck: Truck,
    remaining: Dict[str, int],
    vehicle_idx: int,
    objective: str,
    seed: int,
    pop_size: int = 12,
    generations: int = 6,
) -> VehicleResult:
    """
    问题2采用轻量策略搜索：
    先评估固定策略池，再做少量扰动精修。
    这样仍保留 1.2 的“策略优化”思想，但避免在混合车型规模下
    每辆车都跑完整 GA 导致本地机器耗时过长。
    """
    rng = random.Random(seed)

    base_pool = quick_policy_pool()
    # 基础策略 + 少量随机策略 + 对当前最好策略做扰动
    candidate_policies: List[PackingPolicy] = list(base_pool)
    for _ in range(min(3, max(1, pop_size // 3))):
        candidate_policies.append(random_policy(rng))

    best_plan: Optional[VehicleResult] = None
    best_fit: Optional[Tuple[float, float, float, float]] = None
    best_policy: Optional[PackingPolicy] = None

    # 第一轮：粗筛
    for policy in candidate_policies:
        plan = pack_single_vehicle_with_policy(truck, remaining, policy, vehicle_idx)
        fit = vehicle_fitness(plan, objective)
        if best_plan is None or fit > best_fit:
            best_plan = plan
            best_fit = fit
            best_policy = policy

    assert best_plan is not None and best_policy is not None

    # 第二轮：围绕当前最优策略做少量扰动精修
    refine_rounds = max(2, min(5, generations))
    for _ in range(refine_rounds):
        trial_policy = mutate_policy(best_policy, rng)
        if rng.random() < 0.35:
            trial_policy = crossover_policy(best_policy, random.choice(base_pool), rng)
        plan = pack_single_vehicle_with_policy(truck, remaining, trial_policy, vehicle_idx)
        fit = vehicle_fitness(plan, objective)
        if fit > best_fit:
            best_plan = plan
            best_fit = fit
            best_policy = trial_policy

    return best_plan


# ============================================================
# 混合车型构造
# ============================================================

def compare_vehicle_candidates(plan_a: VehicleResult, plan_b: VehicleResult, objective: str) -> VehicleResult:
    fit_a = vehicle_fitness(plan_a, objective)
    fit_b = vehicle_fitness(plan_b, objective)
    return plan_a if fit_a >= fit_b else plan_b


def build_initial_solution_mixed(objective: str, seed: int, ga_pop: int, ga_gen: int) -> SolutionResult:
    remaining = initial_remaining()
    vehicles: List[VehicleResult] = []
    vehicle_idx = 1

    while not all_loaded(remaining):
        print(f"[初始构造] 第 {vehicle_idx} 辆车，剩余件数={total_remaining_items(remaining)}")
        truck_candidates = choose_truck_candidates_by_screening(remaining, vehicle_idx, objective)
        best: Optional[VehicleResult] = None
        for rank, truck_name in enumerate(truck_candidates):
            plan = ga_search_best_vehicle(
                TRUCKS[truck_name], remaining, vehicle_idx, objective,
                seed + vehicle_idx * 101 + rank * 17 + (1 if truck_name == "车型1" else 2),
                ga_pop, ga_gen
            )
            if best is None or vehicle_fitness(plan, objective) > vehicle_fitness(best, objective):
                best = plan
            # 若快速筛选只返回 1 个车型，这里自动只跑一次 GA

        assert best is not None
        if best.item_count <= 0:
            break

        vehicles.append(best)
        subtract_counts(remaining, best.actual_counts)
        vehicle_idx += 1

    return SolutionResult(
        objective=objective,
        vehicles=vehicles,
        success=all_loaded(remaining),
        total_cost=sum(v.total_cost for v in vehicles),
        vehicle_count=len(vehicles),
        remaining=remaining,
        note="mixed greedy + GA initial solution",
    )


def construct_solution_with_vehicle_limit(
    max_vehicle_count: int,
    objective: str,
    seed: int,
    ga_pop: int,
    ga_gen: int,
) -> SolutionResult:
    remaining = initial_remaining()
    vehicles: List[VehicleResult] = []

    for idx in range(1, max_vehicle_count + 1):
        if all_loaded(remaining):
            break

        print(f"[限车构造] 目标K={max_vehicle_count}, 当前第 {idx} 辆车，剩余件数={total_remaining_items(remaining)}")
        truck_candidates = choose_truck_candidates_by_screening(remaining, idx, objective)
        best: Optional[VehicleResult] = None
        for rank, truck_name in enumerate(truck_candidates):
            plan = ga_search_best_vehicle(
                TRUCKS[truck_name], remaining, idx, objective,
                seed + idx * 131 + rank * 19 + (1 if truck_name == "车型1" else 2),
                ga_pop, ga_gen
            )
            if best is None or vehicle_fitness(plan, objective) > vehicle_fitness(best, objective):
                best = plan

        assert best is not None
        if best.item_count <= 0:
            return SolutionResult(objective, vehicles, False, sum(v.total_cost for v in vehicles), len(vehicles), remaining, note="encountered empty vehicle")

        vehicles.append(best)
        subtract_counts(remaining, best.actual_counts)

    return SolutionResult(
        objective=objective,
        vehicles=vehicles,
        success=all_loaded(remaining),
        total_cost=sum(v.total_cost for v in vehicles),
        vehicle_count=len(vehicles),
        remaining=remaining,
        note=f"construct with vehicle limit {max_vehicle_count}",
    )


# ============================================================
# 下界与两类目标求解
# ============================================================

def lower_bound_mixed_vehicle_count() -> int:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    big = TRUCKS["车型2"]
    basic_lb = max(math.ceil(total_volume / big.effective_volume), math.ceil(total_weight / big.max_weight))

    g3_best = 0
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= big.effective_height:
            g3_best = max(g3_best, (big.length // l) * (big.width // w))
    g3_lb = math.ceil(CARGO_TYPES["G3"].quantity / max(1, g3_best))
    return max(basic_lb, g3_lb)


def try_feasible_solution_for_k(
    k: int,
    objective: str,
    seed: int,
    ga_pop: int,
    ga_gen: int,
    attempts_per_k: int,
) -> Optional[SolutionResult]:
    print(f"[{objective}] 尝试车辆数 K={k} ...")
    feasible_candidates: List[SolutionResult] = []
    for att in range(attempts_per_k):
        trial = construct_solution_with_vehicle_limit(
            max_vehicle_count=k,
            objective=objective,
            seed=seed + k * 1009 + att * 97,
            ga_pop=ga_pop,
            ga_gen=ga_gen,
        )
        if trial.success:
            feasible_candidates.append(trial)
    if not feasible_candidates:
        return None
    if objective == "min_cost":
        feasible_candidates.sort(key=lambda s: (s.total_cost, s.vehicle_count))
    else:
        feasible_candidates.sort(key=lambda s: (s.vehicle_count, s.total_cost))
    return feasible_candidates[0]


def solve_problem_21_min_vehicle(seed: int, ga_pop: int, ga_gen: int, attempts_per_k: int) -> SolutionResult:
    lb = lower_bound_mixed_vehicle_count()
    init_sol = build_initial_solution_mixed("min_vehicles", seed, ga_pop, ga_gen)
    if not init_sol.success:
        raise RuntimeError("初始混合车型解构造失败，请增大 GA 代数或种群规模。")

    best = init_sol
    lo, hi = lb, init_sol.vehicle_count

    # 先用二分法缩小可行车辆数区间，避免从 30、29、28... 逐层重建整套方案
    while lo < hi:
        mid = (lo + hi) // 2
        feasible = try_feasible_solution_for_k(mid, "min_vehicles", seed + 30000, ga_pop, ga_gen, attempts_per_k)
        if feasible is not None:
            best = feasible
            hi = mid
        else:
            lo = mid + 1

    # 在二分收敛点附近再做很小范围精修，提升稳定性
    start_k = max(lb, hi - 2)
    end_k = hi + 1
    for k in range(start_k, end_k + 1):
        feasible = try_feasible_solution_for_k(k, "min_vehicles", seed + 60000, ga_pop, ga_gen, attempts_per_k)
        if feasible is not None and feasible.vehicle_count <= best.vehicle_count:
            best = feasible
            break

    best.note = f"min_vehicle solved, lower_bound={lb}, binary_search_final={best.vehicle_count}"
    return best


def build_small_truck_upper_solution(seed: int, ga_pop: int, ga_gen: int) -> SolutionResult:
    remaining = initial_remaining()
    vehicles: List[VehicleResult] = []
    idx = 1
    while not all_loaded(remaining):
        plan = ga_search_best_vehicle(TRUCKS["车型1"], remaining, idx, "min_cost", seed + idx * 43, ga_pop, ga_gen)
        if plan.item_count <= 0:
            break
        vehicles.append(plan)
        subtract_counts(remaining, plan.actual_counts)
        idx += 1
    return SolutionResult("min_cost", vehicles, all_loaded(remaining), sum(v.total_cost for v in vehicles), len(vehicles), remaining, note="all-small upper solution")


def solve_problem_22_min_cost(seed: int, ga_pop: int, ga_gen: int, attempts_per_k: int) -> SolutionResult:
    lb = lower_bound_mixed_vehicle_count()
    upper_sol = build_small_truck_upper_solution(seed + 7000, ga_pop, ga_gen)
    if not upper_sol.success:
        raise RuntimeError("构造成本优化的上界解失败，请增大 GA 代数或种群规模。")

    best: Optional[SolutionResult] = None
    upper_k = upper_sol.vehicle_count

    # 车型2在单位容量/单位载重上的成本都优于车型1，因此成本最优通常出现在下界附近。
    # 先搜索下界附近的小范围 K；若都失败，再逐步向外扩展。
    candidate_ks: List[int] = []
    for k in range(lb, min(upper_k, lb + 4) + 1):
        candidate_ks.append(k)
    if upper_k not in candidate_ks:
        candidate_ks.append(upper_k)
    mid = (lb + upper_k) // 2
    if mid not in candidate_ks:
        candidate_ks.append(mid)
    candidate_ks = sorted(set(candidate_ks))

    for k in candidate_ks:
        feasible = try_feasible_solution_for_k(k, "min_cost", seed + 90000, ga_pop, ga_gen, attempts_per_k)
        if feasible is not None and (best is None or (feasible.total_cost, feasible.vehicle_count) < (best.total_cost, best.vehicle_count)):
            best = feasible

    if best is None:
        # 回退：再做有限扩展，而不是把整个 [lb, upper_k] 全扫一遍
        for k in range(min(upper_k, lb + 5), upper_k + 1, 2):
            feasible = try_feasible_solution_for_k(k, "min_cost", seed + 120000, ga_pop, ga_gen, attempts_per_k)
            if feasible is not None and (best is None or (feasible.total_cost, feasible.vehicle_count) < (best.total_cost, best.vehicle_count)):
                best = feasible

    if best is None:
        raise RuntimeError("成本最优搜索失败，未找到任何可行混合车型解。")

    best.note = f"min_cost solved, lower_bound={lb}, upper_k={upper_k}, searched={candidate_ks}"
    return best


# ============================================================
# 输出
# ============================================================

def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
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
                p.item_id, p.type_id, p.category,
                p.x, p.y, p.z,
                p.length, p.width, p.height,
                p.weight, p.orientation_id, p.rotation,
                p.truck_id, p.support_by or "", round(p.direct_supported_weight, 6)
            ])


def write_vehicle_summary_csv(path: str, vehicles: List[VehicleResult]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "truck_name", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_count", "loaded_weight_kg", "loaded_volume_cm3", "policy_desc", "vehicle_cost"
        ])
        for v in vehicles:
            truck = TRUCKS[v.truck_name]
            sv, wv, fs = truck_score(truck, v.used_volume, v.used_weight)
            w.writerow([
                v.vehicle_id, v.truck_name,
                round(sv, 6), round(wv, 6), round(fs, 6),
                dict(v.actual_counts), v.item_count,
                round(v.used_weight, 3), v.used_volume,
                v.policy_desc, truck.cost
            ])


def write_overall_summary_csv(path: str, sol21: Optional[SolutionResult], sol22: Optional[SolutionResult]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["problem", "success", "vehicle_count", "total_cost", "truck1_count", "truck2_count", "note"])
        for name, sol in [("问题2.1", sol21), ("问题2.2", sol22)]:
            if sol is None:
                continue
            c1 = sum(1 for v in sol.vehicles if v.truck_name == "车型1")
            c2 = sum(1 for v in sol.vehicles if v.truck_name == "车型2")
            w.writerow([name, sol.success, sol.vehicle_count, sol.total_cost, c1, c2, sol.note])


def save_solution(outdir: str, tag: str, solution: SolutionResult) -> None:
    sol_dir = os.path.join(outdir, tag)
    write_vehicle_summary_csv(os.path.join(sol_dir, f"{tag}_车辆汇总.csv"), solution.vehicles)
    for v in solution.vehicles:
        write_items_csv(os.path.join(sol_dir, f"{v.vehicle_id}_装箱明细.csv"), v.placed)


# ============================================================
# 打印
# ============================================================

def print_solution(solution: SolutionResult, title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(f"success={solution.success}")
    print(f"vehicle_count={solution.vehicle_count}")
    print(f"total_cost={solution.total_cost:.2f}")
    c1 = sum(1 for v in solution.vehicles if v.truck_name == "车型1")
    c2 = sum(1 for v in solution.vehicles if v.truck_name == "车型2")
    print(f"车型1数量={c1}, 车型2数量={c2}")
    if not solution.success:
        print(f"remaining={solution.remaining}")
    print(f"note={solution.note}")

    for v in solution.vehicles:
        truck = TRUCKS[v.truck_name]
        sv, wv, fs = truck_score(truck, v.used_volume, v.used_weight)
        print(
            f"[{v.vehicle_id}] {v.truck_name} | 件数={v.item_count} | "
            f"空间利用率={sv:.4f} | 载重利用率={wv:.4f} | fullness={fs:.4f} | 成本={truck.cost:.0f}"
        )


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题2 混合车型 GCL-3DP 最终版 v4")
    parser.add_argument("--problem", choices=["2.1", "2.2", "all"], default="all", help="选择求解目标")
    parser.add_argument("--outdir", type=str, default="output_problem2_mixed_gcl_3dp", help="输出目录")
    parser.add_argument("--seed", type=int, default=2026, help="随机种子")
    parser.add_argument("--ga-pop", type=int, default=8, help="单车 GA 种群规模")
    parser.add_argument("--ga-gen", type=int, default=4, help="单车 GA 演化代数")
    parser.add_argument("--attempts", type=int, default=3, help="每个 K 或每个阶段的重试次数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    sol21: Optional[SolutionResult] = None
    sol22: Optional[SolutionResult] = None

    if args.problem in ("2.1", "all"):
        sol21 = solve_problem_21_min_vehicle(
            seed=args.seed,
            ga_pop=args.ga_pop,
            ga_gen=args.ga_gen,
            attempts_per_k=args.attempts,
        )
        print_solution(sol21, "问题2.1：总运输车辆最少")
        save_solution(args.outdir, "problem2_1_min_vehicle", sol21)

    if args.problem in ("2.2", "all"):
        sol22 = solve_problem_22_min_cost(
            seed=args.seed + 50000,
            ga_pop=args.ga_pop,
            ga_gen=args.ga_gen,
            attempts_per_k=args.attempts,
        )
        print_solution(sol22, "问题2.2：总运输成本最低")
        save_solution(args.outdir, "problem2_2_min_cost", sol22)

    write_overall_summary_csv(os.path.join(args.outdir, "问题2_总体汇总.csv"), sol21, sol22)
    print(f"\n结果已输出到：{args.outdir}")


if __name__ == "__main__":
    main()
