# -*- coding: utf-8 -*-
"""
附件2通用性检验（问题1.1 终极版）
Block-Combination Layered Beam Greedy for 3D Packing

目标：
- 单车空间利用率最大化
- 针对附件2硬编码数据
- 每类货物 100 件
- 忽略重量约束
- 全按标准件处理

核心升级：
1. 分层装载：先确定层高，再做层内宽度规划
2. 行宽组合：不是逐行贪心，而是先搜索一组 row heights 去尽量铺满车宽
3. 行内长度填充：每一行沿 x 方向做最佳匹配
4. 少量束搜索：对层高候选和行宽组合保留多个候选，避免过早贪心
5. 多策略试探：对不同货物排序和候选组合做多轮搜索，取最好结果

说明：
- 这版是“终极工程启发式”，目标是显著提升利用率，但不保证任何特定车型一定 >0.75。
"""

from __future__ import annotations

import csv
import os
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


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
    return used_volume / max(1, truck.effective_volume)


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


def alignment_bonus_dims(truck: Truck, l: int, w: int, h: int) -> float:
    rx = truck.length % l
    ry = truck.width % w
    rz = truck.effective_height % h
    return (1 / (1 + rx)) + (1 / (1 + ry)) + (1 / (1 + rz))


def unique_layer_heights(remaining: Dict[str, int], remain_height: int) -> List[int]:
    hs = set()
    for t in TYPE_ORDER:
        if remaining[t] <= 0:
            continue
        for ori in ORIENTATIONS[t]:
            if ori.size[2] <= remain_height:
                hs.add(ori.size[2])
    return sorted(hs)


# =========================================================
# 结果类
# =========================================================
class PackedTruck:
    def __init__(self, truck: Truck):
        self.truck = truck
        self.used_volume = 0
        self.actual_counts = Counter()
        self.placed: List[dict] = []

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


# =========================================================
# 行内长度填充
# =========================================================
def eval_item_for_row(
    truck: Truck,
    type_id: str,
    ori: Orientation,
    remaining: Dict[str, int],
    remain_len: int,
    row_height: int,
    layer_height: int,
    remain_width_total: int,
    x_pos: int,
) -> Optional[float]:
    l, w, h = ori.size

    if remaining[type_id] <= 0:
        return None
    if l > remain_len or w > row_height or h > layer_height:
        return None

    cargo = CARGO_TYPES[type_id]
    len_fill = l / max(1, remain_len)
    row_fill = (l * w) / max(1, remain_len * row_height)
    base_fill = (l * w) / max(1, truck.length * row_height)
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    align = alignment_bonus_dims(truck, l, w, h)
    low_x_bonus = 1 / (1 + x_pos)

    # 偏好当前层高充分利用
    height_match = h / max(1, layer_height)

    score = (
        0.26 * len_fill +
        0.22 * row_fill +
        0.12 * base_fill +
        0.10 * remain_bonus +
        0.12 * align +
        0.08 * height_match +
        0.10 * low_x_bonus
    )
    return score


def fill_row_best(
    packed: PackedTruck,
    remaining: Dict[str, int],
    z0: int,
    y0: int,
    row_height: int,
    layer_height: int,
    strategy: str,
):
    truck = packed.truck
    x = 0
    type_order = choose_type_order(strategy)

    while x < truck.length:
        remain_len = truck.length - x
        best = None  # (score, type_id, ori)

        for type_id in type_order:
            for ori in ORIENTATIONS[type_id]:
                val = eval_item_for_row(
                    truck, type_id, ori, remaining,
                    remain_len, row_height, layer_height,
                    truck.width - y0, x
                )
                if val is None:
                    continue
                if best is None or val > best[0]:
                    best = (val, type_id, ori)

        if best is None:
            break

        _, type_id, ori = best
        l, w, h = ori.size
        packed.add_item(type_id, ori, x, y0, z0)
        remaining[type_id] -= 1
        x += l


# =========================================================
# 行宽组合搜索
# =========================================================
def candidate_row_widths(remaining: Dict[str, int], layer_height: int, truck: Truck) -> List[int]:
    ws = set()
    for t in TYPE_ORDER:
        if remaining[t] <= 0:
            continue
        for ori in ORIENTATIONS[t]:
            l, w, h = ori.size
            if h <= layer_height and l <= truck.length and w <= truck.width:
                ws.add(w)
    return sorted(ws)


def search_row_width_patterns(
    truck: Truck,
    remaining: Dict[str, int],
    layer_height: int,
    beam_width: int = 12,
    max_rows: int = 8,
) -> List[List[int]]:
    """
    在一层内，搜索若干组 row heights，使其尽量铺满车宽。
    """
    widths = candidate_row_widths(remaining, layer_height, truck)
    if not widths:
        return []

    # 状态：(used_width, pattern, score)
    states: List[Tuple[int, List[int], float]] = [(0, [], 0.0)]

    for _ in range(max_rows):
        nxt = []
        for used, pattern, score in states:
            remain_w = truck.width - used
            for w in widths:
                if w > remain_w:
                    continue
                # 更鼓励接近铺满
                fill_gain = w / truck.width
                remain_penalty = (remain_w - w) / truck.width
                local_score = score + 0.7 * fill_gain - 0.15 * remain_penalty
                nxt.append((used + w, pattern + [w], local_score))

        if not nxt:
            break

        # 保留若干最优状态
        nxt.sort(key=lambda x: (x[2], x[0], -len(x[1])), reverse=True)
        dedup = []
        seen = set()
        for used, pattern, score in nxt:
            key = (used, tuple(pattern))
            if key in seen:
                continue
            seen.add(key)
            dedup.append((used, pattern, score))
            if len(dedup) >= beam_width:
                break
        states = dedup

    states.sort(key=lambda x: (x[0] / truck.width, x[2], -len(x[1])), reverse=True)
    return [pattern for _, pattern, _ in states[:beam_width]]


