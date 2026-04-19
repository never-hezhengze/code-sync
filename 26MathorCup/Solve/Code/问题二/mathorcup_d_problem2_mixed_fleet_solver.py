
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二
混合车型（车型1 + 车型2）联合求解器
目标支持：
1. 最少车辆数（min_vehicle）
2. 最低运输成本（min_cost）

算法思路：
- 外层枚举/搜索车队结构 (n1, n2)
- 中层对固定车队结构进行货物分配与 SA/LNS 修复
- 内层复用问题1.2最终版的 GA 单车策略优化 + G3 双通道装箱验证
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple


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
    truck_name: str
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


ORIENTATIONS = {k: generate_orientations(v) for k, v in CARGO_TYPES.items()}


def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / truck.effective_volume
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


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
    best_key = None
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
        key = (waste, zone_width, -nx, -ny)
        if best_key is None or key < best_key:
            best_key = key
            best_plan = (zone_width, ori, nx, ny)

    if best_plan is None:
        return 0, 0.0, 0, 0

    zone_width, ori, nx, ny = best_plan
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
                item_id=item_id, type_id="G3", category="fragile",
                x=i * l, y=j * w, z=0,
                length=l, width=w, height=h,
                weight=CARGO_TYPES["G3"].weight,
                orientation_id=ori.orient_id, rotation=ori.rotation,
                truck_id=f"{truck.name}_{vehicle_index:03d}",
            )
            placed.append(p)
            used_weight += p.weight
            used_volume += p.volume
            placed_count += 1
    return zone_width, used_weight, used_volume, placed_count


def candidate_layer_types(quota: Dict[str, int], remaining_height: int, truck: Truck, main_width: int, policy: PackingPolicy):
    cands = []
    order_rank = {t: i for i, t in enumerate(policy.main_order)}
    for type_id in policy.main_order:
        if quota[type_id] <= 0:
            continue
        for ori in ORIENTATIONS[type_id]:
            l, w, h = ori.size
            if h > remaining_height or l > truck.length or w > main_width:
                continue
            remain_ratio = quota[type_id] / max(1, CARGO_TYPES[type_id].quantity)
            area = (l * w) / max(1, truck.length * main_width)
            height_fit = h / max(1, remaining_height)
            score = 1000 * remain_ratio + 100 * area + 10 * height_fit - 3 * order_rank[type_id]
            cands.append((type_id, ori, int(score * 1000)))
    cands.sort(key=lambda x: x[2], reverse=True)
    return cands


def choose_row_height(row_cands, remain_width: int, policy: PackingPolicy) -> int:
    if not row_cands:
        return 0
    if policy.row_mode == 0:
        row_cands.sort(key=lambda x: x[0], reverse=True)
        return row_cands[0][0]
    elif policy.row_mode == 1:
        row_cands.sort(key=lambda x: x[0])
        return row_cands[0][0]
    else:
        row_cands.sort(key=lambda x: abs(remain_width - x[0]))
        return row_cands[0][0]


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
    policy: PackingPolicy,
):
    placed_row: List[PlacedCargo] = []
    x = 0
    used_weight = 0.0
    used_volume = 0
    row_used_width = 0

    while x < area_length:
        best = None
        remain_len = area_length - x
        for type_id in policy.main_order:
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
                score = policy.w_fill * fill_ratio + policy.w_remain * remain_ratio + policy.w_volume * volume_bonus
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
            item_id=item_id, type_id=type_id, category=cargo.category,
            x=x, y=y, z=z,
            length=l, width=w, height=h,
            weight=cargo.weight,
            orientation_id=ori.orient_id, rotation=ori.rotation,
            truck_id=f"{truck.name}_{vehicle_index:03d}",
        )
        placed_row.append(p)
        quota[type_id] -= 1
        used_weight += p.weight
        used_volume += p.volume
        x += l
        row_used_width = max(row_used_width, w)

    return placed_row, row_used_width, used_weight, used_volume


