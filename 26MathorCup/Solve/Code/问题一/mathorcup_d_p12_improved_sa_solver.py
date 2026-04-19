#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2
改进模拟退火（Improved SA）求解代码

思路：
1. 固定车型后，先计算车辆数下界 LB（体积、重量、G3底面积）。
2. 从 K = LB 开始，构造一组“按车分配的货类数量方案” quotas。
3. 外层使用模拟退火（SA）在 quotas 上做扰动：
   - 跨车转移某类货物
   - 两车交换两类货物
   - 对 G3 做定向修复
4. 每次扰动后，使用“稳定单车构造器”快速验证每辆车是否能装：
   - G3 底层规则铺放
   - 其余货物按层/排/列构造
5. 若在当前 K 下找到全部车辆都可装下的方案，则返回；
   否则 K += 1 继续搜索，直到找到可行解。

特点：
- 比“全量单件序列 + SA”稳定得多；
- 比单纯贪心分车更容易降低车辆数；
- 输出每辆车逐件装箱明细和车辆汇总。

说明：
- 这是工程化近似算法，不保证全局最优；
- 重点是：稳定、能跑、结果通常优于纯逐车贪心；
- 保留易碎件 G3 的“可取 6 种姿态，但仅底层单层放置”的约束。
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

    @property
    def density(self) -> float:
        return self.weight / max(1, self.volume)


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

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass
class VehicleResult:
    vehicle_id: str
    placed: List[PlacedCargo]
    target_counts: Dict[str, int]
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int

    @property
    def feasible_full_pack(self) -> bool:
        for t, v in self.target_counts.items():
            if self.actual_counts.get(t, 0) != v:
                return False
        return True


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
TYPE_ORDER_MAIN = ["G4", "G5", "G1", "G2"]


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


ORIENTATIONS: Dict[str, Tuple[Orientation, ...]] = {
    k: generate_orientations(v) for k, v in CARGO_TYPES.items()
}


