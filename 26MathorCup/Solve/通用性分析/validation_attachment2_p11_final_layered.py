# -*- coding: utf-8 -*-
"""
附件2通用性检验（问题1.1 最终版）
Greedy + Layered Rows + Multi-Strategy for 3D Packing

核心改进：
1. 采用“分层-分行-逐件”装载框架，而不是无结构自由堆叠；
2. 每层先选层高，再在层内按“行”逐步填充；
3. 候选货物评分同时考虑：
   - 当前剩余长度填充率
   - 当前剩余宽度/层高匹配
   - 底面积利用率
   - 货物剩余数量
   - 与车厢尺寸的整除匹配度
4. 多策略试探，自动选择当前车型最优方案；
5. 专门用于附件2问题1.1单车满载率通用性检验。

简化设定：
- 每类货物数量统一 100 件
- 忽略重量约束
- 全部按标准件处理
- 仅验证典型封闭车型
"""

from __future__ import annotations

import csv
import os
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple


# =========================================================
# 数据结构
# =========================================================
@dataclass(frozen=True)
class Orientation:
    orient_id: int
    size: Tuple[int, int, int]
    rotation: str


@dataclass(frozen=True)
class CargoType:
    type_id: str
    name: str
    length: int
    width: int
    height: int
    quantity: int = 100

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def base_area(self) -> int:
        return self.length * self.width


@dataclass(frozen=True)
class Truck:
    name: str
    length: int
    width: int
    height: int
    cost: float

    @property
    def effective_height(self) -> int:
        return self.height

    @property
    def effective_volume(self) -> int:
        return self.length * self.width * self.effective_height


# =========================================================
# 附件2硬编码数据
# =========================================================
QUANTITY_EACH = 100

CARGO_TYPES: Dict[str, CargoType] = {
    "P1": CargoType("P1", "3.68L*4", 301, 301, 347, QUANTITY_EACH),
    "P2": CargoType("P2", "1.8L*6", 347, 238, 320, QUANTITY_EACH),
    "P3": CargoType("P3", "4L*4", 318, 265, 380, QUANTITY_EACH),
    "P4": CargoType("P4", "5L*4(异形瓶)", 345, 345, 395, QUANTITY_EACH),
    "P5": CargoType("P5", "5L*4(常规品)", 323, 322, 385, QUANTITY_EACH),
    "P6": CargoType("P6", "8L*2", 435, 226, 370, QUANTITY_EACH),
    "P7": CargoType("P7", "10L*2", 438, 225, 430, QUANTITY_EACH),
    "P8": CargoType("P8", "20L(软)", 306, 178, 495, QUANTITY_EACH),
}

TRUCKS: Dict[str, Truck] = {
    "单节柜": Truck("单节柜", 5900, 2350, 2390, 3625),
    "集装箱": Truck("集装箱", 12000, 2350, 2390, 2000),
    "超高柜": Truck("超高柜", 12000, 2350, 2690, 3900),
    "4.2米箱货": Truck("4.2米箱货", 4100, 1900, 2000, 2800),
    "6.2米箱货": Truck("6.2米箱货", 6000, 2000, 1900, 4500),
    "6.8米箱货": Truck("6.8米箱货", 6800, 2500, 2200, 5000),
    "9.6米箱货": Truck("9.6米箱货", 9500, 2500, 2200, 6500),
    "17米箱货": Truck("17米箱货", 17000, 2500, 2200, 11000),
}

TYPE_ORDER = list(CARGO_TYPES.keys())


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
# 工具函数
# =========================================================
def fullness_score(used_volume: int, truck: Truck) -> float:
    return used_volume / truck.effective_volume


def alignment_bonus(truck: Truck, l: int, w: int, h: int) -> float:
    rx = truck.length % l
    ry = truck.width % w
    rz = truck.effective_height % h
    return (1 / (1 + rx)) + (1 / (1 + ry)) + (1 / (1 + rz))


def best_layer_height_candidates(remaining: Dict[str, int]) -> List[int]:
    heights = set()
    for t in TYPE_ORDER:
        if remaining[t] <= 0:
            continue
        for ori in ORIENTATIONS[t]:
            heights.add(ori.size[2])
    return sorted(heights)


def choose_type_order(strategy: str) -> List[str]:
    if strategy == "volume_first":
        return sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].volume, reverse=True)
    if strategy == "base_first":
        return sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].base_area, reverse=True)
    if strategy == "height_first":
        return sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].height, reverse=True)
    if strategy == "small_first":
        return sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].volume)
    arr = TYPE_ORDER[:]
    random.shuffle(arr)
    return arr


