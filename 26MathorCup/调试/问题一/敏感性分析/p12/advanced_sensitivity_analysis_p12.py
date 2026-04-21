#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级敏感性分析：p12_final_expanded_check.py 对货物完全移除的敏感性
测试移除某种货物类型（quantity=0）的影响
"""

import json
import os
import sys
from copy import deepcopy
from typing import Dict, List

# 导入p12模块
sys.path.insert(0, "/Users/hezhengze/Code/26MathorCup/调试/问题一/代码")
import p12_final_expanded_check as p12

def backup_cargo_types() -> Dict[str, int]:
    """备份原始货物数量"""
    return {k: v.quantity for k, v in p12.CARGO_TYPES.items()}

def restore_cargo_types(backup: Dict[str, int]):
    """恢复货物数量"""
    for type_id, quantity in backup.items():
        object.__setattr__(p12.CARGO_TYPES[type_id], 'quantity', quantity)

def analyze_cargo_zero_impact(truck_name: str, removed_cargo: str) -> Dict:
    """分析移除某种货物的影响"""
    backup = backup_cargo_types()

    try:
        # 移除指定货物
        object.__setattr__(p12.CARGO_TYPES[removed_cargo], 'quantity', 0)

        # 运行基准装箱（所有货物）
        plans_base, summary_base, _ = p12.solve_one_truck_type(truck_name)

        # 运行移除后的装箱
        plans_removed, summary_removed, _ = p12.solve_one_truck_type(truck_name)

        # 计算影响
        vehicle_diff = summary_removed['vehicle_count'] - summary_base['vehicle_count']
        cost_diff = summary_removed['total_cost'] - summary_base['total_cost']
        space_util_diff = summary_removed['avg_space_utilization'] - summary_base['avg_space_utilization']
        weight_util_diff = summary_removed['avg_weight_utilization'] - summary_base['avg_weight_utilization']

        # 计算移除货物的贡献（基于基准）
        removed_quantity = backup[removed_cargo]
        removed_volume = removed_quantity * p12.CARGO_TYPES[removed_cargo].volume
        removed_weight = removed_quantity * p12.CARGO_TYPES[removed_cargo].weight

        total_volume = sum(q * p12.CARGO_TYPES[t].volume for t, q in backup.items())
        total_weight = sum(q * p12.CARGO_TYPES[t].weight for t, q in backup.items())

        volume_contribution = removed_volume / total_volume if total_volume > 0 else 0
        weight_contribution = removed_weight / total_weight if total_weight > 0 else 0

        result = {
            'truck_name': truck_name,
            'removed_cargo': removed_cargo,
            'removed_quantity': removed_quantity,
            'volume_contribution': volume_contribution,
            'weight_contribution': weight_contribution,
            'vehicle_count_base': summary_base['vehicle_count'],
            'vehicle_count_removed': summary_removed['vehicle_count'],
            'vehicle_diff': vehicle_diff,
            'cost_base': summary_base['total_cost'],
            'cost_removed': summary_removed['total_cost'],
            'cost_diff': cost_diff,
            'space_util_base': summary_base['avg_space_utilization'],
            'space_util_removed': summary_removed['avg_space_utilization'],
            'space_util_diff': space_util_diff,
            'weight_util_base': summary_base['avg_weight_utilization'],
            'weight_util_removed': summary_removed['avg_weight_utilization'],
            'weight_util_diff': weight_util_diff,
            'all_loaded_base': summary_base['all_loaded'],
            'all_loaded_removed': summary_removed['all_loaded']
        }

        return result

    finally:
        restore_cargo_types(backup)

def write_advanced_report(results: List[Dict], output_dir: str):
    """生成高级分析报告"""
    os.makedirs(output_dir, exist_ok=True)

    # 按车辆数差异排序（最敏感的先）
    results_sorted = sorted(results, key=lambda x: (-abs(x['vehicle_diff']), -x['cost_diff']))

    report = "# P12 高级敏感性分析报告\n\n"
    report += "## 概述\n"
    report += "分析移除某种货物类型对装箱方案的影响，包括车辆数、成本、利用率的变化。\n\n"

    for truck_name in ['车型1', '车型2']:
        truck_results = [r for r in results_sorted if r['truck_name'] == truck_name]
        report += f"## {truck_name} 分析结果\n\n"
        report += "| 移除货物 | 车辆数变化 | 成本变化 | 空间利用率变化 | 重量利用率变化 | 体积贡献 | 重量贡献 |\n"
        report += "|----------|----------|----------|----------------|----------------|----------|----------|\n"

        for r in truck_results:
            report += f"| {r['removed_cargo']} | {r['vehicle_diff']} | {r['cost_diff']} | {r['space_util_diff']:.4f} | {r['weight_util_diff']:.4f} | {r['volume_contribution']:.4f} | {r['weight_contribution']:.4f} |\n"

        report += "\n"

        # 找出最敏感的货物
        most_sensitive = max(truck_results, key=lambda x: abs(x['vehicle_diff']) + abs(x['cost_diff']))
        report += f"**最敏感货物**: {most_sensitive['removed_cargo']} (车辆数变化: {most_sensitive['vehicle_diff']}, 成本变化: {most_sensitive['cost_diff']})\n\n"

    # 保存报告
    with open(os.path.join(output_dir, "advanced_sensitivity_report_p12.md"), "w", encoding="utf-8") as f:
        f.write(report)

    # 保存详细结果
    with open(os.path.join(output_dir, "advanced_sensitivity_results_p12.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def main():
    truck_names = ['车型1', '车型2']
    cargo_types = list(p12.CARGO_TYPES.keys())

    results = []

    for truck_name in truck_names:
        print(f"分析 {truck_name}...")
        for removed_cargo in cargo_types:
            print(f"  移除 {removed_cargo}...")
            result = analyze_cargo_zero_impact(truck_name, removed_cargo)
            results.append(result)
            print(f"    车辆数变化: {result['vehicle_diff']}, 成本变化: {result['cost_diff']}")

    # 生成报告
    output_dir = "p12"
    write_advanced_report(results, output_dir)

    print("高级敏感性分析完成，结果保存到 p12/ 目录")

if __name__ == "__main__":
    main()