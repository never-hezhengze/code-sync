from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 复用旧版 problem1_1.py
from problem1_1 import (
    RANDOM_SEED,
    CargoItem,
    PackingResult,
    TruckType,
    expand_cargo_items,
    genetic_optimize_single_truck,
    load_cargo_types,
    load_truck_types,
    result_to_dict,
)

# 可选进度条
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


# =========================
# 通用日志输出
# =========================
def log(msg: str) -> None:
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def iter_with_progress(iterable, desc: str):
    if tqdm is not None:
        return tqdm(iterable, desc=desc, leave=False)
    return iterable


# =========================
# 基础工具
# =========================
def lower_bound_vehicle_count(items: Sequence[CargoItem], truck: TruckType) -> int:
    total_volume = sum(item.volume for item in items)
    total_weight = sum(item.weight for item in items)
    lb_volume = math.ceil(total_volume / (truck.length * truck.width * (truck.height - 3)))
    lb_weight = math.ceil(total_weight / truck.max_weight)
    return max(lb_volume, lb_weight)


def evaluate_result_quality(results: Sequence[PackingResult]) -> float:
    """
    用于比较同一K下多个可行方案的优劣。
    优先：
    1. 车数少（固定K时相同）
    2. 平均利用率更高
    3. 最差一辆车不要太差
    """
    if not results:
        return float("-inf")

    avg_score = sum(r.score for r in results) / len(results)
    min_score = min(r.score for r in results)
    avg_vol = sum(r.volume_utilization for r in results) / len(results)
    return 100 * avg_score + 20 * avg_vol + 10 * min_score


def summarize_plan(truck: TruckType, trips: Sequence[PackingResult]) -> Dict[str, Any]:
    total_volume = sum(result.utilized_volume for result in trips)
    total_weight = sum(result.utilized_weight for result in trips)
    return {
        "truck": asdict(truck),
        "vehicle_count": len(trips),
        "total_cost": truck.trip_cost * len(trips),
        "avg_space_utilization": round(sum(result.volume_utilization for result in trips) / len(trips), 6),
        "avg_weight_utilization": round(sum(result.weight_utilization for result in trips) / len(trips), 6),
        "total_volume_cm3": total_volume,
        "total_weight_kg": round(total_weight, 3),
        "trip_summaries": [
            {
                "trip_id": idx + 1,
                **result_to_dict(result)["summary"],
            }
            for idx, result in enumerate(trips)
        ],
    }


# =========================
# 全局排序：更适合问题1.2
# =========================
def difficulty_rank(item: CargoItem) -> int:
    return {
        "fragile": 3,
        "oriented": 2,
        "standard": 1,
    }[item.category]


def global_sort_items(items: Sequence[CargoItem]) -> List[CargoItem]:
    return sorted(
        items,
        key=lambda item: (
            -difficulty_rank(item),
            -item.volume,
            -item.weight,
            item.type_id,
            item.item_id,
        )
    )


# =========================
# 初始分配：固定K辆车
# =========================
def greedy_partition_into_k(items: Sequence[CargoItem], truck: TruckType, k: int) -> List[List[CargoItem]]:
    trips: List[List[CargoItem]] = [[] for _ in range(k)]
    usable_volume = truck.length * truck.width * (truck.height - 3)

    vol_used = [0 for _ in range(k)]
    wt_used = [0.0 for _ in range(k)]

    for item in global_sort_items(items):
        candidates = []
        for idx in range(k):
            if vol_used[idx] + item.volume <= usable_volume * 1.05 and wt_used[idx] + item.weight <= truck.max_weight:
                fill = max(
                    (vol_used[idx] + item.volume) / usable_volume,
                    (wt_used[idx] + item.weight) / truck.max_weight,
                )
                empty_penalty = 0.2 if len(trips[idx]) == 0 else 0.0
                candidates.append((fill + empty_penalty, idx))

        if candidates:
            _, best_idx = min(candidates, key=lambda x: x[0])
        else:
            best_idx = min(range(k), key=lambda idx: (vol_used[idx], wt_used[idx]))

        trips[best_idx].append(item)
        vol_used[best_idx] += item.volume
        wt_used[best_idx] += item.weight

    return trips


# =========================
# 固定一组分配后，逐车调用旧版单车优化器
# =========================
def repack_trip(items: Sequence[CargoItem], truck: TruckType, seed: int) -> PackingResult:
    best = None

    for restart in range(6):
        result = genetic_optimize_single_truck(
            items,
            truck,
            alpha=0.5,
            beta=0.5,
            population_size=18,
            generations=24,
            seed=seed + restart * 137,
        )

        if best is None:
            best = result
            continue

        # 先比较装入件数，再比较综合得分
        if len(result.placed) > len(best.placed) or (
            len(result.placed) == len(best.placed) and result.score > best.score
        ):
            best = result

    return best


