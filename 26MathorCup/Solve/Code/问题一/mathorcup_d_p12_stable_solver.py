
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2 稳定版
固定单一车型，采用“G3底层专区 + 其余货物分层分排”构造式贪心算法。

特点：
1. 不使用复杂三维空间切分，避免“放1件就碎空间”的失稳问题；
2. G3（易碎件）只放在底层左侧专区，单层摆放，不在其上方继续堆放；
3. 其余货物（G4/G5/G1/G2）在右侧主装载区内，按层（z方向）+ 排（y方向）+ 列（x方向）进行稳定构造；
4. 每一层高度固定，层内按行排布，行内按列摆放；
5. 输出逐件货物坐标、姿态、车辆汇总。

说明：
- 这是工程化近似算法，强调可运行、可解释和稳定性；
- 不保证全局最优，但通常会比复杂失稳启发式更可靠；
- 若需要进一步减少车辆数，可在此代码基础上继续做局部改良。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
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
    actual_counts: Dict[str, int]
    used_weight: float
    used_volume: int


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

TYPE_ORDER_MAIN = ["G4", "G5", "G1", "G2"]  # 主装载区优先序
TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]


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

    # 只有定向件仍保持固定方向
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


ORIENTATIONS: Dict[str, Tuple[Orientation, ...]] = {k: generate_orientations(v) for k, v in CARGO_TYPES.items()}


# ============================================================
# 基础工具
# ============================================================

