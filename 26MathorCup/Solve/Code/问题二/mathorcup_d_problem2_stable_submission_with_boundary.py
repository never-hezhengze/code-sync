#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题2 稳定提交版（能跑完优先）

核心思想：
1. 问题2不再沿用问题1.2的“全流程GA精细装箱”作为主循环，避免在3000件规模下计算过慢；
2. 采用“混合车型快速构造 + 少量局部改良”的稳定启发式框架；
3. 继续保留与问题1一致的主要物理约束口径：
   - G3上方禁放；
   - 非底板放置必须完整落在单个支撑面上；
   - 易碎件只能放底板或G1/G2顶面；
   - 直接承压不超过 500 kg/m^2；
   - 定向件保持唯一姿态。
4. 提供两个目标：
   - 问题2.1：总运输车辆最少；
   - 问题2.2：总运输成本最低。

说明：
- 该版本优先保证“可运行、可输出、结果稳定”；
- 属于工程化近优算法，不是严格全局最优；
- 相比前面问题1.2的GA版，本版更适合问题2的大规模混合车型求解。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# =========================================================
# 基础数据
# =========================================================

RANDOM_SEED = 2026
MAX_SPACES_TO_CHECK = 18          # 稳定版：严格限制候选空间数
MIN_SPACE_VOLUME = 18000
MAX_STRATEGIES_PER_TRUCK = 3      # 每辆车最多试3种策略
MAX_REASSIGN_TRIES = 4            # 局部改良最多尝试删除4辆较差车辆


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
TYPE_ORDER_STD = ["G1", "G2", "G4", "G5", "G3"]
TYPE_ORDER_DIR = ["G4", "G5", "G1", "G2", "G3"]
TYPE_ORDER_G3 = ["G3", "G1", "G2", "G4", "G5"]
TYPE_ORDER_MIX = ["G4", "G1", "G5", "G2", "G3"]


# =========================================================
# 姿态
# =========================================================

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
    if cargo.oriented:
        dims = [(l, w, h, "LWH")]

    out = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            out.append(Orientation(len(out) + 1, key, name))
    return tuple(out)


ORIENTATIONS = {k: generate_orientations(v) for k, v in CARGO_TYPES.items()}


# =========================================================
# 数据结构
# =========================================================

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
    top_area_m2_cache: float = 0.0

    def __post_init__(self):
        self.top_area_m2_cache = (self.length * self.width) / 10000.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return self.top_area_m2_cache


@dataclass
class VehiclePlan:
    vehicle_id: str
    truck_name: str
    placed: List[PlacedCargo]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int
    strategy: str

    @property
    def item_count(self) -> int:
        return sum(self.actual_counts.values())

    @property
    def truck(self) -> Truck:
        return TRUCKS[self.truck_name]

    @property
    def fullness_score(self) -> float:
        sv = self.used_volume / max(1, self.truck.effective_volume)
        wv = self.used_weight / max(1.0, self.truck.max_weight)
        return 0.72 * sv + 0.28 * wv


# =========================================================
# 工具函数
# =========================================================

def total_remaining_items(remaining: Dict[str, int]) -> int:
    return sum(remaining.values())


def all_remaining_zero(remaining: Dict[str, int]) -> bool:
    return total_remaining_items(remaining) == 0


def clone_remaining(remaining: Dict[str, int]) -> Dict[str, int]:
    return {k: int(v) for k, v in remaining.items()}


def initial_remaining() -> Dict[str, int]:
    return {k: v.quantity for k, v in CARGO_TYPES.items()}


def subtract_plan_from_remaining(remaining: Dict[str, int], plan: VehiclePlan) -> None:
    for t, c in plan.actual_counts.items():
        remaining[t] -= c


def add_counts_to_remaining(remaining: Dict[str, int], counts: Dict[str, int]) -> None:
    for t, c in counts.items():
        remaining[t] += c


def space_volume(sp: Dict[str, int]) -> int:
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces: List[Dict[str, int]]) -> List[Dict[str, int]]:
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (s["z"], -space_volume(s), s["y"], s["x"]))
    return spaces[:MAX_SPACES_TO_CHECK]


