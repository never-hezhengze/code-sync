# -*- coding: utf-8 -*-
"""
问题1.2 轻量三维装载优化算法
基于：随机化贪心（GRASP）+ 短禁忌搜索（Tabu Search）+ 精英路径重连（Path Relinking）

设计原则：
1. 完全复用 baseline 的物理约束检查与空间切分逻辑；
2. 只优化 5 类货物（G1~G5）的“类型优先级顺序”，避免实例级搜索过慢；
3. 每轮搜索规模受限，保证代码复杂度和运行时间都较可控；
4. 仍输出与 baseline 相同风格的车辆汇总和装箱明细。
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

TYPE_ORDER_ALL = ["G3", "G4", "G5", "G1", "G2"]
DEFAULT_BASE_ORDER = ["G1", "G2", "G4", "G5", "G3"]

# =========================================================
# 参数
# =========================================================
MAX_SPACES_TO_CHECK = 80
MIN_SPACE_VOLUME = 20000


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
class MetaSolution:
    truck_name: str
    plans: List["FastTruck"]
    base_order: List[str]
    vehicle_orders: List[List[str]]
    total_cost: float
    avg_space_utilization: float
    avg_weight_utilization: float

    @property
    def vehicle_count(self) -> int:
        return len(self.plans)

    @property
    def score_tuple(self) -> Tuple[int, float, float]:
        # 先最少车辆，再最大平均空间利用，再最大平均载重利用
        return (
            self.vehicle_count,
            -self.avg_space_utilization,
            -self.avg_weight_utilization,
        )


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


def better_key(plan: "FastTruck") -> Tuple[int, int, float]:
    return (sum(plan.actual_counts.values()), plan.used_volume, plan.used_weight)


def distinct_permutations_from_base(base_order: List[str]) -> List[List[str]]:
    orders = [
        list(base_order),
        ["G1", "G2", "G4", "G5", "G3"],
        ["G4", "G5", "G1", "G2", "G3"],
        ["G3", "G4", "G5", "G1", "G2"],
    ]
    dedup = []
    seen = set()
    for od in orders:
        key = tuple(od)
        if key not in seen:
            seen.add(key)
            dedup.append(od)
    return dedup


def mutate_order(order: List[str], rng: random.Random) -> List[str]:
    arr = list(order)
    op = rng.choice(["swap", "move", "reverse"])
    n = len(arr)

    if op == "swap":
        i, j = sorted(rng.sample(range(n), 2))
        arr[i], arr[j] = arr[j], arr[i]
    elif op == "move":
        i, j = rng.sample(range(n), 2)
        x = arr.pop(i)
        arr.insert(j, x)
    else:
        i, j = sorted(rng.sample(range(n), 2))
        arr[i:j + 1] = reversed(arr[i:j + 1])
    return arr


def randomize_base_order(base_order: List[str], rng: random.Random, strength: int = 2) -> List[str]:
    arr = list(base_order)
    for _ in range(strength):
        arr = mutate_order(arr, rng)
    return arr


# =========================================================
# 货车类（复用 baseline 的物理约束）
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
# 候选评分与随机化贪心
# =========================================================
def eval_candidate(type_id, ori, sp, remaining, truck_obj, type_order):
    l, w, h = ori.size
    cargo = CARGO_TYPES[type_id]

    if l > sp["l"] or w > sp["w"] or h > sp["h"]:
        return None
    if truck_obj.used_weight + cargo.weight > truck_obj.max_weight:
        return None
    if remaining[type_id] <= 0:
        return None

    fill_ratio = (l * w * h) / max(1, sp["l"] * sp["w"] * sp["h"])
    bottom_bonus = 1.0 / (1.0 + sp["z"])
    remain_bonus = remaining[type_id] / max(1, CARGO_TYPES[type_id].quantity)
    support_penalty = 0.02 if sp["z"] > 0 else 0.0
    order_bonus = (len(type_order) - type_order.index(type_id)) / len(type_order) * 0.04

    score = 0.60 * fill_ratio + 0.21 * bottom_bonus + 0.15 * remain_bonus + order_bonus - support_penalty
    return score


def place_one_rcl(truck_obj, remaining, type_order, rcl_size: int, rng: random.Random):
    candidates = []
    candidate_spaces = truck_obj.spaces[:MAX_SPACES_TO_CHECK]

    for sp_idx, _sp in enumerate(candidate_spaces):
        for type_id in type_order:
            if remaining[type_id] <= 0:
                continue
            for ori in ORIENTATIONS[type_id]:
                if not truck_obj.can_place_with_physics(type_id, ori, sp_idx):
                    continue
                val = eval_candidate(type_id, ori, truck_obj.spaces[sp_idx], remaining, truck_obj, type_order)
                if val is None:
                    continue
                candidates.append((val, type_id, ori, sp_idx))

    if not candidates:
        return False

    candidates.sort(key=lambda x: x[0], reverse=True)
    pool = candidates[:max(1, min(rcl_size, len(candidates)))]
    _, type_id, ori, sp_idx = rng.choice(pool)
    truck_obj.place_item(type_id, ori, sp_idx)
    remaining[type_id] -= 1
    return True


def load_one_truck_rcl(truck, remaining, type_order, vehicle_idx, rcl_size: int, rng: random.Random):
    vehicle_id = f"{truck.name}_{vehicle_idx:03d}"
    truck_obj = FastTruck(truck, vehicle_id)

    while True:
        ok = place_one_rcl(truck_obj, remaining, type_order, rcl_size=rcl_size, rng=rng)
        if not ok:
            break

    return truck_obj


def build_one_vehicle_light(truck, remaining, vehicle_idx, base_order, rcl_size: int, rng: random.Random):
    order_pool = distinct_permutations_from_base(base_order)
    for _ in range(2):
        order_pool.append(mutate_order(base_order, rng))

    plans = []
    for order in order_pool:
        rem_copy = deepcopy(remaining)
        plan = load_one_truck_rcl(truck, rem_copy, order, vehicle_idx, rcl_size=rcl_size, rng=rng)
        if sum(plan.actual_counts.values()) > 0:
            plans.append((plan, order))

    if not plans:
        return None, None

    plans.sort(key=lambda x: better_key(x[0]), reverse=True)
    topk = plans[: min(3, len(plans))]
    chosen_plan, chosen_order = rng.choice(topk)
    return chosen_plan, chosen_order


# =========================================================
# 整体求解：给定 base_order 构造全局解
# =========================================================
def construct_solution(truck_name: str, base_order: List[str], rcl_size: int, seed: int, verbose: bool = False) -> MetaSolution:
    rng = random.Random(seed)
    truck = TRUCKS[truck_name]
    remaining = {k: v.quantity for k, v in CARGO_TYPES.items()}
    plans = []
    vehicle_orders = []

    vehicle_idx = 1
    while sum(remaining.values()) > 0:
        plan, used_order = build_one_vehicle_light(
            truck=truck,
            remaining=remaining,
            vehicle_idx=vehicle_idx,
            base_order=base_order,
            rcl_size=rcl_size,
            rng=rng,
        )
        if plan is None or sum(plan.actual_counts.values()) == 0:
            raise RuntimeError(f"{truck_name} 第 {vehicle_idx} 辆车未能装入任何货物，算法停止。")

        for t, c in plan.actual_counts.items():
            remaining[t] -= c
        plans.append(plan)
        vehicle_orders.append(list(used_order))

        if verbose:
            sv, wv, fs = local_truck_score(plan.used_volume, plan.used_weight, truck)
            print(
                f"[{truck_name}] 第 {vehicle_idx} 辆车：装入 {sum(plan.actual_counts.values())} 件，"
                f"空间利用率={sv:.4f}，载重利用率={wv:.4f}，fullness_score={fs:.4f}，"
                f"剩余={sum(remaining.values())}"
            )
        vehicle_idx += 1

    total_cost = len(plans) * truck.cost
    avg_sv = sum(p.used_volume for p in plans) / (len(plans) * truck.length * truck.width * truck.effective_height)
    avg_wv = sum(p.used_weight for p in plans) / (len(plans) * truck.max_weight)

    return MetaSolution(
        truck_name=truck_name,
        plans=plans,
        base_order=list(base_order),
        vehicle_orders=vehicle_orders,
        total_cost=total_cost,
        avg_space_utilization=round(avg_sv, 6),
        avg_weight_utilization=round(avg_wv, 6),
    )


# =========================================================
# Elite / Tabu / Path Relinking
# =========================================================
def is_better_solution(a: MetaSolution, b: Optional[MetaSolution]) -> bool:
    return b is None or a.score_tuple < b.score_tuple


def add_to_elite(elite: List[MetaSolution], sol: MetaSolution, elite_size: int):
    key = tuple(sol.base_order)
    existing = {tuple(x.base_order): i for i, x in enumerate(elite)}
    if key in existing:
        idx = existing[key]
        if is_better_solution(sol, elite[idx]):
            elite[idx] = sol
    else:
        elite.append(sol)
    elite.sort(key=lambda s: s.score_tuple)
    del elite[elite_size:]


def order_neighbors(order: List[str], rng: random.Random, limit: int) -> List[List[str]]:
    neighbors = []
    n = len(order)
    tried = set()
    attempts = 0
    while len(neighbors) < limit and attempts < 50:
        attempts += 1
        arr = list(order)
        op = rng.choice(["swap", "move", "reverse"])
        if op == "swap":
            i, j = sorted(rng.sample(range(n), 2))
            arr[i], arr[j] = arr[j], arr[i]
        elif op == "move":
            i, j = rng.sample(range(n), 2)
            x = arr.pop(i)
            arr.insert(j, x)
        else:
            i, j = sorted(rng.sample(range(n), 2))
            arr[i:j + 1] = reversed(arr[i:j + 1])
        key = tuple(arr)
        if key not in tried and arr != order:
            tried.add(key)
            neighbors.append(arr)
    return neighbors


def tabu_search(truck_name: str, init_order: List[str], args, seed: int) -> MetaSolution:
    rng = random.Random(seed)
    current_order = list(init_order)
    current_sol = construct_solution(truck_name, current_order, rcl_size=args.rcl_size, seed=seed)
    best_sol = current_sol
    tabu = {}

    for it in range(args.tabu_iter):
        candidates = []
        for nbr in order_neighbors(current_order, rng, limit=args.tabu_candidates):
            key = tuple(nbr)
            if tabu.get(key, -1) > it:
                continue
            sol = construct_solution(
                truck_name,
                nbr,
                rcl_size=args.rcl_size,
                seed=seed * 100 + it * 17 + len(candidates) + 1,
            )
            candidates.append((sol, nbr))

        if not candidates:
            break
        candidates.sort(key=lambda x: x[0].score_tuple)
        current_sol, current_order = candidates[0]
        tabu[tuple(current_order)] = it + args.tabu_tenure
        if is_better_solution(current_sol, best_sol):
            best_sol = current_sol

    return best_sol


def path_relinking(truck_name: str, a: MetaSolution, b: MetaSolution, args, seed: int) -> MetaSolution:
    current = list(a.base_order)
    target = list(b.base_order)
    best = a if is_better_solution(a, b) else b
    step = 0

    while current != target and step < len(current):
        for i in range(len(current)):
            if current[i] != target[i]:
                j = current.index(target[i])
                current[i], current[j] = current[j], current[i]
                break
        cand = construct_solution(
            truck_name,
            current,
            rcl_size=args.rcl_size,
            seed=seed * 1000 + step + 1,
        )
        if is_better_solution(cand, best):
            best = cand
        step += 1

    return best


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


# =========================================================
# 总求解器
# =========================================================
def solve_light_meta(truck_name: str, args) -> MetaSolution:
    rng = random.Random(args.seed)
    elite: List[MetaSolution] = []
    best_sol: Optional[MetaSolution] = None

    # baseline 风格 + 随机扰动 的多启动 GRASP
    for it in range(1, args.iterations + 1):
        if it == 1:
            base_order = list(DEFAULT_BASE_ORDER)
        elif it == 2:
            base_order = ["G4", "G5", "G1", "G2", "G3"]
        elif it == 3:
            base_order = ["G3", "G4", "G5", "G1", "G2"]
        else:
            seed_order = best_sol.base_order if best_sol is not None else DEFAULT_BASE_ORDER
            base_order = randomize_base_order(seed_order, rng, strength=2)

        sol = construct_solution(
            truck_name,
            base_order=base_order,
            rcl_size=args.rcl_size,
            seed=args.seed * 100 + it,
        )
        sol = tabu_search(truck_name, sol.base_order, args, seed=args.seed * 1000 + it)
        add_to_elite(elite, sol, args.elite_size)
        if is_better_solution(sol, best_sol):
            best_sol = sol

        if args.show_progress:
            print(
                f"[GRASP {it:02d}] order={sol.base_order} | 车辆数={sol.vehicle_count} | "
                f"平均空间利用率={sol.avg_space_utilization:.6f} | 平均载重利用率={sol.avg_weight_utilization:.6f}"
            )

    # 少量精英路径重连
    pairs_done = 0
    for i in range(len(elite)):
        for j in range(i + 1, len(elite)):
            if pairs_done >= args.pr_pairs:
                break
            pr_sol = path_relinking(
                truck_name,
                elite[i],
                elite[j],
                args,
                seed=args.seed * 2000 + pairs_done + 1,
            )
            pr_sol = tabu_search(truck_name, pr_sol.base_order, args, seed=args.seed * 3000 + pairs_done + 1)
            add_to_elite(elite, pr_sol, args.elite_size)
            if is_better_solution(pr_sol, best_sol):
                best_sol = pr_sol
            pairs_done += 1
            if args.show_progress:
                print(
                    f"[PR {pairs_done:02d}] order={pr_sol.base_order} | 车辆数={pr_sol.vehicle_count} | "
                    f"平均空间利用率={pr_sol.avg_space_utilization:.6f} | 平均载重利用率={pr_sol.avg_weight_utilization:.6f}"
                )
        if pairs_done >= args.pr_pairs:
            break

    assert best_sol is not None
    return best_sol


def solve_for_truck(truck_name, outdir, args):
    truck = TRUCKS[truck_name]
    sol = solve_light_meta(truck_name, args)

    if args.verbose_final:
        print(f"===== {truck_name} 最优解重放 =====")
        replay = construct_solution(
            truck_name,
            base_order=sol.base_order,
            rcl_size=args.rcl_size,
            seed=args.seed * 9999 + 7,
            verbose=True,
        )
        sol = replay

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
        "all_loaded": True,
        "best_base_order": sol.base_order,
        "output_dir": truck_dir,
    }
    return summary


# =========================================================
# CLI
# =========================================================
def parse_args():
    parser = argparse.ArgumentParser(description="问题1.2 轻量 GRASP + Tabu + PR 三维装载优化算法")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../结果展示/output1.2(轻量优化)", help="输出目录")
    parser.add_argument("--iterations", type=int, default=8, help="GRASP 主迭代次数")
    parser.add_argument("--rcl-size", type=int, default=3, help="RCL 候选集大小")
    parser.add_argument("--tabu-iter", type=int, default=5, help="短禁忌搜索迭代次数")
    parser.add_argument("--tabu-tenure", type=int, default=4, help="禁忌长度")
    parser.add_argument("--tabu-candidates", type=int, default=4, help="每轮采样邻域数")
    parser.add_argument("--elite-size", type=int, default=4, help="精英池大小")
    parser.add_argument("--pr-pairs", type=int, default=2, help="路径重连对数上限")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--show-progress", action="store_true", help="打印 GRASP / PR 过程进度")
    parser.add_argument("--verbose-final", action="store_true", help="用最优 base_order 重放并打印最终逐车结果")
    return parser.parse_args()


# =========================================================
# 主程序
# =========================================================
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
