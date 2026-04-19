
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2 终极版
Hybrid SA + LNS solver

思路：
1. 先用稳定构造器逐车贪心得到一组可行解（一定能装完）；
2. 将可行解转成每辆车的货类配额 quotas；
3. 从 greedy_K 开始，尝试压缩为 K-1, K-2, ...：
   - 先把尾车货物重新分配到前 K 辆，得到初始压缩解；
   - 再用 SA + LNS 在 quotas 上优化；
   - 每次优化后用稳定单车装箱器快速验证；
4. 若当前 K 可行，则继续压缩；否则回退到上一个可行 K。

特点：
- 比“从下界盲搜”的 SA 更有效；
- 比单纯稳定贪心更容易减少车辆数；
- 保持 G3 六姿态，但仍按底层单层放置；
- 输出每辆车装箱明细与车辆汇总。
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

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]
TYPE_ORDER_MAIN = ["G4", "G5", "G1", "G2"]


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


# ============================================================
# 工具函数
# ============================================================

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


# ============================================================
# 单车稳定构造器
# ============================================================

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
        cand = (waste, zone_width, ori, nx, ny)
        if best_plan is None or cand < best_plan:
            best_plan = cand

    if best_plan is None:
        return 0, 0.0, 0, 0

    _, zone_width, ori, nx, ny = best_plan
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
    quota: Dict[str, int],
    remaining_height: int,
    truck: Truck,
    main_width: int,
) -> List[Tuple[str, Orientation, int]]:
    cands = []
    for type_id in TYPE_ORDER_MAIN:
        if quota[type_id] <= 0:
            continue
        for ori in ORIENTATIONS[type_id]:
            l, w, h = ori.size
            if h > remaining_height or l > truck.length or w > main_width:
                continue
            remain_ratio = quota[type_id] / max(1, CARGO_TYPES[type_id].quantity)
            area = (l * w) / max(1, truck.length * main_width)
            height_fit = h / max(1, remaining_height)
            score = 1000 * remain_ratio + 100 * area + 10 * height_fit
            cands.append((type_id, ori, int(score * 1000)))
    cands.sort(key=lambda x: x[2], reverse=True)
    return cands


def fill_one_row(
    truck: Truck,
    quota: Dict[str, int],
    vehicle_index: int,
    z: int,
    y: int,
    row_height: int,
    area_length: int,
    serial_counter: Counter,
    layer_height: int,
) -> Tuple[List[PlacedCargo], int, float, int]:
    placed_row: List[PlacedCargo] = []
    x = 0
    used_weight = 0.0
    used_volume = 0
    row_used_width = 0

    while x < area_length:
        best = None
        remain_len = area_length - x
        for type_id in TYPE_ORDER_MAIN:
            if quota[type_id] <= 0:
                continue
            cargo = CARGO_TYPES[type_id]
            for ori in ORIENTATIONS[type_id]:
                l, w, h = ori.size
                if h > layer_height or w > row_height or l > remain_len:
                    continue
                fill_ratio = (l * w) / max(1, remain_len * row_height)
                remain_ratio = quota[type_id] / max(1, cargo.quantity)
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
        quota[type_id] -= 1
        used_weight += p.weight
        used_volume += p.volume
        x += l
        row_used_width = max(row_used_width, w)

    return placed_row, row_used_width, used_weight, used_volume


def fill_main_zone_layers(
    truck: Truck,
    quota: Dict[str, int],
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
        cands = candidate_layer_types(quota, remaining_height, truck, main_width)
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
                if quota[type_id] <= 0:
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
                truck, quota, vehicle_index, z, y, row_height, truck.length, serial_counter, layer_height
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


def pack_one_vehicle_given_counts(truck: Truck, target_quota: Dict[str, int], vehicle_index: int) -> VehicleResult:
    quota = {t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL}
    placed: List[PlacedCargo] = []
    serial_counter = Counter()
    used_weight = 0.0
    used_volume = 0

    g3_zone_width, add_w, add_v, actual_g3 = place_g3_exact(
        truck, quota["G3"], vehicle_index, placed, serial_counter
    )
    used_weight += add_w
    used_volume += add_v
    quota["G3"] -= actual_g3

    used_weight, used_volume = fill_main_zone_layers(
        truck, quota, vehicle_index, g3_zone_width, placed, used_weight, used_volume, serial_counter
    )

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        target_counts={t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL},
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
    )


def revalidate_all(truck: Truck, quotas: List[Dict[str, int]]) -> List[VehicleResult]:
    return [pack_one_vehicle_given_counts(truck, q, i + 1) for i, q in enumerate(quotas)]


def collect_missing(plans: List[VehicleResult]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER_ALL}
    for vp in plans:
        for t in TYPE_ORDER_ALL:
            missing[t] += max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))
    return missing


