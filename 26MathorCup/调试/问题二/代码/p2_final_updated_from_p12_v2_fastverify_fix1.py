#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MathorCup D题 - 问题二（二维点枚举 + 快筛验证器 + 强验证器）
文件名建议：p2_final_updated_from_p12_v2_fastverify.py

思路
----
保留问题二原有主框架：
1. 二维整数点 (x, y) 枚举
2. 固定点逐点验证
3. 目标排序后搜索首个更优可行点

但将“固定点验证”分为两层：
- 快筛验证器：使用缩小模板库 + 少量车辆顺序 + 少量单车策略，快速排除大多数点
- 强验证器：仅对高概率点/快筛通过点调用最新 p12 强单车构造器做精细验证

这样既保留二维方案枚举思路，又避免每个点都直接调用最重的 p12 内核。
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
# 常量
# ============================================================
BOUND_X1 = 25
BOUND_Y2 = 13
TRUCK1_COST = 450.0
TRUCK2_COST = 700.0
RANDOM_SEED = 42

# 快筛模板保留数
FAST_KEEP_TRUCK1 = 12
FAST_KEEP_TRUCK2 = 10

# 快筛重启 / 强验证重启
FAST_RESTARTS = 1
FAST_RESTARTS_HIGH_PROB = 2
STRONG_RESTARTS = 2
STRONG_RESTARTS_HIGH_PROB = 4

# 高概率点：问题2.1 和 2.2
HIGH_PROB_POINTS_21 = [
    (1, 12), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7),
    (7, 6), (8, 5), (0, 13)
]
HIGH_PROB_POINTS_22 = [
    (1, 12), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7),
    (0, 13)
]


# ============================================================
# 动态加载最新问题1.2求解器
# ============================================================
def load_p12_module(p12_path: str):
    import sys
    from pathlib import Path

    p12_file = Path(p12_path).expanduser().resolve()
    if not p12_file.exists():
        raise FileNotFoundError(f"未找到问题1.2求解器文件: {p12_file}")

    p12_dir = str(p12_file.parent)
    if p12_dir not in sys.path:
        sys.path.insert(0, p12_dir)

    module_name = "p12_module_latest_for_p2_fastverify"
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
    plans: List[object]
    feasible: bool
    construction_mode: str

    @property
    def vehicle_count(self) -> int:
        return self.x_truck1 + self.y_truck2

    @property
    def total_cost(self) -> float:
        return self.x_truck1 * TRUCK1_COST + self.y_truck2 * TRUCK2_COST


# ============================================================
# 基础工具
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


def diagonal_priority_from_boundary(x: int, y: int) -> Tuple[int, int, int]:
    diag_y = max(0, 13 - x)
    diag_gap = abs(y - diag_y)
    boundary_dist = abs(x) + abs(y - 13)
    return (diag_gap, boundary_dist, x)


def is_high_prob_point(x: int, y: int, objective_name: str) -> bool:
    if objective_name == "min_vehicle":
        return (x, y) in HIGH_PROB_POINTS_21
    return (x, y) in HIGH_PROB_POINTS_22


def quick_mix_feasible_bounds(p12, x: int, y: int, objective_name: str) -> bool:
    """
    弱剪枝：
    1) 总体积必要条件
    2) 总重量必要条件
    3) 对高概率点不加额外几何剪枝
    """
    t1 = p12.TRUCKS["车型1"]
    t2 = p12.TRUCKS["车型2"]

    total_volume = sum(c.volume * c.quantity for c in p12.CARGO_TYPES.values())
    total_weight = sum(c.weight * c.quantity for c in p12.CARGO_TYPES.values())

    total_cap_vol = x * (t1.length * t1.width * t1.effective_height) + y * (t2.length * t2.width * t2.effective_height)
    total_cap_wt = x * t1.max_weight + y * t2.max_weight
    if total_cap_vol < total_volume or total_cap_wt < total_weight:
        return False

    return True


# ============================================================
# 固定点车辆顺序
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


