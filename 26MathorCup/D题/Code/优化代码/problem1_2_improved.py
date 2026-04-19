from __future__ import annotations

import json
import math
import random
import time
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from problem1_1_improved import (
    RANDOM_SEED,
    CargoItem,
    PackingResult,
    TruckType,
    expand_cargo_items,
    genetic_optimize_single_truck,
    load_cargo_types,
    load_truck_types,
    pack_single_truck,
    result_to_dict,
)

# -----------------------------
# 基础工具
# -----------------------------

def lower_bound_vehicle_count(items: Sequence[CargoItem], truck: TruckType) -> int:
    total_volume = sum(item.volume for item in items)
    total_weight = sum(item.weight for item in items)
    lb_volume = math.ceil(total_volume / truck.volume)
    lb_weight = math.ceil(total_weight / truck.max_weight)
    return max(lb_volume, lb_weight)


def repack_trip(items: Sequence[CargoItem], truck: TruckType, seed: int, alpha: float = 0.5, beta: float = 0.5) -> PackingResult:
    # 多次重启，挑一个最好的单车打包结果
    best = None
    for r in range(8):
        result = genetic_optimize_single_truck(
            items,
            truck,
            alpha=alpha,
            beta=beta,
            population_size=18,
            generations=24,
            seed=seed + r * 131,
        )
        if best is None:
            best = result
            continue

        # 优先更多装入件数，其次更高得分
        if len(result.placed) > len(best.placed) or (
            len(result.placed) == len(best.placed) and result.score > best.score
        ):
            best = result
    return best


def trip_items_from_result(result: PackingResult, item_map: Dict[str, CargoItem]) -> List[CargoItem]:
    placed_ids = [p.item_id for p in result.placed]
    return [item_map[iid] for iid in placed_ids]


def build_item_map(items: Sequence[CargoItem]) -> Dict[str, CargoItem]:
    return {item.item_id: item for item in items}


def plan_vehicle_count(plan: List[List[CargoItem]]) -> int:
    return sum(1 for trip in plan if trip)


def plan_signature(plan: List[List[CargoItem]]) -> Tuple[Tuple[str, ...], ...]:
    sig = []
    for trip in plan:
        sig.append(tuple(sorted(item.item_id for item in trip)))
    return tuple(sorted(sig))


# -----------------------------
# 初始解构造：固定 K 辆车
# -----------------------------

def global_difficulty_sort(items: Sequence[CargoItem]) -> List[CargoItem]:
    def difficulty(item: CargoItem) -> int:
        return {"fragile": 3, "oriented": 2, "standard": 1}[item.category]

    return sorted(
        items,
        key=lambda item: (
            -difficulty(item),
            -item.volume,
            -item.weight,
            item.type_id,
            item.item_id,
        )
    )


def greedy_partition_into_k(items: Sequence[CargoItem], truck: TruckType, k: int) -> List[List[CargoItem]]:
    """
    先用体积和重量的双重平衡做一个全局初分配。
    这里只做“分车”，不做坐标装箱。
    """
    trips: List[List[CargoItem]] = [[] for _ in range(k)]
    vol_used = [0 for _ in range(k)]
    wt_used = [0.0 for _ in range(k)]

    for item in global_difficulty_sort(items):
        feasible_bins = []
        for idx in range(k):
            if vol_used[idx] + item.volume <= truck.volume * 1.05 and wt_used[idx] + item.weight <= truck.max_weight:
                fill_score = max(
                    (vol_used[idx] + item.volume) / truck.volume,
                    (wt_used[idx] + item.weight) / truck.max_weight,
                )
                balance_penalty = 0.15 * ((vol_used[idx] + item.volume) / truck.volume)
                feasible_bins.append((fill_score - balance_penalty, idx))

        if feasible_bins:
            _, best_idx = min(feasible_bins, key=lambda x: x[0])
        else:
            best_idx = min(range(k), key=lambda idx: (vol_used[idx] / truck.volume, wt_used[idx] / truck.max_weight))

        trips[best_idx].append(item)
        vol_used[best_idx] += item.volume
        wt_used[best_idx] += item.weight

    return trips