def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / truck.effective_volume
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def lower_bound_vehicle_count(truck: Truck) -> Tuple[int, int, int]:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    basic = max(
        math.ceil(total_volume / truck.effective_volume),
        math.ceil(total_weight / truck.max_weight),
    )
    g3_best = 0
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            g3_best = max(g3_best, (truck.length // l) * (truck.width // w))
    g3_lb = math.ceil(CARGO_TYPES["G3"].quantity / max(1, g3_best))
    return max(basic, g3_lb), basic, g3_lb


def residual_volume(truck: Truck, counts: Dict[str, int]) -> int:
    return truck.effective_volume - sum(CARGO_TYPES[t].volume * counts.get(t, 0) for t in TYPE_ORDER_ALL)


def residual_weight(truck: Truck, counts: Dict[str, int]) -> float:
    return truck.max_weight - sum(CARGO_TYPES[t].weight * counts.get(t, 0) for t in TYPE_ORDER_ALL)


def counts_total(counts: Dict[str, int]) -> int:
    return sum(counts.get(t, 0) for t in TYPE_ORDER_ALL)


def place_g3_exact(
    truck: Truck,
    target_g3: int,
    vehicle_index: int,
    placed: List[PlacedCargo],
    serial_counter: Counter,
) -> Tuple[int, float, int, int]:
    if target_g3 <= 0:
        return 0, 0.0, 0, 0

    best_plan = None
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h > truck.effective_height:
            continue
        nx = truck.length // l
        if nx <= 0:
            continue
        ny = math.ceil(target_g3 / nx)
        zone_width = ny * w
        if zone_width > truck.width:
            continue
        cap = nx * ny
        waste = cap - target_g3
        cand = (waste, zone_width, ori, nx, ny, cap)
        if best_plan is None or cand < best_plan:
            best_plan = cand

    if best_plan is None:
        return 0, 0.0, 0, 0

    _, zone_width, ori, nx, ny, _ = best_plan
    l, w, h = ori.size

    used_weight = 0.0
    used_volume = 0
    placed_count = 0
    for j in range(ny):
        for i in range(nx):
            if placed_count >= target_g3:
                break
            serial_counter["G3"] += 1
            item_id = f"G3_{vehicle_index:03d}_{serial_counter['G3']:04d}"
            p = PlacedCargo(
                item_id=item_id,
                type_id="G3",
                category="fragile",
                x=i * l,
                y=j * w,
                z=0,
                length=l,
                width=w,
                height=h,
                weight=CARGO_TYPES["G3"].weight,
                orientation_id=ori.orient_id,
                rotation=ori.rotation,
                truck_id=f"{truck.name}_{vehicle_index:03d}",
            )
            placed.append(p)
            used_weight += p.weight
            used_volume += p.volume
            placed_count += 1
    return zone_width, used_weight, used_volume, placed_count


def candidate_layer_types(
    counts: Dict[str, int],
    remaining_height: int,
    truck: Truck,
    main_width: int,
) -> List[Tuple[str, Orientation, int]]:
    cands = []
    for type_id in TYPE_ORDER_MAIN:
        if counts[type_id] <= 0:
            continue
        for ori in ORIENTATIONS[type_id]:
            l, w, h = ori.size
            if h > remaining_height:
                continue
            if l > truck.length or w > main_width:
                continue
            remain_ratio = counts[type_id] / max(1, CARGO_TYPES[type_id].quantity)
            area = (l * w) / max(1, truck.length * main_width)
            height_fit = h / max(1, remaining_height)
            score = 1000 * remain_ratio + 100 * area + 10 * height_fit
            cands.append((type_id, ori, int(score * 1000)))
    cands.sort(key=lambda x: x[2], reverse=True)
    return cands


def fill_one_row(
    truck: Truck,
    counts: Dict[str, int],
    vehicle_index: int,
    z: int,
    y: int,
    row_height: int,
    x_start: int,
    area_length: int,
    serial_counter: Counter,
    layer_height: int,
) -> Tuple[List[PlacedCargo], int, float, int]:
    placed_row: List[PlacedCargo] = []
    x = x_start
    used_weight = 0.0
    used_volume = 0
    row_max_width = 0

    while x < x_start + area_length:
        best = None
        remain_len = x_start + area_length - x
        for type_id in TYPE_ORDER_MAIN:
            if counts[type_id] <= 0:
                continue
            cargo = CARGO_TYPES[type_id]
            for ori in ORIENTATIONS[type_id]:
                l, w, h = ori.size
                if h > layer_height or w > row_height or l > remain_len:
                    continue
                fill_ratio = (l * w) / max(1, remain_len * row_height)
                remain_ratio = counts[type_id] / max(1, cargo.quantity)
                volume_bonus = cargo.volume / 100000.0
                score = 0.60 * fill_ratio + 0.20 * remain_ratio + 0.20 * volume_bonus
                if best is None or score > best[0]:
                    best = (score, type_id, ori)

        if best is None:
            break

        _, type_id, ori = best
        cargo = CARGO_TYPES[type_id]
        l, w, h = ori.size
        serial_counter[type_id] += 1
        item_id = f"{type_id}_{vehicle_index:03d}_{serial_counter[type_id]:04d}"
        p = PlacedCargo(
            item_id=item_id,
            type_id=type_id,
            category=cargo.category,
            x=x,
            y=y,
            z=z,
            length=l,
            width=w,
            height=h,
            weight=cargo.weight,
            orientation_id=ori.orient_id,
            rotation=ori.rotation,
            truck_id=f"{truck.name}_{vehicle_index:03d}",
        )
        placed_row.append(p)
        counts[type_id] -= 1
        used_weight += p.weight
        used_volume += p.volume
        x += l
        row_max_width = max(row_max_width, w)

    return placed_row, row_max_width, used_weight, used_volume


def fill_main_zone_layers(
    truck: Truck,
    counts: Dict[str, int],
    vehicle_index: int,
    g3_zone_width: int,
    placed: List[PlacedCargo],
    used_weight: float,
    used_volume: int,
    serial_counter: Counter,
) -> Tuple[float, int]:
    main_width = truck.width - g3_zone_width
    if main_width <= 0:
        return used_weight, used_volume

    z = 0
    while z < truck.effective_height:
        remaining_height = truck.effective_height - z
        cands = candidate_layer_types(counts, remaining_height, truck, main_width)
        if not cands:
            break
        _, ori0, _ = cands[0]
        layer_height = ori0.size[2]
        if layer_height <= 0 or z + layer_height > truck.effective_height:
            break

        y = g3_zone_width
        layer_placed_any = False
        while y < truck.width:
            remain_width = truck.width - y
            if remain_width <= 0:
                break

            row_cands = []
            for type_id in TYPE_ORDER_MAIN:
                if counts[type_id] <= 0:
                    continue
                for ori in ORIENTATIONS[type_id]:
                    l, w, h = ori.size
                    if h <= layer_height and w <= remain_width and l <= truck.length:
                        row_cands.append((w, type_id, ori))
            if not row_cands:
                break

            row_cands.sort(key=lambda x: x[0], reverse=True)
            row_height = row_cands[0][0]
            row_items, row_used_width, add_w, add_v = fill_one_row(
                truck, counts, vehicle_index, z, y, row_height, 0, truck.length, serial_counter, layer_height
            )
            if not row_items:
                break

            layer_placed_any = True
            placed.extend(row_items)
            used_weight += add_w
            used_volume += add_v
            y += row_used_width if row_used_width > 0 else row_height

            if used_weight >= truck.max_weight - 1e-9:
                return used_weight, used_volume

        if not layer_placed_any:
            break
        z += layer_height
        if used_weight >= truck.max_weight - 1e-9:
            break
    return used_weight, used_volume


def pack_one_vehicle_given_counts(truck: Truck, target_counts: Dict[str, int], vehicle_index: int) -> VehicleResult:
    counts = {t: int(target_counts.get(t, 0)) for t in TYPE_ORDER_ALL}
    placed: List[PlacedCargo] = []
    used_weight = 0.0
    used_volume = 0
    serial_counter = Counter()

    g3_zone_width, add_w, add_v, actual_g3 = place_g3_exact(
        truck, counts["G3"], vehicle_index, placed, serial_counter
    )
    used_weight += add_w
    used_volume += add_v
    counts["G3"] -= actual_g3

    used_weight, used_volume = fill_main_zone_layers(
        truck, counts, vehicle_index, g3_zone_width, placed, used_weight, used_volume, serial_counter
    )

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        target_counts={t: int(target_counts.get(t, 0)) for t in TYPE_ORDER_ALL},
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
    )


def initial_quota_split_sa(truck: Truck, K: int) -> List[Dict[str, int]]:
    quotas = [{t: 0 for t in TYPE_ORDER_ALL} for _ in range(K)]

    g3_total = CARGO_TYPES["G3"].quantity
    per = g3_total // K
    rem = g3_total % K
    for i in range(K):
        quotas[i]["G3"] = per + (1 if i < rem else 0)

    for t in ["G4", "G5"]:
        qty = CARGO_TYPES[t].quantity
        i = 0
        while qty > 0:
            idx = i % K
            c = CARGO_TYPES[t]
            if residual_volume(truck, quotas[idx]) >= c.volume and residual_weight(truck, quotas[idx]) >= c.weight:
                quotas[idx][t] += 1
                qty -= 1
            i += 1

    for t in ["G1", "G2"]:
        qty = CARGO_TYPES[t].quantity
        c = CARGO_TYPES[t]
        while qty > 0:
            candidates = []
            for i in range(K):
                rv = residual_volume(truck, quotas[i])
                rw = residual_weight(truck, quotas[i])
                if rv >= c.volume and rw >= c.weight:
                    candidates.append((rv / truck.effective_volume + rw / truck.max_weight, i))
            if not candidates:
                break
            candidates.sort(reverse=True)
            best_i = candidates[0][1]
            quotas[best_i][t] += 1
            qty -= 1
    return quotas


def revalidate_all(truck: Truck, quotas: List[Dict[str, int]]) -> List[VehicleResult]:
    return [pack_one_vehicle_given_counts(truck, q, i + 1) for i, q in enumerate(quotas)]


def collect_missing(plans: List[VehicleResult]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER_ALL}
    for vp in plans:
        for t in TYPE_ORDER_ALL:
            missing[t] += max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))
    return missing


