#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题1.2（p12）敏感性分析脚本
--------------------------------
功能：
1. 动态导入用户的 p12 主求解脚本（支持文件名中含括号）
2. 对关键算法参数做单因素敏感性分析（OAT: one-at-a-time）
3. 记录每次实验的：车辆数、总成本、平均空间利用率、平均载重利用率、平均 fullness_score
4. 输出详细 CSV、汇总 CSV、JSON
5. 用 Python（matplotlib）绘制条形图，比较不同参数的敏感度

默认分析参数：
- 车型1：HYBRID_KEEP_BASE, HYBRID_KEEP_EXT, HYBRID_KEEP_LIFTED, MAX_SPACES_TO_CHECK, MIN_SPACE_VOLUME
- 车型2：BASE_ONLY_KEEP, MAX_SPACES_TO_CHECK, MIN_SPACE_VOLUME

使用示例：
python p12_sensitivity_analysis.py \
    --solver "/path/to/p12_final_expanded_check(1).py" \
    --truck all \
    --outdir "./p12_sensitivity_output"

说明：
- 本脚本优先比较算法参数敏感性；这比单纯货物数量敏感性更贴合 p12 的模型特征。
- 条形图默认展示“对 avg_fullness_score 的敏感度排名”。
"""

from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt


# =========================
# 可自行调整的默认测试集合
# =========================
DEFAULT_PARAM_GRID = {
    "车型1": {
        "HYBRID_KEEP_BASE": [10, 14, 18, 22, 26],
        "HYBRID_KEEP_EXT": [8, 11, 14, 17, 20],
        "HYBRID_KEEP_LIFTED": [10, 14, 18, 22, 26],
        "MAX_SPACES_TO_CHECK": [40, 60, 80, 100, 120],
        "MIN_SPACE_VOLUME": [10000, 15000, 20000, 25000, 30000],
    },
    "车型2": {
        "BASE_ONLY_KEEP": [10, 15, 20, 25, 30],
        "MAX_SPACES_TO_CHECK": [40, 60, 80, 100, 120],
        "MIN_SPACE_VOLUME": [10000, 15000, 20000, 25000, 30000],
    },
}

def get_param_grid(solver, truck_name: str) -> Dict[str, List[Any]]:
    grid = DEFAULT_PARAM_GRID.get(truck_name, {})
    return {k: v for k, v in grid.items() if hasattr(solver, k)}


@dataclass
class RunResult:
    truck_name: str
    param_name: str
    param_value: Any
    vehicle_count: int
    total_cost: float
    avg_space_utilization: float
    avg_weight_utilization: float
    avg_fullness_score: float
    success: bool
    error: str = ""


def load_solver_module(solver_path: str):
    """按文件路径动态导入 p12 主程序，兼容文件名中含空格/括号。"""
    solver_path = os.path.abspath(solver_path)
    if not os.path.exists(solver_path):
        raise FileNotFoundError(f"未找到求解器文件：{solver_path}")

    module_name = "p12_solver_dynamic"
    spec = importlib.util.spec_from_file_location(module_name, solver_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法导入求解器文件：{solver_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def snapshot_globals(solver) -> Dict[str, Any]:
    """备份会被敏感性分析修改的全局参数。"""
    keys = [
        "HYBRID_KEEP_BASE",
        "HYBRID_KEEP_EXT",
        "HYBRID_KEEP_LIFTED",
        "BASE_ONLY_KEEP",
        "MAX_SPACES_TO_CHECK",
        "MIN_SPACE_VOLUME",
        "RANDOM_SEED",
    ]
    snap = {}
    for k in keys:
        if hasattr(solver, k):
            snap[k] = getattr(solver, k)
    return snap


def restore_globals(solver, snap: Dict[str, Any]) -> None:
    for k, v in snap.items():
        setattr(solver, k, v)


def snapshot_cargo_quantities(solver) -> Dict[str, int]:
    """备份货物数量，防止求解过程外部改动留下副作用。"""
    backup = {}
    for cargo_id, cargo in solver.CARGO_TYPES.items():
        backup[cargo_id] = cargo.quantity
    return backup


def restore_cargo_quantities(solver, backup: Dict[str, int]) -> None:
    for cargo_id, qty in backup.items():
        object.__setattr__(solver.CARGO_TYPES[cargo_id], "quantity", qty)


def compute_avg_fullness(summary: Dict[str, Any]) -> float:
    sv = float(summary.get("avg_space_utilization", 0.0))
    wv = float(summary.get("avg_weight_utilization", 0.0))
    return 0.72 * sv + 0.28 * wv


def safe_run_solver_once(solver, truck_name: str, param_name: str, param_value: Any) -> RunResult:
    """执行一次单参数实验。"""
    global_snap = snapshot_globals(solver)
    cargo_snap = snapshot_cargo_quantities(solver)

    try:
        setattr(solver, param_name, param_value)
        if hasattr(solver, "random") and hasattr(solver, "RANDOM_SEED"):
            solver.random.seed(getattr(solver, "RANDOM_SEED"))

        solver_func = solver.solve_one_truck_type
        plans, summary, _templates = solver_func(truck_name)
        avg_fullness = compute_avg_fullness(summary)

        return RunResult(
            truck_name=truck_name,
            param_name=param_name,
            param_value=param_value,
            vehicle_count=int(summary["vehicle_count"]),
            total_cost=float(summary["total_cost"]),
            avg_space_utilization=float(summary["avg_space_utilization"]),
            avg_weight_utilization=float(summary["avg_weight_utilization"]),
            avg_fullness_score=float(avg_fullness),
            success=True,
        )
    except Exception as e:
        return RunResult(
            truck_name=truck_name,
            param_name=param_name,
            param_value=param_value,
            vehicle_count=-1,
            total_cost=float("nan"),
            avg_space_utilization=float("nan"),
            avg_weight_utilization=float("nan"),
            avg_fullness_score=float("nan"),
            success=False,
            error=str(e),
        )
    finally:
        restore_globals(solver, global_snap)
        restore_cargo_quantities(solver, cargo_snap)


def pick_baseline_value(solver, param_name: str, values: List[Any]) -> Any:
    """优先使用求解器当前值作为 baseline；若不在列表中则用列表中间值。"""
    current = getattr(solver, param_name, None)
    if current in values:
        return current
    return values[len(values) // 2]


def run_parameter_sensitivity(solver, truck_name: str, grid: Dict[str, List[Any]]) -> Tuple[List[RunResult], List[Dict[str, Any]]]:
    """对某车型运行完整参数敏感性分析。"""
    all_runs: List[RunResult] = []
    metric_rows: List[Dict[str, Any]] = []

    for param_name, values in grid.items():
        print(f"\n[{truck_name}] 开始敏感性分析参数：{param_name}")
        baseline_value = pick_baseline_value(solver, param_name, values)
        param_runs: List[RunResult] = []

        for val in values:
            res = safe_run_solver_once(solver, truck_name, param_name, val)
            all_runs.append(res)
            param_runs.append(res)
            if res.success:
                print(
                    f"  {param_name}={val:<8} -> 车辆数={res.vehicle_count:<3d}, "
                    f"avg_fullness={res.avg_fullness_score:.6f}, "
                    f"空={res.avg_space_utilization:.6f}, 重={res.avg_weight_utilization:.6f}"
                )
            else:
                print(f"  {param_name}={val:<8} -> 失败: {res.error}")

        baseline_run = next((r for r in param_runs if r.param_value == baseline_value and r.success), None)
        successful = [r for r in param_runs if r.success]

        if baseline_run is None or len(successful) < 2:
            metric_rows.append({
                "truck_name": truck_name,
                "param_name": param_name,
                "baseline_value": baseline_value,
                "baseline_vehicle_count": baseline_run.vehicle_count if baseline_run else "",
                "baseline_avg_fullness": baseline_run.avg_fullness_score if baseline_run else "",
                "fullness_range": "",
                "vehicle_count_range": "",
                "relative_sensitivity_fullness": "",
                "relative_sensitivity_vehicle_count": "",
                "success_count": len(successful),
            })
            continue

        fullness_vals = [r.avg_fullness_score for r in successful]
        vehicle_vals = [r.vehicle_count for r in successful]

        # 相对敏感度：平均 |相对输出变化 / 相对输入变化|
        sens_fullness_list = []
        sens_vehicle_list = []
        x0 = float(baseline_value)
        y0f = baseline_run.avg_fullness_score
        y0v = float(baseline_run.vehicle_count)

        for r in successful:
            x = float(r.param_value)
            if abs(x - x0) < 1e-12:
                continue
            dx_rel = abs((x - x0) / max(abs(x0), 1e-12))
            if dx_rel < 1e-12:
                continue

            dyf_rel = abs((r.avg_fullness_score - y0f) / max(abs(y0f), 1e-12))
            dyv_rel = abs((float(r.vehicle_count) - y0v) / max(abs(y0v), 1e-12))

            sens_fullness_list.append(dyf_rel / dx_rel)
            sens_vehicle_list.append(dyv_rel / dx_rel)

        metric_rows.append({
            "truck_name": truck_name,
            "param_name": param_name,
            "baseline_value": baseline_value,
            "baseline_vehicle_count": baseline_run.vehicle_count,
            "baseline_avg_fullness": round(baseline_run.avg_fullness_score, 6),
            "fullness_range": round(max(fullness_vals) - min(fullness_vals), 6),
            "vehicle_count_range": int(max(vehicle_vals) - min(vehicle_vals)),
            "relative_sensitivity_fullness": round(sum(sens_fullness_list) / max(len(sens_fullness_list), 1), 6),
            "relative_sensitivity_vehicle_count": round(sum(sens_vehicle_list) / max(len(sens_vehicle_list), 1), 6),
            "success_count": len(successful),
        })

    metric_rows.sort(
        key=lambda d: (d["relative_sensitivity_fullness"] if d["relative_sensitivity_fullness"] != "" else -1),
        reverse=True,
    )
    return all_runs, metric_rows


def write_run_results_csv(path: str, rows: List[RunResult]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "truck_name",
            "param_name",
            "param_value",
            "vehicle_count",
            "total_cost",
            "avg_space_utilization",
            "avg_weight_utilization",
            "avg_fullness_score",
            "success",
            "error",
        ])
        for r in rows:
            w.writerow([
                r.truck_name,
                r.param_name,
                r.param_value,
                r.vehicle_count,
                "" if math.isnan(r.total_cost) else round(r.total_cost, 6),
                "" if math.isnan(r.avg_space_utilization) else round(r.avg_space_utilization, 6),
                "" if math.isnan(r.avg_weight_utilization) else round(r.avg_weight_utilization, 6),
                "" if math.isnan(r.avg_fullness_score) else round(r.avg_fullness_score, 6),
                int(r.success),
                r.error,
            ])


def write_metric_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "truck_name",
            "param_name",
            "baseline_value",
            "baseline_vehicle_count",
            "baseline_avg_fullness",
            "fullness_range",
            "vehicle_count_range",
            "relative_sensitivity_fullness",
            "relative_sensitivity_vehicle_count",
            "success_count",
        ])
        for d in rows:
            w.writerow([
                d["truck_name"],
                d["param_name"],
                d["baseline_value"],
                d["baseline_vehicle_count"],
                d["baseline_avg_fullness"],
                d["fullness_range"],
                d["vehicle_count_range"],
                d["relative_sensitivity_fullness"],
                d["relative_sensitivity_vehicle_count"],
                d["success_count"],
            ])


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def plot_sensitivity_bar(metric_rows: List[Dict[str, Any]], truck_name: str, outdir: str) -> str:
    """绘制条形图：比较不同参数对 avg_fullness 的敏感度。"""
    valid = [d for d in metric_rows if d["relative_sensitivity_fullness"] != ""]
    if not valid:
        raise RuntimeError(f"{truck_name} 没有可用于绘图的敏感度数据。")

    # 设置中文字体兼容性
    plt.rcParams['font.sans-serif'] = ['Heiti TC', 'STHeiti', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    names = [d["param_name"] for d in valid]
    values = [float(d["relative_sensitivity_fullness"]) for d in valid]

    truck_label = {
        "车型1": "车型1",
        "车型2": "车型2",
    }.get(truck_name, truck_name)

    # 定义好看的配色方案
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    plt.figure(figsize=(10, 5.8))
    bars = plt.bar(names, values, color=colors[:len(names)])
    plt.ylabel("avg_fullness_score 的相对敏感度")
    plt.xlabel("参数")
    plt.title(f"{truck_label} 参数敏感度排名")
    plt.xticks(rotation=20, ha="right")

    for bar, v in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{v:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    path = os.path.join(outdir, f"{truck_name}_参数敏感度条形图.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    return path


def save_analysis_summary_txt(path: str, metric_rows: List[Dict[str, Any]], truck_name: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"=== {truck_name} 参数敏感性分析结论 ===\n\n")
        if not metric_rows:
            f.write("无可用结果。\n")
            return

        ranked = [d for d in metric_rows if d["relative_sensitivity_fullness"] != ""]
        ranked.sort(key=lambda x: x["relative_sensitivity_fullness"], reverse=True)

        f.write("按 avg_fullness_score 相对敏感度从高到低排序：\n\n")
        for i, d in enumerate(ranked, 1):
            f.write(
                f"{i}. {d['param_name']}\n"
                f"   baseline={d['baseline_value']}\n"
                f"   baseline_avg_fullness={d['baseline_avg_fullness']}\n"
                f"   fullness_range={d['fullness_range']}\n"
                f"   vehicle_count_range={d['vehicle_count_range']}\n"
                f"   relative_sensitivity_fullness={d['relative_sensitivity_fullness']}\n"
                f"   relative_sensitivity_vehicle_count={d['relative_sensitivity_vehicle_count']}\n\n"
            )

        if ranked:
            top = ranked[0]
            f.write("结论建议：\n")
            f.write(
                f"- {top['param_name']} 是当前 {truck_name} 下最敏感的算法参数，优先调参应首先关注它。\n"
                "- 若某参数的 fullness_range 较小但 vehicle_count_range 较大，说明它对车辆数更敏感，适合从“少车目标”角度单独讨论。\n"
                "- 若某参数的相对敏感度较低，则可在该参数附近固定取值，以减少调参成本。\n"
            )


def analyze_one_truck(solver, truck_name: str, outdir: str) -> Dict[str, Any]:
    grid = get_param_grid(solver, truck_name)
    if not grid:
        raise RuntimeError(f"求解器 {getattr(solver, '__file__', 'unknown')} 未提供可用于{truck_name}的参数网格。")

    truck_dir = os.path.join(outdir, truck_name)
    os.makedirs(truck_dir, exist_ok=True)

    run_rows, metric_rows = run_parameter_sensitivity(solver, truck_name, grid)
    run_csv = os.path.join(truck_dir, f"{truck_name}_参数敏感性明细.csv")
    metric_csv = os.path.join(truck_dir, f"{truck_name}_参数敏感度汇总.csv")
    json_path = os.path.join(truck_dir, f"{truck_name}_参数敏感性结果.json")
    txt_path = os.path.join(truck_dir, f"{truck_name}_参数敏感性结论.txt")

    write_run_results_csv(run_csv, run_rows)
    write_metric_csv(metric_csv, metric_rows)
    write_json(
        json_path,
        {
            "truck_name": truck_name,
            "parameter_grid": grid,
            "run_rows": [r.__dict__ for r in run_rows],
            "metric_rows": metric_rows,
        },
    )
    save_analysis_summary_txt(txt_path, metric_rows, truck_name)
    plot_path = plot_sensitivity_bar(metric_rows, truck_name, truck_dir)

    return {
        "truck_name": truck_name,
        "run_csv": run_csv,
        "metric_csv": metric_csv,
        "json_path": json_path,
        "txt_path": txt_path,
        "plot_path": plot_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="p12 参数敏感性分析 + Python 条形图")
    parser.add_argument("--solver", type=str, required=True, help="p12 主程序路径，例如 p12_final_expanded_check(1).py")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="./p12_sensitivity_output", help="输出目录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    solver = load_solver_module(args.solver)
    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    final_report = {}

    print("=" * 72)
    print("开始 p12 参数敏感性分析")
    print("=" * 72)
    print(f"求解器文件：{os.path.abspath(args.solver)}")
    print(f"输出目录：{outdir}\n")

    for truck_name in truck_list:
        print("=" * 72)
        print(f"开始分析：{truck_name}")
        print("=" * 72)
        result = analyze_one_truck(solver, truck_name, outdir)
        final_report[truck_name] = result
        print(f"\n[{truck_name}] 条形图已保存到：{result['plot_path']}")
        print(f"[{truck_name}] 汇总 CSV 已保存到：{result['metric_csv']}")
        print()

    final_json = os.path.join(outdir, "p12_sensitivity_master_report.json")
    write_json(final_json, final_report)
    print("=" * 72)
    print("全部分析完成")
    print(f"总报告：{final_json}")
    print("=" * 72)


if __name__ == "__main__":
    main()
