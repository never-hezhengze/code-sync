# -*- coding: utf-8 -*-
"""
问题1.2 轻量化 GRASP + Tabu + Path Relinking

设计目标：
1. 尽量兼容 p12_baseline.py 的数据接口与输出风格；
2. 在 baseline 的物理约束之上，只加入“轻量”的元启发式增强；
3. 控制复杂度，优先保证可跑、可调、便于和 baseline 做对照。

轻量化策略：
- GRASP：每辆车构造时不再穷举全部货物，而是仅在“优先队列前窗”中选取；
- Tabu：只在“货物优先级序列”上做少量邻域扰动；
- PR：仅在 elite 池前几个解之间做很少次数的路径重连；
- 不做复杂跨车搬移、不做大规模重装，以减少重建次数。
"""

from __future__ import annotations

import argparse
import csv
import os
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from mathorcup_d_common import CARGO_TYPES, TRUCKS, ORIENTATIONS

# =========================================================
# 参数
# =========================================================
MAX_SPACES_TO_CHECK = 60
MIN_SPACE_VOLUME = 20000
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]


# =========================================================
# 数据结构
# =========================================================
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
    rotation: str
    orientation_id: int
    truck_id: str
    support_by: Optional[str] = None
    direct_supported_weight: float = 0.0

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def top_area_m2(self) -> float:
        return (self.length * self.width) / 10000.0


@dataclass
class Solution:
    truck_name: str
    plans: List["FastTruck"]
    sequence: List[str]
    vehicle_count: int
    total_cost: float
    avg_space_utilization: float
    avg_weight_utilization: float
    score_tuple: Tuple


# =========================================================
# 工具函数
# =========================================================
def space_volume(sp):
    return sp["l"] * sp["w"] * sp["h"]


def sort_spaces(spaces):
    spaces = [sp for sp in spaces if sp["l"] > 0 and sp["w"] > 0 and sp["h"] > 0]
    spaces = [sp for sp in spaces if space_volume(sp) >= MIN_SPACE_VOLUME]
    spaces.sort(key=lambda s: (s["z"], -space_volume(s), s["y"], s["x"]))
    return spaces


def local_truck_score(used_volume, used_weight, truck):
    sv = used_volume / (truck.length * truck.width * truck.effective_height)
    wv = used_weight / truck.max_weight
    fs = 0.72 * sv + 0.28 * wv
    return sv, wv, fs


def all_item_instances() -> List[str]:
    seq = []
    for t in TYPE_ORDER_ALL:
        qty = CARGO_TYPES[t].quantity
        for i in range(qty):
            seq.append(f"{t}#{i+1:04d}")
    return seq


def type_of_instance(inst: str) -> str:
    return inst.split("#", 1)[0]


def build_randomized_sequence(seed: int = 0) -> List[str]:
    rnd = random.Random(RANDOM_SEED + seed)
    seq = all_item_instances()
    grouped = {t: [] for t in TYPE_ORDER_ALL}
    for s in seq:
        grouped[type_of_instance(s)].append(s)

    out = []
    type_order = TYPE_ORDER_ALL[:]
    rnd.shuffle(type_order)
    for t in type_order:
        arr = grouped[t]
        rnd.shuffle(arr)
        out.extend(arr)
    return out


def solution_key(sol: Solution):
    return sol.score_tuple


def sequence_distance(a: List[str], b: List[str], sample_n: int = 60) -> int:
    if not a or not b:
        return 10**9
    n = min(sample_n, len(a), len(b))
    if n <= 0:
        return 0
    pos_b = {x: i for i, x in enumerate(b[:n * 3])}
    dist = 0
    for i, x in enumerate(a[:n]):
        j = pos_b.get(x)
        if j is None:
            dist += n
        else:
            dist += abs(i - j)
    return dist


