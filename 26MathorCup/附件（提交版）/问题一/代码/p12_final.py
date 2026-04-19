
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2
GA增强单车装箱策略 + G3第二通道 + 外层减车 Hybrid SA/LNS 求解器

核心思想：
1. 外层：先用稳定贪心构造可行解，再通过“减车 + SA/LNS 重分配”压缩车辆数；
2. 内层：对每一辆车的给定货类配额 quota，不再只用固定单车装箱规则，
   而是使用一个轻量 GA（遗传算法）搜索更优的单车装箱策略 policy；
3. policy 基因包括：
   - G3底层目标比例
   - 主区货类优先顺序
   - 行内评分权重（填充率/剩余量/体积）
   - 行高选择模式
4. GA 找到最优策略后，再调用稳定装箱器生成该车的逐件坐标明细；
5. 如果当前 K 辆可行，则继续压缩；否则回退到上一可行 K。

特点：
- 比单一固定规则的单车装箱器更灵活；
- 比“全局纯GA”更稳定，因为 GA 只作用于单车策略层；
- 适合用于问题1.2中“外层减车，内层提质”的混合框架。
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

from mathorcup_d_common import (
    Orientation,
    CargoType,
    Truck,
    CARGO_TYPES,
    TRUCKS,
    ORIENTATIONS,
    truck_score,
)
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
    policy_desc: str = ""

    @property
    def feasible_full_pack(self) -> bool:
        return all(self.actual_counts.get(t, 0) == self.target_counts.get(t, 0) for t in TYPE_ORDER_ALL)


@dataclass(frozen=True)
class PackingPolicy:
    g3_ratio: float              # G3 底层目标比例
    main_order: Tuple[str, ...]  # 主区货类优先序
    w_fill: float
    w_remain: float
    w_volume: float
    row_mode: int                # 0: 宽优先  1: 窄优先  2: 最贴合优先
    layer_height_relax: int      # 0 or 1，是否放宽层高一点点

    def desc(self) -> str:
        return (
            f"g3_ratio={self.g3_ratio:.2f};order={'-'.join(self.main_order)};"
            f"wf={self.w_fill:.2f};wr={self.w_remain:.2f};wv={self.w_volume:.2f};"
            f"row={self.row_mode};relax={self.layer_height_relax}"
        )



TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]
TYPE_ORDER_MAIN = ["G4", "G5", "G1", "G2"]




def lower_bound_vehicle_count(truck: Truck) -> Tuple[int, int, int]:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    basic = max(math.ceil(total_volume / truck.effective_volume), math.ceil(total_weight / truck.max_weight))

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


# ============================================================
# 单车装箱器（支持策略参数）
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

        # 只比较数值项，避免 Orientation 对象参与比较
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
    policy: PackingPolicy,
) -> List[Tuple[str, Orientation, int]]:
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


def choose_row_height(
    row_cands: List[Tuple[int, str, Orientation]],
    remain_width: int,
    policy: PackingPolicy,
) -> int:
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
) -> Tuple[List[PlacedCargo], int, float, int]:
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


def place_g3_second_channel_on_supports(
    truck: Truck,
    quota: Dict[str, int],
    vehicle_index: int,
    layer_items: List[PlacedCargo],
    placed: List[PlacedCargo],
    serial_counter: Counter,
) -> Tuple[float, int, int]:
    """
    第二通道：将剩余 G3 尽量放到当前层 G1/G2 顶面上。
    返回：(新增重量, 新增体积, 当前层所需额外高度上界)
    """
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

            # 优先：能放更多件、覆盖率更高、总高度更低
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
) -> Tuple[float, int]:
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
                truck, quota, vehicle_index, z, y, row_height, truck.length,
                serial_counter, layer_height, policy
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

        # 第二通道：当前层构造完后，尝试把剩余 G3 放到本层 G1/G2 顶面
        add_w2, add_v2, layer_top_height = place_g3_second_channel_on_supports(
            truck, quota, vehicle_index, layer_items, placed, serial_counter
        )
        used_weight += add_w2
        used_volume += add_v2

        z += max(layer_height, layer_top_height)

        if used_weight >= truck.max_weight - 1e-9:
            break

    return used_weight, used_volume