def place_g3_second_channel_on_supports(
    truck: Truck,
    quota: Dict[str, int],
    vehicle_index: int,
    layer_items: List[PlacedCargo],
    placed: List[PlacedCargo],
    serial_counter: Counter,
):
    if quota.get("G3", 0) <= 0:
        return 0.0, 0, 0
    used_weight = 0.0
    used_volume = 0
    layer_top_height = 0
    supports = [p for p in layer_items if p.type_id in ("G1", "G2")]
    supports.sort(key=lambda p: (p.z, -(p.length * p.width), p.y, p.x))

    for sup in supports:
        if quota["G3"] <= 0:
            break
        best = None
        best_key = None
        for ori in ORIENTATIONS["G3"]:
            l, w, h = ori.size
            if sup.z + sup.height + h > truck.effective_height:
                continue
            nx = sup.length // l
            ny = sup.width // w
            cnt = nx * ny
            if cnt <= 0:
                continue
            used_area = cnt * l * w
            area_ratio = used_area / max(1, sup.length * sup.width)
            key = (-min(cnt, quota["G3"]), -area_ratio, sup.height + h)
            if best_key is None or key < best_key:
                best_key = key
                best = (ori, nx, ny)
        if best is None:
            continue

        ori, nx, ny = best
        l, w, h = ori.size
        top_z = sup.z + sup.height
        placed_cnt = 0
        for j in range(ny):
            for i in range(nx):
                if quota["G3"] <= 0:
                    break
                serial_counter["G3"] += 1
                item_id = f"G3_{vehicle_index:03d}_{serial_counter['G3']:04d}"
                p = PlacedCargo(
                    item_id=item_id, type_id="G3", category="fragile",
                    x=sup.x + i * l, y=sup.y + j * w, z=top_z,
                    length=l, width=w, height=h,
                    weight=CARGO_TYPES["G3"].weight,
                    orientation_id=ori.orient_id, rotation=ori.rotation,
                    truck_id=f"{truck.name}_{vehicle_index:03d}",
                )
                placed.append(p)
                quota["G3"] -= 1
                used_weight += p.weight
                used_volume += p.volume
                placed_cnt += 1
            if quota["G3"] <= 0:
                break
        if placed_cnt > 0:
            layer_top_height = max(layer_top_height, sup.height + h)
    return used_weight, used_volume, layer_top_height


def fill_main_zone_layers(
    truck: Truck,
    quota: Dict[str, int],
    vehicle_index: int,
    g3_zone_width: int,
    placed: List[PlacedCargo],
    used_weight: float,
    used_volume: int,
    serial_counter: Counter,
    policy: PackingPolicy,
):
    main_width = truck.width - g3_zone_width
    if main_width <= 0:
        return used_weight, used_volume
    z = 0
    while z < truck.effective_height:
        remaining_height = truck.effective_height - z
        cands = candidate_layer_types(quota, remaining_height, truck, main_width, policy)
        if not cands:
            break
        _, ori0, _ = cands[0]
        layer_height = ori0.size[2]
        if policy.layer_height_relax == 1:
            layer_height = min(remaining_height, layer_height + 20)
        if layer_height <= 0 or z + layer_height > truck.effective_height:
            break

        y = g3_zone_width
        layer_placed_any = False
        layer_items: List[PlacedCargo] = []

        while y < truck.width:
            remain_width = truck.width - y
            if remain_width <= 0:
                break
            row_cands = []
            for type_id in policy.main_order:
                if quota[type_id] <= 0:
                    continue
                for ori in ORIENTATIONS[type_id]:
                    l, w, h = ori.size
                    if h <= layer_height and w <= remain_width and l <= truck.length:
                        row_cands.append((w, type_id, ori))
            if not row_cands:
                break

            row_height = choose_row_height(row_cands, remain_width, policy)
            row_items, row_used_width, add_w, add_v = fill_one_row(
                truck, quota, vehicle_index, z, y, row_height, truck.length, serial_counter, layer_height, policy
            )
            if not row_items:
                break

            layer_placed_any = True
            layer_items.extend(row_items)
            placed.extend(row_items)
            used_weight += add_w
            used_volume += add_v
            y += row_used_width if row_used_width > 0 else row_height
            if used_weight >= truck.max_weight - 1e-9:
                return used_weight, used_volume

        if not layer_placed_any:
            break

        add_w2, add_v2, layer_top_height = place_g3_second_channel_on_supports(
            truck, quota, vehicle_index, layer_items, placed, serial_counter
        )
        used_weight += add_w2
        used_volume += add_v2
        z += max(layer_height, layer_top_height)
        if used_weight >= truck.max_weight - 1e-9:
            break

    return used_weight, used_volume