# =========================================================
# 最终版分层装箱器
# =========================================================
class LayeredTruck:
    def __init__(self, truck: Truck):
        self.truck = truck
        self.used_volume = 0
        self.placed: List[dict] = []
        self.actual_counts = Counter()

    def add_item(self, type_id: str, ori: Orientation, x: int, y: int, z: int):
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]
        self.placed.append({
            "type_id": type_id,
            "product_name": cargo.name,
            "x": x,
            "y": y,
            "z": z,
            "length": l,
            "width": w,
            "height": h,
            "rotation": ori.rotation,
            "orientation_id": ori.orient_id,
        })
        self.used_volume += l * w * h
        self.actual_counts[type_id] += 1


def eval_item_for_row(
    truck: Truck,
    type_id: str,
    ori: Orientation,
    remaining: Dict[str, int],
    remain_len: int,
    row_height: int,
    layer_height: int,
    remain_width: int,
) -> float | None:
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if remaining[type_id] <= 0:
        return None
    if l > remain_len or w > remain_width or h > layer_height:
        return None
    if w > row_height:
        return None

    len_fill = l / max(1, remain_len)
    row_fill = (l * w) / max(1, remain_len * row_height)
    base_fill = (l * w) / max(1, remain_len * remain_width)
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    align = alignment_bonus(truck, l, w, h)
    height_match = h / max(1, layer_height)
    width_match = w / max(1, row_height)

    score = (
        0.28 * len_fill +
        0.22 * row_fill +
        0.16 * base_fill +
        0.10 * remain_bonus +
        0.12 * align +
        0.07 * height_match +
        0.05 * width_match
    )
    return score


def fill_one_row(
    truck_obj: LayeredTruck,
    remaining: Dict[str, int],
    z0: int,
    y0: int,
    row_height: int,
    layer_height: int,
    strategy: str,
) -> Tuple[int, bool]:
    """
    在当前层的当前行内，沿 x 方向填充。
    返回：(该行实际占用宽度, 是否放入过货物)
    """
    truck = truck_obj.truck
    x = 0
    placed_any = False
    type_order = choose_type_order(strategy)

    while x < truck.length:
        remain_len = truck.length - x
        best = None  # (score, type_id, ori)

        for type_id in type_order:
            for ori in ORIENTATIONS[type_id]:
                val = eval_item_for_row(
                    truck, type_id, ori, remaining,
                    remain_len, row_height, layer_height, row_height
                )
                if val is None:
                    continue
                if best is None or val > best[0]:
                    best = (val, type_id, ori)

        if best is None:
            break

        _, type_id, ori = best
        l, w, h = ori.size
        truck_obj.add_item(type_id, ori, x, y0, z0)
        remaining[type_id] -= 1
        x += l
        placed_any = True

    return row_height, placed_any


def fill_one_layer(
    truck_obj: LayeredTruck,
    remaining: Dict[str, int],
    z0: int,
    layer_height: int,
    strategy: str,
) -> bool:
    """
    在高度为 layer_height 的层内，按行填充。
    """
    truck = truck_obj.truck
    y = 0
    placed_any = False
    type_order = choose_type_order(strategy)

    while y < truck.width:
        remain_width = truck.width - y

        # 选当前行高度：尽量选择能放下、且宽度适中的候选
        row_candidates = []
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                l, w, h = ori.size
                if l <= truck.length and w <= remain_width and h <= layer_height:
                    width_fit = w / max(1, remain_width)
                    align = alignment_bonus(truck, l, w, h)
                    row_candidates.append((0.7 * width_fit + 0.3 * align, w))

        if not row_candidates:
            break

        row_candidates.sort(reverse=True)
        row_height = row_candidates[0][1]

        used_row_width, ok = fill_one_row(
            truck_obj, remaining, z0, y, row_height, layer_height, strategy
        )
        if not ok:
            break

        placed_any = True
        y += used_row_width

    return placed_any


def load_one_truck_layered(truck: Truck, strategy: str) -> LayeredTruck:
    truck_obj = LayeredTruck(truck)
    remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}

    z = 0
    while z < truck.effective_height:
        remaining_height = truck.effective_height - z
        layer_candidates = best_layer_height_candidates(remaining)
        layer_candidates = [h for h in layer_candidates if h <= remaining_height]
        if not layer_candidates:
            break

        # 选层高：优先选择更容易填满宽度和长度的层
        best_layer = None
        best_val = None

        for layer_h in layer_candidates:
            score = 0.0
            for t in TYPE_ORDER:
                if remaining[t] <= 0:
                    continue
                for ori in ORIENTATIONS[t]:
                    l, w, h = ori.size
                    if h == layer_h:
                        score += alignment_bonus(truck, l, w, h) + (l * w) / max(1, truck.length * truck.width)
            if best_layer is None or score > best_val:
                best_layer = layer_h
                best_val = score

        if best_layer is None:
            break

        ok = fill_one_layer(truck_obj, remaining, z, best_layer, strategy)
        if not ok:
            break
        z += best_layer

    return truck_obj