def solution_energy(truck: Truck, quotas: List[Dict[str, int]], plans: List[VehicleResult], K: int) -> float:
    missing = collect_missing(plans)
    miss_cnt = sum(missing.values())
    miss_weighted = 25 * missing["G3"] + 12 * missing["G4"] + 10 * missing["G5"] + 4 * missing["G1"] + 3 * missing["G2"]
    used_vol = sum(vp.used_volume for vp in plans)
    used_w = sum(vp.used_weight for vp in plans)
    avg_sv = used_vol / (K * truck.effective_volume)
    avg_wv = used_w / (K * truck.max_weight)
    g3_spread = sum(1 for q in quotas if q["G3"] > 0)
    return 1_000_000 * miss_cnt + 10_000 * miss_weighted + 500 * g3_spread + 100 * K - 200 * avg_sv - 80 * avg_wv


def all_feasible(plans: List[VehicleResult]) -> bool:
    return all(vp.feasible_full_pack for vp in plans)


def move_one_between_trucks(quotas: List[Dict[str, int]], truck: Truck, rng: random.Random) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    donors = [i for i, q in enumerate(child) if counts_total(q) > 0]
    if not donors:
        return child
    d = rng.choice(donors)
    choices = [x for x in TYPE_ORDER_ALL if child[d][x] > 0]
    if not choices:
        return child
    t = rng.choice(choices)
    c = CARGO_TYPES[t]
    receivers = list(range(len(child)))
    rng.shuffle(receivers)
    for r in receivers:
        if r == d:
            continue
        if residual_volume(truck, child[r]) >= c.volume and residual_weight(truck, child[r]) >= c.weight:
            child[d][t] -= 1
            child[r][t] += 1
            return child
    return child