def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / max(1, truck.effective_volume)
    wv = used_weight / max(1.0, truck.max_weight)
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def cheap_capacity_estimate(truck: Truck) -> int:
    # 稳定粗上界：按G1/G2平均件的几何和载重能力估计
    avg_vol = (CARGO_TYPES["G1"].volume + CARGO_TYPES["G2"].volume) / 2
    avg_wt = (CARGO_TYPES["G1"].weight + CARGO_TYPES["G2"].weight) / 2
    by_v = int(truck.effective_volume // avg_vol)
    by_w = int(truck.max_weight // avg_wt)
    return max(1, min(by_v, by_w))


# =========================================================
# 轻量货车类（物理约束版）
# =========================================================

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

            # 完整落在单一支撑物顶面内
            if l > support.length or w > support.width:
                return False

            # 易碎件不能作为支撑物
            if support.category == "fragile":
                return False

            # G3只能放底板或G1/G2顶面
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
            rotation=ori.rotation,
            orientation_id=ori.orient_id,
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
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": sp["w"],
            "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
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
        }
        new_spaces = [right, front]

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
            }
            new_spaces.append(upper)

        self.spaces.pop(sp_idx)
        self.spaces.extend(new_spaces)
        self.spaces = sort_spaces(self.spaces)


# =========================================================
# 快速单车装箱策略
# =========================================================

def build_type_order(strategy: str) -> List[str]:
    if strategy == "std_first":
        return TYPE_ORDER_STD
    if strategy == "dir_first":
        return TYPE_ORDER_DIR
    if strategy == "g3_first":
        return TYPE_ORDER_G3
    return TYPE_ORDER_MIX


def evaluate_candidate(
    type_id: str,
    ori: Orientation,
    sp: Dict[str, int],
    remaining: Dict[str, int],
    truck_obj: FastTruck,
    objective: str,
) -> Optional[float]:
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if remaining[type_id] <= 0:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight + 1e-9:
        return None
    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    remain_ratio = remaining[type_id] / max(1, CARGO_TYPES[type_id].quantity)

    score = 2.1 * fill_ratio + 0.75 * bottom_bonus + 0.35 * remain_ratio

    if type_id == "G3":
        # G3适度优先，但不能过高，否则容易导致碎空间
        score += 0.08
    if type_id in ("G4", "G5"):
        score += 0.05

    # 成本目标下，稍微偏向车型1的紧凑高值填充，减少大车滥用
    if objective == "min_cost":
        volume_ratio = cargo.volume / max(1, truck_obj.truck.effective_volume)
        score += 0.25 * volume_ratio

    return score


def place_one_best(truck_obj: FastTruck, remaining: Dict[str, int], type_order: List[str], objective: str) -> bool:
    best = None

    # 只看前若干候选空间
    num_spaces = min(8, len(truck_obj.spaces))
    for sp_idx in range(num_spaces):
        sp = truck_obj.spaces[sp_idx]
        # 只遍历有限类型顺序
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = evaluate_candidate(type_id, ori, sp, remaining, truck_obj, objective)
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


def pack_single_vehicle_greedy(
    truck: Truck,
    remaining_input: Dict[str, int],
    vehicle_idx: int,
    strategy: str,
    objective: str,
) -> VehiclePlan:
    remaining = clone_remaining(remaining_input)
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)
    type_order = build_type_order(strategy)

    while True:
        ok = place_one_best(truck_obj, remaining, type_order, objective)
        if not ok:
            break

    return VehiclePlan(
        vehicle_id=vehicle_id,
        truck_name=truck.name,
        placed=truck_obj.placed,
        actual_counts=dict(truck_obj.actual_counts),
        used_weight=truck_obj.used_weight,
        used_volume=truck_obj.used_volume,
        strategy=strategy,
    )


# =========================================================
# 混合车型单车选择
# =========================================================

def strategy_pool(objective: str, remaining: Dict[str, int], truck: Truck) -> List[str]:
    # 稳定版：最多3种策略
    g3_ratio = remaining.get("G3", 0) / max(1, total_remaining_items(remaining))
    if objective == "min_vehicles":
        if truck.name == "车型2":
            pool = ["dir_first", "std_first", "mixed"]
        else:
            pool = ["std_first", "mixed", "dir_first"]
    else:
        pool = ["std_first", "mixed", "dir_first"] if truck.name == "车型1" else ["mixed", "dir_first", "std_first"]
    if g3_ratio > 0.15 and "g3_first" not in pool:
        pool[-1] = "g3_first"
    return pool[:MAX_STRATEGIES_PER_TRUCK]