def all_feasible(plans: List[VehicleResult]) -> bool:
    return all(vp.feasible_full_pack for vp in plans)


# ============================================================
# 初始可行解：稳定逐车贪心
# ============================================================

def compute_g3_target_for_vehicle(truck: Truck, remaining: Dict[str, int]) -> int:
    if remaining["G3"] <= 0:
        return 0
    best_floor = 0
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
    return min(remaining["G3"], max(6, int(best_floor * 0.6)))


def pack_one_vehicle_greedy_from_remaining(truck: Truck, remaining: Dict[str, int], vehicle_index: int) -> VehicleResult:
    quota = {t: 0 for t in TYPE_ORDER_ALL}
    placed: List[PlacedCargo] = []
    serial_counter = Counter()
    used_weight = 0.0
    used_volume = 0

    g3_target = compute_g3_target_for_vehicle(truck, remaining)
    g3_zone_width, add_w, add_v, actual_g3 = place_g3_exact(
        truck, g3_target, vehicle_index, placed, serial_counter
    )
    quota["G3"] = actual_g3
    remaining["G3"] -= actual_g3
    used_weight += add_w
    used_volume += add_v

    # 主区构造：使用临时 quota 容器，逐步从 remaining 中抽货
    local = {t: 0 for t in TYPE_ORDER_ALL}
    # 先给一个上限池，避免装满前无货可选
    for t in TYPE_ORDER_MAIN:
        local[t] = remaining[t]

    before = local.copy()
    used_weight, used_volume = fill_main_zone_layers(
        truck, local, vehicle_index, g3_zone_width, placed, used_weight, used_volume, serial_counter
    )

    # 实际装了多少 = before - local
    for t in TYPE_ORDER_MAIN:
        quota[t] = before[t] - local[t]
        remaining[t] -= quota[t]

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        target_counts=quota,
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
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
# 压缩初始化：把尾车货物塞回前 K 辆
# ============================================================

def compress_quotas_from_feasible(
    truck: Truck,
    feasible_quotas: List[Dict[str, int]],
    target_k: int,
) -> List[Dict[str, int]]:
    if target_k >= len(feasible_quotas):
        return [q.copy() for q in feasible_quotas[:target_k]]

    kept = [q.copy() for q in feasible_quotas[:target_k]]
    tails = feasible_quotas[target_k:]

    # 将尾车货物按 type 顺序重新塞入前 K 辆
    leftover = {t: 0 for t in TYPE_ORDER_ALL}
    for q in tails:
        for t in TYPE_ORDER_ALL:
            leftover[t] += q.get(t, 0)

    # 先尝试大件、再小件；G3 单独处理
    order = ["G4", "G5", "G1", "G2"]
    for t in order:
        qty = leftover[t]
        c = CARGO_TYPES[t]
        while qty > 0:
            candidates = []
            for i in range(target_k):
                rv = residual_volume(truck, kept[i])
                rw = residual_weight(truck, kept[i])
                if rv >= c.volume and rw >= c.weight:
                    # 偏向装得还不满的车
                    sv, wv, fs = truck_score(truck, quota_total_volume(kept[i]), quota_total_weight(kept[i]))
                    slack = (1 - sv) + (1 - wv)
                    candidates.append((slack, i))
            if not candidates:
                break
            candidates.sort(reverse=True)
            i = candidates[0][1]
            kept[i][t] += 1
            qty -= 1
        leftover[t] = qty

    # G3：按当前目标车底层能力分配
    qty = leftover["G3"]
    while qty > 0:
        caps = []
        for i in range(target_k):
            cur = kept[i]["G3"]
            best_floor = 0
            for ori in ORIENTATIONS["G3"]:
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

    # 剩余无法塞入的货，随机压到前 K 辆（作为 SA 初始近似，后续再修）
    rng = random.Random(2026 + target_k)
    for t in TYPE_ORDER_ALL:
        while leftover[t] > 0:
            i = rng.randrange(target_k)
            kept[i][t] += 1
            leftover[t] -= 1

    return kept


# ============================================================
# SA + LNS
# ============================================================

def solution_energy(truck: Truck, quotas: List[Dict[str, int]], plans: List[VehicleResult], K: int) -> float:
    missing = collect_missing(plans)
    miss_cnt = sum(missing.values())
    miss_weighted = (
        35 * missing["G3"] +
        16 * missing["G4"] +
        12 * missing["G5"] +
        5 * missing["G1"] +
        4 * missing["G2"]
    )
    used_vol = sum(vp.used_volume for vp in plans)
    used_w = sum(vp.used_weight for vp in plans)
    avg_sv = used_vol / (K * truck.effective_volume)
    avg_wv = used_w / (K * truck.max_weight)

    tail_bad = sum(1 for vp in plans if vp.used_volume / truck.effective_volume < 0.18)

    return (
        5000 * miss_cnt
        + 50 * miss_weighted
        + 120 * K
        + 40 * tail_bad
        - 600 * avg_sv
        - 220 * avg_wv
    )


