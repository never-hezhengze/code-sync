#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敏感性分析：p12_final_expanded_check.py 对货物数量变化的敏感性
测试货物数量从50%到200%的变化，看车辆数、成本、利用率的变化
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

def run_sensitivity_test(truck_name: str, cargo_type: str, scale: float) -> Dict:
    """运行单个敏感性测试"""
    backup = backup_cargo_types()

    try:
        # 修改指定货物的数量
        original_qty = p12.CARGO_TYPES[cargo_type].quantity
        new_qty = int(original_qty * scale)
        object.__setattr__(p12.CARGO_TYPES[cargo_type], 'quantity', new_qty)

        # 运行p12装箱
        plans, summary, module_templates = p12.solve_one_truck_type(truck_name)

        result = {
            'truck_name': truck_name,
            'cargo_type': cargo_type,
            'scale': scale,
            'original_quantity': original_qty,
            'new_quantity': new_qty,
            'vehicle_count': summary['vehicle_count'],
            'total_cost': summary['total_cost'],
            'avg_space_utilization': summary['avg_space_utilization'],
            'avg_weight_utilization': summary['avg_weight_utilization'],
            'all_loaded': summary['all_loaded']
        }

        return result

    finally:
        restore_cargo_types(backup)

def main():
    truck_names = ['车型1', '车型2']
    cargo_types = list(p12.CARGO_TYPES.keys())
    scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    results = []

    for truck_name in truck_names:
        print(f"分析 {truck_name}...")
        for cargo_type in cargo_types:
            print(f"  测试 {cargo_type}...")
            for scale in scales:
                print(f"    比例 {scale}...")
                result = run_sensitivity_test(truck_name, cargo_type, scale)
                results.append(result)
                print(f"      车辆数: {result['vehicle_count']}, 成本: {result['total_cost']}")

    # 保存结果
    output_dir = "p12"
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "sensitivity_analysis_p12.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 生成CSV
    import csv
    with open(os.path.join(output_dir, "sensitivity_analysis_p12.csv"), "w", newline="", encoding="utf-8-sig") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    print("敏感性分析完成，结果保存到 p12/ 目录")

if __name__ == "__main__":
    main()