# =========================================================
# 货车类（沿用 baseline 物理约束）
# =========================================================
class FastTruck:
    def __init__(self, truck, vehicle_id):
        self.truck = truck
        self.vehicle_id = vehicle_id
        self.L = truck.length
        self.W = truck.width
        self.H = truck.effective_height
        self.max_weight = truck.max_weight

        self.spaces = [{
            "x": 0, "y": 0, "z": 0,
            "l": self.L, "w": self.W, "h": self.H,
            "support_item_id": None,
            "support_type_id": None,
            "support_length": self.L,
            "support_width": self.W,
        }]
        self.spaces = sort_spaces(self.spaces)

        self.placed: List[PlacedCargo] = []
        self.placed_map: Dict[str, PlacedCargo] = {}
        self.used_weight = 0.0
        self.used_volume = 0
        self.actual_counts = Counter()
        self.serial_counter = Counter()

    def can_place_with_physics(self, type_id, ori, sp_idx):
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        if l > sp["l"] or w > sp["w"] or h > sp["h"]:
            return False
        if self.used_weight + cargo.weight > self.max_weight:
            return False

        if sp["z"] > 0:
            support_item_id = sp.get("support_item_id")
            support_type_id = sp.get("support_type_id")
            if support_item_id is None or support_item_id not in self.placed_map:
                return False

            support = self.placed_map[support_item_id]
            if l > support.length or w > support.width:
                return False
            if support.category == "fragile":
                return False
            if type_id == "G3" and support_type_id not in ("G1", "G2"):
                return False

            support_limit = CARGO_TYPES[support.type_id].max_support_pressure
            projected_pressure = (support.direct_supported_weight + cargo.weight) / max(1e-9, support.top_area_m2)
            if projected_pressure > support_limit + 1e-9:
                return False

        return True

    def place_item(self, type_id, ori, sp_idx):
        sp = self.spaces[sp_idx]
        l, w, h = ori.size
        cargo = CARGO_TYPES[type_id]

        self.serial_counter[type_id] += 1
        item_id = f"{type_id}_{self.vehicle_id}_{self.serial_counter[type_id]:04d}"

        placed = PlacedCargo(
            item_id=item_id,
            type_id=type_id,
            category=cargo.category,
            x=sp["x"],
            y=sp["y"],
            z=sp["z"],
            length=l,
            width=w,
            height=h,
            weight=cargo.weight,
            rotation=ori.rotation,
            orientation_id=ori.orient_id,
            truck_id=self.vehicle_id,
            support_by=sp.get("support_item_id"),
        )

        self.placed.append(placed)
        self.placed_map[item_id] = placed
        self.used_weight += cargo.weight
        self.used_volume += l * w * h
        self.actual_counts[type_id] += 1

        support_by = sp.get("support_item_id")
        if support_by is not None and support_by in self.placed_map:
            self.placed_map[support_by].direct_supported_weight += cargo.weight

        right = {
            "x": sp["x"] + l,
            "y": sp["y"],
            "z": sp["z"],
            "l": sp["l"] - l,
            "w": sp["w"],
            "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
            "support_length": sp.get("support_length"),
            "support_width": sp.get("support_width"),
        }
        front = {
            "x": sp["x"],
            "y": sp["y"] + w,
            "z": sp["z"],
            "l": l,
            "w": sp["w"] - w,
            "h": sp["h"],
            "support_item_id": sp.get("support_item_id"),
            "support_type_id": sp.get("support_type_id"),
            "support_length": sp.get("support_length"),
            "support_width": sp.get("support_width"),
        }
        new_spaces = [right, front]

        if cargo.category != "fragile":
            upper = {
                "x": sp["x"],
                "y": sp["y"],
                "z": sp["z"] + h,
                "l": l,
                "w": w,
                "h": sp["h"] - h,
                "support_item_id": item_id,
                "support_type_id": type_id,
                "support_length": l,
                "support_width": w,
            }
            new_spaces.append(upper)

        self.spaces.pop(sp_idx)
        self.spaces.extend(new_spaces)
        self.spaces = sort_spaces(self.spaces)[:MAX_SPACES_TO_CHECK]


# =========================================================
# 轻量 GRASP 构造
# =========================================================
def eval_candidate(type_id, ori, sp, truck_obj, type_bias=0.0):
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]
    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    wall_bonus = 0.5 / (1.0 + sp["x"] + sp["y"])
    support_penalty = 0.03 if sp["z"] > 0 else 0.0
    return 0.60 * fill_ratio + 0.22 * bottom_bonus + 0.12 * wall_bonus + 0.06 * type_bias - support_penalty