# =========================================================
# 层高选择
# =========================================================
def eval_layer_height(
    truck: Truck,
    remaining: Dict[str, int],
    layer_height: int,
) -> float:
    score = 0.0
    cnt = 0
    for t in TYPE_ORDER:
        if remaining[t] <= 0:
            continue
        best_local = 0.0
        for ori in ORIENTATIONS[t]:
            l, w, h = ori.size
            if h != layer_height:
                continue
            local = alignment_bonus_dims(truck, l, w, h) + (l * w) / max(1, truck.length * truck.width)
            if local > best_local:
                best_local = local
        if best_local > 0:
            score += best_local
            cnt += 1
    if cnt == 0:
        return -1e18
    return score / cnt


def candidate_layer_plans(
    truck: Truck,
    remaining: Dict[str, int],
    remain_height: int,
    topk_heights: int = 4,
    beam_width_patterns: int = 10,
):
    hs = unique_layer_heights(remaining, remain_height)
    if not hs:
        return []

    scored_heights = []
    for h in hs:
        scored_heights.append((eval_layer_height(truck, remaining, h), h))
    scored_heights.sort(reverse=True)

    plans = []
    for _, layer_h in scored_heights[:topk_heights]:
        patterns = search_row_width_patterns(truck, remaining, layer_h, beam_width=beam_width_patterns)
        for p in patterns:
            used_w = sum(p)
            width_util = used_w / truck.width
            plans.append((0.6 * width_util + 0.4 * eval_layer_height(truck, remaining, layer_h), layer_h, p))

    plans.sort(reverse=True)
    return plans[:beam_width_patterns]


# =========================================================
# 模拟某个层方案（不改原状态）
# =========================================================
def simulate_layer_plan(
    truck: Truck,
    base_remaining: Dict[str, int],
    z0: int,
    layer_h: int,
    row_pattern: List[int],
    strategy: str,
):
    packed = PackedTruck(truck)
    remaining = base_remaining.copy()

    y = 0
    for row_h in row_pattern:
        if y + row_h > truck.width:
            break
        fill_row_best(packed, remaining, z0, y, row_h, layer_h, strategy)
        y += row_h

    return packed, remaining


# =========================================================
# 多层束搜索
# =========================================================
def solve_one_truck_ultimate(truck: Truck, strategy: str) -> PackedTruck:
    initial_remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}

    # 状态：(z, remaining, packed, score)
    beam = [(0, initial_remaining, PackedTruck(truck), 0.0)]
    best_state = beam[0]

    while beam:
        next_beam = []

        for z, remaining, packed, score in beam:
            if z >= truck.effective_height:
                next_beam.append((z, remaining, packed, score))
                continue

            remain_height = truck.effective_height - z
            layer_plans = candidate_layer_plans(truck, remaining, remain_height, topk_heights=4, beam_width_patterns=8)

            if not layer_plans:
                next_beam.append((z, remaining, packed, score))
                continue

            expanded = False
            for _, layer_h, row_pattern in layer_plans:
                layer_packed, new_remaining = simulate_layer_plan(truck, remaining, z, layer_h, row_pattern, strategy)

                if sum(layer_packed.actual_counts.values()) == 0:
                    continue

                expanded = True
                new_packed = PackedTruck(truck)
                new_packed.placed = packed.placed + layer_packed.placed
                new_packed.used_volume = packed.used_volume + layer_packed.used_volume
                new_packed.actual_counts = packed.actual_counts + layer_packed.actual_counts

                new_score = fullness_score(new_packed.used_volume, truck)
                next_beam.append((z + layer_h, new_remaining, new_packed, new_score))

            if not expanded:
                next_beam.append((z, remaining, packed, score))

        if not next_beam:
            break

        next_beam.sort(key=lambda x: (x[3], x[2].used_volume, sum(x[2].actual_counts.values())), reverse=True)
        beam = next_beam[:6]
        if beam[0][3] > best_state[3]:
            best_state = beam[0]

        # 所有状态都不能继续扩展
        if all(item[0] >= truck.effective_height or sum(item[1].values()) == 0 for item in beam):
            break

    return best_state[2]


# =========================================================
# 多策略试探
# =========================================================
def build_one_vehicle_best(truck: Truck) -> PackedTruck:
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
        plan = solve_one_truck_ultimate(truck, st)
        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue

        sv = fullness_score(plan.used_volume, truck)
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

        sv = fullness_score(plan.used_volume, truck)

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
    outdir = os.path.join(base_dir, "附件2_通用性检验结果_终极版")

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
