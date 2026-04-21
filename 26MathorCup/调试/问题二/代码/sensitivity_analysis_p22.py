#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题2.2 敏感性分析：分析货物数量变化对混合车队成本优化的影响
测试货物数量从50%到200%的变化，看车辆配置(x,y)和总成本的变化
"""

import argparse
import json
import os
import sys
import importlib.util
from copy import deepcopy
from typing import Dict, List

import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 导入p2_2模块
sys.path.insert(0, "/Users/hezhengze/Code/26MathorCup/调试/问题二/代码")
import p2_2_final_only as p22

def load_p12_module(p12_path: str):
    """动态加载p12模块"""
    import importlib.util
    from pathlib import Path

    p12_file = Path(p12_path).expanduser().resolve()
    if not p12_file.exists():
        raise FileNotFoundError(f"未找到问题1.2求解器文件: {p12_file}")

    p12_dir = str(p12_file.parent)
    if p12_dir not in sys.path:
        sys.path.insert(0, p12_dir)

    module_name = "p12_module_latest_for_p22"
    spec = importlib.util.spec_from_file_location(module_name, str(p12_file))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法为以下文件创建加载器: {p12_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# 加载p12模块
p12_path = "../../问题一/代码/p12_final_best_combo_v2.py"
base_dir = os.path.dirname(os.path.abspath(__file__))
if not os.path.isabs(p12_path):
    p12_path = os.path.normpath(os.path.join(base_dir, p12_path))

p12 = load_p12_module(p12_path)

def backup_cargo_types() -> Dict[str, int]:
    """备份原始货物数量"""
    return {k: v.quantity for k, v in p12.CARGO_TYPES.items()}

def restore_cargo_types(backup: Dict[str, int]):
    """恢复货物数量"""
    for type_id, quantity in backup.items():
        object.__setattr__(p12.CARGO_TYPES[type_id], 'quantity', quantity)

def run_sensitivity_test(cargo_type: str, scale: float) -> Dict:
    """运行单个敏感性测试"""
    backup = backup_cargo_types()

    try:
        # 修改指定货物的数量
        original_qty = p12.CARGO_TYPES[cargo_type].quantity
        new_qty = int(original_qty * scale)
        object.__setattr__(p12.CARGO_TYPES[cargo_type], 'quantity', new_qty)

        # 运行p2.2求解
        solution = p22.solve_problem_22(p12)

        result = {
            'cargo_type': cargo_type,
            'scale': scale,
            'original_quantity': original_qty,
            'new_quantity': new_qty,
            'x_truck1': solution.x_truck1,
            'y_truck2': solution.y_truck2,
            'vehicle_count': solution.vehicle_count,
            'total_cost': solution.total_cost,
            'feasible': solution.feasible,
            'construction_mode': solution.construction_mode,
        }

        return result

    finally:
        restore_cargo_types(backup)

def plot_total_cost_vs_scale(results: List[Dict], output_dir: str):
    if not results:
        print("No results to plot.")
        return

    # 设置中文字体兼容性
    plt.rcParams['font.sans-serif'] = ['Heiti TC', 'STHeiti', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    grouped = {}
    for row in results:
        grouped.setdefault(row["cargo_type"], []).append(row)

    plt.figure(figsize=(10, 6))
    cmap = plt.get_cmap("tab10")
    for idx, (cargo_type, rows) in enumerate(sorted(grouped.items())):
        sorted_rows = sorted(rows, key=lambda x: x["scale"])
        x = [item["scale"] for item in sorted_rows]
        y = [item["total_cost"] for item in sorted_rows]
        plt.plot(x, y, marker="o", label=cargo_type, color=cmap(idx))

    plt.xlabel("货物数量扰动比例")
    plt.ylabel("总成本")
    plt.title("问题2.2敏感性分析：总成本 vs 货物数量扰动")
    plt.xticks([0.5, 0.75, 1.0, 1.25, 1.5, 2.0], ["50%", "75%", "100%", "125%", "150%", "200%"])
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(title="货物类型")
    plt.tight_layout()

    plot_path = os.path.join(output_dir, "p22_total_cost_vs_scale.png")
    plt.savefig(plot_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved plot: {plot_path}")


def load_existing_results(output_dir: str = None) -> List[Dict]:
    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "p22_sensitivity")
    json_path = os.path.join(output_dir, "sensitivity_analysis_p22.json")
    if not os.path.isfile(json_path):
        print(f"No existing results file found at: {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_existing_results(output_dir: str = None):
    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "p22_sensitivity")
    results = load_existing_results(output_dir)
    if not results:
        return
    plot_total_cost_vs_scale(results, output_dir)


def main():
    parser = argparse.ArgumentParser(description="Problem 2.2 sensitivity analysis and plotting")
    parser.add_argument("--plot-only", action="store_true", help="Plot from existing p22_sensitivity/sensitivity_analysis_p22.json results")
    args = parser.parse_args()

    output_dir = os.path.join(SCRIPT_DIR, "p22_sensitivity")
    os.makedirs(output_dir, exist_ok=True)

    if args.plot_only:
        plot_existing_results(output_dir)
        return

    cargo_types = list(p12.CARGO_TYPES.keys())
    scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    results = []

    for cargo_type in cargo_types:
        print(f"分析货物 {cargo_type}...")
        for scale in scales:
            print(f"  比例 {scale}...")
            result = run_sensitivity_test(cargo_type, scale)
            results.append(result)
            print(f"      车辆配置: ({result['x_truck1']},{result['y_truck2']}), 成本: {result['total_cost']}")

    with open(os.path.join(output_dir, "sensitivity_analysis_p22.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    import csv
    with open(os.path.join(output_dir, "sensitivity_analysis_p22.csv"), "w", newline="", encoding="utf-8-sig") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    plot_total_cost_vs_scale(results, output_dir)

    print("问题2.2敏感性分析完成，结果保存到 p22_sensitivity/ 目录")

if __name__ == "__main__":
    main()