def pack_partition(partition: List[List[CargoItem]], truck: TruckType, seed: int) -> Tuple[bool, List[PackingResult], List[CargoItem]]:
    """
    对固定分组后的每辆车分别做单车装箱。
    若所有货物都能装入各自车辆，则 success=True。
    """
    packed_results: List[PackingResult] = []
    leftover: List[CargoItem] = []

    for idx, trip_items in enumerate(partition):
        if not trip_items:
            packed_results.append(PackingResult(truck, [], [], 0, 0.0, 0.0))
            continue

        result = repack_trip(trip_items, truck, seed + idx * 997)
        packed_results.append(result)
        leftover.extend(result.unplaced)

    success = (len(leftover) == 0)
    return success, packed_results, leftover


# -----------------------------
# 大邻域搜索（LNS）
# -----------------------------

def destroy_repair_once(
    current_partition: List[List[CargoItem]],
    truck: TruckType,
    item_map: Dict[str, CargoItem],
    rng: random.Random,
) -> List[List[CargoItem]]:
    """
    destroy:
      - 挑利用率最差的1~2辆车
      - 挑其中部分“难装货”与“大件”
    repair:
      - 重新全局插入到所有车
    """
    new_partition = [trip[:] for trip in current_partition]

    non_empty_indices = [i for i, trip in enumerate(new_partition) if trip]
    if not non_empty_indices:
        return new_partition

    # 挑 1~2 辆非空车做 destroy
    rng.shuffle(non_empty_indices)
    selected_bins = non_empty_indices[: min(2, len(non_empty_indices))]

    removed: List[CargoItem] = []
    for idx in selected_bins:
        trip = new_partition[idx]
        if not trip:
            continue

        trip_sorted = sorted(
            trip,
            key=lambda item: (
                {"fragile": 3, "oriented": 2, "standard": 1}[item.category],
                item.volume,
                item.weight,
            ),
            reverse=True,
        )

        remove_count = max(1, min(len(trip_sorted), max(2, len(trip_sorted) // 4)))
        chosen = trip_sorted[:remove_count]

        chosen_ids = {x.item_id for x in chosen}
        new_partition[idx] = [x for x in trip if x.item_id not in chosen_ids]
        removed.extend(chosen)

    # repair：按困难货优先重新插入
    removed = global_difficulty_sort(removed)

    vol_used = [sum(x.volume for x in trip) for trip in new_partition]
    wt_used = [sum(x.weight for x in trip) for trip in new_partition]

    for item in removed:
        candidate_bins = []
        for idx in range(len(new_partition)):
            if vol_used[idx] + item.volume <= truck.volume * 1.03 and wt_used[idx] + item.weight <= truck.max_weight:
                fill = max(
                    (vol_used[idx] + item.volume) / truck.volume,
                    (wt_used[idx] + item.weight) / truck.max_weight,
                )
                # 倾向于先塞到已有货物的车里，避免出现空车
                empty_penalty = 0.15 if len(new_partition[idx]) == 0 else 0.0
                candidate_bins.append((fill + empty_penalty, idx))

        if candidate_bins:
            _, best_idx = min(candidate_bins, key=lambda x: x[0])
        else:
            # 找最空的那辆
            best_idx = min(range(len(new_partition)), key=lambda idx: (vol_used[idx], wt_used[idx]))

        new_partition[best_idx].append(item)
        vol_used[best_idx] += item.volume
        wt_used[best_idx] += item.weight

    return new_partition


def evaluate_partition(
    partition: List[List[CargoItem]],
    truck: TruckType,
    seed: int,
) -> Tuple[float, bool, List[PackingResult], List[CargoItem]]:
    """
    评价固定 K 辆车分组方案。
    核心：
    - 未装入货物重罚
    - 车数少更优
    - 空车越多越好（说明可压缩）
    - 总利用率更高更优
    """
    success, packed_results, leftover = pack_partition(partition, truck, seed)

    used_bins = sum(1 for trip in partition if trip)
    total_util = sum(r.volume_utilization + 0.4 * r.weight_utilization for r in packed_results)

    score = 0.0
    score -= 100000 * len(leftover)
    score -= 2000 * used_bins
    score += 100 * total_util

    return score, success, packed_results, leftover


def large_neighborhood_search(
    initial_partition: List[List[CargoItem]],
    truck: TruckType,
    max_iters: int = 120,
    seed: int = RANDOM_SEED,
) -> Tuple[bool, List[PackingResult], List[List[CargoItem]]]:
    rng = random.Random(seed)
    item_map = build_item_map([item for trip in initial_partition for item in trip])

    current = [trip[:] for trip in initial_partition]
    best = [trip[:] for trip in initial_partition]

    best_score, best_success, best_results, best_leftover = evaluate_partition(best, truck, seed + 1)
    current_score = best_score

    seen = {plan_signature(best)}

    for it in range(max_iters):
        candidate = destroy_repair_once(current, truck, item_map, rng)
        sig = plan_signature(candidate)
        if sig in seen:
            continue
        seen.add(sig)

        score, success, results, leftover = evaluate_partition(candidate, truck, seed + 1000 + it)

        # 接受准则：优先更优，也允许极少量平局附近移动
        if score > current_score or rng.random() < 0.05:
            current = candidate
            current_score = score

        if score > best_score:
            best = candidate
            best_score = score
            best_success = success
            best_results = results
            best_leftover = leftover

            # 若已完全可行且空车较多，可提前收敛
            if best_success and len(best_leftover) == 0:
                pass

    return best_success, best_results, best


# -----------------------------
# 固定 K 辆车可行性搜索
# -----------------------------

def try_pack_with_fixed_k(
    items: Sequence[CargoItem],
    truck: TruckType,
    k: int,
    restarts: int = 10,
    seed: int = RANDOM_SEED,
) -> Optional[List[PackingResult]]:
    """
    对固定 K 做多次重启：
    1. 全局初分配
    2. LNS 改进
    3. 若找到所有货物都能装入的方案，则返回
    """
    best_feasible = None
    best_feasible_score = float("-inf")

    for r in range(restarts):
        init_partition = greedy_partition_into_k(items, truck, k)
        success, results, best_partition = large_neighborhood_search(
            init_partition,
            truck,
            max_iters=120,
            seed=seed + r * 10007,
        )

        # 再评估一次拿最终结果
        score, success, results, leftover = evaluate_partition(best_partition, truck, seed + r * 777 + 999)

        if success and len(leftover) == 0:
            total_score = sum(res.score for res in results)
            if total_score > best_feasible_score:
                best_feasible = results
                best_feasible_score = total_score

    return best_feasible


def compress_empty_trips(results: List[PackingResult]) -> List[PackingResult]:
    return [r for r in results if r.placed]


def solve_single_truck_type_min_vehicles(
    items: Sequence[CargoItem],
    truck: TruckType,
    seed: int = RANDOM_SEED,
    max_extra_search: int = 4,
) -> List[PackingResult]:
    lb = lower_bound_vehicle_count(items, truck)

    for k in range(lb, lb + max_extra_search + 1):
        plan = try_pack_with_fixed_k(items, truck, k, restarts=12, seed=seed + truck.truck_id * 1000 + k)
        if plan is not None:
            return compress_empty_trips(plan)

    raise RuntimeError(f"未能在 K={lb} 到 K={lb + max_extra_search} 中找到 {truck.name} 的可行方案")


# -----------------------------
# 汇总与输出
# -----------------------------

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


def solve_problem_1_2_improved() -> tuple[Dict[int, Dict[str, Any]], int]:
    items = expand_cargo_items(load_cargo_types())
    trucks = load_truck_types()

    plans = {}
    for truck_id, truck in trucks.items():
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
    print("问题1.2 改进版：固定 K + 大邻域搜索")
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