def place_one_grasp(truck_obj, inst_seq, remain_counter, start_ptr, priority_window, rcl_size, rnd):
    candidates = []
    spaces_limit = min(len(truck_obj.spaces), MAX_SPACES_TO_CHECK)
    end_ptr = min(len(inst_seq), start_ptr + priority_window)

    for sp_idx in range(spaces_limit):
        sp = truck_obj.spaces[sp_idx]
        checked_types = set()
        for idx in range(start_ptr, end_ptr):
            inst = inst_seq[idx]
            t = type_of_instance(inst)
            if remain_counter[t] <= 0 or t in checked_types:
                continue
            checked_types.add(t)
            type_bias = 1.0 if t in ("G4", "G5") else (0.8 if t == "G3" else 0.6)
            for ori in ORIENTATIONS[t]:
                if not truck_obj.can_place_with_physics(t, ori, sp_idx):
                    continue
                val = eval_candidate(t, ori, sp, truck_obj, type_bias=type_bias)
                if val is not None:
                    candidates.append((val, t, ori, sp_idx))

    if not candidates:
        return False, start_ptr

    candidates.sort(key=lambda x: x[0], reverse=True)
    rcl = candidates[:max(1, min(rcl_size, len(candidates)))]
    _, t, ori, sp_idx = rnd.choice(rcl)
    truck_obj.place_item(t, ori, sp_idx)
    remain_counter[t] -= 1

    while start_ptr < len(inst_seq) and remain_counter[type_of_instance(inst_seq[start_ptr])] <= 0:
        start_ptr += 1
    return True, start_ptr


def construct_solution_grasp(truck_name, inst_seq, seed, priority_window=80, rcl_size=5):
    rnd = random.Random(RANDOM_SEED + 1000 + seed)
    truck = TRUCKS[truck_name]
    remain_counter = Counter({k: v.quantity for k, v in CARGO_TYPES.items()})
    plans = []
    start_ptr = 0
    vehicle_idx = 1

    while sum(remain_counter.values()) > 0:
        vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
        ft = FastTruck(truck, vehicle_id)
        loaded_before = sum(ft.actual_counts.values())

        while True:
            ok, start_ptr = place_one_grasp(
                ft, inst_seq, remain_counter, start_ptr,
                priority_window=priority_window,
                rcl_size=rcl_size,
                rnd=rnd,
            )
            if not ok:
                break

        loaded_now = sum(ft.actual_counts.values()) - loaded_before
        if loaded_now <= 0:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车未能装入任何货物，算法停止。")
        plans.append(ft)
        vehicle_idx += 1

    total_cost = len(plans) * truck.cost
    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)

    score_tuple = (
        -len(plans),
        round(avg_sv, 8),
        round(avg_wv, 8),
        -sum(abs(sum(p.actual_counts.values()) - (sum(CARGO_TYPES[t].quantity for t in CARGO_TYPES) / max(1, len(plans)))) for p in plans),
    )

    return Solution(
        truck_name=truck_name,
        plans=plans,
        sequence=inst_seq[:],
        vehicle_count=len(plans),
        total_cost=total_cost,
        avg_space_utilization=round(avg_sv, 6),
        avg_weight_utilization=round(avg_wv, 6),
        score_tuple=score_tuple,
    )


# =========================================================
# 轻量 Tabu：仅做少量序列扰动
# =========================================================
def op_swap(seq, i, j):
    s = seq[:]
    s[i], s[j] = s[j], s[i]
    return s


def op_move(seq, i, j):
    s = seq[:]
    x = s.pop(i)
    s.insert(j, x)
    return s


def op_reverse(seq, i, j):
    s = seq[:]
    if i > j:
        i, j = j, i
    s[i:j+1] = reversed(s[i:j+1])
    return s