def truck2_double_block_sequence(x: int, y: int) -> List[str]:
    seq: List[str] = []
    a, b = x, y
    while a > 0 or b > 0:
        take2 = min(2, b)
        take1 = min(1, a)
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
        add("车型2双块推进", truck2_double_block_sequence(x, y))
        add("车型2前置2块", ["车型2"] * min(2, y) + ["车型1"] * x + ["车型2"] * max(0, y - 2))
        add("车型1前置2块", ["车型1"] * min(2, x) + ["车型2"] * y + ["车型1"] * max(0, x - 2))

    return patterns


# ============================================================
# 模板缓存
# ============================================================
def build_vehicle_templates_full(p12, truck_name: str):
    if truck_name == "车型1":
        return p12.build_templates_hybrid_for_truck1()
    return p12.build_templates_base_only_for_truck2()


def build_boundary_solution_from_p12(p12, objective_name: str) -> MixedSolution:
    """
    直接调用最新 p12 的单车型最终求解结果来构造边界解：
    - 边界点固定为 (0,13)
    - 避免在问题2里再用强验证器重复证明一次
    """
    plans, summary, _templates = p12.solve_one_truck_type("车型2")
    return MixedSolution(
        objective_name=objective_name,
        x_truck1=0,
        y_truck2=summary["vehicle_count"],
        plans=plans,
        feasible=True,
        construction_mode="直接复用p12边界解(0,13)",
    )


def build_vehicle_templates_fast(p12, truck_name: str):
    full = build_vehicle_templates_full(p12, truck_name)
    if truck_name == "车型1":
        return full[:FAST_KEEP_TRUCK1]
    return full[:FAST_KEEP_TRUCK2]


# ============================================================
# 单车构造：快筛验证器
# ============================================================
def fast_strategy_candidates(truck_name: str, thorough: bool) -> List[str]:
    if truck_name == "车型1":
        return ["g3_first", "std_first"] if thorough else ["g3_first"]
    return ["std_first", "dir_first"] if thorough else ["std_first"]


def build_one_vehicle_fast(
    p12,
    truck_name: str,
    remaining: Dict[str, int],
    vehicle_index: int,
    module_templates: List[object],
    module_quota_left: Dict[str, int],
    thorough: bool,
):
    truck = p12.TRUCKS[truck_name]
    best_plan = None
    best_quota_after = None
    best_key = None

    for st in fast_strategy_candidates(truck_name, thorough):
        rem_copy = remaining.copy()
        quota_copy = module_quota_left.copy()
        plan = p12.load_one_truck_with_modules(
            truck=truck,
            remaining=rem_copy,
            strategy=st,
            vehicle_idx=vehicle_index,
            module_templates=module_templates,
            module_quota_left=quota_copy,
            truck_name=truck_name,
        )
        loaded_cnt = sum(plan.actual_counts.values())
        if loaded_cnt <= 0:
            continue
        key = (loaded_cnt, plan.used_volume, -plan.used_weight)
        if best_plan is None or key > best_key:
            best_plan = plan
            best_key = key
            best_quota_after = quota_copy

    if best_plan is None:
        return None, None
    return best_plan, best_quota_after