def vehicle_objective_value(plan: VehiclePlan, objective: str) -> Tuple[float, float, float]:
    # 返回用于比较的三元组，越大越好
    if plan.item_count <= 0:
        return (-1e18, -1e18, -1e18)
    sv, wv, fs = truck_score(plan.truck, plan.used_volume, plan.used_weight)
    if objective == "min_vehicles":
        return (plan.item_count, fs, -plan.truck.cost)
    # min_cost: 更看重“单位成本带来的装载量/满载率”
    efficiency = (0.7 * sv + 0.3 * wv) / max(1e-9, plan.truck.cost)
    return (plan.item_count / max(1.0, plan.truck.cost), efficiency, fs)


def choose_best_vehicle_plan(remaining: Dict[str, int], vehicle_idx: int, objective: str) -> VehiclePlan:
    total_items = total_remaining_items(remaining)

    # 初步车型倾向：问题2.1偏向大车，问题2.2同时考虑成本
    truck_candidates: List[Truck]
    if objective == "min_vehicles":
        truck_candidates = [TRUCKS["车型2"], TRUCKS["车型1"]]
    else:
        # 问题2.2同时试两种车型，但优先小车
        truck_candidates = [TRUCKS["车型1"], TRUCKS["车型2"]]

    # 当剩余已很少，优先尝试小车，避免尾车过大
    if total_items < 120:
        truck_candidates = [TRUCKS["车型1"], TRUCKS["车型2"]]

    best_plan = None
    best_key = None

    for truck in truck_candidates:
        for strategy in strategy_pool(objective, remaining, truck):
            plan = pack_single_vehicle_greedy(truck, remaining, vehicle_idx, strategy, objective)
            key = vehicle_objective_value(plan, objective)
            if best_key is None or key > best_key:
                best_key = key
                best_plan = plan

        # 问题2.1中若车型2已经装得显著更多，可提前停止，省时
        if objective == "min_vehicles" and truck.name == "车型2" and best_plan is not None:
            if best_plan.item_count >= 130:
                break

    assert best_plan is not None
    return best_plan


# =========================================================
# 构造完整方案
# =========================================================

def build_solution_mixed(objective: str, seed: int = RANDOM_SEED, verbose: bool = True) -> List[VehiclePlan]:
    random.seed(seed)
    remaining = initial_remaining()
    vehicles: List[VehiclePlan] = []
    vehicle_idx = 1

    while not all_remaining_zero(remaining):
        if verbose:
            print(f"[初始构造] 第 {vehicle_idx} 辆车，剩余件数={total_remaining_items(remaining)}")
        plan = choose_best_vehicle_plan(remaining, vehicle_idx, objective)
        if plan.item_count <= 0:
            raise RuntimeError("构造失败：某一步未能装入任何货物，请检查策略或约束设置。")
        subtract_plan_from_remaining(remaining, plan)
        vehicles.append(plan)
        vehicle_idx += 1

    return vehicles


def build_pure_solution(truck_name: str, objective: str, seed: int = RANDOM_SEED, verbose: bool = True) -> List[VehiclePlan]:
    """
    基于问题1.2“只考虑一种车型”的思路，构造纯车型方案。
    该结果在问题2中作为决策边界：
    - 对问题2.1：给出单车型车辆数边界；
    - 对问题2.2：给出单车型总成本边界。
    """
    random.seed(seed)
    remaining = initial_remaining()
    vehicles: List[VehiclePlan] = []
    vehicle_idx = 1
    truck = TRUCKS[truck_name]

    while not all_remaining_zero(remaining):
        if verbose:
            print(f"[单车型边界-{truck_name}] 第 {vehicle_idx} 辆车，剩余件数={total_remaining_items(remaining)}")
        plan = build_plan_for_specific_truck(truck, remaining, vehicle_idx, objective)
        if plan.item_count <= 0:
            raise RuntimeError(f"单车型边界构造失败：{truck_name} 第 {vehicle_idx} 辆车未装入货物。")
        subtract_plan_from_remaining(remaining, plan)
        vehicles.append(plan)
        vehicle_idx += 1

    return vehicles