def swap_two_trucks(quotas: List[Dict[str, int]], truck: Truck, rng: random.Random) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    if len(child) < 2:
        return child
    a, b = rng.sample(range(len(child)), 2)
    ta_choices = [t for t in TYPE_ORDER_ALL if child[a][t] > 0]
    tb_choices = [t for t in TYPE_ORDER_ALL if child[b][t] > 0]
    if not ta_choices or not tb_choices:
        return child
    ta = rng.choice(ta_choices)
    tb = rng.choice(tb_choices)
    if ta == tb:
        return child
    child[a][ta] -= 1
    child[b][tb] -= 1
    child[a][tb] += 1
    child[b][ta] += 1
    for i in (a, b):
        if residual_volume(truck, child[i]) < -1e-9 or residual_weight(truck, child[i]) < -1e-9:
            return [q.copy() for q in quotas]
    return child


def targeted_g3_rebalance(quotas: List[Dict[str, int]], plans: List[VehicleResult], truck: Truck) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    deficits = []
    slackers = []
    for i, vp in enumerate(plans):
        target = vp.target_counts.get("G3", 0)
        actual = vp.actual_counts.get("G3", 0)
        deficit = target - actual
        if deficit > 0:
            deficits.append((deficit, i))
        else:
            g3_actual = actual
            best_floor = 0
            for ori in ORIENTATIONS["G3"]:
                l, w, h = ori.size
                if h <= truck.effective_height:
                    best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
            slack = max(0, best_floor - g3_actual)
            if slack > 0:
                slackers.append((slack, i))

    deficits.sort(reverse=True)
    slackers.sort(reverse=True)
    for deficit, d in deficits:
        for idx, (slack, s) in enumerate(slackers):
            if s == d or slack <= 0:
                continue
            move = min(deficit, slack, child[d]["G3"])
            if move <= 0:
                continue
            child[d]["G3"] -= move
            child[s]["G3"] += move
            slackers[idx] = (slack - move, s)
            break
    return child


def make_neighbor(quotas: List[Dict[str, int]], plans: List[VehicleResult], truck: Truck, rng: random.Random) -> List[Dict[str, int]]:
    op = rng.choice(["move", "swap", "g3_rebalance", "move", "move"])
    if op == "move":
        return move_one_between_trucks(quotas, truck, rng)
    if op == "swap":
        return swap_two_trucks(quotas, truck, rng)
    return targeted_g3_rebalance(quotas, plans, truck)