def pack_one_vehicle_with_policy(truck: Truck, target_quota: Dict[str, int], vehicle_index: int, policy: PackingPolicy) -> VehicleResult:
    quota = {t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL}
    placed: List[PlacedCargo] = []
    serial_counter = Counter()
    used_weight = 0.0
    used_volume = 0

    g3_target = min(quota["G3"], max(0, int(math.ceil(quota["G3"] * policy.g3_ratio))))
    if quota["G3"] > 0 and quota_size(target_quota) <= quota["G3"] + 10:
        g3_target = quota["G3"]
    if quota["G3"] > 0 and g3_target == 0:
        g3_target = min(2, quota["G3"])

    g3_zone_width, add_w, add_v, actual_g3 = place_g3_exact(truck, g3_target, vehicle_index, placed, serial_counter)
    used_weight += add_w
    used_volume += add_v
    quota["G3"] -= actual_g3

    used_weight, used_volume = fill_main_zone_layers(
        truck, quota, vehicle_index, g3_zone_width, placed, used_weight, used_volume, serial_counter, policy
    )

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        truck_name=truck.name,
        placed=placed,
        target_counts={t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL},
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
        policy_desc=policy.desc(),
    )


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
    g3_ratio = min(1.0, max(0.1, p.g3_ratio + rng.uniform(-0.15, 0.15)))
    wf = max(0.05, p.w_fill + rng.uniform(-0.12, 0.12))
    wr = max(0.05, p.w_remain + rng.uniform(-0.12, 0.12))
    wv = max(0.05, p.w_volume + rng.uniform(-0.12, 0.12))
    s = wf + wr + wv
    return PackingPolicy(
        g3_ratio=g3_ratio,
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
        weighted_missing += (15 if t == "G3" else 8 if t in ("G4", "G5") else 3) * d
    sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
    return -2000 * missing - 120 * weighted_missing + 300 * sv + 120 * wv + 60 * fs


def ga_optimize_vehicle_policy(truck: Truck, quota: Dict[str, int], vehicle_index: int, seed: int = 2026, pop_size: int = 10, generations: int = 6):
    sig = (truck.name, quota_signature(quota))
    if sig in _POLICY_CACHE:
        best_policy = _POLICY_CACHE[sig]
        best_plan = pack_one_vehicle_with_policy(truck, quota, vehicle_index, best_policy)
        return best_plan, best_policy

    rng = random.Random(seed + vehicle_index + sum(quota.values()))
    population = [default_policy()]
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


def fleet_from_structure(n1: int, n2: int) -> List[Truck]:
    return [TRUCKS["车型1"] for _ in range(n1)] + [TRUCKS["车型2"] for _ in range(n2)]


def structure_cost(n1: int, n2: int) -> float:
    return n1 * TRUCKS["车型1"].cost + n2 * TRUCKS["车型2"].cost


def collect_missing(plans: List[VehicleResult]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER_ALL}
    for vp in plans:
        for t in TYPE_ORDER_ALL:
            missing[t] += max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))
    return missing


def all_feasible(plans: List[VehicleResult]) -> bool:
    return all(vp.feasible_full_pack for vp in plans)


def revalidate_all_mixed(fleet: List[Truck], quotas: List[Dict[str, int]]) -> List[VehicleResult]:
    plans = []
    for i, (truck, quota) in enumerate(zip(fleet, quotas), 1):
        plan, _ = ga_optimize_vehicle_policy(truck, quota, i)
        plans.append(plan)
    return plans