# ============================================================
# 单车构造：强验证器
# ============================================================
def build_one_vehicle_strong(
    p12,
    truck_name: str,
    remaining: Dict[str, int],
    vehicle_index: int,
    module_templates: List[object],
    module_quota_left: Dict[str, int],
):
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
# 快筛固定点验证
# ============================================================
def try_fixed_point_solution_fast(
    p12,
    x: int,
    y: int,
    objective_name: str,
    thorough: bool = False,
) -> Optional[MixedSolution]:
    if x < 0 or y < 0 or x > BOUND_X1 or y > BOUND_Y2:
        return None
    if not quick_mix_feasible_bounds(p12, x, y, objective_name):
        return None

    best_local: Optional[MixedSolution] = None
    patterns = generate_order_patterns(x, y, thorough=thorough)
    all_types = type_order_all(p12)
    restarts = FAST_RESTARTS_HIGH_PROB if thorough else FAST_RESTARTS

    templates_fast = {
        "车型1": build_vehicle_templates_fast(p12, "车型1"),
        "车型2": build_vehicle_templates_fast(p12, "车型2"),
    }

    for restart in range(restarts):
        random.seed(RANDOM_SEED + 1000 * x + 100 * y + 17 * restart)

        for mode_name, seq in patterns:
            remaining = full_remaining(p12)
            quota_cache = {
                "车型1": p12.init_module_quota(templates_fast["车型1"], remaining.copy(), "车型1"),
                "车型2": p12.init_module_quota(templates_fast["车型2"], remaining.copy(), "车型2"),
            }

            plans: List[object] = []
            feasible = True

            for vehicle_index, truck_name in enumerate(seq, 1):
                if is_empty(remaining):
                    break

                plan, quota_after = build_one_vehicle_fast(
                    p12=p12,
                    truck_name=truck_name,
                    remaining=remaining,
                    vehicle_index=vehicle_index,
                    module_templates=templates_fast[truck_name],
                    module_quota_left=quota_cache[truck_name],
                    thorough=thorough,
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
                construction_mode=f"快筛固定点({x},{y})-{mode_name}-r{restart+1}",
            )

            if objective_name == "min_vehicle":
                best_local = compare_solution_for_vehicle(best_local, sol)
            else:
                best_local = compare_solution_for_cost(best_local, sol)

    return best_local