def pack_partition(partition: List[List[CargoItem]], truck: TruckType, seed: int) -> Tuple[bool, List[PackingResult], List[CargoItem]]:
    results: List[PackingResult] = []
    leftovers: List[CargoItem] = []

    for idx, trip_items in enumerate(partition):
        if not trip_items:
            results.append(PackingResult(truck, [], [], 0, 0.0, 0.0))
            continue

        result = repack_trip(trip_items, truck, seed + idx * 1009)
        results.append(result)
        leftovers.extend(result.unplaced)

    success = (len(leftovers) == 0)
    return success, results, leftovers


# =========================
# 大邻域搜索（LNS）
# =========================
def plan_signature(plan: List[List[CargoItem]]) -> Tuple[Tuple[str, ...], ...]:
    sig = []
    for trip in plan:
        sig.append(tuple(sorted(item.item_id for item in trip)))
    return tuple(sorted(sig))


def destroy_repair_once(plan: List[List[CargoItem]], truck: TruckType, rng: random.Random) -> List[List[CargoItem]]:
    new_plan = [trip[:] for trip in plan]
    non_empty = [i for i, trip in enumerate(new_plan) if trip]
    if not non_empty:
        return new_plan

    # 选 1~2 辆车进行 destroy
    rng.shuffle(non_empty)
    selected = non_empty[: min(2, len(non_empty))]

    removed: List[CargoItem] = []

    for idx in selected:
        trip = new_plan[idx]
        trip_sorted = sorted(
            trip,
            key=lambda item: (
                difficulty_rank(item),
                item.volume,
                item.weight,
            ),
            reverse=True,
        )
        remove_count = max(1, min(len(trip_sorted), max(2, len(trip_sorted) // 4)))
        chosen = trip_sorted[:remove_count]

        chosen_ids = {x.item_id for x in chosen}
        new_plan[idx] = [x for x in trip if x.item_id not in chosen_ids]
        removed.extend(chosen)

    # repair：困难货优先插入
    removed = global_sort_items(removed)
    usable_volume = truck.length * truck.width * (truck.height - 3)
    vol_used = [sum(x.volume for x in trip) for trip in new_plan]
    wt_used = [sum(x.weight for x in trip) for trip in new_plan]

    for item in removed:
        candidates = []
        for idx in range(len(new_plan)):
            if vol_used[idx] + item.volume <= usable_volume * 1.03 and wt_used[idx] + item.weight <= truck.max_weight:
                fill = max(
                    (vol_used[idx] + item.volume) / usable_volume,
                    (wt_used[idx] + item.weight) / truck.max_weight,
                )
                empty_penalty = 0.15 if len(new_plan[idx]) == 0 else 0.0
                candidates.append((fill + empty_penalty, idx))

        if candidates:
            _, best_idx = min(candidates, key=lambda x: x[0])
        else:
            best_idx = min(range(len(new_plan)), key=lambda idx: (vol_used[idx], wt_used[idx]))

        new_plan[best_idx].append(item)
        vol_used[best_idx] += item.volume
        wt_used[best_idx] += item.weight

    return new_plan


def evaluate_partition(plan: List[List[CargoItem]], truck: TruckType, seed: int) -> Tuple[float, bool, List[PackingResult], List[CargoItem]]:
    success, results, leftovers = pack_partition(plan, truck, seed)

    used_bins = sum(1 for trip in plan if trip)
    total_util = sum(r.volume_utilization + 0.4 * r.weight_utilization for r in results)

    score = 0.0
    score -= 100000 * len(leftovers)
    score -= 2000 * used_bins
    score += 100 * total_util

    # 惩罚“最后一辆车极差”的解
    non_empty_results = [r for r in results if r.placed]
    if non_empty_results:
        min_util = min(r.volume_utilization for r in non_empty_results)
        score -= 50 * (0.15 - min_util) if min_util < 0.15 else 0.0

    return score, success, results, leftovers


def large_neighborhood_search(
    initial_plan: List[List[CargoItem]],
    truck: TruckType,
    max_iters: int = 100,
    seed: int = RANDOM_SEED,
) -> Tuple[bool, List[PackingResult], List[List[CargoItem]]]:
    rng = random.Random(seed)

    current = [trip[:] for trip in initial_plan]
    best = [trip[:] for trip in initial_plan]

    best_score, best_success, best_results, best_leftovers = evaluate_partition(best, truck, seed + 1)
    current_score = best_score
    seen = {plan_signature(best)}

    log(f"  LNS开始：初始得分={best_score:.2f}，是否可行={best_success}，剩余货物={len(best_leftovers)}")

    iterator = iter_with_progress(range(max_iters), desc="LNS迭代")
    for it in iterator:
        candidate = destroy_repair_once(current, truck, rng)
        sig = plan_signature(candidate)
        if sig in seen:
            continue
        seen.add(sig)

        score, success, results, leftovers = evaluate_partition(candidate, truck, seed + 1000 + it)

        # 接受准则：更优必收，少量随机扰动也允许
        if score > current_score or rng.random() < 0.05:
            current = candidate
            current_score = score

        if score > best_score:
            best = candidate
            best_score = score
            best_success = success
            best_results = results
            best_leftovers = leftovers
            log(f"  LNS更新：iter={it+1}, best_score={best_score:.2f}, feasible={best_success}, leftovers={len(best_leftovers)}")

    return best_success, best_results, best


# =========================
# 固定K辆车搜索
# =========================
def try_pack_with_fixed_k(
    items: Sequence[CargoItem],
    truck: TruckType,
    k: int,
    restarts: int = 8,
    seed: int = RANDOM_SEED,
) -> Optional[List[PackingResult]]:
    log(f"开始尝试固定 K={k} 辆 {truck.name}")

    best_feasible = None
    best_quality = float("-inf")

    iterator = iter_with_progress(range(restarts), desc=f"{truck.name}-K={k}-重启")
    for r in iterator:
        log(f"  重启 {r+1}/{restarts}：构造初始分配")
        init_plan = greedy_partition_into_k(items, truck, k)

        log(f"  重启 {r+1}/{restarts}：进入大邻域搜索")
        success, results, best_plan = large_neighborhood_search(
            init_plan,
            truck,
            max_iters=80,
            seed=seed + r * 10007,
        )

        score, success, results, leftovers = evaluate_partition(best_plan, truck, seed + r * 777 + 999)

        if success and len(leftovers) == 0:
            quality = evaluate_result_quality([r for r in results if r.placed])
            log(f"  找到可行解：K={k}, 重启={r+1}, quality={quality:.2f}")
            if quality > best_quality:
                best_quality = quality
                best_feasible = [res for res in results if res.placed]

    if best_feasible is not None:
        log(f"K={k} 已找到可行方案")
    else:
        log(f"K={k} 未找到可行方案")

    return best_feasible


def solve_single_truck_type_min_vehicles(
    items: Sequence[CargoItem],
    truck: TruckType,
    seed: int = RANDOM_SEED,
    max_extra_search: int = 4,
) -> List[PackingResult]:
    lb = lower_bound_vehicle_count(items, truck)
    log(f"{truck.name} 理论下界 LB = {lb}")

    for k in range(lb, lb + max_extra_search + 1):
        plan = try_pack_with_fixed_k(items, truck, k, restarts=8, seed=seed + truck.truck_id * 1000 + k)
        if plan is not None:
            return plan

    raise RuntimeError(f"未能在 K={lb} 到 K={lb + max_extra_search} 中找到 {truck.name} 的可行方案")


# =========================
# 问题1.2总入口
# =========================
def solve_problem_1_2_improved() -> tuple[Dict[int, Dict[str, Any]], int]:
    log("加载数据...")
    items = expand_cargo_items(load_cargo_types())
    trucks = load_truck_types()

    plans = {}
    for truck_id, truck in trucks.items():
        log(f"================ 开始求解 {truck.name} ================")
        trips = solve_single_truck_type_min_vehicles(items, truck, seed=RANDOM_SEED)
        plans[truck_id] = {
            "truck": truck,
            "trips": trips,
            "summary": summarize_plan(truck, trips),
        }

    best = min(plans.items(), key=lambda kv: (kv[1]["summary"]["vehicle_count"], kv[1]["summary"]["total_cost"]))
    return plans, best[0]


def save_problem_1_2_results(plans: Dict[int, Dict[str, Any]], best_id: int, output_dir: Path | None = None) -> None:
    output_dir = output_dir or Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    overview = {
        "best_truck_type": best_id,
        "plans": {truck_id: plan["summary"] for truck_id, plan in plans.items()},
    }
    (output_dir / "problem1_2_summary_improved.json").write_text(
        json.dumps(overview, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for truck_id, plan in plans.items():
        trip_details = []
        for idx, result in enumerate(plan["trips"], 1):
            detail = result_to_dict(result)
            detail["trip_id"] = idx
            trip_details.append(detail)

        payload = {
            "summary": plan["summary"],
            "trip_details": trip_details,
        }
        (output_dir / f"problem1_2_truck_{truck_id}_solution_improved.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def print_problem_1_2_summary(plans: Dict[int, Dict[str, Any]], best_id: int, elapsed: float) -> None:
    print("\n问题1.2 改进版：固定 K + 大邻域搜索")
    print("=" * 60)
    for plan in plans.values():
        summary = plan["summary"]
        print(f"{plan['truck'].name}：")
        print(f"  车辆数：{summary['vehicle_count']}")
        print(f"  总成本：{summary['total_cost']:.2f} 元")
        print(f"  平均空间利用率：{summary['avg_space_utilization']:.4%}")
        print(f"  平均载重利用率：{summary['avg_weight_utilization']:.4%}")
        print("-" * 60)

    print(f"推荐车型：车型{best_id}")
    print(f"总耗时：{elapsed:.2f} s")


if __name__ == "__main__":
    start = time.time()
    plans, best_id = solve_problem_1_2_improved()
    save_problem_1_2_results(plans, best_id)
    print_problem_1_2_summary(plans, best_id, time.time() - start)