def pack_one_vehicle_with_policy(
    truck: Truck,
    target_quota: Dict[str, int],
    vehicle_index: int,
    policy: PackingPolicy,
) -> VehicleResult:
    quota = {t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL}
    placed: List[PlacedCargo] = []
    serial_counter = Counter()
    used_weight = 0.0
    used_volume = 0

    # G3 目标比例由 policy 控制
    g3_target = min(quota["G3"], max(0, int(math.ceil(quota["G3"] * policy.g3_ratio))))
    # 若本车只有 G3 或 G3很少，避免过度削减
    if quota["G3"] > 0 and quota_size(target_quota) <= quota["G3"] + 10:
        g3_target = quota["G3"]
    if quota["G3"] > 0 and g3_target == 0:
        g3_target = min(2, quota["G3"])

    g3_zone_width, add_w, add_v, actual_g3 = place_g3_exact(
        truck, g3_target, vehicle_index, placed, serial_counter
    )
    used_weight += add_w
    used_volume += add_v
    quota["G3"] -= actual_g3

    used_weight, used_volume = fill_main_zone_layers(
        truck, quota, vehicle_index, g3_zone_width, placed, used_weight, used_volume, serial_counter, policy
    )

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        target_counts={t: int(target_quota.get(t, 0)) for t in TYPE_ORDER_ALL},
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
        policy_desc=policy.desc(),
    )


# ============================================================
# 轻量 GA：优化单车装箱策略
# ============================================================

_POLICY_CACHE: Dict[Tuple[str, Tuple[Tuple[str, int], ...]], PackingPolicy] = {}

def quota_signature(quota: Dict[str, int]) -> Tuple[Tuple[str, int], ...]:
    return tuple((t, int(quota.get(t, 0))) for t in TYPE_ORDER_ALL)


def random_policy(rng: random.Random) -> PackingPolicy:
    order = TYPE_ORDER_MAIN[:]
    rng.shuffle(order)
    a, b = rng.random(), rng.random()
    c = rng.random()
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
    # 顺序交叉：保留 a 前半段，剩余按 b 顺序补齐
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
        if t == "G3":
            weighted_missing += 15 * d
        elif t == "G4":
            weighted_missing += 8 * d
        elif t == "G5":
            weighted_missing += 8 * d
        else:
            weighted_missing += 3 * d

    sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
    return -2000 * missing - 120 * weighted_missing + 300 * sv + 120 * wv + 60 * fs