# ============================================================
# 强固定点验证
# ============================================================
def try_fixed_point_solution_strong(
    p12,
    x: int,
    y: int,
    objective_name: str,
    thorough: bool = False,
) -> Optional[MixedSolution]:
    if x < 0 or y < 0 or x > BOUND_X1 or y > BOUND_Y2:
        return None
    if not quick_mix_feasible_bounds(p12, x, y, objective_name):
        return None

    best_local: Optional[MixedSolution] = None
    patterns = generate_order_patterns(x, y, thorough=thorough)
    all_types = type_order_all(p12)
    restarts = STRONG_RESTARTS_HIGH_PROB if thorough else STRONG_RESTARTS

    templates_full = {
        "车型1": build_vehicle_templates_full(p12, "车型1"),
        "车型2": build_vehicle_templates_full(p12, "车型2"),
    }

    for restart in range(restarts):
        random.seed(RANDOM_SEED + 1000 * x + 100 * y + 17 * restart)

        for mode_name, seq in patterns:
            remaining = full_remaining(p12)
            quota_cache = {
                "车型1": p12.init_module_quota(templates_full["车型1"], remaining.copy(), "车型1"),
                "车型2": p12.init_module_quota(templates_full["车型2"], remaining.copy(), "车型2"),
            }

            plans: List[object] = []
            feasible = True

            for vehicle_index, truck_name in enumerate(seq, 1):
                if is_empty(remaining):
                    break

                plan, quota_after = build_one_vehicle_strong(
                    p12=p12,
                    truck_name=truck_name,
                    remaining=remaining,
                    vehicle_index=vehicle_index,
                    module_templates=templates_full[truck_name],
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
                construction_mode=f"强验证固定点({x},{y})-{mode_name}-r{restart+1}",
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
            if not quick_mix_feasible_bounds(p12, x, y, "min_vehicle"):
                continue

            cost = x * TRUCK1_COST + y * TRUCK2_COST
            candidates.append((vehicles, cost, x, y))

    # 高概率点优先，然后车辆数、成本、坐标
    candidates.sort(key=lambda t: (0 if is_high_prob_point(t[2], t[3], "min_vehicle") else 1, t[0], t[1], t[2], t[3]))
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
            if not quick_mix_feasible_bounds(p12, x, y, "min_cost"):
                continue

            candidates.append((cost, vehicles, x, y))

    candidates.sort(
        key=lambda t: (
            0 if is_high_prob_point(t[2], t[3], "min_cost") else 1,
            t[0],
            *diagonal_priority_from_boundary(t[2], t[3]),
            t[1],
            t[2],
            t[3],
        )
    )
    return candidates


# ============================================================
# 搜索问题2.1与2.2
# ============================================================
def solve_problem_21(p12) -> MixedSolution:
    print("[问题2.1] 直接复用 p12 已验证边界点 (0,13)...", flush=True)
    boundary = build_boundary_solution_from_p12(p12, "min_vehicle")
    if boundary is None or (not boundary.feasible):
        raise RuntimeError("无法从最新 p12 直接构造边界点 (0,13)。")
    print("[问题2.1] 边界点 (0,13) 已由 p12 直接给出。", flush=True)

    candidates = generate_candidates_for_problem_21(p12)
    print(f"[问题2.1] 候选点数量：{len(candidates)}", flush=True)

    best = boundary
    best_vehicle = boundary.vehicle_count

    for vehicles, cost, x, y in candidates:
        if vehicles >= best_vehicle:
            continue

        thorough = is_high_prob_point(x, y, "min_vehicle")
        flag = "高概率点-精细验证" if thorough else "普通点-快筛"
        print(f"[问题2.1] 验证点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}，模式={flag}", flush=True)

        # 先快筛
        sol_fast = try_fixed_point_solution_fast(p12, x, y, "min_vehicle", thorough=thorough)
        if sol_fast is None or (not sol_fast.feasible):
            continue

        # 快筛通过后再强验证
        print(f"[问题2.1] 点 ({x},{y}) 快筛通过，进入强验证...", flush=True)
        sol = try_fixed_point_solution_strong(p12, x, y, "min_vehicle", thorough=thorough)

        if sol is not None and sol.feasible:
            print(f"[问题2.1] 找到更优可行点 ({x},{y})", flush=True)
            return sol

    print("[问题2.1] 未找到优于边界点的混合方案，返回边界解 (0,13)。", flush=True)
    return best


def solve_problem_22(p12) -> MixedSolution:
    print("[问题2.2] 直接复用 p12 已验证边界点 (0,13)...", flush=True)
    boundary = build_boundary_solution_from_p12(p12, "min_cost")
    if boundary is None or (not boundary.feasible):
        raise RuntimeError("无法从最新 p12 直接构造边界点 (0,13)。")
    print("[问题2.2] 边界点 (0,13) 已由 p12 直接给出。", flush=True)
    print("[问题2.2] 搜索空间限制在成本三角域 450x+700y < 9100 内。", flush=True)
    print("[问题2.2] 优先检查从 (0,13) 向左下展开的对角线及次对角线附近点。", flush=True)

    candidates = generate_candidates_for_problem_22(p12)
    print(f"[问题2.2] 候选点数量：{len(candidates)}", flush=True)

    best = boundary
    best_cost = boundary.total_cost

    for cost, vehicles, x, y in candidates:
        if cost >= best_cost:
            continue

        thorough = is_high_prob_point(x, y, "min_cost") or diagonal_priority_from_boundary(x, y)[0] <= 1
        flag = "高概率点-精细验证" if thorough else "普通点-快筛"
        print(f"[问题2.2] 验证点 ({x},{y})，车辆数={vehicles}，成本={cost:.0f}，模式={flag}", flush=True)

        sol_fast = try_fixed_point_solution_fast(p12, x, y, "min_cost", thorough=thorough)
        if sol_fast is None or (not sol_fast.feasible):
            continue

        print(f"[问题2.2] 点 ({x},{y}) 快筛通过，进入强验证...", flush=True)
        sol = try_fixed_point_solution_strong(p12, x, y, "min_cost", thorough=thorough)

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
    parser = argparse.ArgumentParser(description="MathorCup D题 - 问题二（二维点枚举 + 快筛验证器 + 强验证器）")
    parser.add_argument(
        "--p12-path",
        type=str,
        default="../../问题一/代码/p12_final_best_combo_v2.py",
        help="最新问题1.2求解器路径",
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
    print("开始求解问题二（二维点枚举 + 快筛验证器 + 强验证器）")
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