def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    sv = used_volume / truck.effective_volume
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def lower_bound_vehicle_count(truck: Truck) -> Tuple[int, int, int]:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    basic = max(math.ceil(total_volume / truck.effective_volume), math.ceil(total_weight / truck.max_weight))

    # G3 底层下界（用最佳底面积姿态估计）
    best_floor = 0
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            best_floor = max(best_floor, (truck.length // l) * (truck.width // w))
    g3_lb = math.ceil(CARGO_TYPES["G3"].quantity / max(1, best_floor))
    return max(basic, g3_lb), basic, g3_lb


def choose_best_grid_fit(area_length: int, area_width: int, type_id: str) -> Optional[Tuple[Orientation, int, int]]:
    """
    返回在给定矩形区域内，对某货类最优的底面平铺姿态及列数/行数
    """
    best = None  # (count, used_area_ratio, ori, nx, ny)
    for ori in ORIENTATIONS[type_id]:
        l, w, h = ori.size
        nx = area_length // l
        ny = area_width // w
        count = nx * ny
        if count <= 0:
            continue
        used_area = count * l * w
        ratio = used_area / max(1, area_length * area_width)
        cand = (count, ratio, ori, nx, ny)
        if best is None or cand[:2] > best[:2]:
            best = cand
    if best is None:
        return None
    _, _, ori, nx, ny = best
    return ori, nx, ny


# ============================================================
# G3 底层专区
# ============================================================

def compute_g3_target_for_vehicle(truck: Truck, remaining: Dict[str, int]) -> int:
    """
    给当前车估一个 G3 目标量：既不要太多占死主区，也不要太少导致拖到最后。
    """
    if remaining["G3"] <= 0:
        return 0

    # 先估最优底层容量
    best_floor = 0
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            best_floor = max(best_floor, (truck.length // l) * (truck.width // w))

    # 保守使用：取底层理论最大数的一半到 2/3 左右
    target = min(remaining["G3"], max(6, int(best_floor * 0.6)))
    return target


def place_g3_zone(
    truck: Truck,
    remaining: Dict[str, int],
    vehicle_index: int,
    placed: List[PlacedCargo],
    used_weight: float,
    used_volume: int,
    serial_counter: Counter
) -> Tuple[int, float, int]:
    """
    在车厢左侧底层布置 G3，返回占用的专区宽度 g3_zone_width、更新后的重量/体积。
    规则：
    - 仅底层
    - 用最适合的姿态在左侧区域规则平铺
    """
    target = compute_g3_target_for_vehicle(truck, remaining)
    if target <= 0:
        return 0, used_weight, used_volume

    best_plan = None  # (placed_count, zone_width, ori, nx, ny)
    for ori in ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h > truck.effective_height:
            continue
        nx = truck.length // l
        if nx <= 0:
            continue

        # 为达到 target，需要多少行（沿宽方向）
        ny_need = math.ceil(target / nx)
        zone_width = ny_need * w
        if zone_width > truck.width:
            # 能放的最大行数
            ny = truck.width // w
            cnt = nx * ny
            if cnt <= 0:
                continue
            zone_width = ny * w
        else:
            ny = ny_need
            cnt = target

        # 实际上能放满 nx * ny
        cnt = min(nx * ny, remaining["G3"])
        if cnt <= 0:
            continue

        if best_plan is None or cnt > best_plan[0] or (cnt == best_plan[0] and zone_width < best_plan[1]):
            best_plan = (cnt, zone_width, ori, nx, ny)

    if best_plan is None:
        return 0, used_weight, used_volume

    cnt, zone_width, ori, nx, ny = best_plan
    l, w, h = ori.size

    placed_count = 0
    for j in range(ny):
        for i in range(nx):
            if remaining["G3"] <= 0 or placed_count >= cnt:
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
            remaining["G3"] -= 1
            used_weight += p.weight
            used_volume += p.volume
            placed_count += 1
        if placed_count >= cnt:
            break

    return zone_width, used_weight, used_volume


# ============================================================
# 主装载区：分层 + 分排 + 分列
# ============================================================

def candidate_layer_types(remaining: Dict[str, int], remaining_height: int, truck: Truck, main_width: int) -> List[Tuple[str, Orientation, int]]:
    """
    为新的一层挑选候选货类及姿态，返回列表 (type_id, ori, rough_score)
    """
    cands = []
    for type_id in TYPE_ORDER_MAIN:
        if remaining[type_id] <= 0:
            continue
        for ori in ORIENTATIONS[type_id]:
            l, w, h = ori.size
            if h > remaining_height:
                continue
            if l > truck.length or w > main_width:
                continue
            # 粗分：剩余量大、单件底面大、层高不太浪费优先
            base = remaining[type_id] / max(1, CARGO_TYPES[type_id].quantity)
            area = (l * w) / max(1, truck.length * main_width)
            height_fit = h / max(1, remaining_height)
            score = 1000 * base + 100 * area + 10 * height_fit
            cands.append((type_id, ori, int(score * 1000)))
    cands.sort(key=lambda x: x[2], reverse=True)
    return cands


def fill_one_row(
    truck: Truck,
    remaining: Dict[str, int],
    vehicle_index: int,
    z: int,
    y: int,
    row_height: int,
    x_start: int,
    area_length: int,
    serial_counter: Counter,
    layer_height: int,
) -> Tuple[List[PlacedCargo], int, float, int]:
    """
    在一排中从左到右填充，统一用行高 row_height，允许选择 G4/G5/G1/G2。
    """
    placed_row: List[PlacedCargo] = []
    x = x_start
    used_weight = 0.0
    used_volume = 0
    row_max_width = 0

    while x < x_start + area_length:
        best = None  # (score, type_id, ori)
        remain_len = x_start + area_length - x

        for type_id in TYPE_ORDER_MAIN:
            if remaining[type_id] <= 0:
                continue
            cargo = CARGO_TYPES[type_id]
            for ori in ORIENTATIONS[type_id]:
                l, w, h = ori.size
                if h > layer_height:
                    continue
                if w > row_height:
                    continue
                if l > remain_len:
                    continue

                # 简单行内评分
                fill_ratio = (l * w) / max(1, remain_len * row_height)
                remain_ratio = remaining[type_id] / max(1, cargo.quantity)
                heavy_bonus = cargo.weight / 25.0
                score = 0.55 * fill_ratio + 0.25 * remain_ratio + 0.20 * heavy_bonus
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
        remaining[type_id] -= 1
        used_weight += p.weight
        used_volume += p.volume
        x += l
        row_max_width = max(row_max_width, w)

    return placed_row, row_max_width, used_weight, used_volume


def fill_main_zone_layers(
    truck: Truck,
    remaining: Dict[str, int],
    vehicle_index: int,
    g3_zone_width: int,
    placed: List[PlacedCargo],
    used_weight: float,
    used_volume: int,
    serial_counter: Counter,
) -> Tuple[float, int]:
    """
    在主装载区（y >= g3_zone_width）进行分层构造。
    """
    main_width = truck.width - g3_zone_width
    if main_width <= 0:
        return used_weight, used_volume

    z = 0
    while z < truck.effective_height:
        remaining_height = truck.effective_height - z
        cands = candidate_layer_types(remaining, remaining_height, truck, main_width)
        if not cands:
            break

        # 选当前层的主高度（由最佳候选决定）
        type_id0, ori0, _ = cands[0]
        layer_height = ori0.size[2]
        if layer_height <= 0 or z + layer_height > truck.effective_height:
            break

        y = g3_zone_width
        layer_placed_any = False

        while y < truck.width:
            remain_width = truck.width - y
            if remain_width <= 0:
                break

            # 行高取不超过层高、且能放入某类货物的较优宽度
            row_cands = []
            for type_id in TYPE_ORDER_MAIN:
                if remaining[type_id] <= 0:
                    continue
                for ori in ORIENTATIONS[type_id]:
                    l, w, h = ori.size
                    if h <= layer_height and w <= remain_width and l <= truck.length:
                        row_cands.append((w, type_id, ori))
            if not row_cands:
                break

            # 优先较宽的行，减少碎片
            row_cands.sort(key=lambda x: x[0], reverse=True)
            row_height = row_cands[0][0]

            row_items, row_used_width, add_w, add_v = fill_one_row(
                truck=truck,
                remaining=remaining,
                vehicle_index=vehicle_index,
                z=z,
                y=y,
                row_height=row_height,
                x_start=0,
                area_length=truck.length,
                serial_counter=serial_counter,
                layer_height=layer_height,
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


# ============================================================
# 单车构造
# ============================================================

def pack_one_vehicle_stable(
    truck: Truck,
    remaining_counts: Dict[str, int],
    vehicle_index: int,
) -> VehicleResult:
    placed: List[PlacedCargo] = []
    used_weight = 0.0
    used_volume = 0
    serial_counter = Counter()

    # Step 1: G3 底层专区
    g3_zone_width, used_weight, used_volume = place_g3_zone(
        truck=truck,
        remaining=remaining_counts,
        vehicle_index=vehicle_index,
        placed=placed,
        used_weight=used_weight,
        used_volume=used_volume,
        serial_counter=serial_counter,
    )

    # Step 2: 主装载区分层构造
    used_weight, used_volume = fill_main_zone_layers(
        truck=truck,
        remaining=remaining_counts,
        vehicle_index=vehicle_index,
        g3_zone_width=g3_zone_width,
        placed=placed,
        used_weight=used_weight,
        used_volume=used_volume,
        serial_counter=serial_counter,
    )

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
    )


# ============================================================
# 问题1.2：逐车贪心
# ============================================================

def solve_problem_12_stable(truck: Truck) -> Tuple[List[VehicleResult], Dict[str, object]]:
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER_ALL}
    plans: List[VehicleResult] = []

    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)

    vehicle_index = 1
    prev_total = sum(remaining.values())

    while sum(remaining.values()) > 0:
        print(f"[{truck.name}] 正在构造第 {vehicle_index} 辆车，当前剩余: {remaining}", flush=True)
        plan = pack_one_vehicle_stable(truck, remaining, vehicle_index)
        loaded_now = sum(plan.actual_counts.values())
        if loaded_now == 0:
            raise RuntimeError(f"{truck.name} 第 {vehicle_index} 辆车未能装入任何货物，算法停止。")

        plans.append(plan)
        sv, wv, _ = truck_score(truck, plan.used_volume, plan.used_weight)
        print(
            f"[{truck.name}] 第 {vehicle_index} 辆车完成："
            f"装入 {loaded_now} 件，空间利用率={sv:.4f}，载重利用率={wv:.4f}",
            flush=True
        )

        after_total = sum(remaining.values())
        if after_total >= prev_total:
            raise RuntimeError(f"{truck.name} 构造后未减少剩余货物，算法停止。")
        prev_total = after_total
        vehicle_index += 1

    K = len(plans)
    avg_sv = sum(p.used_volume for p in plans) / (K * truck.effective_volume)
    avg_wv = sum(p.used_weight for p in plans) / (K * truck.max_weight)
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
    return plans, summary


# ============================================================
# 输出
# ============================================================

def write_vehicle_summary_csv(path: str, plans: List[VehicleResult], truck: Truck) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_weight_kg", "loaded_volume_cm3"
        ])
        for vp in plans:
            sv, wv, fs = truck_score(truck, vp.used_volume, vp.used_weight)
            w.writerow([
                vp.vehicle_id,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                vp.actual_counts,
                round(vp.used_weight, 3),
                vp.used_volume,
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


def solve_for_truck(truck: Truck, outdir: str) -> Dict[str, object]:
    plans, summary = solve_problem_12_stable(truck)
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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 稳定版（G3专区 + 分层分排）")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="output_p12_stable", help="输出目录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for name in truck_list:
        truck = TRUCKS[name]
        print("\n" + "=" * 56)
        print(f"开始求解问题1.2：{truck.name}")
        print("=" * 56)
        summary = solve_for_truck(truck, args.outdir)
        print(summary)


if __name__ == "__main__":
    main()