def simulated_annealing_for_fixed_k(
    truck: Truck,
    K: int,
    seed: int = 2026,
    init_temp: float = 120.0,
    final_temp: float = 1.0,
    iterations: int = 120,
) -> Tuple[List[Dict[str, int]], List[VehicleResult], float]:
    rng = random.Random(seed + K)
    current = initial_quota_split_sa(truck, K)
    current_plans = revalidate_all(truck, current)
    current_energy = solution_energy(truck, current, current_plans, K)

    best = [q.copy() for q in current]
    best_plans = current_plans
    best_energy = current_energy

    print(f"[{truck.name}] SA 初始能量 = {current_energy:.2f}", flush=True)

    for it in range(1, iterations + 1):
        ratio = (it - 1) / max(1, iterations - 1)
        temp = init_temp * ((final_temp / init_temp) ** ratio)

        candidate = make_neighbor(current, current_plans, truck, rng)
        candidate_plans = revalidate_all(truck, candidate)
        candidate_energy = solution_energy(truck, candidate, candidate_plans, K)

        delta = candidate_energy - current_energy
        accept = False
        if delta <= 0:
            accept = True
        else:
            prob = math.exp(-delta / max(temp, 1e-9))
            if rng.random() < prob:
                accept = True

        if accept:
            current = candidate
            current_plans = candidate_plans
            current_energy = candidate_energy

        if candidate_energy < best_energy:
            best = [q.copy() for q in candidate]
            best_plans = candidate_plans
            best_energy = candidate_energy

        if it == 1 or it % 10 == 0 or it == iterations:
            missing = collect_missing(best_plans)
            print(
                f"[{truck.name}] SA iter={it:03d}/{iterations} temp={temp:.2f} "
                f"bestE={best_energy:.2f} missing={missing}",
                flush=True
            )
        if all_feasible(best_plans):
            break

    return best, best_plans, best_energy


def solve_problem_12_improved_sa(truck: Truck, max_extra_k: int = 10, sa_iterations: int = 120) -> Tuple[int, List[VehicleResult], Dict[str, object]]:
    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)

    best_global = None
    for extra in range(max_extra_k + 1):
        K = lb + extra
        print(f"[{truck.name}] 正在尝试 K = {K} ...", flush=True)
        quotas, plans, energy = simulated_annealing_for_fixed_k(truck, K, iterations=sa_iterations)
        ok = all_feasible(plans)
        print(f"[{truck.name}] K = {K} 可行性结果: {ok}", flush=True)

        if best_global is None or energy < best_global[0]:
            best_global = (energy, K, quotas, plans)

        if ok:
            avg_sv = sum(vp.used_volume for vp in plans) / (K * truck.effective_volume)
            avg_wv = sum(vp.used_weight for vp in plans) / (K * truck.max_weight)
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

    assert best_global is not None
    _, K, _, plans = best_global
    avg_sv = sum(vp.used_volume for vp in plans) / (K * truck.effective_volume)
    avg_wv = sum(vp.used_weight for vp in plans) / (K * truck.max_weight)
    summary = {
        "truck": truck.name,
        "vehicle_count": K,
        "lower_bound": lb,
        "lower_bound_basic": basic_lb,
        "lower_bound_g3": g3_lb,
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "total_cost": round(K * truck.cost, 2),
        "all_loaded": False,
        "missing": collect_missing(plans),
    }
    return K, plans, summary


def write_vehicle_summary_csv(path: str, plans: List[VehicleResult], truck: Truck) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "target_counts", "actual_counts", "loaded_weight_kg", "loaded_volume_cm3", "feasible_full_pack"
        ])
        for vp in plans:
            sv, wv, fs = truck_score(truck, vp.used_volume, vp.used_weight)
            w.writerow([
                vp.vehicle_id, round(sv, 6), round(wv, 6), round(fs, 6),
                vp.target_counts, vp.actual_counts, round(vp.used_weight, 3), vp.used_volume, vp.feasible_full_pack
            ])


def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight", "orientation_id", "rotation", "truck_id"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z, p.length, p.width, p.height,
                p.weight, p.orientation_id, p.rotation, p.truck_id
            ])


def solve_for_truck(truck: Truck, outdir: str, max_extra_k: int, sa_iterations: int) -> Dict[str, object]:
    K, plans, summary = solve_problem_12_improved_sa(truck, max_extra_k=max_extra_k, sa_iterations=sa_iterations)
    truck_dir = os.path.join(outdir, truck.name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck.name}_车辆汇总.csv"), plans, truck)
    for vp in plans:
        write_items_csv(os.path.join(truck_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp.placed)
    summary["output_dir"] = truck_dir
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 改进模拟退火算法")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="output_p12_improved_sa", help="输出目录")
    parser.add_argument("--max-extra-k", type=int, default=10, help="相对下界最多额外搜索的车辆数")
    parser.add_argument("--sa-iterations", type=int, default=120, help="每个 K 下的 SA 迭代次数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for name in truck_list:
        truck = TRUCKS[name]
        print("\\n" + "=" * 60)
        print(f"开始求解问题1.2：{truck.name}")
        print("=" * 60)
        summary = solve_for_truck(truck, args.outdir, args.max_extra_k, args.sa_iterations)
        print(summary)


if __name__ == "__main__":
    main()
