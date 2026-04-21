#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（二维点枚举 + 强验证器 最终版）

核心思路：
1. 直接复用问题1.2中的单车构造与 GA 单车策略优化内核；
2. 将问题二的混合车型方案表示为二维整数点 (x, y)：
   - x: 车型1车辆数
   - y: 车型2车辆数
3. 对候选点先计算目标值（车辆数 / 成本），按从优到劣排序；
4. 对每个固定点 (x, y)，使用“强验证器”判断是否可行：
   - 先按给定车辆顺序逐车用问题1.2贪心得到配额草案；
   - 再对每辆车调用问题1.2的 GA 单车策略优化器精修；
   - 若仍有少量剩余货物，则进行小规模配额修补并重验证；
5. 首个可行点即为当前目标下的最优解。

说明：
- 这是“二维点枚举 + 逐点验证”的正式实现；
- 与简单版不同，这里固定点验证器不再只依赖单车贪心，而是显式调用问题1.2中的
  ga_optimize_vehicle_policy 等更强内核，以尽量接近问题1.2的真实求解能力。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================
# 边界（来自问题1.2既有结果）
# ============================================================
BOUND_X1 = 27
BOUND_Y2 = 13
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
# 数据结构
# ============================================================
@dataclass
class MixedSolution:
    objective_name: str
    x_truck1: int
    y_truck2: int
    plans: List[object]   # p12.VehicleResult
    feasible: bool
    construction_mode: str
    quotas: Optional[List[Dict[str, int]]] = None

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


def subtract_counts(remaining: Dict[str, int], counts: Dict[str, int], type_order_all: List[str]) -> None:
    for t in type_order_all:
        remaining[t] = max(0, remaining[t] - int(counts.get(t, 0)))


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


def plan_score(p12, truck_name: str, plan) -> float:
    loaded = sum(plan.actual_counts.values())
    _, _, fs = p12.truck_score(p12.TRUCKS[truck_name], plan.used_volume, plan.used_weight)
    return loaded + 100.0 * fs