def solution_cmp_key(vehicles: List[VehiclePlan], objective: str) -> Tuple[float, float, float]:
    """
    返回最终解比较键。
    - 2.1: 先比车辆数，再比总成本，再比平均空间利用率
    - 2.2: 先比总成本，再比车辆数，再比平均空间利用率
    """
    if objective == "min_vehicles":
        return (len(vehicles), total_cost(vehicles), -average_space_util(vehicles))
    return (total_cost(vehicles), len(vehicles), -average_space_util(vehicles))


def pick_best_solution(candidates: List[List[VehiclePlan]], objective: str) -> List[VehiclePlan]:
    return min(candidates, key=lambda s: solution_cmp_key(s, objective))

# =========================================================
# 少量局部改良：删除若干利用率最低车辆并尝试重分配
# =========================================================

def merge_counts_from_removed(removed_plans: List[VehiclePlan]) -> Dict[str, int]:
    cnt = {t: 0 for t in TYPE_ORDER_ALL}
    for plan in removed_plans:
        for t, c in plan.actual_counts.items():
            cnt[t] += c
    return cnt


def build_plan_for_specific_truck(
    truck: Truck,
    remaining: Dict[str, int],
    vehicle_idx: int,
    objective: str,
) -> VehiclePlan:
    best_plan = None
    best_key = None
    for strategy in strategy_pool(objective, remaining, truck):
        plan = pack_single_vehicle_greedy(truck, remaining, vehicle_idx, strategy, objective)
        key = vehicle_objective_value(plan, objective)
        if best_key is None or key > best_key:
            best_key = key
            best_plan = plan
    assert best_plan is not None
    return best_plan


def try_remove_and_rebuild_once(vehicles: List[VehiclePlan], objective: str, remove_idx: int) -> Optional[List[VehiclePlan]]:
    base = [v for i, v in enumerate(vehicles) if i != remove_idx]
    removed = [vehicles[remove_idx]]
    need = merge_counts_from_removed(removed)

    # 尝试先在尾部追加1辆更合适的车，如果仍不足，再判失败
    if total_remaining_items(need) == 0:
        return base

    # 若目标是最少车辆，删除1辆后最多允许用0辆补回；若无法补入已有方案，则失败
    # 为保证稳定性，这里采用“整体重构最后若干车”的简洁做法：
    pivot = max(0, len(base) - 3)
    fixed = base[:pivot]
    tail = base[pivot:]
    need_tail = merge_counts_from_removed(tail)
    for t, c in need.items():
        need_tail[t] += c

    rebuilt: List[VehiclePlan] = []
    remaining = clone_remaining(need_tail)
    vehicle_idx = len(fixed) + 1

    # 仅允许用与原tail同数目的车辆重建；若重建失败则认为删除不可行
    while not all_remaining_zero(remaining) and len(rebuilt) < len(tail):
        plan = choose_best_vehicle_plan(remaining, vehicle_idx, objective)
        if plan.item_count <= 0:
            return None
        subtract_plan_from_remaining(remaining, plan)
        rebuilt.append(plan)
        vehicle_idx += 1

    if not all_remaining_zero(remaining):
        return None

    return fixed + rebuilt


def local_improve_min_vehicles(vehicles: List[VehiclePlan], verbose: bool = True) -> List[VehiclePlan]:
    cur = vehicles[:]
    # 删除若干最差车辆试试
    ranked = sorted(range(len(cur)), key=lambda i: (cur[i].fullness_score, cur[i].item_count))
    tried = 0
    improved = True
    while improved and tried < MAX_REASSIGN_TRIES:
        improved = False
        for idx in ranked[:MAX_REASSIGN_TRIES]:
            if idx >= len(cur):
                continue
            cand = try_remove_and_rebuild_once(cur, "min_vehicles", idx)
            if cand is not None and len(cand) < len(cur):
                cur = cand
                improved = True
                if verbose:
                    print(f"[局部改良-2.1] 成功删除1辆车，当前车辆数={len(cur)}")
                break
        tried += 1
    return cur


def local_improve_min_cost(vehicles: List[VehiclePlan], verbose: bool = True) -> List[VehiclePlan]:
    # 尝试把尾部大车改成若干小车或更省成本的组合，但不做复杂搜索
    # 稳定版：重新用min_cost目标整体重构一遍，与当前解比较，取成本更小者。
    alt = build_solution_mixed("min_cost", seed=RANDOM_SEED + 77, verbose=False)
    if total_cost(alt) < total_cost(vehicles):
        if verbose:
            print(f"[局部改良-2.2] 找到更低成本方案：{total_cost(vehicles):.2f} -> {total_cost(alt):.2f}")
        return alt
    return vehicles