def ga_optimize_vehicle_policy(
    truck: Truck,
    quota: Dict[str, int],
    vehicle_index: int,
    seed: int = 2026,
    pop_size: int = 10,
    generations: int = 6,
) -> Tuple[VehicleResult, PackingPolicy]:
    sig = (truck.name, quota_signature(quota))
    if sig in _POLICY_CACHE:
        best_policy = _POLICY_CACHE[sig]
        best_plan = pack_one_vehicle_with_policy(truck, quota, vehicle_index, best_policy)
        return best_plan, best_policy

    rng = random.Random(seed + vehicle_index + sum(quota.values()))

    # 初始种群包含默认策略 + 随机策略
    population: List[PackingPolicy] = [default_policy()]
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
                best_fit = fit
                best_policy = p
                best_plan = plan

        scored.sort(key=lambda x: x[0], reverse=True)
        elites = [x[1] for x in scored[:max(2, pop_size // 3)]]

        new_pop = elites[:]
        while len(new_pop) < pop_size:
            if rng.random() < 0.55 and len(elites) >= 2:
                a, b = rng.sample(elites, 2)
                child = crossover_policy(a, b, rng)
            else:
                parent = rng.choice(elites)
                child = mutate_policy(parent, rng)
            new_pop.append(child)
        population = new_pop

        if best_plan.feasible_full_pack:
            break

    _POLICY_CACHE[sig] = best_policy
    return best_plan, best_policy


def revalidate_all(truck: Truck, quotas: List[Dict[str, int]]) -> List[VehicleResult]:
    plans: List[VehicleResult] = []
    for i, q in enumerate(quotas, 1):
        plan, _ = ga_optimize_vehicle_policy(truck, q, i)
        plans.append(plan)
    return plans


def collect_missing(plans: List[VehicleResult]) -> Dict[str, int]:
    missing = {t: 0 for t in TYPE_ORDER_ALL}
    for vp in plans:
        for t in TYPE_ORDER_ALL:
            missing[t] += max(0, vp.target_counts.get(t, 0) - vp.actual_counts.get(t, 0))
    return missing


def all_feasible(plans: List[VehicleResult]) -> bool:
    return all(vp.feasible_full_pack for vp in plans)


# ============================================================
# 初始可行解：稳定逐车贪心（沿用默认策略）
# ============================================================

def compute_g3_target_for_vehicle(truck: Truck, remaining: Dict[str, int], g3_ratio: float = 0.60) -> int:
    if remaining["G3"] <= 0:
        return 0
    best_floor = 0
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
    return min(remaining["G3"], max(6, int(best_floor * g3_ratio)))


def pack_one_vehicle_greedy_from_remaining(truck: Truck, remaining: Dict[str, int], vehicle_index: int) -> VehicleResult:
    quota = {t: 0 for t in TYPE_ORDER_ALL}
    placed: List[PlacedCargo] = []
    serial_counter = Counter()
    used_weight = 0.0
    used_volume = 0
    policy = default_policy()

    g3_target = compute_g3_target_for_vehicle(truck, remaining, policy.g3_ratio)
    g3_zone_width, add_w, add_v, actual_g3 = place_g3_exact(
        truck, g3_target, vehicle_index, placed, serial_counter
    )
    quota["G3"] = actual_g3
    remaining["G3"] -= actual_g3
    used_weight += add_w
    used_volume += add_v

    local = {t: 0 for t in TYPE_ORDER_ALL}
    local["G3"] = remaining["G3"]
    for t in TYPE_ORDER_MAIN:
        local[t] = remaining[t]

    before = local.copy()
    used_weight, used_volume = fill_main_zone_layers(
        truck, local, vehicle_index, g3_zone_width, placed, used_weight, used_volume, serial_counter, policy
    )

    for t in ["G3"] + TYPE_ORDER_MAIN:
        delta = before[t] - local[t]
        quota[t] += delta
        remaining[t] -= delta

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        target_counts=quota,
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
        policy_desc=policy.desc(),
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

def compress_quotas_from_feasible(truck: Truck, feasible_quotas: List[Dict[str, int]], target_k: int) -> List[Dict[str, int]]:
    if target_k >= len(feasible_quotas):
        return [q.copy() for q in feasible_quotas[:target_k]]

    kept = [q.copy() for q in feasible_quotas[:target_k]]
    tails = feasible_quotas[target_k:]
    leftover = {t: 0 for t in TYPE_ORDER_ALL}

    for q in tails:
        for t in TYPE_ORDER_ALL:
            leftover[t] += q.get(t, 0)

    for t in ["G4", "G5", "G1", "G2"]:
        qty = leftover[t]
        c = CARGO_TYPES[t]
        while qty > 0:
            candidates = []
            for i in range(target_k):
                rv = residual_volume(truck, kept[i])
                rw = residual_weight(truck, kept[i])
                if rv >= c.volume and rw >= c.weight:
                    sv, wv, _ = truck_score(truck, quota_total_volume(kept[i]), quota_total_weight(kept[i]))
                    slack = (1 - sv) + (1 - wv)
                    candidates.append((slack, i))
            if not candidates:
                break
            candidates.sort(reverse=True)
            i = candidates[0][1]
            kept[i][t] += 1
            qty -= 1
        leftover[t] = qty

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

    rng = random.Random(2026 + target_k)
    for t in TYPE_ORDER_ALL:
        while leftover[t] > 0:
            i = rng.randrange(target_k)
            kept[i][t] += 1
            leftover[t] -= 1

    return kept


# ============================================================
# SA + LNS（外层减车）
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


def block_move_neighbor(quotas: List[Dict[str, int]], rng: random.Random) -> List[Dict[str, int]]:
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


def make_neighbor(quotas: List[Dict[str, int]], plans: List[VehicleResult], truck: Truck, rng: random.Random) -> List[Dict[str, int]]:
    op = rng.choice(["block", "swap", "g3", "lns", "block", "lns"])
    if op == "block":
        return block_move_neighbor(quotas, rng)
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

def solve_problem_12_ultimate_ga(
    truck: Truck,
    sa_iterations: int = 140,
    min_extra_over_lb: int = 0,
) -> Tuple[int, List[VehicleResult], Dict[str, object]]:
    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)

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
        quotas, plans, _ = simulated_annealing_optimize(
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
            "target_counts", "actual_counts", "loaded_weight_kg", "loaded_volume_cm3",
            "feasible_full_pack", "policy_desc"
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
                vp.policy_desc,
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
    K, plans, summary = solve_problem_12_ultimate_ga(truck, sa_iterations=sa_iterations)
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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 GA增强单车策略 + 外层减车")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2(final)", help="输出目录")
    parser.add_argument("--sa-iterations", type=int, default=140, help="每轮压缩的 SA 迭代次数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    for name in truck_list:
        truck = TRUCKS[name]
        print("\\n" + "=" * 68)
        print(f"开始求解问题1.2：{truck.name}")
        print("=" * 68)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        summary = solve_for_truck(truck, outdir, args.sa_iterations)
        print(summary)


if __name__ == "__main__":
    main()