def random_neighbor(seq, rnd, prefix_window=120):
    n = min(prefix_window, len(seq))
    if n < 2:
        return seq[:], ("noop", 0, 0)
    i, j = sorted(rnd.sample(range(n), 2))
    typ = rnd.choice(["swap", "move", "reverse"])
    if typ == "swap":
        return op_swap(seq, i, j), (typ, i, j)
    if typ == "move":
        return op_move(seq, i, j), (typ, i, j)
    return op_reverse(seq, i, j), (typ, i, j)


def tabu_search_light(base_sol: Solution, seed: int, tabu_iter=12, tabu_tenure=6, candidate_num=10,
                      priority_window=80, rcl_size=4):
    rnd = random.Random(RANDOM_SEED + 2000 + seed)
    best = base_sol
    curr = base_sol
    tabu = {}

    for step in range(1, tabu_iter + 1):
        best_candidate = None
        best_move = None
        best_key = None

        for _ in range(candidate_num):
            new_seq, move = random_neighbor(curr.sequence, rnd)
            is_tabu = tabu.get(move, -10**9) > step
            try:
                cand = construct_solution_grasp(
                    curr.truck_name, new_seq, seed + step,
                    priority_window=priority_window,
                    rcl_size=rcl_size,
                )
            except RuntimeError:
                continue

            key = solution_key(cand)
            asp = key > solution_key(best)
            if is_tabu and not asp:
                continue
            if best_candidate is None or key > best_key:
                best_candidate = cand
                best_move = move
                best_key = key

        if best_candidate is None:
            break

        curr = best_candidate
        tabu[best_move] = step + tabu_tenure
        if solution_key(curr) > solution_key(best):
            best = curr

    return best


# =========================================================
# Elite 池 + 轻量 PR
# =========================================================
def update_elite_pool(elites: List[Solution], sol: Solution, max_size=6, min_dist=20):
    for e in elites:
        if sequence_distance(e.sequence, sol.sequence) < min_dist:
            if solution_key(sol) > solution_key(e):
                elites.remove(e)
                elites.append(sol)
                elites.sort(key=solution_key, reverse=True)
                return
            return
    elites.append(sol)
    elites.sort(key=solution_key, reverse=True)
    if len(elites) > max_size:
        elites.pop()


def path_relink_light(a: Solution, b: Solution, seed: int, steps_limit=8,
                      priority_window=80, rcl_size=4):
    pos_b = {x: i for i, x in enumerate(b.sequence)}
    seq = a.sequence[:]
    best = a
    n = len(seq)
    changed = 0

    for i in range(min(n, 150)):
        target_item = b.sequence[i]
        if seq[i] == target_item:
            continue
        j = seq.index(target_item)
        seq[i], seq[j] = seq[j], seq[i]
        changed += 1
        try:
            cand = construct_solution_grasp(
                a.truck_name, seq, seed + changed,
                priority_window=priority_window,
                rcl_size=rcl_size,
            )
        except RuntimeError:
            continue
        if solution_key(cand) > solution_key(best):
            best = cand
        if changed >= steps_limit:
            break

    return best


