
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题1.2
固定单一车型，采用“贪心逐车装满”启发式算法，把附件1全部货物装完，并统计车辆数。

算法思想：
1. 每次只构造当前一辆车，不做全局多车联动搜索；
2. 在当前车内，直接在“剩余货物集合”上做逐件放置：
   - 优先考虑易碎件 G3 的底层放置；
   - 再考虑大件/定向件 G4/G5；
   - 最后用 G1/G2 填缝；
3. 每次在当前自由空间中，枚举可放置货物类型与合法姿态，选取得分最高的一个放入；
4. 当前车无法再放置任何货物时，结束该车，继续下一辆车；
5. 输出每辆车明细与车辆汇总。

说明：
- 这是工程化近似算法，强调“稳定可运行 + 可解释 + 能输出坐标姿态”；
- 不保证全局最优，但通常比复杂多车联动修复更稳定；
- 以车厢右后下为原点，x/y/z 分别对应长/宽/高方向。
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from collections import Counter
from dataclasses import dataclass
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
    max_support_pressure: float = 500.0  # kg/m^2
    top_clearance: int = 3

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
class VehicleResult:
    vehicle_id: str
    placed: List[PlacedCargo]
    target_counts: Dict[str, int]
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

TYPE_ORDER = ["G3", "G4", "G5", "G1", "G2"]

def dynamic_type_order(remaining_counts: Dict[str, int]) -> List[str]:
    """
    动态排序：
    - 剩余数量多的优先
    - G3（难装）稍微优先
    """
    return sorted(
        TYPE_ORDER,
        key=lambda t: (
            -remaining_counts[t],      # 数量多优先
            0 if t == "G3" else 1      # G3稍微优先
        )
    )
# ============================================================
# 姿态与工具
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

    out: List[Orientation] = []
    seen = set()
    for a, b, c, name in dims:
        key = (a, b, c)
        if key not in seen:
            seen.add(key)
            out.append(Orientation(len(out) + 1, key, name))
    return tuple(out)


ORIENTATIONS = {k: generate_orientations(v) for k, v in CARGO_TYPES.items()}


def truck_score(truck: Truck, used_volume: int, used_weight: float) -> Tuple[float, float, float]:
    space_util = used_volume / truck.effective_volume
    weight_util = used_weight / truck.max_weight
    fullness = 0.72 * space_util + 0.28 * weight_util
    return space_util, weight_util, fullness