def best_floor_g3(p12, truck_name: str) -> int:
    truck = p12.TRUCKS[truck_name]
    best = 0
    for ori in p12.ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= truck.effective_height:
            best = max(best, (truck.length // l) * (truck.width // w))
    return best


def quota_residual_volume(p12, truck_name: str, quota: Dict[str, int]) -> int:
    truck = p12.TRUCKS[truck_name]
    return truck.effective_volume - p12.quota_total_volume(quota)


def quota_residual_weight(p12, truck_name: str, quota: Dict[str, int]) -> float:
    truck = p12.TRUCKS[truck_name]
    return truck.max_weight - p12.quota_total_weight(quota)

def lower_bound_vehicle_count_mix(p12) -> int:
    total_volume = sum(c.volume * c.quantity for c in p12.CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in p12.CARGO_TYPES.values())

    big = p12.TRUCKS["车型2"]

    lb_vol = (total_volume + big.effective_volume - 1) // big.effective_volume
    lb_wt = int((total_weight + big.max_weight - 1) // big.max_weight)

    best_g3 = 0
    for ori in p12.ORIENTATIONS["G3"]:
        l, w, h = ori.size
        if h <= big.effective_height:
            best_g3 = max(best_g3, (big.length // l) * (big.width // w))
    lb_g3 = (p12.CARGO_TYPES["G3"].quantity + best_g3 - 1) // max(1, best_g3)

    return max(lb_vol, lb_wt, lb_g3)
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
# 强验证器：固定点 (x, y)
# ============================================================
def build_one_vehicle_strong_from_remaining(p12, truck_name: str, remaining: Dict[str, int], vehicle_index: int):
    """
    先用问题1.2贪心得到该车的配额草案，再用问题1.2的 GA 单车策略优化器精修。
    """
    truck = p12.TRUCKS[truck_name]

    # 1) 用 greedy 生成本车配额草案（在拷贝上做，避免直接污染 remaining）
    greedy_remaining = remaining.copy()
    draft_plan = p12.pack_one_vehicle_greedy_from_remaining(truck, greedy_remaining, vehicle_index)
    draft_loaded = sum(draft_plan.actual_counts.values())
    if draft_loaded <= 0:
        return None, None

    quota = {t: int(draft_plan.target_counts.get(t, 0)) for t in p12.TYPE_ORDER_ALL}

    # 2) 用问题1.2的 GA 单车策略优化器精修这个配额
    try:
        ga_plan, _ = p12.ga_optimize_vehicle_policy(truck, quota, vehicle_index)
    except Exception:
        ga_plan = draft_plan

    # 3) 在 draft / ga 之间选更优
    cand = draft_plan
    if ga_plan is not None and plan_score(p12, truck_name, ga_plan) >= plan_score(p12, truck_name, draft_plan):
        cand = ga_plan

    loaded = sum(cand.actual_counts.values())
    if loaded <= 0:
        return None, None

    subtract_counts(remaining, cand.actual_counts, p12.TYPE_ORDER_ALL)
    return cand, quota


def try_small_quota_repair(p12, seq: List[str], quotas: List[Dict[str, int]], max_rounds: int = 2):
    """
    小规模配额修补：把剩余货物塞入当前配额，然后逐车 GA 重验证。
    """
    quotas = [q.copy() for q in quotas]
    plans = []
    for i, (truck_name, quota) in enumerate(zip(seq, quotas), 1):
        truck = p12.TRUCKS[truck_name]
        plan, _ = p12.ga_optimize_vehicle_policy(truck, quota, i)
        plans.append(plan)

    missing = {t: 0 for t in p12.TYPE_ORDER_ALL}
    for t in p12.TYPE_ORDER_ALL:
        total_actual = sum(vp.actual_counts.get(t, 0) for vp in plans)
        missing[t] = max(0, p12.CARGO_TYPES[t].quantity - total_actual)

    for _ in range(max_rounds):
        if sum(missing.values()) == 0:
            break

        changed = False
        # 先补标准/定向件，再补 G3
        order = ["G4", "G5", "G1", "G2", "G3"]
        for t in order:
            while missing[t] > 0:
                candidates = []
                c = p12.CARGO_TYPES[t]
                for i, truck_name in enumerate(seq):
                    q = quotas[i]
                    rv = quota_residual_volume(p12, truck_name, q)
                    rw = quota_residual_weight(p12, truck_name, q)
                    if rv < c.volume or rw < c.weight:
                        continue
                    bonus = 0.0
                    if t == "G3":
                        slack = max(0, best_floor_g3(p12, truck_name) - q.get("G3", 0))
                        if slack <= 0:
                            continue
                        bonus = 10.0 + slack
                    else:
                        _, _, fs = p12.truck_score(
                            p12.TRUCKS[truck_name],
                            p12.quota_total_volume(q),
                            p12.quota_total_weight(q),
                        )
                        bonus = (1.0 - fs)
                    candidates.append((bonus, i))

                if not candidates:
                    break

                candidates.sort(reverse=True)
                i = candidates[0][1]
                quotas[i][t] = quotas[i].get(t, 0) + 1
                missing[t] -= 1
                changed = True

        if not changed:
            break

        new_plans = []
        for i, (truck_name, quota) in enumerate(zip(seq, quotas), 1):
            truck = p12.TRUCKS[truck_name]
            plan, _ = p12.ga_optimize_vehicle_policy(truck, quota, i)
            new_plans.append(plan)
        plans = new_plans

        missing = {t: 0 for t in p12.TYPE_ORDER_ALL}
        for t in p12.TYPE_ORDER_ALL:
            total_actual = sum(vp.actual_counts.get(t, 0) for vp in plans)
            missing[t] = max(0, p12.CARGO_TYPES[t].quantity - total_actual)

    feasible = sum(missing.values()) == 0
    return feasible, plans, quotas, missing


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
        quotas: List[Dict[str, int]] = []
        feasible = True

        # A. 逐车强构造（greedy quota + GA refine）
        for vehicle_index, truck_name in enumerate(seq, 1):
            if is_empty(remaining):
                break
            plan, quota = build_one_vehicle_strong_from_remaining(p12, truck_name, remaining, vehicle_index)
            if plan is None:
                feasible = False
                break
            plans.append(plan)
            quotas.append(quota)

        # B. 若还有剩余，则尝试小规模配额修补并重验证
        if not is_empty(remaining):
            feasible, repaired_plans, repaired_quotas, _ = try_small_quota_repair(p12, seq, quotas, max_rounds=2)
            if feasible:
                plans = repaired_plans
                quotas = repaired_quotas

        # C. 终判
        if not feasible:
            continue

        total_actual_loaded = {t: 0 for t in p12.TYPE_ORDER_ALL}
        for vp in plans:
            for t in p12.TYPE_ORDER_ALL:
                total_actual_loaded[t] += int(vp.actual_counts.get(t, 0))
        if any(total_actual_loaded[t] < p12.CARGO_TYPES[t].quantity for t in p12.TYPE_ORDER_ALL):
            continue

        sol = MixedSolution(
            objective_name=objective_name,
            x_truck1=x,
            y_truck2=y,
            plans=plans,
            feasible=True,
            construction_mode=f"固定点({x},{y})-{mode_name}",
            quotas=quotas,
        )

        if objective_name == "min_vehicle":
            best_local = compare_solution_for_vehicle(best_local, sol)
        else:
            best_local = compare_solution_for_cost(best_local, sol)
    return best_local

def try_fixed_point_solution_ultra(
    p12,
    x: int,
    y: int,
    objective_name: str,
) -> Optional[MixedSolution]:
    """
    仅对少数可疑点启用的超强验证器：
    1. 在原有顺序模式基础上增加几种更激进的车辆顺序；
    2. 提高配额修补轮数；
    3. 对同一点进行更充分的重验证。
    """
    if x < 0 or y < 0 or x > BOUND_X1 or y > BOUND_Y2:
        return None

    best_local: Optional[MixedSolution] = None
    patterns = generate_order_patterns(x, y)

    extra_patterns = [
        ("车型2集中后车型1补尾", ["车型2"] * max(0, y - 2) + ["车型1"] * x + ["车型2"] * min(2, y)),
        ("车型1集中后车型2补尾", ["车型1"] * max(0, x - 2) + ["车型2"] * y + ["车型1"] * min(2, x)),
        ("严格交替扩展", interleave_sequence(x, y, "车型2")),
        ("车型2半段-车型1插入-车型2收尾", ["车型2"] * (y // 2) + ["车型1"] * x + ["车型2"] * (y - y // 2)),
    ]

    seen = set(tuple(seq) for _, seq in patterns)
    for name, seq in extra_patterns:
        key = tuple(seq)
        if key not in seen:
            seen.add(key)
            patterns.append((name, seq))

    for mode_name, seq in patterns:
        remaining = full_remaining(p12)
        plans: List[object] = []
        quotas: List[Dict[str, int]] = []
        feasible = True

        for vehicle_index, truck_name in enumerate(seq, 1):
            if is_empty(remaining):
                break
            plan, quota = build_one_vehicle_strong_from_remaining(p12, truck_name, remaining, vehicle_index)
            if plan is None:
                feasible = False
                break
            plans.append(plan)
            quotas.append(quota)

        if not is_empty(remaining):
            feasible, repaired_plans, repaired_quotas, _ = try_small_quota_repair(
                p12, seq, quotas, max_rounds=5
            )
            if feasible:
                plans = repaired_plans
                quotas = repaired_quotas

        if not feasible:
            continue

        total_actual_loaded = {t: 0 for t in p12.TYPE_ORDER_ALL}
        for vp in plans:
            for t in p12.TYPE_ORDER_ALL:
                total_actual_loaded[t] += int(vp.actual_counts.get(t, 0))

        if any(total_actual_loaded[t] < p12.CARGO_TYPES[t].quantity for t in p12.TYPE_ORDER_ALL):
            continue

        sol = MixedSolution(
            objective_name=objective_name,
            x_truck1=x,
            y_truck2=y,
            plans=plans,
            feasible=True,
            construction_mode=f"超强验证-固定点({x},{y})-{mode_name}",
            quotas=quotas,
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

            candidates.append((cost, vehicles, x, y))

    candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return candidates

# ============================================================
# 搜索问题2.1与2.2
# ============================================================
def solve_problem_21(p12) -> MixedSolution:
    print("[问题2.1] 先验证边界点 (0,13)...", flush=True)
    boundary = try_fixed_point_solution(p12, 0, BOUND_Y2, "min_vehicle")
    if boundary is None or (not boundary.feasible):
        raise RuntimeError("强验证器连边界点 (0,13) 都无法通过，请检查固定点验证逻辑。")
    print("[问题2.1] 边界点 (0,13) 可行。", flush=True)

    candidates = generate_candidates_for_problem_21(p12)
    print(f"[问题2.1] 候选点数量：{len(candidates)}", flush=True)

    best = boundary
    best_vehicle = boundary.vehicle_count
    suspicious_points_21 = {(0, 12), (1, 11), (2, 10), (3, 9), (4, 8)}

    for vehicles, cost, x, y in candidates:
        if vehicles >= best_vehicle:
            continue

        print(f"[问题2.1] 验证点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}", flush=True)
        if (x, y) in suspicious_points_21:
            print(f"[问题2.1] 对可疑点 ({x},{y}) 启用超强验证", flush=True)
            sol = try_fixed_point_solution_ultra(p12, x, y, "min_vehicle")
        else:
            sol = try_fixed_point_solution(p12, x, y, "min_vehicle")

        if sol is not None and sol.feasible:
            print(f"[问题2.1] 找到更优可行点 ({x},{y})", flush=True)
            return sol

    print("[问题2.1] 未找到优于边界点的混合方案，返回边界解 (0,13)。", flush=True)
    return best


def solve_problem_22(p12) -> MixedSolution:
    print("[问题2.2] 先验证边界点 (0,13)...", flush=True)
    boundary = try_fixed_point_solution(p12, 0, BOUND_Y2, "min_cost")
    if boundary is None or (not boundary.feasible):
        raise RuntimeError("强验证器连边界点 (0,13) 都无法通过，请检查固定点验证逻辑。")
    print("[问题2.2] 边界点 (0,13) 可行。", flush=True)

    candidates = generate_candidates_for_problem_22(p12)
    print(f"[问题2.2] 候选点数量：{len(candidates)}", flush=True)

    best = boundary
    best_cost = boundary.total_cost
    suspicious_points_22 = {(1, 12), (2, 11), (3, 10), (4, 9), (5, 8)}

    for cost, vehicles, x, y in candidates:
        if cost >= best_cost:
            continue

        print(f"[问题2.2] 验证点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}", flush=True)
        if (x, y) in suspicious_points_22:
            print(f"[问题2.2] 对可疑点 ({x},{y}) 启用超强验证", flush=True)
            sol = try_fixed_point_solution_ultra(p12, x, y, "min_cost")
        else:
            sol = try_fixed_point_solution(p12, x, y, "min_cost")

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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（二维点枚举 + 强验证器 最终版）")
    parser.add_argument(
        "--p12-path",
        type=str,
        default="../../问题一/代码/p12_final.py",
        help="问题1.2求解器路径，默认指向问题一/代码/p12_final.py",
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
    print("开始求解问题二（二维点枚举 + 强验证器）")
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
        print(f"\n总体汇总已写入：{os.path.join(args.outdir, '问题二_总体汇总.csv')}")


if __name__ == "__main__":
    main()