# =========================================================
# 主求解
# =========================================================
def solve_light_meta(truck_name, iterations=16, rcl_size=5, priority_window=80,
                     tabu_iter=12, tabu_tenure=6, tabu_candidates=10,
                     elite_size=6, pr_pairs=4, seed=0):
    elites: List[Solution] = []
    global_best = None

    for it in range(1, iterations + 1):
        seq = build_randomized_sequence(seed + it)
        sol = construct_solution_grasp(
            truck_name, seq, seed + it,
            priority_window=priority_window,
            rcl_size=rcl_size,
        )
        sol = tabu_search_light(
            sol, seed + it,
            tabu_iter=tabu_iter,
            tabu_tenure=tabu_tenure,
            candidate_num=tabu_candidates,
            priority_window=priority_window,
            rcl_size=max(2, rcl_size - 1),
        )

        update_elite_pool(elites, sol, max_size=elite_size)
        if global_best is None or solution_key(sol) > solution_key(global_best):
            global_best = sol

        print(
            f"[{truck_name}] iter={it:03d} | vehicles={sol.vehicle_count} | "
            f"avg_sv={sol.avg_space_utilization:.4f} | avg_wv={sol.avg_weight_utilization:.4f}"
        )

    if len(elites) >= 2 and pr_pairs > 0:
        pairs_done = 0
        top = elites[:min(len(elites), 4)]
        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                pr_sol = path_relink_light(
                    top[i], top[j], seed + 500 + pairs_done,
                    steps_limit=8,
                    priority_window=priority_window,
                    rcl_size=max(2, rcl_size - 1),
                )
                pr_sol = tabu_search_light(
                    pr_sol, seed + 800 + pairs_done,
                    tabu_iter=max(6, tabu_iter // 2),
                    tabu_tenure=tabu_tenure,
                    candidate_num=max(6, tabu_candidates // 2),
                    priority_window=priority_window,
                    rcl_size=max(2, rcl_size - 1),
                )
                update_elite_pool(elites, pr_sol, max_size=elite_size)
                if solution_key(pr_sol) > solution_key(global_best):
                    global_best = pr_sol
                pairs_done += 1
                if pairs_done >= pr_pairs:
                    break
            if pairs_done >= pr_pairs:
                break

    return global_best


# =========================================================
# 输出
# =========================================================
def write_vehicle_summary_csv(path, plans, truck):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_weight_kg", "loaded_volume_cm3"
        ])
        for plan in plans:
            sv, wv, fs = local_truck_score(plan.used_volume, plan.used_weight, truck)
            w.writerow([
                plan.vehicle_id,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                dict(plan.actual_counts),
                round(plan.used_weight, 3),
                plan.used_volume,
            ])


def write_items_csv(path, placed):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "item_id", "type_id", "category", "x", "y", "z",
            "length", "width", "height", "weight",
            "orientation_id", "rotation", "truck_id",
            "support_by", "direct_supported_weight"
        ])
        for p in placed:
            w.writerow([
                p.item_id, p.type_id, p.category, p.x, p.y, p.z,
                p.length, p.width, p.height, p.weight,
                p.orientation_id, p.rotation, p.truck_id,
                p.support_by or "",
                round(p.direct_supported_weight, 6),
            ])


def solve_for_truck(truck_name, outdir, args):
    truck = TRUCKS[truck_name]
    sol = solve_light_meta(
        truck_name,
        iterations=args.iterations,
        rcl_size=args.rcl_size,
        priority_window=args.priority_window,
        tabu_iter=args.tabu_iter,
        tabu_tenure=args.tabu_tenure,
        tabu_candidates=args.tabu_candidates,
        elite_size=args.elite_size,
        pr_pairs=args.pr_pairs,
        seed=args.seed,
    )

    truck_dir = os.path.join(outdir, truck_name)
    write_vehicle_summary_csv(os.path.join(truck_dir, f"{truck_name}_车辆汇总.csv"), sol.plans, truck)
    for plan in sol.plans:
        write_items_csv(os.path.join(truck_dir, f"{plan.vehicle_id}_装箱明细.csv"), plan.placed)

    summary = {
        "truck": truck_name,
        "vehicle_count": sol.vehicle_count,
        "total_cost": sol.total_cost,
        "avg_space_utilization": sol.avg_space_utilization,
        "avg_weight_utilization": sol.avg_weight_utilization,
        "output_dir": truck_dir,
    }
    return summary


# =========================================================
# CLI
# =========================================================
def parse_args():
    parser = argparse.ArgumentParser(description="问题1.2 轻量化 GRASP + Tabu + Path Relinking")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2_light_meta", help="输出目录")
    parser.add_argument("--iterations", type=int, default=16)
    parser.add_argument("--rcl-size", type=int, default=5)
    parser.add_argument("--priority-window", type=int, default=80)
    parser.add_argument("--tabu-iter", type=int, default=12)
    parser.add_argument("--tabu-tenure", type=int, default=6)
    parser.add_argument("--tabu-candidates", type=int, default=10)
    parser.add_argument("--elite-size", type=int, default=6)
    parser.add_argument("--pr-pairs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]

    for truck_name in truck_list:
        print(f"===== {truck_name} =====")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
        summary = solve_for_truck(truck_name, outdir, args)
        print(summary)
        print()


if __name__ == "__main__":
    main()