# =========================================================
# 多策略试探
# =========================================================
def build_one_vehicle_best(truck: Truck) -> LayeredTruck:
    strategies = [
        "volume_first",
        "base_first",
        "height_first",
        "small_first",
        "mixed",
    ]

    best_plan = None
    best_key = None

    for st in strategies:
        plan = load_one_truck_layered(truck, st)
        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue

        sv = plan.used_volume / truck.effective_volume
        diversity = len([k for k, v in plan.actual_counts.items() if v > 0])

        key = (
            round(sv, 8),
            loaded_cnt,
            diversity,
            plan.used_volume,
        )

        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key

    return best_plan


# =========================================================
# 求解问题1.1
# =========================================================
def solve_problem11_all_trucks():
    results = []

    for truck_name, truck in TRUCKS.items():
        print(f"\n开始求解问题1.1：{truck_name}")
        plan = build_one_vehicle_best(truck)

        if plan is None:
            raise RuntimeError(f"{truck_name} 未能生成可行装载方案。")

        sv = plan.used_volume / truck.effective_volume

        result = {
            "truck_name": truck_name,
            "truck_length_mm": truck.length,
            "truck_width_mm": truck.width,
            "truck_height_mm": truck.height,
            "truck_volume_mm3": truck.effective_volume,
            "used_volume_mm3": plan.used_volume,
            "space_utilization": round(sv, 6),
            "placed_item_count": sum(plan.actual_counts.values()),
            "actual_counts": dict(plan.actual_counts),
            "placed": plan.placed,
        }
        results.append(result)
        print(result)

    results.sort(key=lambda x: x["space_utilization"], reverse=True)
    return results


# =========================================================
# 输出
# =========================================================
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_csv(path: str, header: List[str], rows: List[List[object]]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_problem11_results(outdir: str, results: List[Dict[str, object]]) -> None:
    rows = []
    for r in results:
        actual_named = {CARGO_TYPES[k].name: v for k, v in r["actual_counts"].items()}
        rows.append([
            r["truck_name"],
            r["truck_length_mm"],
            r["truck_width_mm"],
            r["truck_height_mm"],
            r["truck_volume_mm3"],
            r["used_volume_mm3"],
            r["space_utilization"],
            r["placed_item_count"],
            str(actual_named),
        ])
    write_csv(
        os.path.join(outdir, "problem11_single_truck_fullness.csv"),
        [
            "truck_name", "truck_length_mm", "truck_width_mm", "truck_height_mm",
            "truck_volume_mm3", "used_volume_mm3", "space_utilization",
            "placed_item_count", "actual_counts_named"
        ],
        rows
    )


def write_item_details(outdir: str, results: List[Dict[str, object]]) -> None:
    details_dir = os.path.join(outdir, "problem11_item_details")
    ensure_dir(details_dir)

    for r in results:
        rows = []
        for p in r["placed"]:
            rows.append([
                p["type_id"], p["product_name"],
                p["x"], p["y"], p["z"],
                p["length"], p["width"], p["height"],
                p["orientation_id"], p["rotation"],
            ])
        write_csv(
            os.path.join(details_dir, f"{r['truck_name']}_items.csv"),
            ["type_id", "product_name", "x", "y", "z", "length", "width", "height", "orientation_id", "rotation"],
            rows
        )


# =========================================================
# 主程序
# =========================================================
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(base_dir, "附件2_通用性检验结果_最终版")

    print(f"读取产品种类数: {len(CARGO_TYPES)}")
    print(f"读取典型封闭车型数: {len(TRUCKS)}")
    print(f"产品列表: {[CARGO_TYPES[k].name for k in TYPE_ORDER]}")
    print(f"车型列表: {list(TRUCKS.keys())}")

    results = solve_problem11_all_trucks()
    write_problem11_results(outdir, results)
    write_item_details(outdir, results)

    print("\n问题1.1结果（前3名车型）:")
    for r in results[:3]:
        print(r)

    print(f"\n输出目录: {outdir}")


if __name__ == "__main__":
    main()
