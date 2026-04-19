#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（最终提交版）
基于问题1.2单车型装箱内核的混合车型求解器

核心思路：
1. 直接复用问题1.2中的单车构造内核（含 G3 第二通道）；
2. 将问题1.2得到的单车型解作为问题二的边界：
   - 纯车型1边界：(27, 0)
   - 纯车型2边界：(0, 13)
3. 在边界范围内搜索混合车型方案，而不再重做高代价的全局 GA/LNS；
4. 问题2.1：在可行解中选车辆总数最少；
5. 问题2.2：在可行解中选总运输成本最低。

说明：
- 本程序“基于问题1.2”，指的是直接复用问题1.2的单车装箱构造逻辑；
- 为保证稳定运行，问题二主流程采用“边界枚举 + 顺序构造”，
  不在混合车型外层再次套用重型 SA/LNS。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量：来自问题1.2单车型结果的边界
# ============================================================
BOUND_X1 = 27  # 纯车型1最优车辆数边界：(27, 0)
BOUND_Y2 = 13  # 纯车型2最优车辆数边界：(0, 13)


# ============================================================
# 动态加载问题1.2求解器
# ============================================================

def load_p12_module(p12_path):
    import importlib.util
    import sys
    from pathlib import Path

    p12_path = str(Path(p12_path).expanduser().resolve())
    spec = importlib.util.spec_from_file_location("p12_module", p12_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块文件: {p12_path}")

    module = importlib.util.module_from_spec(spec)

    # 关键：先注册到 sys.modules，避免 dataclass 在解析时找不到模块
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)
    return module

# ============================================================
# 结果结构
# ============================================================
@dataclass
class MixedSolution:
    objective_name: str
    x_truck1: int
    y_truck2: int
    plans: List[object]  # p12.VehicleResult
    feasible: bool
    construction_mode: str

    @property
    def vehicle_count(self) -> int:
        return self.x_truck1 + self.y_truck2

    @property
    def total_cost(self) -> float:
        return self.x_truck1 * 450.0 + self.y_truck2 * 700.0


# ============================================================
# 基础函数
# ============================================================

def full_remaining(p12) -> Dict[str, int]:
    return {t: p12.CARGO_TYPES[t].quantity for t in p12.TYPE_ORDER_ALL}


def remaining_total(remaining: Dict[str, int]) -> int:
    return sum(remaining.values())


def is_empty(remaining: Dict[str, int]) -> bool:
    return remaining_total(remaining) == 0


def subtract_plan_from_remaining(remaining: Dict[str, int], plan, type_order_all: List[str]) -> None:
    for t in type_order_all:
        remaining[t] = max(0, remaining[t] - int(plan.actual_counts.get(t, 0)))


def count_truck_types(plans: List[object]) -> Tuple[int, int]:
    x = sum(1 for p in plans if str(p.vehicle_id).startswith("车型1_"))
    y = sum(1 for p in plans if str(p.vehicle_id).startswith("车型2_"))
    return x, y


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


# ============================================================
# 单车构造：直接复用问题1.2内核
# ============================================================

def build_one_vehicle_from_remaining(p12, truck_name: str, remaining: Dict[str, int], vehicle_index: int):
    truck = p12.TRUCKS[truck_name]
    local_remaining = remaining.copy()
    plan = p12.pack_one_vehicle_greedy_from_remaining(truck, local_remaining, vehicle_index)
    loaded = sum(plan.actual_counts.values())
    if loaded <= 0:
        return None
    subtract_plan_from_remaining(remaining, plan, p12.TYPE_ORDER_ALL)
    return plan


# ============================================================
# 顺序构造一个混合车型方案
# ============================================================