# =========================================================
# 目标函数与汇总
# =========================================================

def total_cost(vehicles: List[VehiclePlan]) -> float:
    return sum(v.truck.cost for v in vehicles)


def count_by_truck_type(vehicles: List[VehiclePlan]) -> Dict[str, int]:
    cnt = Counter(v.truck_name for v in vehicles)
    return {"车型1": cnt.get("车型1", 0), "车型2": cnt.get("车型2", 0)}


def average_space_util(vehicles: List[VehiclePlan]) -> float:
    if not vehicles:
        return 0.0
    vals = [v.used_volume / max(1, v.truck.effective_volume) for v in vehicles]
    return sum(vals) / len(vals)


def average_weight_util(vehicles: List[VehiclePlan]) -> float:
    if not vehicles:
        return 0.0
    vals = [v.used_weight / max(1.0, v.truck.max_weight) for v in vehicles]
    return sum(vals) / len(vals)


# =========================================================
# 问题2.1 与 问题2.2
# =========================================================

def solve_problem_21_min_vehicle(seed: int = RANDOM_SEED, verbose: bool = True) -> List[VehiclePlan]:
    # 先计算“只考虑一种车型”的两个边界解，作为问题2.1的决策边界
    pure1 = build_pure_solution("车型1", "min_vehicles", seed=seed + 11, verbose=False)
    pure2 = build_pure_solution("车型2", "min_vehicles", seed=seed + 22, verbose=False)
    boundary = pick_best_solution([pure1, pure2], "min_vehicles")

    if verbose:
        print(f"[问题2.1] 单车型边界：车型1={len(pure1)}辆，车型2={len(pure2)}辆，当前边界={len(boundary)}辆")

    mixed = build_solution_mixed("min_vehicles", seed=seed, verbose=verbose)
    if verbose:
        print(f"[问题2.1] 混合车型初始车辆数={len(mixed)}")
    mixed = local_improve_min_vehicles(mixed, verbose=verbose)

    # 最终解在“混合方案”和“单车型边界”之间择优
    best = pick_best_solution([mixed, boundary], "min_vehicles")

    if verbose:
        boundary_source = "车型1" if boundary is pure1 else "车型2"
        final_source = "混合车型方案" if best is mixed else f"单车型边界方案（{boundary_source}）"
        print(f"[问题2.1] 最终采用：{final_source}，车辆数={len(best)}，总成本={total_cost(best):.2f}")

    return best


def solve_problem_22_min_cost(seed: int = RANDOM_SEED + 1, verbose: bool = True) -> List[VehiclePlan]:
    # 引入问题1.2中“单车型”结果作为决策边界
    pure1 = build_pure_solution("车型1", "min_cost", seed=seed + 11, verbose=False)
    pure2 = build_pure_solution("车型2", "min_cost", seed=seed + 22, verbose=False)
    boundary = pick_best_solution([pure1, pure2], "min_cost")

    if verbose:
        print(f"[问题2.2] 单车型边界：车型1成本={total_cost(pure1):.2f}，车型2成本={total_cost(pure2):.2f}，当前边界成本={total_cost(boundary):.2f}")

    mixed = build_solution_mixed("min_cost", seed=seed, verbose=verbose)
    mixed = local_improve_min_cost(mixed, verbose=verbose)

    best = pick_best_solution([mixed, pure1, pure2], "min_cost")
    if verbose:
        if best is mixed:
            final_source = "混合车型方案"
        elif best is pure1:
            final_source = "单车型边界方案（车型1）"
        else:
            final_source = "单车型边界方案（车型2）"
        print(f"[问题2.2] 最终采用：{final_source}，总成本={total_cost(best):.2f}，车辆数={len(best)}")
    return best


