from __future__ import annotations

import json, time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Sequence

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


def pack_all_with_single_truck_type(
    items: Sequence[CargoItem],
    truck: TruckType,
    alpha: float = 0.5,
    beta: float = 0.5,
) -> List[PackingResult]:
    remaining = list(items)
    trips: List[PackingResult] = []
    trip_idx = 1
    while remaining:
        seed = RANDOM_SEED + truck.truck_id * 1000 + trip_idx
        result = genetic_optimize_single_truck(remaining, truck, alpha=alpha, beta=beta, seed=seed)
        if not result.placed:
            raise RuntimeError(f"存在无法装入 {truck.name} 的货物，无法完成问题1.2求解")
        trips.append(result)
        loaded_ids = {item.item_id for item in result.placed}
        remaining = [item for item in remaining if item.item_id not in loaded_ids]
        trip_idx += 1
    return trips


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


def solve_problem_1_2(alpha: float = 0.5, beta: float = 0.5) -> tuple[Dict[int, Dict[str, Any]], int]:
    items = expand_cargo_items(load_cargo_types())
    trucks = load_truck_types()
    plans = {}
    for truck_id, truck in trucks.items():
        trips = pack_all_with_single_truck_type(items, truck, alpha=alpha, beta=beta)
        plans[truck_id] = {"truck": truck, "trips": trips, "summary": summarize_plan(truck, trips)}
    best = min(plans.items(), key=lambda kv: (kv[1]["summary"]["vehicle_count"], kv[1]["summary"]["total_cost"]))
    return plans, best[0]


def save_problem_1_2_results(plans: Dict[int, Dict[str, Any]], best_id: int, output_dir: Path | None = None) -> None:
    output_dir = output_dir or Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    overview = {
        "best_truck_type": best_id,
        "plans": {truck_id: plan["summary"] for truck_id, plan in plans.items()},
    }
    (output_dir / "problem1_2_summary.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")
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
        (output_dir / f"problem1_2_truck_{truck_id}_solution.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def print_problem_1_2_summary(plans: Dict[int, Dict[str, Any]], best_id: int, elapsed: float) -> None:
    print("问题1.2 单一车型下车辆数最少求解结果")
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
    plans, best_id = solve_problem_1_2()
    save_problem_1_2_results(plans, best_id)
    print_problem_1_2_summary(plans, best_id, time.time() - start)