def construct_solution_with_prefix(
    p12,
    prefix: List[str],
    objective_name: str,
    mode_name: str,
    max_total_vehicles: int,
) -> MixedSolution:
    """
    先按 prefix 给定顺序装前缀车辆，再用另一车型补齐。
    prefix 例如：['车型1','车型1','车型2']。
    """
    remaining = full_remaining(p12)
    plans: List[object] = []
    vehicle_index = 1

    # 先装前缀
    for truck_name in prefix:
        if is_empty(remaining):
            break
        plan = build_one_vehicle_from_remaining(p12, truck_name, remaining, vehicle_index)
        if plan is None:
            x, y = count_truck_types(plans)
            return MixedSolution(objective_name, x, y, plans, False, mode_name)
        plans.append(plan)
        vehicle_index += 1

        if len(plans) > max_total_vehicles:
            x, y = count_truck_types(plans)
            return MixedSolution(objective_name, x, y, plans, False, mode_name)

    # 再补齐：根据目标选当前“更合适”的车型，但仍受边界控制
    while not is_empty(remaining):
        x, y = count_truck_types(plans)
        if x > BOUND_X1 or y > BOUND_Y2 or len(plans) >= max_total_vehicles:
            return MixedSolution(objective_name, x, y, plans, False, mode_name)

        can_use_1 = x < BOUND_X1
        can_use_2 = y < BOUND_Y2
        if not can_use_1 and not can_use_2:
            return MixedSolution(objective_name, x, y, plans, False, mode_name)

        # 同时试两种车型，选当前一步更优的构造结果
        candidates = []
        for truck_name in ["车型1", "车型2"]:
            if truck_name == "车型1" and not can_use_1:
                continue
            if truck_name == "车型2" and not can_use_2:
                continue
            tmp_remaining = remaining.copy()
            plan = build_one_vehicle_from_remaining(p12, truck_name, tmp_remaining, vehicle_index)
            if plan is None:
                continue
            loaded = sum(plan.actual_counts.values())
            sv, wv, fs = p12.truck_score(p12.TRUCKS[truck_name], plan.used_volume, plan.used_weight)
            # 2.1 更重装载件数与综合利用，2.2 额外考虑成本效率
            if objective_name == "min_cost":
                score = loaded + 80.0 * fs - 0.08 * p12.TRUCKS[truck_name].cost
            else:
                score = loaded + 100.0 * fs
            candidates.append((score, truck_name, plan))

        if not candidates:
            x, y = count_truck_types(plans)
            return MixedSolution(objective_name, x, y, plans, False, mode_name)

        candidates.sort(key=lambda z: z[0], reverse=True)
        _, truck_name, chosen = candidates[0]
        subtract_plan_from_remaining(remaining, chosen, p12.TYPE_ORDER_ALL)
        plans.append(chosen)
        vehicle_index += 1

    x, y = count_truck_types(plans)
    return MixedSolution(objective_name, x, y, plans, True, mode_name)


# ============================================================
# 搜索问题2.1与2.2
# ============================================================

def solve_problem_21(p12) -> MixedSolution:
    best: Optional[MixedSolution] = None

    # 先把纯车型2边界构造成真实方案，而不是空方案
    best = construct_solution_with_prefix(
        p12=p12,
        prefix=["车型2"] * BOUND_Y2,
        objective_name="min_vehicle",
        mode_name="纯车型2边界",
        max_total_vehicles=BOUND_Y2,
    )
    # 单车型边界本身也作为候选
    for x in range(0, BOUND_X1 + 1):
        prefix = ["车型1"] * x
        sol = construct_solution_with_prefix(
            p12=p12,
            prefix=prefix,
            objective_name="min_vehicle",
            mode_name=f"先{x}辆车型1后自适应补齐",
            max_total_vehicles=BOUND_Y2,
        )
        if sol.feasible:
            print(f"[问题2.1] 可行解 ({sol.x_truck1},{sol.y_truck2})，车辆数={sol.vehicle_count}，成本={sol.total_cost:.0f}", flush=True)
            best = compare_solution_for_vehicle(best, sol)

    for y in range(0, BOUND_Y2 + 1):
        prefix = ["车型2"] * y
        sol = construct_solution_with_prefix(
            p12=p12,
            prefix=prefix,
            objective_name="min_vehicle",
            mode_name=f"先{y}辆车型2后自适应补齐",
            max_total_vehicles=BOUND_X1,
        )
        if sol.feasible:
            print(f"[问题2.1] 可行解 ({sol.x_truck1},{sol.y_truck2})，车辆数={sol.vehicle_count}，成本={sol.total_cost:.0f}", flush=True)
            best = compare_solution_for_vehicle(best, sol)

    if best is None:
        raise RuntimeError("问题2.1未找到可行解，请检查问题1.2内核或边界设置。")
    return best


