#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题1.1 敏感性分析：调节各货物数量，分析方案的敏感性
"""

import os
import sys
import csv
import copy
import json
from typing import Dict, List, Tuple
from collections import OrderedDict

import matplotlib.pyplot as plt

# 添加当前目录到路径以导入mathorcup_d_common
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mathorcup_d_common import CARGO_TYPES, TRUCKS
from p11_final import (
    solve_problem_11_greedy,
    truck_score,
)


def backup_cargo_types():
    """备份原始货物数量"""
    backup = {}
    for cargo_id, cargo in CARGO_TYPES.items():
        backup[cargo_id] = cargo.quantity
    return backup


def restore_cargo_types(backup: Dict[str, int]):
    """恢复货物数量"""
    for cargo_id, quantity in backup.items():
        object.__setattr__(CARGO_TYPES[cargo_id], 'quantity', quantity)


def set_cargo_quantity(cargo_id: str, quantity: int):
    """设置单个货物数量"""
    if cargo_id in CARGO_TYPES:
        object.__setattr__(CARGO_TYPES[cargo_id], 'quantity', quantity)
    else:
        raise ValueError(f"未知货物类型：{cargo_id}")


def run_sensitivity_test(truck_name: str, cargo_id: str, percentage: float, original_qty: int) -> Dict:
    """
    对单个货物的某个百分比进行测试
    
    Args:
        truck_name: 车型名称
        cargo_id: 货物类型
        percentage: 相对原始数量的百分比（1.0 = 100%）
        original_qty: 原始数量
    
    Returns:
        测试结果字典
    """
    test_qty = int(original_qty * percentage)
    set_cargo_quantity(cargo_id, test_qty)
    
    try:
        plans, summary = solve_problem_11_greedy(truck_name)
        
        if plans:
            plan = plans[0]
            truck = TRUCKS[truck_name]
            sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
            
            result = {
                "cargo_id": cargo_id,
                "percentage": percentage,
                "test_qty": test_qty,
                "original_qty": original_qty,
                "loaded_count": plan.item_count,
                "actual_counts": dict(plan.actual_counts),
                "used_weight": round(plan.used_weight, 2),
                "used_volume": plan.used_volume,
                "space_utilization": round(sv, 6),
                "weight_utilization": round(wv, 6),
                "fullness_score": round(fs, 6),
                "success": True,
            }
        else:
            result = {
                "cargo_id": cargo_id,
                "percentage": percentage,
                "test_qty": test_qty,
                "original_qty": original_qty,
                "success": False,
                "reason": "未能找到可行方案",
            }
    except Exception as e:
        result = {
            "cargo_id": cargo_id,
            "percentage": percentage,
            "test_qty": test_qty,
            "original_qty": original_qty,
            "success": False,
            "reason": str(e),
        }
    
    return result


def run_full_sensitivity_analysis(truck_name: str) -> Dict:
    """
    对所有货物类型进行敏感性分析
    
    Args:
        truck_name: 车型名称
    
    Returns:
        完整的敏感性分析结果
    """
    # 保存原始数量
    original_backup = backup_cargo_types()
    
    # 测试百分比列表
    test_percentages = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    
    results = {
        "truck_name": truck_name,
        "test_percentages": test_percentages,
        "cargo_tests": OrderedDict(),
    }
    
    cargo_ids = list(CARGO_TYPES.keys())
    print(f"[敏感性分析] 开始测试 {truck_name}，共 {len(cargo_ids)} 种货物")
    print(f"[敏感性分析] 测试百分比：{test_percentages}")
    print()
    
    for cargo_id in cargo_ids:
        original_qty = original_backup[cargo_id]
        print(f"[{truck_name}] 开始测试货物：{cargo_id}（原始数量：{original_qty}）")
        
        cargo_results = []
        
        for percentage in test_percentages:
            # 恢复所有货物到原始数量
            restore_cargo_types(original_backup)
            
            # 执行敏感性测试
            result = run_sensitivity_test(truck_name, cargo_id, percentage, original_qty)
            cargo_results.append(result)
            
            if result["success"]:
                print(f"  {percentage*100:5.0f}% ({result['test_qty']:2d}件) -> "
                      f"装入{result['loaded_count']:2d}件, fs={result['fullness_score']:.6f}, "
                      f"空={result['space_utilization']:.4f}, 重={result['weight_utilization']:.4f}")
            else:
                print(f"  {percentage*100:5.0f}% ({result['test_qty']:2d}件) -> 失败: {result['reason']}")
        
        results["cargo_tests"][cargo_id] = cargo_results
        print()
    
    # 恢复所有货物到原始数量
    restore_cargo_types(original_backup)
    
    return results


def calculate_sensitivity_metrics(results: Dict) -> Dict:
    """
    计算敏感性指标
    
    指标包括：
    - 数量变化率对装入件数的影响
    - 数量变化率对fullness_score的影响
    - 货物优先级排名
    """
    metrics = {}
    test_percentages = results["test_percentages"]
    
    for cargo_id, cargo_results in results["cargo_tests"].items():
        successful_results = [r for r in cargo_results if r["success"]]
        
        if len(successful_results) < 2:
            continue
        
        # 计算fullness_score相对于数量变化的敏感度
        fs_values = [r["fullness_score"] for r in successful_results]
        qty_values = [r["test_qty"] for r in successful_results]
        
        # 从50%到150%的变化范围
        if len(successful_results) >= 5:
            fs_low = successful_results[0]["fullness_score"]  # 50%
            fs_high = successful_results[4]["fullness_score"]  # 150%
            qty_low = successful_results[0]["test_qty"]
            qty_high = successful_results[4]["test_qty"]
            
            # 敏感度 = fullness_score变化量 / 数量变化量
            qty_change_pct = (qty_high - qty_low) / max(1, qty_low)
            fs_change = fs_high - fs_low
            
            if qty_change_pct > 0:
                sensitivity = fs_change / qty_change_pct
            else:
                sensitivity = 0
        else:
            sensitivity = 0
        
        metrics[cargo_id] = {
            "avg_fullness_score": sum(fs_values) / len(fs_values),
            "min_fullness_score": min(fs_values),
            "max_fullness_score": max(fs_values),
            "fullness_score_range": max(fs_values) - min(fs_values),
            "sensitivity": abs(sensitivity),  # 绝对值表示敏感度幅度
            "test_count": len(successful_results),
        }
    
    # 按敏感度排序
    ranked = sorted(metrics.items(), key=lambda x: x[1]["sensitivity"], reverse=True)
    
    return {
        "metrics": metrics,
        "ranked_by_sensitivity": ranked,
    }


def write_analysis_report(truck_name: str, results: Dict, metrics: Dict, outdir: str):
    """生成敏感性分析报告"""
    os.makedirs(outdir, exist_ok=True)
    
    # 写入原始结果 JSON
    json_path = os.path.join(outdir, f"sensitivity_results_{truck_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        # 转换为可序列化的格式
        json_results = {
            "truck_name": results["truck_name"],
            "test_percentages": results["test_percentages"],
            "cargo_tests": {k: v for k, v in results["cargo_tests"].items()},
        }
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"[报告] 原始结果已保存到：{json_path}")
    
    # 写入敏感性指标报告 CSV
    csv_path = os.path.join(outdir, f"sensitivity_metrics_{truck_name}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "Cargo Type", "Average fullness_score", "Min fullness_score", "Max fullness_score",
            "Score Range", "Sensitivity Index", "Successful Tests"
        ])
        
        for cargo_id, metric_data in metrics["metrics"].items():
            w.writerow([
                cargo_id,
                round(metric_data["avg_fullness_score"], 6),
                round(metric_data["min_fullness_score"], 6),
                round(metric_data["max_fullness_score"], 6),
                round(metric_data["fullness_score_range"], 6),
                round(metric_data["sensitivity"], 6),
                metric_data["test_count"],
            ])
    print(f"[报告] 敏感性指标已保存到：{csv_path}")
    
    # 写入排名报告
    rank_path = os.path.join(outdir, f"sensitivity_ranking_{truck_name}.csv")
    with open(rank_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Rank", "Cargo Type", "Sensitivity Index", "Average fullness_score", "Score Range"])
        for rank, (cargo_id, metric_data) in enumerate(metrics["ranked_by_sensitivity"], 1):
            w.writerow([
                rank,
                cargo_id,
                round(metric_data["sensitivity"], 6),
                round(metric_data["avg_fullness_score"], 6),
                round(metric_data["fullness_score_range"], 6),
            ])
    print(f"[Report] Sensitivity ranking saved to: {rank_path}")
    
    # 写入详细报告文本
    text_path = os.path.join(outdir, f"sensitivity_report_{truck_name}.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(f"=== Problem 1.1 Sensitivity Analysis Report ({truck_name}) ===\n\n")
        
        f.write("[Sensitivity Ranking - High to Low]\n")
        f.write("The higher the rank, the more sensitive the cargo quantity is to the overall packing solution.\n\n")
        
        for rank, (cargo_id, metric_data) in enumerate(metrics["ranked_by_sensitivity"], 1):
            f.write(f"{rank}. {cargo_id}\n")
            f.write(f"   Sensitivity Index: {metric_data['sensitivity']:.6f}\n")
            f.write(f"   Average fullness_score: {metric_data['avg_fullness_score']:.6f}\n")
            f.write(f"   Score Range: {metric_data['fullness_score_range']:.6f}\n")
            f.write(f"   Successful Test Count: {metric_data['test_count']}\n\n")
        
        f.write("\n[Explanation]\n")
        f.write("- A larger sensitivity index means the cargo quantity change has a greater impact on the final solution.\n")
        f.write("- A larger fullness_score range indicates a stronger effect on solution quality.\n")
        f.write("- High-sensitivity cargo quantities should be adjusted first.\n")
    
    print(f"[Report] Detailed report saved to: {text_path}")

    plot_path = plot_sensitivity_ranking(truck_name, metrics, outdir)
    print(f"[Report] Sensitivity ranking plot saved to: {plot_path}")


CARGO_COLOR_MAP = {
    'G1': '#f8d4a0',
    'G2': '#bca6cd',
    'G3': '#f59694',
    'G4': '#9bc2ee',
    'G5': '#a6df91',
}


def plot_sensitivity_ranking(truck_name: str, metrics: Dict, outdir: str) -> str:
    ranked = metrics["ranked_by_sensitivity"]
    cargo_ids = [item[0] for item in ranked]
    sensitivities = [item[1]["sensitivity"] for item in ranked]
    colors = [CARGO_COLOR_MAP.get(cid, '#888888') for cid in cargo_ids]
    truck_label = {'车型1': 'Truck 1', '车型2': 'Truck 2'}.get(truck_name, truck_name)

    plt.figure(figsize=(12, 6))
    bars = plt.bar(cargo_ids, sensitivities, color=colors)
    plt.title(f"{truck_label} Sensitivity Ranking")
    plt.xlabel("Cargo Type")
    plt.ylabel("Sensitivity Index")
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    plot_path = os.path.join(outdir, f"sensitivity_ranking_{truck_name}.png")
    plt.savefig(plot_path, dpi=200, bbox_inches='tight')
    plt.close()
    return plot_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Problem 1.1 Sensitivity Analysis")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../敏感性分析", help="输出目录")
    args = parser.parse_args()
    
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
    
    print("="*72)
    print("Start Problem 1.1 Sensitivity Analysis")
    print("="*72)
    print()
    
    for truck_name in truck_list:
        print(f"\n{'='*72}")
        print(f"Analyzing: {truck_name}")
        print(f"{'='*72}\n")
        
        # 运行敏感性分析
        results = run_full_sensitivity_analysis(truck_name)
        
        print("\nCalculating sensitivity metrics...")
        metrics = calculate_sensitivity_metrics(results)
        
        print("\nSensitivity ranking (high to low)")
        for rank, (cargo_id, metric_data) in enumerate(metrics["ranked_by_sensitivity"], 1):
            print(f"{rank}. {cargo_id:3s} - Sensitivity Index: {metric_data['sensitivity']:8.6f}, "
                  f"Score Range: {metric_data['fullness_score_range']:8.6f}")
        
        # Generate report
        print("\nGenerating reports...")
        write_analysis_report(truck_name, results, metrics, outdir)
        print()
    
    print(f"\nAll analysis results saved to: {outdir}")
    print("="*72)


if __name__ == "__main__":
    main()
