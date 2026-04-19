#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（二维点枚举 + 逐点验证 最终版）
基于问题1.2单车型装箱内核的混合车型求解器

核心思路：
1. 直接复用问题1.2中的单车构造内核（含 G3 第二通道）；
2. 将问题1.2得到的单车型解作为问题二的边界：
   - 纯车型1边界：(27, 0)
   - 纯车型2边界：(0, 13)
3. 将问题二的混合车型方案表示为二维整数点 (x, y)：
   - x: 车型1车辆数
   - y: 车型2车辆数
4. 对候选点先计算目标值（车辆数/成本），按目标值从优到劣排序；
5. 再对每个点做真实装载可行性验证，首个可行点即为当前目标下的最优解。

说明：
- 本程序采用“二维点枚举 + 固定点逐点验证”框架；
- 每个点 (x, y) 的验证中，会尝试若干种合理的车辆使用顺序；
- 单车装箱内核仍复用问题1.2，以保证与前文模型求解保持一致。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量：来自问题1.2单车型结果的边界
# ============================================================
BOUND_X1 = 27  # 纯车型1最优车辆数边界：(27, 0)
BOUND_Y2 = 13  # 纯车型2最优车辆数边界：(0, 13)
TRUCK1_COST = 450.0
TRUCK2_COST = 700.0


# ============================================================
# 动态加载问题1.2求解器
# ============================================================
def load_p12_module(p12_path: str):
    import sys
    from pathlib import Path

    p12_file = Path(p12_path).expanduser().resolve()
    if not p12_file.exists():
        raise FileNotFoundError(f"未找到问题1.2求解器文件: {p12_file}")

    module_name = "p12_module"
    spec = importlib.util.spec_from_file_location(module_name, str(p12_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法为以下文件创建加载器: {p12_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
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
        return self.x_truck1 * TRUCK1_COST + self.y_truck2 * TRUCK2_COST


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
# 固定点 (x, y) 的若干车辆使用顺序
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
    # 车型2容量更强，先放车型2，再放车型1
    return ["车型2"] * y + ["车型1"] * x


def small_first_sequence(x: int, y: int) -> List[str]:
    # 小车先行，观察是否更利于吸收剩余零散货物
    return ["车型1"] * x + ["车型2"] * y


def balanced_blocks_sequence(x: int, y: int) -> List[str]:
    seq: List[str] = []
    a, b = x, y
    while a > 0 or b > 0:
        take1 = min(2, a)
        take2 = min(1, b)
        seq.extend(["车型1"] * take1)
        seq.extend(["车型2"] * take2)
        a -= take1
        b -= take2
    return seq


def generate_order_patterns(x: int, y: int) -> List[Tuple[str, List[str]]]:
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

    return patterns


# ============================================================
# 对固定点 (x, y) 做真实装载可行性验证
# ============================================================
def try_fixed_point_solution(
    p12,
    x: int,
    y: int,
    objective_name: str,
) -> Optional[MixedSolution]:
    if x < 0 or y < 0 or x > BOUND_X1 or y > BOUND_Y2:
        return None

    best_local: Optional[MixedSolution] = None
    patterns = generate_order_patterns(x, y)

    for mode_name, seq in patterns:
        remaining = full_remaining(p12)
        plans: List[object] = []
        vehicle_index = 1
        feasible = True

        for truck_name in seq:
            if is_empty(remaining):
                break
            plan = build_one_vehicle_from_remaining(p12, truck_name, remaining, vehicle_index)
            if plan is None:
                feasible = False
                break
            plans.append(plan)
            vehicle_index += 1

        if not is_empty(remaining):
            feasible = False

        sol = MixedSolution(
            objective_name=objective_name,
            x_truck1=x,
            y_truck2=y,
            plans=plans,
            feasible=feasible,
            construction_mode=f"固定点({x},{y})-{mode_name}",
        )

        if not feasible:
            continue

        if objective_name == "min_vehicle":
            best_local = compare_solution_for_vehicle(best_local, sol)
        else:
            best_local = compare_solution_for_cost(best_local, sol)

    return best_local


# ============================================================
# 候选点生成：二维点枚举
# ============================================================
def generate_candidates_for_problem_21() -> List[Tuple[int, float, int, int]]:
    # 目标：车辆总数最少；同车辆数下，再比较成本
    candidates: List[Tuple[int, float, int, int]] = []
    for x in range(0, BOUND_X1 + 1):
        for y in range(0, BOUND_Y2 + 1):
            vehicles = x + y
            if vehicles > BOUND_Y2:
                # 已有可行上界 13 辆，超过该值无需再做 2.1 搜索
                continue
            cost = x * TRUCK1_COST + y * TRUCK2_COST
            candidates.append((vehicles, cost, x, y))
    candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return candidates


def generate_candidates_for_problem_22() -> List[Tuple[float, int, int, int]]:
    # 目标：总成本最低；同成本下，再比较车辆数
    candidates: List[Tuple[float, int, int, int]] = []
    boundary_cost = BOUND_Y2 * TRUCK2_COST  # (0,13) 的成本上界 9100
    for x in range(0, BOUND_X1 + 1):
        for y in range(0, BOUND_Y2 + 1):
            cost = x * TRUCK1_COST + y * TRUCK2_COST
            if cost > boundary_cost:
                # 已有可行上界 9100，超过该值无需再做 2.2 搜索
                continue
            vehicles = x + y
            candidates.append((cost, vehicles, x, y))
    candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return candidates


# ============================================================
# 搜索问题2.1与2.2
# ============================================================
def solve_problem_21(p12) -> MixedSolution:
    candidates = generate_candidates_for_problem_21()

    print(f"[问题2.1] 候选点数量：{len(candidates)}", flush=True)

    for vehicles, cost, x, y in candidates:
        sol = try_fixed_point_solution(p12, x, y, "min_vehicle")
        if sol is not None and sol.feasible:
            print(f"[问题2.1] 首个可行点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}", flush=True)
            return sol

    raise RuntimeError("问题2.1未找到可行解，请检查问题1.2内核或边界设置。")


def solve_problem_22(p12) -> MixedSolution:
    candidates = generate_candidates_for_problem_22()

    print(f"[问题2.2] 候选点数量：{len(candidates)}", flush=True)

    for cost, vehicles, x, y in candidates:
        sol = try_fixed_point_solution(p12, x, y, "min_cost")
        if sol is not None and sol.feasible:
            print(f"[问题2.2] 首个可行点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}", flush=True)
            return sol

    raise RuntimeError("问题2.2未找到可行解，请检查问题1.2内核或边界设置。")


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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（二维点枚举 + 逐点验证 最终版）")
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
        default="output_problem2_point_enumeration",
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
    print("开始求解问题二（二维点枚举 + 逐点验证）")
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