def solve_problem_22(p12) -> MixedSolution:
    best: Optional[MixedSolution] = None

    # 先把纯车型2边界构造成真实方案，而不是空方案
    best = construct_solution_with_prefix(
        p12=p12,
        prefix=["车型2"] * BOUND_Y2,
        objective_name="min_cost",
        mode_name="纯车型2边界",
        max_total_vehicles=BOUND_Y2,
    )
    for x in range(0, BOUND_X1 + 1):
        prefix = ["车型1"] * x
        sol = construct_solution_with_prefix(
            p12=p12,
            prefix=prefix,
            objective_name="min_cost",
            mode_name=f"先{x}辆车型1后自适应补齐",
            max_total_vehicles=BOUND_Y2,
        )
        if sol.feasible:
            print(f"[问题2.2] 可行解 ({sol.x_truck1},{sol.y_truck2})，车辆数={sol.vehicle_count}，成本={sol.total_cost:.0f}", flush=True)
            best = compare_solution_for_cost(best, sol)

    for y in range(0, BOUND_Y2 + 1):
        prefix = ["车型2"] * y
        sol = construct_solution_with_prefix(
            p12=p12,
            prefix=prefix,
            objective_name="min_cost",
            mode_name=f"先{y}辆车型2后自适应补齐",
            max_total_vehicles=BOUND_Y2,
        )
        if sol.feasible:
            print(f"[问题2.2] 可行解 ({sol.x_truck1},{sol.y_truck2})，车辆数={sol.vehicle_count}，成本={sol.total_cost:.0f}", flush=True)
            best = compare_solution_for_cost(best, sol)

    if best is None:
        raise RuntimeError("问题2.2未找到可行解，请检查问题1.2内核或边界设置。")
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
            "target_counts", "actual_counts", "loaded_weight_kg", "loaded_volume_cm3",
            "feasible_full_pack", "policy_desc"
        ])
        for vp in solution.plans:
            truck_name = "车型1" if str(vp.vehicle_id).startswith("车型1_") else "车型2"
            truck = p12.TRUCKS[truck_name]
            sv, wv, fs = p12.truck_score(truck, vp.used_volume, vp.used_weight)
            w.writerow([
                vp.vehicle_id,
                truck_name,
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

#max_total_vehicles
def write_solution_outputs(outdir: str, tag: str, p12, solution: MixedSolution) -> Dict[str, object]:
    sol_dir = os.path.join(outdir, tag)
    os.makedirs(sol_dir, exist_ok=True)

    write_mixed_vehicle_summary_csv(os.path.join(sol_dir, f"{tag}_车辆汇总.csv"), p12, solution)
    for vp in solution.plans:
        p12.write_items_csv(os.path.join(sol_dir, f"{vp.vehicle_id}_装箱明细.csv"), vp.placed)

    truck1_used = solution.x_truck1
    truck2_used = solution.y_truck2
    avg_sv = 0.0
    avg_wv = 0.0
    if solution.plans:
        total_sv = 0.0
        total_wv = 0.0
        for vp in solution.plans:
            truck_name = "车型1" if str(vp.vehicle_id).startswith("车型1_") else "车型2"
            truck = p12.TRUCKS[truck_name]
            sv, wv, _ = p12.truck_score(truck, vp.used_volume, vp.used_weight)
            total_sv += sv
            total_wv += wv
        avg_sv = total_sv / len(solution.plans)
        avg_wv = total_wv / len(solution.plans)

    summary = {
        "tag": tag,
        "objective": solution.objective_name,
        "construction_mode": solution.construction_mode,
        "x_truck1": truck1_used,
        "y_truck2": truck2_used,
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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（基于问题1.2边界搜索的最终提交版）")
    parser.add_argument(
        "--p12-path",
        type=str,
        default="mathorcup_d_p12_ultimate_ga_g3_second_channel_solver.py",
        help="问题1.2求解器路径，默认与本文件同目录",
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
        default="output_problem2_from_p12_final",
        help="输出目录",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    p12_path = args.p12_path
    if not os.path.isabs(p12_path):
        p12_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), p12_path)

    p12 = load_p12_module(p12_path)

    print("=" * 72)
    print("开始求解问题二（基于问题1.2内核 + 单车型边界）")
    print(f"边界点：({BOUND_X1},0), (0,{BOUND_Y2})")
    print("=" * 72)

    rows: List[Dict[str, object]] = []

    if args.problem in ("2.1", "all"):
        print("\n" + "-" * 72)
        print("开始求解问题2.1：总运输车辆最少")
        print("-" * 72)
        sol21 = solve_problem_21(p12)
        summary21 = write_solution_outputs(args.outdir, "problem2_1_min_vehicle", p12, sol21)
        rows.append(summary21)
        print("[问题2.1] 最优解：")
        print(summary21)

    if args.problem in ("2.2", "all"):
        print("\n" + "-" * 72)
        print("开始求解问题2.2：总运输成本最低")
        print("-" * 72)
        sol22 = solve_problem_22(p12)
        summary22 = write_solution_outputs(args.outdir, "problem2_2_min_cost", p12, sol22)
        rows.append(summary22)
        print("[问题2.2] 最优解：")
        print(summary22)

    if rows:
        write_overall_summary(os.path.join(args.outdir, "问题二_总体汇总.csv"), rows)
        print(f"\n总体汇总已写入：{os.path.join(args.outdir, '问题二_总体汇总.csv')}")


if __name__ == "__main__":
    main()
