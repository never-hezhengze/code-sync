# -*- coding: utf-8 -*-
"""
问题1.2 加速版贪心
直接复用 mathorcup_d_p12_stable_solver.py 里的数据结构
"""

import random
from collections import Counter
from copy import deepcopy

from mathorcup_d_p12_stable_solver import (
    CARGO_TYPES,
    TRUCKS,
    ORIENTATIONS,
)


# =========================================================
# 参数：这几个参数直接决定速度
# =========================================================
MAX_SPACES_TO_CHECK = 80       # 每轮最多检查多少个空间
MIN_SPACE_VOLUME = 20000       # 太小的碎空间直接丢弃
RANDOM_SEED = 42
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


def truck_score(used_volume, used_weight, truck):
    sv = used_volume / (truck.length * truck.width * truck.effective_height)
    wv = used_weight / truck.max_weight
    return 0.72 * sv + 0.28 * wv


# =========================================================
# 轻量货车类
# =========================================================
class FastTruck:
    def __init__(self, truck):
        self.truck = truck
        self.L = truck.length
        self.W = truck.width
        self.H = truck.effective_height
        self.max_weight = truck.max_weight

        self.spaces = [{
            "x": 0, "y": 0, "z": 0,
            "l": self.L, "w": self.W, "h": self.H
        }]
        self.spaces = sort_spaces(self.spaces)

        self.placed = []
        self.used_weight = 0.0
        self.used_volume = 0
        self.actual_counts = Counter()

    def can_load_weight(self, type_id):
        return self.used_weight + CARGO_TYPES[type_id].weight <= self.max_weight

    def place_item(self, type_id, ori, sp_idx):
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        self.placed.append({
            "type_id": type_id,
            "x": sp["x"],
            "y": sp["y"],
            "z": sp["z"],
            "length": l,
            "width": w,
            "height": h,
            "weight": cargo.weight,
            "rotation": ori.rotation,
            "orientation_id": ori.orient_id,
        })

        self.used_weight += cargo.weight
        self.used_volume += l * w * h
        self.actual_counts[type_id] += 1

        # 三切分
        right = {
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": w,
            "h": h
        }
        front = {
            "x": sp["x"],
            "y": sp["y"] + w,
            "z": sp["z"],
            "l": sp["l"],
            "w": sp["w"] - w,
            "h": h
        }
        upper = {
            "x": sp["x"],
            "y": sp["y"],
            "z": sp["z"] + h,
            "l": sp["l"],
            "w": sp["w"],
            "h": sp["h"] - h
        }

        self.spaces.pop(sp_idx)
        self.spaces.extend([right, front, upper])
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


# =========================================================
# 候选类型顺序
# =========================================================
def build_type_order(strategy):
    std_types = ["G1", "G2"]
    dir_types = ["G4", "G5"]

    if strategy == "std_first":
        return std_types + dir_types + ["G3"]
    elif strategy == "dir_first":
        return dir_types + std_types + ["G3"]
    elif strategy == "g3_first":
        return ["G3"] + dir_types + std_types
    else:
        arr = ["G1", "G2", "G4", "G5", "G3"]
        random.shuffle(arr)
        return arr


# =========================================================
# 空间-货物匹配评分
# =========================================================
def eval_candidate(type_id, ori, sp, remaining, truck_obj):
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight:
        return None
    if remaining[type_id] <= 0:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])   # 越低越优
    remain_bonus = remaining[type_id] / max(1, CARGO_TYPES[type_id].quantity)

    # G3 单独偏置：更偏好放在较高或独立空间中，但这里只做轻量处理
    if type_id == "G3":
        fragile_bonus = 0.08
    else:
        fragile_bonus = 0.0

    score = 0.62 * fill_ratio + 0.23 * bottom_bonus + 0.15 * remain_bonus + fragile_bonus
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

    # 循环装载直到放不进去
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
# 多策略试探当前车
# =========================================================
def build_one_vehicle_best(truck, remaining):
    strategies = ["std_first", "dir_first", "mixed", "g3_first"]

    best_plan = None
    best_key = None

    for st in strategies:
        rem_copy = deepcopy(remaining)
        plan = load_one_truck(truck, rem_copy, st)

        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt == 0:
            continue

        key = (
            loaded_cnt,
            plan.used_volume,
            -plan.used_weight,
        )
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key

    return best_plan


# =========================================================
# 求解单一车型
# =========================================================
def solve_one_truck_type(truck_name):
    truck = TRUCKS[truck_name]
    remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}
    plans = []

    vehicle_idx = 1
    while sum(remaining.values()) > 0:
        plan = build_one_vehicle_best(truck, remaining)
        if plan is None:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车未能装入任何货物，算法停止。")

        loaded_now = sum(plan.actual_counts.values())
        if loaded_now == 0:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车装载数为0，算法停止。")

        # 真正扣减 remaining
        for t, c in plan.actual_counts.items():
            remaining[t] -= c

        plans.append(plan)

        sv = plan.used_volume / (truck.length * truck.width * truck.effective_height)
        wv = plan.used_weight / truck.max_weight
        fs = 0.72 * sv + 0.28 * wv

        print(
            f"[{truck_name}] 第 {vehicle_idx} 辆车："
            f"装入 {loaded_now} 件，"
            f"空间利用率={sv:.4f}，"
            f"载重利用率={wv:.4f}，"
            f"fullness_score={fs:.4f}，"
            f"剩余={sum(remaining.values())}"
        )

        vehicle_idx += 1

    total_cost = len(plans) * truck.cost
    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)

    summary = {
        "truck": truck_name,
        "vehicle_count": len(plans),
        "total_cost": total_cost,
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "all_loaded": True,
    }
    return plans, summary


# =========================================================
# 主程序
# =========================================================
def main():
    print("===== 车型1 =====")
    plans1, summary1 = solve_one_truck_type("车型1")
    print(summary1)

    print("\n===== 车型2 =====")
    plans2, summary2 = solve_one_truck_type("车型2")
    print(summary2)


if __name__ == "__main__":
    main()