#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成P12敏感性分析汇总报告
"""

import json
import os

def generate_summary_report():
    output_dir = "p12"

    # 读取基本分析结果
    basic_results_file = os.path.join(output_dir, "sensitivity_analysis_p12.json")
    if os.path.exists(basic_results_file):
        with open(basic_results_file, "r", encoding="utf-8") as f:
            basic_results = json.load(f)
    else:
        basic_results = []

    # 读取高级分析结果
    advanced_results_file = os.path.join(output_dir, "advanced_sensitivity_results_p12.json")
    if os.path.exists(advanced_results_file):
        with open(advanced_results_file, "r", encoding="utf-8") as f:
            advanced_results = json.load(f)
    else:
        advanced_results = []

    # 生成汇总报告
    report = "# P12 敏感性分析汇总报告\n\n"

    report += "## 基本敏感性分析（货物数量比例变化）\n\n"
    report += "测试货物数量从50%到200%的变化对车辆数、成本、利用率的影响。\n\n"

    for truck_name in ['车型1', '车型2']:
        truck_basic = [r for r in basic_results if r['truck_name'] == truck_name]
        if not truck_basic:
            continue

        report += f"### {truck_name}\n\n"
        report += "| 货物类型 | 比例 | 新数量 | 车辆数 | 总成本 | 平均空间利用率 | 平均重量利用率 |\n"
        report += "|----------|------|--------|--------|--------|----------------|----------------|\n"

        for r in sorted(truck_basic, key=lambda x: (x['cargo_type'], x['scale'])):
            report += f"| {r['cargo_type']} | {r['scale']} | {r['new_quantity']} | {r['vehicle_count']} | {r['total_cost']} | {r['avg_space_utilization']:.4f} | {r['avg_weight_utilization']:.4f} |\n"

        report += "\n"

    report += "## 高级敏感性分析（货物完全移除）\n\n"
    report += "测试完全移除某种货物类型的影响。\n\n"

    for truck_name in ['车型1', '车型2']:
        truck_advanced = [r for r in advanced_results if r['truck_name'] == truck_name]
        if not truck_advanced:
            continue

        report += f"### {truck_name}\n\n"
        report += "| 移除货物 | 车辆数变化 | 成本变化 | 空间利用率变化 | 体积贡献 | 重量贡献 |\n"
        report += "|----------|----------|----------|----------------|----------|----------|\n"

        for r in sorted(truck_advanced, key=lambda x: -abs(x['vehicle_diff'])):
            report += f"| {r['removed_cargo']} | {r['vehicle_diff']} | {r['cost_diff']} | {r['space_util_diff']:.4f} | {r['volume_contribution']:.4f} | {r['weight_contribution']:.4f} |\n"

        report += "\n"

        # 最敏感货物
        most_sensitive = max(truck_advanced, key=lambda x: abs(x['vehicle_diff']) + abs(x['cost_diff']))
        report += f"**最敏感货物**: {most_sensitive['removed_cargo']} "
        report += f"(车辆数变化: {most_sensitive['vehicle_diff']}, 成本变化: {most_sensitive['cost_diff']})\n\n"

    # 保存报告
    with open(os.path.join(output_dir, "SENSITIVITY_ANALYSIS_SUMMARY_P12.md"), "w", encoding="utf-8") as f:
        f.write(report)

    print("汇总报告生成完成：SENSITIVITY_ANALYSIS_SUMMARY_P12.md")

if __name__ == "__main__":
    generate_summary_report()