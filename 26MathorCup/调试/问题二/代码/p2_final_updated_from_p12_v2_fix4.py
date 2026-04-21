#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（二维点枚举 + 最新 p12 单点验证器）
文件名建议：p2_final_updated_from_p12_v2.py

更新说明
--------
基于最新问题1.2代码 `p12_final_best_combo_v2.py` 更新问题二求解器，保留：
- 二维方案枚举
- 固定点 (x, y) 逐点验证
- 先目标排序，再逐点找首个可行解

与旧版 p2_final.py 的主要差异：
1. 旧版依赖旧 p12 接口（如 ga_optimize_vehicle_policy / pack_one_vehicle_greedy_from_remaining）；
2. 新版改为直接调用最新 p12 的模块化单车构造内核：
   - 车型1：hybrid 模板库
   - 车型2：base-only 模板库
   - build_one_vehicle_best_with_modules(...)
3. 边界同步更新为最新问题1.2结果：
   - 车型1边界：25
   - 车型2边界：13
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================
# 边界（来自最新问题1.2结果）
# ============================================================
BOUND_X1 = 25
BOUND_Y2 = 13
TRUCK1_COST = 450.0
TRUCK2_COST = 700.0
RANDOM_SEED = 42

# 高概率点精细验证设置
HIGH_PROB_POINTS_21 = [
    (1, 12), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7),
    (0, 13), (7, 6)
]
HIGH_PROB_POINTS_22 = [
    (1, 12), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7),
    (0, 13)
]
THOROUGH_RESTARTS = 4
NORMAL_RESTARTS = 1