# =========================================================
# 输出
# =========================================================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_vehicle_summary_csv(path: str, vehicles: List[VehiclePlan], problem_name: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "problem", "vehicle_id", "truck_name", "strategy", "item_count",
            "used_weight", "max_weight", "weight_util",
            "used_volume", "effective_volume", "space_util", "fullness_score", "cost"
        ])
        for v in vehicles:
            sv, wv, fs = truck_score(v.truck, v.used_volume, v.used_weight)
            writer.writerow([
                problem_name,
                v.vehicle_id,
                v.truck_name,
                v.strategy,
                v.item_count,
                f"{v.used_weight:.2f}",
                f"{v.truck.max_weight:.2f}",
                f"{wv:.6f}",
                v.used_volume,
                v.truck.effective_volume,
                f"{sv:.6f}",
                f"{fs:.6f}",
                f"{v.truck.cost:.2f}",
            ])


def write_vehicle_detail_csv(path: str, vehicles: List[VehiclePlan], problem_name: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "problem", "vehicle_id", "truck_name", "item_id", "type_id", "category",
            "x", "y", "z", "length", "width", "height", "weight",
            "rotation", "orientation_id", "support_by"
        ])
        for v in vehicles:
            for p in v.placed:
                writer.writerow([
                    problem_name,
                    v.vehicle_id,
                    v.truck_name,
                    p.item_id,
                    p.type_id,
                    p.category,
                    p.x, p.y, p.z,
                    p.length, p.width, p.height,
                    f"{p.weight:.2f}",
                    p.rotation,
                    p.orientation_id,
                    p.support_by or "",
                ])


def write_overall_summary_csv(path: str, sol21: Optional[List[VehiclePlan]], sol22: Optional[List[VehiclePlan]]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "problem", "vehicle_count", "truck1_count", "truck2_count",
            "total_cost", "avg_space_util", "avg_weight_util"
        ])
        if sol21 is not None:
            c = count_by_truck_type(sol21)
            writer.writerow([
                "2.1",
                len(sol21),
                c["车型1"],
                c["车型2"],
                f"{total_cost(sol21):.2f}",
                f"{average_space_util(sol21):.6f}",
                f"{average_weight_util(sol21):.6f}",
            ])
        if sol22 is not None:
            c = count_by_truck_type(sol22)
            writer.writerow([
                "2.2",
                len(sol22),
                c["车型1"],
                c["车型2"],
                f"{total_cost(sol22):.2f}",
                f"{average_space_util(sol22):.6f}",
                f"{average_weight_util(sol22):.6f}",
            ])


def print_solution_brief(title: str, vehicles: List[VehiclePlan]) -> None:
    c = count_by_truck_type(vehicles)
    print("=" * 70)
    print(title)
    print(f"车辆数：{len(vehicles)}")
    print(f"车型1数量：{c['车型1']}  |  车型2数量：{c['车型2']}")
    print(f"总成本：{total_cost(vehicles):.2f} 元")
    print(f"平均空间利用率：{average_space_util(vehicles):.4%}")
    print(f"平均载重利用率：{average_weight_util(vehicles):.4%}")
    print("=" * 70)


# =========================================================
# main
# =========================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题2 稳定提交版")
    parser.add_argument("--problem", choices=["2.1", "2.2", "all"], default="all")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--output-dir", type=str, default="output_problem2_stable")
    args = parser.parse_args()

    ensure_dir(args.output_dir)

    sol21: Optional[List[VehiclePlan]] = None
    sol22: Optional[List[VehiclePlan]] = None

    if args.problem in ("2.1", "all"):
        sol21 = solve_problem_21_min_vehicle(seed=args.seed, verbose=True)
        print_solution_brief("问题2.1：总运输车辆最少", sol21)
        write_vehicle_summary_csv(os.path.join(args.output_dir, "problem2_1_vehicle_summary.csv"), sol21, "2.1")
        write_vehicle_detail_csv(os.path.join(args.output_dir, "problem2_1_vehicle_detail.csv"), sol21, "2.1")

    if args.problem in ("2.2", "all"):
        sol22 = solve_problem_22_min_cost(seed=args.seed + 1, verbose=True)
        print_solution_brief("问题2.2：总运输成本最低", sol22)
        write_vehicle_summary_csv(os.path.join(args.output_dir, "problem2_2_vehicle_summary.csv"), sol22, "2.2")
        write_vehicle_detail_csv(os.path.join(args.output_dir, "problem2_2_vehicle_detail.csv"), sol22, "2.2")

    write_overall_summary_csv(os.path.join(args.output_dir, "problem2_overall_summary.csv"), sol21, sol22)
    print(f"结果已输出到目录：{args.output_dir}")


if __name__ == "__main__":
    main()
