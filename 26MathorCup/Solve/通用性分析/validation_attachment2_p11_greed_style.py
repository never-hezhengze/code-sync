# -*- coding: utf-8 -*-
"""
附件2通用性检验（问题1.1专用，借鉴 greed1.2 思路重写版）

核心思路（借鉴 greed1.2）：
1. 用轻量空间类 FastTruck 管理剩余空间；
2. 每次从有限个候选空间中，筛选“空间-货物-姿态”最佳匹配；
3. 用多种货物优先顺序策略分别试探，取当前车型的最好结果；
4. 目标改为：单车空间利用率最大化（问题1.1），不再做多车递推。

简化设定：
- 每类货物 100 件
- 忽略重量约束
- 全部按标准件处理
- 只验证典型封闭车型
"""

import csv
import os
import random
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple


# =========================================================
# 基础数据结构
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
# 参数（借鉴 greed1.2 风格）
# =========================================================
MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 50000
RANDOM_SEED = 2026
random.seed(RANDOM_SEED)


# =========================================================
# 工具函数
# =========================================================
def space_volume(sp):
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces):
    """
    优先保留更大的、更低的、更规整的空间
    """
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (-space_volume(s), s["z"], s["y"], s["x"]))
    return spaces


def fullness_score(used_volume, truck):
    return used_volume / truck.effective_volume


def alignment_bonus(truck, l, w, h):
    rx = truck.length % l
    ry = truck.width % w
    rz = truck.effective_height % h
    return (1 / (1 + rx)) + (1 / (1 + ry)) + (1 / (1 + rz))


# =========================================================
# 轻量货车类
# =========================================================
class FastTruck:
    def __init__(self, truck):
        self.truck = truck
        self.L = truck.length
        self.W = truck.width
        self.H = truck.effective_height

        self.spaces = [{
            "x": 0, "y": 0, "z": 0,
            "l": self.L, "w": self.W, "h": self.H
        }]
        self.spaces = sort_spaces(self.spaces)

        self.placed = []
        self.used_volume = 0
        self.actual_counts = Counter()

    def place_item(self, type_id, ori, sp_idx):
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        self.placed.append({
            "type_id": type_id,
            "product_name": cargo.name,
            "x": sp["x"],
            "y": sp["y"],
            "z": sp["z"],
            "length": l,
            "width": w,
            "height": h,
            "rotation": ori.rotation,
            "orientation_id": ori.orient_id,
        })

        self.used_volume += l * w * h
        self.actual_counts[type_id] += 1

        # 三切分
        right = {
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": sp["w"],
            "h": sp["h"]
        }
        front = {
            "x": sp["x"],
            "y": sp["y"] + w,
            "z": sp["z"],
            "l": l,
            "w": sp["w"] - w,
            "h": sp["h"]
        }
        upper = {
            "x": sp["x"],
            "y": sp["y"],
            "z": sp["z"] + h,
            "l": l,
            "w": w,
            "h": sp["h"] - h
        }

        self.spaces.pop(sp_idx)
        self.spaces.extend([right, front, upper])
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


# =========================================================
# 候选类型顺序（借鉴 greed1.2，多策略）
# =========================================================
def build_type_order(strategy):
    large_base = sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].base_area, reverse=True)
    large_vol = sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].volume, reverse=True)
    high_first = sorted(TYPE_ORDER, key=lambda t: CARGO_TYPES[t].height, reverse=True)

    if strategy == "base_first":
        return large_base
    elif strategy == "vol_first":
        return large_vol
    elif strategy == "high_first":
        return high_first
    elif strategy == "mixed":
        arr = TYPE_ORDER[:]
        random.shuffle(arr)
        return arr
    else:
        return TYPE_ORDER[:]


# =========================================================
# 空间-货物匹配评分（借鉴 greed1.2，但适配问题1.1）
# =========================================================
def eval_candidate(type_id, ori, sp, remaining, truck_obj):
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if remaining[type_id] <= 0:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    tight_bonus = 1.0 / (1.0 + (sp["l"] - l) + (sp["w"] - w) + (sp["h"] - h))
    remain_bonus = remaining[type_id] / max(1, cargo.quantity)
    align_bonus = alignment_bonus(truck_obj.truck, l, w, h)
    base_bonus = (l * w) / max(1, sp["l"] * sp["w"])

    score = (
        0.42 * fill_ratio
        + 0.18 * bottom_bonus
        + 0.12 * tight_bonus
        + 0.10 * remain_bonus
        + 0.10 * base_bonus
        + 0.08 * align_bonus
    )
    return score


# =========================================================
# 单轮放一个货物
# =========================================================
def place_one_best(truck_obj, remaining, type_order):
    best = None  # (score, type_id, ori, sp_idx)

    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    for sp_idx, sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue

            for ori in ORIENTATIONS[type_id]:
                val = eval_candidate(type_id, ori, sp, remaining, truck_obj)
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


# =========================================================
# 单车装载
# =========================================================
def load_one_truck(truck, remaining, strategy):
    truck_obj = FastTruck(truck)
    type_order = build_type_order(strategy)

    fail_count = 0
    while True:
        ok = place_one_best(truck_obj, remaining, type_order)
        if ok:
            fail_count = 0
        else:
            fail_count += 1
            if fail_count >= 1:
                break

    return truck_obj


# =========================================================
# 多策略试探当前车型（借鉴 greed1.2）
# =========================================================
def build_one_vehicle_best(truck):
    strategies = ["base_first", "vol_first", "high_first", "mixed"]
    remaining_template = {k: v.quantity for k, v in CARGO_TYPES.items()}

    best_plan = None
    best_key = None

    for st in strategies:
        rem_copy = remaining_template.copy()
        plan = load_one_truck(truck, rem_copy, st)

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
# 求解所有车型（问题1.1）
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
    outdir = os.path.join(base_dir, "附件2_通用性检验结果_借鉴greed思路版")

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