def block_move_neighbor(quotas: List[Dict[str, int]], truck: Truck, rng: random.Random) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    a, b = rng.sample(range(len(child)), 2)
    t = rng.choice(TYPE_ORDER_ALL)
    if child[a][t] <= 0:
        return child
    max_move = min(child[a][t], rng.randint(1, 8))
    child[a][t] -= max_move
    child[b][t] += max_move
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

    deficits = []
    receivers = []
    for i, vp in enumerate(plans):
        target = vp.target_counts.get("G3", 0)
        actual = vp.actual_counts.get("G3", 0)
        if target > actual:
            deficits.append((target - actual, i))
        else:
            best_floor = 0
            for ori in ORIENTATIONS["G3"]:
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

    # 优先修 missing 最大的货类
    types_by_need = sorted(TYPE_ORDER_ALL, key=lambda t: missing[t], reverse=True)
    for t in types_by_need:
        if missing[t] <= 0:
            continue
        donors = []
        receivers = []
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


def make_neighbor(
    quotas: List[Dict[str, int]],
    plans: List[VehicleResult],
    truck: Truck,
    rng: random.Random,
) -> List[Dict[str, int]]:
    op = rng.choice(["block", "swap", "g3", "lns", "block", "lns"])
    if op == "block":
        return block_move_neighbor(quotas, truck, rng)
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
        accept = False
        if delta <= 0:
            accept = True
        else:
            prob = math.exp(-delta / max(temp, 1e-9))
            if rng.random() < prob:
                accept = True

        if accept:
            current = cand
            current_plans = cand_plans
            current_energy = cand_energy

        if cand_energy < best_energy:
            best = [q.copy() for q in cand]
            best_plans = cand_plans
            best_energy = cand_energy

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


# ============================================================
# 终极版求解流程
# ============================================================

def solve_problem_12_ultimate(
    truck: Truck,
    sa_iterations: int = 140,
    min_extra_over_lb: int = 0,
) -> Tuple[int, List[VehicleResult], Dict[str, object]]:
    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)

    # 1) 先构造 greedy 可行解
    greedy_plans, greedy_quotas = greedy_initial_solution(truck)
    greedy_k = len(greedy_plans)
    print(f"[{truck.name}] greedy 初始可行车辆数 = {greedy_k}", flush=True)

    best_feasible_k = greedy_k
    best_feasible_plans = greedy_plans
    best_feasible_quotas = greedy_quotas

    lower_search = lb + min_extra_over_lb
    current_k = greedy_k - 1

    while current_k >= lower_search:
        print(f"[{truck.name}] 尝试压缩到 K = {current_k} ...", flush=True)
        init_quotas = compress_quotas_from_feasible(truck, best_feasible_quotas, current_k)
        quotas, plans, energy = simulated_annealing_optimize(
            truck=truck,
            init_quotas=init_quotas,
            iterations=sa_iterations,
            seed=2026 + current_k,
        )
        ok = all_feasible(plans)
        print(f"[{truck.name}] K = {current_k} 可行性结果: {ok}", flush=True)

        if ok:
            best_feasible_k = current_k
            best_feasible_plans = plans
            best_feasible_quotas = quotas
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


# ============================================================
# 输出
# ============================================================

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
                vp.vehicle_id,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                vp.target_counts,
                vp.actual_counts,
                round(vp.used_weight, 3),
                vp.used_volume,
                vp.feasible_full_pack,
            ])


def write_items_csv(path: str, placed: List[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id
            ])


def solve_for_truck(truck: Truck, outdir: str, sa_iterations: int) -> Dict[str, object]:
    K, plans, summary = solve_problem_12_ultimate(truck, sa_iterations=sa_iterations)
    truck_dir = os.path.join(outdir, truck.name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck.name}_车辆汇总.csv"), plans, truck)
    for vp in plans:
        write_items_csv(os.path.join(truck_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp.placed)
    summary["output_dir"] = truck_dir
    return summary


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 终极版 Hybrid SA")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="output_p12_ultimate_sa", help="输出目录")
    parser.add_argument("--sa-iterations", type=int, default=140, help="每轮压缩的 SA 迭代次数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for name in truck_list:
        truck = TRUCKS[name]
        print("\n" + "=" * 64)
        print(f"开始求解问题1.2：{truck.name}")
        print("=" * 64)
        summary = solve_for_truck(truck, args.outdir, args.sa_iterations)
        print(summary)


if __name__ == "__main__":
    main()