def greedy_initial_quotas_for_fleet(fleet: List[Truck]) -> List[Dict[str, int]]:
    quotas = [{t: 0 for t in TYPE_ORDER_ALL} for _ in fleet]
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER_ALL}

    # G3 优先给底层能力更强的车
    idx_order_g3 = []
    for i, tr in enumerate(fleet):
        best_floor = 0
        for ori in ORIENTATIONS["G3"]:
            l, w, h = ori.size
            if h <= tr.effective_height:
                best_floor = max(best_floor, (tr.length // l) * (tr.width // w))
        idx_order_g3.append((best_floor, tr.effective_volume, i))
    idx_order_g3.sort(reverse=True)
    idx_order_g3 = [x[2] for x in idx_order_g3]

    qty = remaining["G3"]
    while qty > 0 and idx_order_g3:
        moved_any = False
        for i in idx_order_g3:
            tr = fleet[i]
            best_floor = 0
            for ori in ORIENTATIONS["G3"]:
                l, w, h = ori.size
                if h <= tr.effective_height:
                    best_floor = max(best_floor, (tr.length // l) * (tr.width // w))
            slack = max(0, int(best_floor * 0.7) - quotas[i]["G3"])
            if slack > 0:
                mv = min(slack, qty)
                quotas[i]["G3"] += mv
                qty -= mv
                moved_any = True
                if qty <= 0:
                    break
        if not moved_any:
            break
    remaining["G3"] = qty

    # G4/G5 优先给大车
    for t in ["G4", "G5"]:
        qty = remaining[t]
        c = CARGO_TYPES[t]
        order = sorted(range(len(fleet)), key=lambda i: (fleet[i].effective_volume, fleet[i].max_weight), reverse=True)
        while qty > 0:
            placed_any = False
            for i in order:
                if residual_volume(fleet[i], quotas[i]) >= c.volume and residual_weight(fleet[i], quotas[i]) >= c.weight:
                    quotas[i][t] += 1
                    qty -= 1
                    placed_any = True
                    if qty <= 0:
                        break
            if not placed_any:
                break
        remaining[t] = qty

    # G1/G2 填充
    for t in ["G1", "G2"]:
        qty = remaining[t]
        c = CARGO_TYPES[t]
        while qty > 0:
            candidates = []
            for i, tr in enumerate(fleet):
                rv = residual_volume(tr, quotas[i])
                rw = residual_weight(tr, quotas[i])
                if rv >= c.volume and rw >= c.weight:
                    slack = rv / max(1, tr.effective_volume) + rw / max(1.0, tr.max_weight)
                    candidates.append((slack, i))
            if not candidates:
                break
            candidates.sort(reverse=True)
            i = candidates[0][1]
            quotas[i][t] += 1
            qty -= 1
        remaining[t] = qty

    # 剩余随机回填
    rng = random.Random(2026 + len(fleet))
    for t in TYPE_ORDER_ALL:
        while remaining[t] > 0:
            if t == "G3" and idx_order_g3:
                i = idx_order_g3[0]
            else:
                order = sorted(range(len(fleet)), key=lambda i: (fleet[i].effective_volume, fleet[i].max_weight), reverse=True)
                i = order[0] if order else rng.randrange(len(fleet))
            quotas[i][t] += 1
            remaining[t] -= 1

    return quotas


def solution_energy_mixed(fleet: List[Truck], quotas: List[Dict[str, int]], plans: List[VehicleResult], objective: str) -> float:
    missing = collect_missing(plans)
    miss_cnt = sum(missing.values())
    miss_weighted = 35 * missing["G3"] + 16 * missing["G4"] + 12 * missing["G5"] + 5 * missing["G1"] + 4 * missing["G2"]
    total_cost = sum(tr.cost for tr in fleet)
    used_vol = sum(vp.used_volume for vp in plans)
    total_vol = sum(tr.effective_volume for tr in fleet)
    used_w = sum(vp.used_weight for vp in plans)
    total_w = sum(tr.max_weight for tr in fleet)
    avg_sv = used_vol / max(1, total_vol)
    avg_wv = used_w / max(1.0, total_w)
    tail_bad = sum(1 for vp, tr in zip(plans, fleet) if vp.used_volume / max(1, tr.effective_volume) < 0.15)

    if objective == "min_vehicle":
        return 5000 * miss_cnt + 50 * miss_weighted + 120 * len(fleet) + 0.1 * total_cost + 40 * tail_bad - 600 * avg_sv - 220 * avg_wv
    else:
        return 5000 * miss_cnt + 50 * miss_weighted + 4.0 * total_cost + 5 * len(fleet) + 40 * tail_bad - 600 * avg_sv - 220 * avg_wv


def block_move_neighbor_mixed(quotas: List[Dict[str, int]], rng: random.Random) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    if len(child) < 2:
        return child

    a, b = rng.sample(range(len(child)), 2)
    t = rng.choice(TYPE_ORDER_ALL)
    if child[a][t] <= 0:
        return child
    mv = min(child[a][t], rng.randint(1, 8))
    child[a][t] -= mv
    child[b][t] += mv
    return child


def swap_neighbor_mixed(quotas: List[Dict[str, int]], rng: random.Random) -> List[Dict[str, int]]:
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

    da = min(child[a][ta], rng.randint(1, 4))
    db = min(child[b][tb], rng.randint(1, 4))
    child[a][ta] -= da
    child[b][tb] -= db
    child[a][tb] += db
    child[b][ta] += da
    return child


def targeted_lns_repair_mixed(fleet: List[Truck], quotas: List[Dict[str, int]], plans: List[VehicleResult]) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    missing = collect_missing(plans)
    types_by_need = sorted(TYPE_ORDER_ALL, key=lambda t: missing[t], reverse=True)
    for t in types_by_need:
        if missing[t] <= 0:
            continue
        c = CARGO_TYPES[t]
        donors, receivers = [], []
        for i, vp in enumerate(plans):
            target = vp.target_counts.get(t, 0)
            actual = vp.actual_counts.get(t, 0)
            if target > actual and child[i][t] > 0:
                donors.append((target - actual, i))
            else:
                receivers.append(i)
        donors.sort(reverse=True)
        receivers.sort(key=lambda i: (fleet[i].name == "车型2", residual_volume(fleet[i], child[i]), residual_weight(fleet[i], child[i])), reverse=True)
        for deficit, d in donors:
            for r in receivers:
                if r == d:
                    continue
                if residual_volume(fleet[r], child[r]) >= c.volume and residual_weight(fleet[r], child[r]) >= c.weight:
                    mv = min(deficit, child[d][t], 3 if t in ("G4", "G5") else 10)
                    if mv > 0:
                        child[d][t] -= mv
                        child[r][t] += mv
                        break
    return child


def rebalance_g3_to_bigger_floor(fleet: List[Truck], quotas: List[Dict[str, int]], plans: List[VehicleResult]) -> List[Dict[str, int]]:
    child = [q.copy() for q in quotas]
    missing = collect_missing(plans)
    if missing["G3"] == 0:
        return child
    deficits, receivers = [], []
    for i, (vp, tr) in enumerate(zip(plans, fleet)):
        target = vp.target_counts.get("G3", 0)
        actual = vp.actual_counts.get("G3", 0)
        if target > actual:
            deficits.append((target - actual, i))
        else:
            best_floor = 0
            for ori in ORIENTATIONS["G3"]:
                l, w, h = ori.size
                if h <= tr.effective_height:
                    best_floor = max(best_floor, (tr.length // l) * (tr.width // w))
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


def make_neighbor_mixed(
    fleet: List[Truck],
    quotas: List[Dict[str, int]],
    plans: List[VehicleResult],
    rng: random.Random
) -> List[Dict[str, int]]:
    if len(quotas) < 2:
        return [q.copy() for q in quotas]

    op = rng.choice(["block", "swap", "lns", "g3", "block", "lns"])
    if op == "block":
        return block_move_neighbor_mixed(quotas, rng)
    if op == "swap":
        return swap_neighbor_mixed(quotas, rng)
    if op == "g3":
        return rebalance_g3_to_bigger_floor(fleet, quotas, plans)
    return targeted_lns_repair_mixed(fleet, quotas, plans)


def simulated_annealing_optimize_mixed(fleet: List[Truck], init_quotas: List[Dict[str, int]], objective: str, iterations: int = 120, seed: int = 2026):
    rng = random.Random(seed + len(fleet))
    current = [q.copy() for q in init_quotas]
    current_plans = revalidate_all_mixed(fleet, current)
    current_energy = solution_energy_mixed(fleet, current, current_plans, objective)

    best = [q.copy() for q in current]
    best_plans = current_plans
    best_energy = current_energy

    init_temp = 80.0
    final_temp = 0.8
    for it in range(1, iterations + 1):
        ratio = (it - 1) / max(1, iterations - 1)
        temp = init_temp * ((final_temp / init_temp) ** ratio)

        cand = make_neighbor_mixed(fleet, current, current_plans, rng)
        cand_plans = revalidate_all_mixed(fleet, cand)
        cand_energy = solution_energy_mixed(fleet, cand, cand_plans, objective)

        delta = cand_energy - current_energy
        accept = False
        if delta <= 0:
            accept = True
        elif rng.random() < math.exp(-delta / max(temp, 1e-9)):
            accept = True

        if accept:
            current, current_plans, current_energy = cand, cand_plans, cand_energy
        if cand_energy < best_energy:
            best, best_plans, best_energy = [q.copy() for q in cand], cand_plans, cand_energy
        if all_feasible(best_plans):
            break
    return best, best_plans, best_energy


def candidate_structures_for_min_vehicle(max_vehicle: int, max_n1: int, max_n2: int) -> List[Tuple[int, int]]:
    structs = []
    for K in range(1, max_vehicle + 1):
        for n1 in range(0, min(max_n1, K) + 1):
            n2 = K - n1
            if 0 <= n2 <= max_n2:
                structs.append((n1, n2))
    return structs


def candidate_structures_for_min_cost(max_n1: int, max_n2: int) -> List[Tuple[int, int]]:
    structs = []
    for n1 in range(max_n1 + 1):
        for n2 in range(max_n2 + 1):
            if n1 + n2 == 0:
                continue
            structs.append((n1, n2))
    structs.sort(key=lambda x: (structure_cost(x[0], x[1]), x[0] + x[1]))
    return structs


def solve_mixed_fleet(objective: str, sa_iterations: int = 120, max_vehicle: int = 30, max_n1: int = 27, max_n2: int = 13):
    candidates = candidate_structures_for_min_vehicle(max_vehicle, max_n1, max_n2) if objective == "min_vehicle" else candidate_structures_for_min_cost(max_n1, max_n2)
    best_feasible = None
    best_record = None

    for n1, n2 in candidates:
        fleet = fleet_from_structure(n1, n2)
        if not fleet:
            continue

        init_quotas = greedy_initial_quotas_for_fleet(fleet)
        quotas, plans, energy = simulated_annealing_optimize_mixed(
            fleet=fleet,
            init_quotas=init_quotas,
            objective=objective,
            iterations=sa_iterations,
            seed=2026 + n1 * 100 + n2,
        )
        feasible = all_feasible(plans)

        if feasible:
            record = {
                "objective": objective,
                "fleet_structure": {"车型1": n1, "车型2": n2},
                "vehicle_count": n1 + n2,
                "total_cost": structure_cost(n1, n2),
                "avg_space_utilization": round(sum(vp.used_volume for vp in plans) / max(1, sum(tr.effective_volume for tr in fleet)), 6),
                "avg_weight_utilization": round(sum(vp.used_weight for vp in plans) / max(1.0, sum(tr.max_weight for tr in fleet)), 6),
                "all_loaded": True,
            }
            return (n1, n2), plans, record

        else:
            record = {
                "objective": objective,
                "fleet_structure": {"车型1": n1, "车型2": n2},
                "vehicle_count": n1 + n2,
                "total_cost": structure_cost(n1, n2),
                "missing": collect_missing(plans),
                "energy": round(energy, 3),
                "all_loaded": False,
            }
            if best_record is None or energy < best_record["energy"]:
                best_record = record
                best_feasible = ((n1, n2), plans)

    assert best_feasible is not None
    return best_feasible[0], best_feasible[1], best_record


def write_vehicle_summary_csv(path: str, plans: List[VehicleResult], fleet: List[Truck]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "truck_name", "space_utilization", "weight_utilization", "fullness_score",
            "target_counts", "actual_counts", "loaded_weight_kg", "loaded_volume_cm3", "feasible_full_pack", "policy_desc"
        ])
        for vp, tr in zip(plans, fleet):
            sv, wv, fs = truck_score(tr, vp.used_volume, vp.used_weight)
            w.writerow([
                vp.vehicle_id, vp.truck_name, round(sv, 6), round(wv, 6), round(fs, 6),
                vp.target_counts, vp.actual_counts, round(vp.used_weight, 3), vp.used_volume,
                vp.feasible_full_pack, vp.policy_desc
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
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight, p.orientation_id, p.rotation, p.truck_id
            ])


def export_solution(base_dir: str, n1: int, n2: int, plans: List[VehicleResult]) -> None:
    fleet = fleet_from_structure(n1, n2)
    write_vehicle_summary_csv(os.path.join(base_dir, "车辆汇总.csv"), plans, fleet)
    for vp in plans:
        write_items_csv(os.path.join(base_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp.placed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二 混合车型联合求解器")
    parser.add_argument("--objective", choices=["min_vehicle", "min_cost", "both"], default="both")
    parser.add_argument("--outdir", type=str, default="output_problem2_mixed_fleet")
    parser.add_argument("--sa-iterations", type=int, default=120)
    parser.add_argument("--max-vehicle", type=int, default=30)
    parser.add_argument("--max-n1", type=int, default=27)
    parser.add_argument("--max-n2", type=int, default=13)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    objectives = ["min_vehicle", "min_cost"] if args.objective == "both" else [args.objective]
    for obj in objectives:
        print("=" * 72)
        print(f"开始求解问题二，目标 = {obj}")
        print("=" * 72)

        (n1, n2), plans, summary = solve_mixed_fleet(
            objective=obj,
            sa_iterations=args.sa_iterations,
            max_vehicle=args.max_vehicle,
            max_n1=args.max_n1,
            max_n2=args.max_n2,
        )
        obj_dir = os.path.join(args.outdir, obj)
        os.makedirs(obj_dir, exist_ok=True)
        export_solution(obj_dir, n1, n2, plans)
        summary["output_dir"] = obj_dir
        print(summary)


if __name__ == "__main__":
    main()