# ============================================================
# 动态加载最新问题1.2求解器
# ============================================================
def load_p12_module(p12_path: str):
    import sys
    from pathlib import Path

    p12_file = Path(p12_path).expanduser().resolve()
    if not p12_file.exists():
        raise FileNotFoundError(f"未找到问题1.2求解器文件: {p12_file}")

    # 关键修复：
    # 把 p12 文件所在目录加入 sys.path，
    # 这样 p12 内部的 `from mathorcup_d_common import ...` 才能正常导入。
    p12_dir = str(p12_file.parent)
    if p12_dir not in sys.path:
        sys.path.insert(0, p12_dir)

    module_name = "p12_module_latest"
    spec = importlib.util.spec_from_file_location(module_name, str(p12_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法为以下文件创建加载器: {p12_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ============================================================
# 数据结构
# ============================================================
@dataclass
class MixedSolution:
    objective_name: str
    x_truck1: int
    y_truck2: int
    plans: List[object]   # p12.FastTruck
    feasible: bool
    construction_mode: str

    @property
    def vehicle_count(self) -> int:
        return self.x_truck1 + self.y_truck2

    @property
    def total_cost(self) -> float:
        return self.x_truck1 * TRUCK1_COST + self.y_truck2 * TRUCK2_COST


# ============================================================
# 基础函数
# ============================================================
def type_order_all(p12) -> List[str]:
    return list(p12.CARGO_TYPES.keys())


def full_remaining(p12) -> Dict[str, int]:
    return {t: p12.CARGO_TYPES[t].quantity for t in type_order_all(p12)}


def remaining_total(remaining: Dict[str, int]) -> int:
    return sum(remaining.values())


def is_empty(remaining: Dict[str, int]) -> bool:
    return remaining_total(remaining) == 0


def subtract_counts(remaining: Dict[str, int], counts: Dict[str, int], all_types: List[str]) -> None:
    for t in all_types:
        remaining[t] = max(0, remaining[t] - int(counts.get(t, 0)))


def compare_solution_for_vehicle(a: Optional[MixedSolution], b: Optional[MixedSolution]) -> Optional[MixedSolution]:
    if a is None:
        return b
    if b is None:
        return a
    if b.vehicle_count != a.vehicle_count:
        return b if b.vehicle_count < a.vehicle_count else a
    if b.total_cost != a.total_cost:
        return b if b.total_cost < a.total_cost else a
    return b if (b.x_truck1, b.y_truck2) < (a.x_truck1, a.y_truck2) else a


def compare_solution_for_cost(a: Optional[MixedSolution], b: Optional[MixedSolution]) -> Optional[MixedSolution]:
    if a is None:
        return b
    if b is None:
        return a
    if b.total_cost != a.total_cost:
        return b if b.total_cost < a.total_cost else a
    if b.vehicle_count != a.vehicle_count:
        return b if b.vehicle_count < a.vehicle_count else a
    return b if (b.x_truck1, b.y_truck2) < (a.x_truck1, a.y_truck2) else a


def lower_bound_vehicle_count_mix(p12) -> int:
    total_volume = sum(c.volume * c.quantity for c in p12.CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in p12.CARGO_TYPES.values())

    big = p12.TRUCKS["车型2"]
    lb_vol = (total_volume + big.length * big.width * big.effective_height - 1) // (big.length * big.width * big.effective_height)
    lb_wt = int((total_weight + big.max_weight - 1) // big.max_weight)

    best_g3 = 0
    for ori in p12.ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= big.effective_height:
            best_g3 = max(best_g3, (big.length // l) * (big.width // w))
    lb_g3 = (p12.CARGO_TYPES["G3"].quantity + best_g3 - 1) // max(1, best_g3)

    return max(lb_vol, lb_wt, lb_g3)


def max_floor_count_for_type(p12, truck_name: str, type_id: str) -> int:
    truck = p12.TRUCKS[truck_name]
    best = 0
    for ori in p12.ORIENTATIONS[type_id]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            best = max(best, (truck.length // l) * (truck.width // w))
    return best


def quick_mix_feasible_bounds(p12, x: int, y: int) -> bool:
    """快速必要条件过滤，尽可能在调用重型单车构造前剪枝。"""
    t1 = p12.TRUCKS["车型1"]
    t2 = p12.TRUCKS["车型2"]

    total_volume = sum(c.volume * c.quantity for c in p12.CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in p12.CARGO_TYPES.values())

    # 1) 总体积 / 总重量必要条件
    total_cap_vol = x * (t1.length * t1.width * t1.effective_height) + y * (t2.length * t2.width * t2.effective_height)
    total_cap_wt = x * t1.max_weight + y * t2.max_weight
    if total_cap_vol < total_volume or total_cap_wt < total_weight:
        return False

    # 2) G3 地板摆放必要条件（保守但很有效）
    g3_need = p12.CARGO_TYPES["G3"].quantity
    g3_cap = (
        x * max_floor_count_for_type(p12, "车型1", "G3")
        + y * max_floor_count_for_type(p12, "车型2", "G3")
    )
    if g3_cap < g3_need:
        return False

    # 3) 对定向/大件做一个地板数量必要条件，进一步排掉明显不可能的点
    for tid in ("G4", "G5"):
        need = p12.CARGO_TYPES[tid].quantity
        cap = (
            x * max_floor_count_for_type(p12, "车型1", tid)
            + y * max_floor_count_for_type(p12, "车型2", tid)
        )
        if cap < need:
            return False

    return True


# ============================================================
# 固定点 (x, y) 的车辆顺序模式
# ============================================================
def interleave_sequence(x: int, y: int, start_with: str) -> List[str]:
    seq: List[str] = []
    a, b = x, y
    turn = start_with
    while a > 0 or b > 0:
        if turn == "车型1":
            if a > 0:
                seq.append("车型1")
                a -= 1
            elif b > 0:
                seq.append("车型2")
                b -= 1
            turn = "车型2"
        else:
            if b > 0:
                seq.append("车型2")
                b -= 1
            elif a > 0:
                seq.append("车型1")
                a -= 1
            turn = "车型1"
    return seq


def capacity_first_sequence(x: int, y: int) -> List[str]:
    return ["车型2"] * y + ["车型1"] * x


def small_first_sequence(x: int, y: int) -> List[str]:
    return ["车型1"] * x + ["车型2"] * y


def balanced_blocks_sequence(x: int, y: int) -> List[str]:
    seq: List[str] = []
    a, b = x, y
    while a > 0 or b > 0:
        take2 = min(1, b)
        take1 = min(2, a)
        seq.extend(["车型2"] * take2)
        seq.extend(["车型1"] * take1)
        b -= take2
        a -= take1
    return seq


def generate_order_patterns(x: int, y: int, thorough: bool = False) -> List[Tuple[str, List[str]]]:
    patterns: List[Tuple[str, List[str]]] = []
    seen = set()

    def add(name: str, seq: List[str]) -> None:
        key = tuple(seq)
        if key not in seen:
            seen.add(key)
            patterns.append((name, seq))

    add("车型1优先", small_first_sequence(x, y))
    add("车型2优先", capacity_first_sequence(x, y))
    add("交替-车型1起始", interleave_sequence(x, y, "车型1"))
    add("交替-车型2起始", interleave_sequence(x, y, "车型2"))
    add("分块平衡", balanced_blocks_sequence(x, y))

    if thorough:
        # 更细的高概率点验证：增加一些偏向车型2先吃货、再穿插车型1的模式
        add("车型2-车型1交替偏置", ["车型2", "车型1"] * min(x, y) + ["车型2"] * max(0, y - x) + ["车型1"] * max(0, x - y))
        add("车型2前置2块", ["车型2"] * min(2, y) + ["车型1"] * x + ["车型2"] * max(0, y - 2))
        add("车型1前置2块", ["车型1"] * min(2, x) + ["车型2"] * y + ["车型1"] * max(0, x - 2))
        if y >= 2:
            seq = []
            a, b = x, y
            while a > 0 or b > 0:
                take2 = min(2, b)
                take1 = min(1, a)
                seq.extend(["车型2"] * take2)
                seq.extend(["车型1"] * take1)
                b -= take2
                a -= take1
            add("车型2双块推进", seq)

    return patterns


# ============================================================
# 最新 p12 单车构造适配器
# ============================================================
def build_vehicle_templates_for_truck(p12, truck_name: str):
    if truck_name == "车型1":
        return p12.build_templates_hybrid_for_truck1()
    return p12.build_templates_base_only_for_truck2()


def build_one_vehicle_from_remaining_latest(
    p12,
    truck_name: str,
    remaining: Dict[str, int],
    vehicle_index: int,
    module_templates: List[object],
    module_quota_left: Dict[str, int],
):
    """
    直接调用最新 p12 的单车构造器。
    """
    truck = p12.TRUCKS[truck_name]
    plan, quota_after = p12.build_one_vehicle_best_with_modules(
        truck=truck,
        remaining=remaining,
        vehicle_idx=vehicle_index,
        module_templates=module_templates,
        module_quota_left=module_quota_left,
        truck_name=truck_name,
    )
    if plan is None or sum(plan.actual_counts.values()) <= 0:
        return None, None

    return plan, quota_after


# ============================================================
# 强验证器：固定点 (x, y)
# ============================================================
def try_fixed_point_solution(
    p12,
    x: int,
    y: int,
    objective_name: str,
    thorough: bool = False,
) -> Optional[MixedSolution]:
    if x < 0 or y < 0 or x > BOUND_X1 or y > BOUND_Y2:
        return None
    if not quick_mix_feasible_bounds(p12, x, y):
        return None

    best_local: Optional[MixedSolution] = None
    patterns = generate_order_patterns(x, y, thorough=thorough)
    all_types = type_order_all(p12)
    restarts = THOROUGH_RESTARTS if thorough else NORMAL_RESTARTS

    for restart in range(restarts):
        # 通过设置随机种子，让 p12 内部 mixed 顺序在高概率点上多尝试几次
        random_seed = RANDOM_SEED + 1000 * x + 100 * y + 17 * restart
        random.seed(random_seed)

        for mode_name, seq in patterns:
            remaining = full_remaining(p12)

            templates_cache = {
                "车型1": build_vehicle_templates_for_truck(p12, "车型1"),
                "车型2": build_vehicle_templates_for_truck(p12, "车型2"),
            }
            quota_cache = {
                "车型1": p12.init_module_quota(templates_cache["车型1"], remaining.copy(), "车型1"),
                "车型2": p12.init_module_quota(templates_cache["车型2"], remaining.copy(), "车型2"),
            }

            plans: List[object] = []
            feasible = True

            for vehicle_index, truck_name in enumerate(seq, 1):
                if is_empty(remaining):
                    break

                plan, quota_after = build_one_vehicle_from_remaining_latest(
                    p12=p12,
                    truck_name=truck_name,
                    remaining=remaining,
                    vehicle_index=vehicle_index,
                    module_templates=templates_cache[truck_name],
                    module_quota_left=quota_cache[truck_name],
                )
                if plan is None:
                    feasible = False
                    break

                subtract_counts(remaining, plan.actual_counts, all_types)
                quota_cache[truck_name] = quota_after
                plans.append(plan)

            if not feasible or not is_empty(remaining):
                continue

            sol = MixedSolution(
                objective_name=objective_name,
                x_truck1=x,
                y_truck2=y,
                plans=plans,
                feasible=True,
                construction_mode=f"固定点({x},{y})-{mode_name}-r{restart+1}",
            )

            if objective_name == "min_vehicle":
                best_local = compare_solution_for_vehicle(best_local, sol)
            else:
                best_local = compare_solution_for_cost(best_local, sol)

    return best_local


# ============================================================
# 候选点生成：二维点枚举
# ============================================================
def generate_candidates_for_problem_21(p12) -> List[Tuple[int, float, int, int]]:
    candidates: List[Tuple[int, float, int, int]] = []
    lb = lower_bound_vehicle_count_mix(p12)

    for x in range(0, BOUND_X1 + 1):
        for y in range(0, BOUND_Y2 + 1):
            vehicles = x + y
            if vehicles < lb:
                continue
            if vehicles >= BOUND_Y2:
                continue
            if not quick_mix_feasible_bounds(p12, x, y):
                continue

            cost = x * TRUCK1_COST + y * TRUCK2_COST
            candidates.append((vehicles, cost, x, y))

    candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return candidates


def generate_candidates_for_problem_22(p12) -> List[Tuple[float, int, int, int]]:
    candidates: List[Tuple[float, int, int, int]] = []
    boundary_cost = BOUND_Y2 * TRUCK2_COST
    lb = lower_bound_vehicle_count_mix(p12)

    for x in range(0, BOUND_X1 + 1):
        for y in range(0, BOUND_Y2 + 1):
            vehicles = x + y
            if vehicles < lb:
                continue

            cost = x * TRUCK1_COST + y * TRUCK2_COST
            if cost >= boundary_cost:
                continue
            if not quick_mix_feasible_bounds(p12, x, y):
                continue

            candidates.append((cost, vehicles, x, y))

    candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return candidates


def is_high_prob_point(x: int, y: int, objective_name: str) -> bool:
    if objective_name == "min_vehicle":
        return (x, y) in HIGH_PROB_POINTS_21
    return (x, y) in HIGH_PROB_POINTS_22


# ============================================================
# 搜索问题2.1与2.2
# ============================================================
def solve_problem_21(p12) -> MixedSolution:
    print("[问题2.1] 先验证边界点 (0,13)...", flush=True)
    boundary = try_fixed_point_solution(p12, 0, BOUND_Y2, "min_vehicle")
    if boundary is None or (not boundary.feasible):
        raise RuntimeError("最新固定点验证器连边界点 (0,13) 都无法通过，请检查验证逻辑。")
    print("[问题2.1] 边界点 (0,13) 可行。", flush=True)

    candidates = generate_candidates_for_problem_21(p12)
    print(f"[问题2.1] 候选点数量：{len(candidates)}", flush=True)

    best = boundary
    best_vehicle = boundary.vehicle_count

    # 优先把高概率点提前
    candidates.sort(key=lambda t: (0 if is_high_prob_point(t[2], t[3], "min_vehicle") else 1, t[0], t[1], t[2], t[3]))

    for vehicles, cost, x, y in candidates:
        if vehicles >= best_vehicle:
            continue

        thorough = is_high_prob_point(x, y, "min_vehicle")
        flag = "高概率点-精细验证" if thorough else "普通验证"
        print(f"[问题2.1] 验证点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}，模式={flag}", flush=True)
        sol = try_fixed_point_solution(p12, x, y, "min_vehicle", thorough=thorough)

        if sol is not None and sol.feasible:
            print(f"[问题2.1] 找到更优可行点 ({x},{y})", flush=True)
            return sol

    print("[问题2.1] 未找到优于边界点的混合方案，返回边界解 (0,13)。", flush=True)
    return best


def solve_problem_22(p12) -> MixedSolution:
    print("[问题2.2] 先验证边界点 (0,13)...", flush=True)
    boundary = try_fixed_point_solution(p12, 0, BOUND_Y2, "min_cost")
    if boundary is None or (not boundary.feasible):
        raise RuntimeError("最新固定点验证器连边界点 (0,13) 都无法通过，请检查验证逻辑。")
    print("[问题2.2] 边界点 (0,13) 可行。", flush=True)

    candidates = generate_candidates_for_problem_22(p12)
    print(f"[问题2.2] 候选点数量：{len(candidates)}", flush=True)

    best = boundary
    best_cost = boundary.total_cost

    candidates.sort(key=lambda t: (0 if is_high_prob_point(t[2], t[3], "min_cost") else 1, t[0], t[1], t[2], t[3]))

    for cost, vehicles, x, y in candidates:
        if cost >= best_cost:
            continue

        thorough = is_high_prob_point(x, y, "min_cost")
        flag = "高概率点-精细验证" if thorough else "普通验证"
        print(f"[问题2.2] 验证点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}，模式={flag}", flush=True)
        sol = try_fixed_point_solution(p12, x, y, "min_cost", thorough=thorough)

        if sol is not None and sol.feasible:
            print(f"[问题2.2] 找到更优可行点 ({x},{y})", flush=True)
            return sol

    print("[问题2.2] 未找到优于边界点的混合方案，返回边界解 (0,13)。", flush=True)
    return best


# ============================================================
# 输出
# ============================================================
def write_mixed_vehicle_summary_csv(path: str, p12, solution: MixedSolution) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "vehicle_id", "truck_type", "space_utilization", "weight_utilization", "fullness_score",
            "actual_counts", "loaded_weight_kg", "loaded_volume_cm3", "module_count"
        ])
        for vp in solution.plans:
            truck_name = "车型1" if str(vp.vehicle_id).startswith("车型1_") else "车型2"
            truck = p12.TRUCKS[truck_name]
            sv, wv, fs = p12.local_truck_score(vp.used_volume, vp.used_weight, truck)
            w.writerow([
                vp.vehicle_id,
                truck_name,
                round(sv, 6),
                round(wv, 6),
                round(fs, 6),
                dict(vp.actual_counts),
                round(vp.used_weight, 3),
                vp.used_volume,
                len(vp.placed_modules),
            ])


def write_solution_outputs(outdir: str, tag: str, p12, solution: MixedSolution) -> Dict[str, object]:
    sol_dir = os.path.join(outdir, tag)
    os.makedirs(sol_dir, exist_ok=True)

    write_mixed_vehicle_summary_csv(os.path.join(sol_dir, f"{tag}_车辆汇总.csv"), p12, solution)
    for vp in solution.plans:
        p12.write_items_csv(os.path.join(sol_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp)

    avg_sv = 0.0
    avg_wv = 0.0
    if solution.plans:
        total_sv = 0.0
        total_wv = 0.0
        for vp in solution.plans:
            truck_name = "车型1" if str(vp.vehicle_id).startswith("车型1_") else "车型2"
            truck = p12.TRUCKS[truck_name]
            sv, wv, _ = p12.local_truck_score(vp.used_volume, vp.used_weight, truck)
            total_sv += sv
            total_wv += wv
        avg_sv = total_sv / len(solution.plans)
        avg_wv = total_wv / len(solution.plans)

    summary = {
        "tag": tag,
        "objective": solution.objective_name,
        "construction_mode": solution.construction_mode,
        "x_truck1": solution.x_truck1,
        "y_truck2": solution.y_truck2,
        "vehicle_count": solution.vehicle_count,
        "total_cost": round(solution.total_cost, 2),
        "avg_space_utilization": round(avg_sv, 6),
        "avg_weight_utilization": round(avg_wv, 6),
        "boundary_point_1": f"({BOUND_X1},0)",
        "boundary_point_2": f"(0,{BOUND_Y2})",
        "output_dir": sol_dir,
    }
    return summary


def write_overall_summary(path: str, rows: List[Dict[str, object]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "tag", "objective", "construction_mode", "x_truck1", "y_truck2",
            "vehicle_count", "total_cost", "avg_space_utilization", "avg_weight_utilization",
            "boundary_point_1", "boundary_point_2", "output_dir"
        ])
        for r in rows:
            w.writerow([
                r["tag"], r["objective"], r["construction_mode"], r["x_truck1"], r["y_truck2"],
                r["vehicle_count"], r["total_cost"], r["avg_space_utilization"], r["avg_weight_utilization"],
                r["boundary_point_1"], r["boundary_point_2"], r["output_dir"]
            ])


# ============================================================
# CLI
# ============================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（二维点枚举 + 最新 p12 单点验证器）")
    parser.add_argument(
        "--p12-path",
        type=str,
        default="../../问题一/代码/p12_final_best_combo_v2.py",
        help="最新问题1.2求解器路径，默认指向问题一/代码/p12_final_best_combo_v2.py",
    )
    parser.add_argument(
        "--problem",
        choices=["2.1", "2.2", "all"],
        default="all",
        help="选择求解目标：2.1/2.2/all",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="../结果展示",
        help="输出目录",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    p12_path = args.p12_path
    if not os.path.isabs(p12_path):
        p12_path = os.path.normpath(os.path.join(base_dir, p12_path))

    outdir = args.outdir
    if not os.path.isabs(outdir):
        outdir = os.path.normpath(os.path.join(base_dir, outdir))

    p12 = load_p12_module(p12_path)

    print("=" * 72)
    print("开始求解问题二（二维点枚举 + 最新 p12 单点验证器）")
    print(f"边界点：({BOUND_X1},0), (0,{BOUND_Y2})")
    print("=" * 72)

    rows: List[Dict[str, object]] = []

    if args.problem in ("2.1", "all"):
        print("\n" + "-" * 72)
        print("开始求解问题2.1：总运输车辆最少")
        print("-" * 72)
        sol21 = solve_problem_21(p12)
        summary21 = write_solution_outputs(outdir, "problem2_1_min_vehicle", p12, sol21)
        rows.append(summary21)
        print("[问题2.1] 最优解：")
        print(summary21)

    if args.problem in ("2.2", "all"):
        print("\n" + "-" * 72)
        print("开始求解问题2.2：总运输成本最低")
        print("-" * 72)
        sol22 = solve_problem_22(p12)
        summary22 = write_solution_outputs(outdir, "problem2_2_min_cost", p12, sol22)
        rows.append(summary22)
        print("[问题2.2] 最优解：")
        print(summary22)

    if rows:
        write_overall_summary(os.path.join(outdir, "问题二_总体汇总.csv"), rows)
        print(f"\n总体汇总已写入：{os.path.join(outdir, '问题二_总体汇总.csv')}")


if __name__ == "__main__":
    main()