def floor_capacity_for_type(truck: Truck, type_id: str) -> int:
    cargo = CARGO_TYPES[type_id]
    best = 0
    for ori in ORIENTATIONS[type_id]:
        l, w, h = ori.size
        if h > truck.effective_height:
            continue
        best = max(best, (truck.length // l) * (truck.width // w))
    return best


def lower_bound_vehicle_count(truck: Truck) -> Tuple[int, int, int]:
    total_volume = sum(c.volume * c.quantity for c in CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in CARGO_TYPES.values())
    basic = max(math.ceil(total_volume / truck.effective_volume), math.ceil(total_weight / truck.max_weight))
    g3_cap = floor_capacity_for_type(truck, "G3")
    g3_lb = math.ceil(CARGO_TYPES["G3"].quantity / max(1, g3_cap))
    return max(basic, g3_lb), basic, g3_lb


def sort_spaces_dblf(spaces: Sequence[Space]) -> List[Space]:
    return sorted(spaces, key=lambda s: (s.z, s.y, s.x, s.volume))


def remove_contained_spaces(spaces: List[Space]) -> List[Space]:
    out: List[Space] = []
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
                (a.x, a.y, a.z, a.length, a.width, a.height) != (b.x, b.y, b.z, b.length, b.width, b.height)
            ):
                contained = True
                break
        if not contained and a.length > 0 and a.width > 0 and a.height > 0:
            out.append(a)
    return out


def try_merge_two_spaces(a: Space, b: Space) -> Optional[Space]:
    support_same = (
        a.support_item_id == b.support_item_id and
        a.support_type_id == b.support_type_id and
        a.support_length == b.support_length and
        a.support_width == b.support_width
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


# ============================================================
# 单车逐件贪心构造
# ============================================================

def can_place(
    truck: Truck,
    cargo: CargoType,
    ori: Orientation,
    space: Space,
    placed_map: Dict[str, PlacedCargo],
    used_weight: float,
) -> bool:
    l, w, h = ori.size

    if l > space.length or w > space.width or h > space.height:
        return False
    if used_weight + cargo.weight > truck.max_weight + 1e-9:
        return False
    if space.z + h > truck.effective_height:
        return False

    # G3（易碎件）只允许在底板上单层摆放
    if cargo.fragile and space.z > 0:
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
        pressure = (support.direct_supported_weight + cargo.weight) / max(1e-9, support.top_area_m2)
        if pressure > CARGO_TYPES[support.type_id].max_support_pressure + 1e-9:
            return False

    return True


def placement_gain(
    truck: Truck,
    cargo: CargoType,
    ori: Orientation,
    space: Space,
    used_weight: float,
    used_volume: int,
) -> float:
    l, w, h = ori.size
    fill_ratio = (l * w * h) / max(1, space.length * space.width * space.height)
    low_z_bonus = 1.0 / (1.0 + space.z)
    tight_bonus = 1.0 / (1.0 + (space.length - l) + (space.width - w) + (space.height - h))
    base_area_fit = (l * w) / max(1, space.length * space.width)

    next_used_weight = used_weight + cargo.weight
    next_used_volume = used_volume + cargo.volume
    sv, wv, fullness = truck_score(truck, next_used_volume, next_used_weight)

    g3_bonus = 0.25 if cargo.type_id == "G3" and space.z == 0 else 0.0
    big_bonus = 0.10 if cargo.type_id in ("G4", "G5") and space.z == 0 else 0.0
    fill_bonus = 0.08 if cargo.type_id in ("G1", "G2") else 0.0

    return (
        fullness
        + 0.10 * fill_ratio
        + 0.04 * low_z_bonus
        + 0.03 * tight_bonus
        + 0.02 * base_area_fit
        + g3_bonus
        + big_bonus
        + fill_bonus
        + 0.02 * sv
        + 0.01 * wv
    )


def split_space(space: Space, placed: PlacedCargo) -> List[Space]:
    out: List[Space] = []
    if space.length > placed.length:
        out.append(
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
        out.append(
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
        out.append(
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
    return out


def pack_one_vehicle_greedily(
    truck: Truck,
    remaining_counts: Dict[str, int],
    vehicle_index: int,
) -> VehicleResult:
    spaces = sort_spaces_dblf([Space(0, 0, 0, truck.length, truck.width, truck.effective_height, None, None, truck.length, truck.width)])
    placed: List[PlacedCargo] = []
    used_weight = 0.0
    used_volume = 0
    local_counts = {t: 0 for t in TYPE_ORDER}
    serial_counter = Counter()

    while True:
        placed_map = {p.item_id: p for p in placed}
        best = None  # (score, type_id, ori, space_idx)

        for type_id in dynamic_type_order(remaining_counts):
            if remaining_counts[type_id] <= 0:
                continue

            cargo = CARGO_TYPES[type_id]

            if type_id == "G3":
                cap = floor_capacity_for_type(truck, "G3")
                if local_counts["G3"] >= cap:
                    continue
                if local_counts["G3"] >= max(8, cap // 2):
                    continue

            for space_idx, space in enumerate(spaces[:18]):
                for ori in ORIENTATIONS[type_id]:
                    if can_place(truck, cargo, ori, space, placed_map, used_weight):
                        gain = placement_gain(truck, cargo, ori, space, used_weight, used_volume)
                        if best is None or gain > best[0]:
                            best = (gain, type_id, ori, space_idx)

        if best is None:
            break

        _, type_id, ori, space_idx = best
        cargo = CARGO_TYPES[type_id]
        space = spaces[space_idx]
        l, w, h = ori.size

        serial_counter[type_id] += 1
        item_id = f"{type_id}_{vehicle_index:03d}_{serial_counter[type_id]:04d}"

        placed_item = PlacedCargo(
            item_id=item_id,
            type_id=type_id,
            category=cargo.category,
            x=space.x,
            y=space.y,
            z=space.z,
            length=l,
            width=w,
            height=h,
            weight=cargo.weight,
            orientation_id=ori.orient_id,
            rotation=ori.rotation,
            support_by=space.support_item_id,
            truck_id=f"{truck.name}_{vehicle_index:03d}",
        )

        placed.append(placed_item)
        if placed_item.support_by is not None:
            for p in placed:
                if p.item_id == placed_item.support_by:
                    p.direct_supported_weight += cargo.weight
                    break

        used_weight += cargo.weight
        used_volume += cargo.volume
        local_counts[type_id] += 1
        remaining_counts[type_id] -= 1

        new_spaces = [s for idx, s in enumerate(spaces) if idx != space_idx]
        new_spaces.extend(split_space(space, placed_item))
        spaces = sort_spaces_dblf(merge_spaces(new_spaces))

    actual_counts = dict(Counter(p.type_id for p in placed))
    return VehicleResult(
        vehicle_id=f"{truck.name}_{vehicle_index:03d}",
        placed=placed,
        target_counts=local_counts.copy(),
        actual_counts=actual_counts,
        used_weight=used_weight,
        used_volume=used_volume,
    )


# ============================================================
# 问题1.2：逐车贪心装满
# ============================================================

def solve_problem_12_greedy_by_vehicle(truck: Truck) -> Tuple[List[VehicleResult], Dict[str, object]]:
    remaining = {t: CARGO_TYPES[t].quantity for t in TYPE_ORDER}
    plans: List[VehicleResult] = []

    lb, basic_lb, g3_lb = lower_bound_vehicle_count(truck)
    print(f"[{truck.name}] 理论下界 LB = {lb} (体积/重量={basic_lb}, G3底面积={g3_lb})", flush=True)

    vehicle_index = 1
    prev_total = sum(remaining.values())

    while sum(remaining.values()) > 0:
        before = remaining.copy()
        print(f"[{truck.name}] 正在构造第 {vehicle_index} 辆车，当前剩余: {before}", flush=True)
        plan = pack_one_vehicle_greedily(truck, remaining, vehicle_index)
        loaded_now = sum(plan.actual_counts.values())
        if loaded_now == 0:
            raise RuntimeError(f"{truck.name} 第 {vehicle_index} 辆车未能装入任何货物，算法停止。")

        plans.append(plan)
        after_total = sum(remaining.values())
        print(
            f"[{truck.name}] 第 {vehicle_index} 辆车完成："
            f"装入 {loaded_now} 件，空间利用率={truck_score(truck, plan.used_volume, plan.used_weight)[0]:.4f}，"
            f"载重利用率={truck_score(truck, plan.used_volume, plan.used_weight)[1]:.4f}",
            flush=True
        )

        if after_total >= prev_total:
            raise RuntimeError(f"{truck.name} 贪心构造未减少剩余货物，算法停止。")
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


def write_items_csv(path: str, placed: Sequence[PlacedCargo]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "support_by", "truck_id"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.support_by or "", p.truck_id or ""
            ])


def solve_for_truck(truck: Truck, outdir: str) -> Dict[str, object]:
    plans, summary = solve_problem_12_greedy_by_vehicle(truck)
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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题1.2 贪心逐车装满版")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="output_p12_greedy", help="输出目录")
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
