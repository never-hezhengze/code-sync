#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题1.1 高级敏感性分析：测试关键货物的影响
- 测试完全缺少某种货物时对装箱方案的影响
- 测试关键货物对利用率的影响
"""

import os
import sys
import csv
import json
from typing import Dict, List, Tuple
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mathorcup_d_common import CARGO_TYPES, TRUCKS
from p11_final import solve_problem_11_greedy, truck_score


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


def analyze_cargo_zero_impact(truck_name: str, original_backup: Dict[str, int]) -> Dict:
    """
    分析当某种货物的数量为0时对装箱方案的影响
    """
    results = {
        "truck_name": truck_name,
        "test_scenario": "去除单种货物",
        "cargo_impact": OrderedDict(),
    }
    
    # 首先获取原始方案
    restore_cargo_types(original_backup)
    baseline_plans, _ = solve_problem_11_greedy(truck_name)
    
    if baseline_plans:
        baseline = baseline_plans[0]
        truck = TRUCKS[truck_name]
        sv_base, wv_base, fs_base = truck_score(truck, baseline.used_volume, baseline.used_weight)
        
        baseline_result = {
            "scenario": "完整货物(基准)",
            "loaded_count": baseline.item_count,
            "actual_counts": dict(baseline.actual_counts),
            "used_weight": baseline.used_weight,
            "used_volume": baseline.used_volume,
            "space_utilization": round(sv_base, 6),
            "weight_utilization": round(wv_base, 6),
            "fullness_score": round(fs_base, 6),
        }
        
        results["baseline"] = baseline_result
        print(f"\n【基准方案】{truck_name}")
        print(f"  装入件数: {baseline.item_count}")
        print(f"  fullness_score: {fs_base:.6f}")
        print(f"  空间利用率: {sv_base:.6f}, 载重利用率: {wv_base:.6f}")
        print(f"  货物分布: {dict(baseline.actual_counts)}\n")
    else:
        results["baseline"] = None
        return results
    
    # 逐个去除每种货物，测试影响
    cargo_ids = list(CARGO_TYPES.keys())
    
    print(f"【敏感性测试】去除单种货物的影响：")
    
    for cargo_id in cargo_ids:
        restore_cargo_types(original_backup)
        set_cargo_quantity(cargo_id, 0)  # 完全去除该货物
        
        try:
            plans, _ = solve_problem_11_greedy(truck_name)
            
            if plans:
                plan = plans[0]
                sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
                
                impact = {
                    "removed_cargo": cargo_id,
                    "loaded_count": plan.item_count,
                    "actual_counts": dict(plan.actual_counts),
                    "used_weight": plan.used_weight,
                    "used_volume": plan.used_volume,
                    "space_utilization": round(sv, 6),
                    "weight_utilization": round(wv, 6),
                    "fullness_score": round(fs, 6),
                    "fullness_score_delta": round(fs - fs_base, 6),
                    "loaded_count_delta": plan.item_count - baseline.item_count,
                    "success": True,
                }
                
                results["cargo_impact"][cargo_id] = impact
                
                print(f"  移除 {cargo_id:3s}: 装入{plan.item_count:2d}件 (Δ{impact['loaded_count_delta']:3d}), "
                      f"fs={fs:.6f} (Δ{impact['fullness_score_delta']:+.6f})")
            else:
                results["cargo_impact"][cargo_id] = {
                    "removed_cargo": cargo_id,
                    "success": False,
                    "reason": "未能找到方案"
                }
                print(f"  移除 {cargo_id:3s}: 失败 - 无可行方案")
                
        except Exception as e:
            results["cargo_impact"][cargo_id] = {
                "removed_cargo": cargo_id,
                "success": False,
                "reason": str(e)
            }
            print(f"  移除 {cargo_id:3s}: 失败 - {str(e)[:50]}")
    
    return results


def analyze_cargo_criticality(truck_name: str, original_backup: Dict[str, int]) -> Dict:
    """
    分析每种货物对最终方案的'关键性'
    """
    results = {
        "truck_name": truck_name,
        "criticality_analysis": OrderedDict(),
    }
    
    # 获取基准方案
    restore_cargo_types(original_backup)
    baseline_plans, _ = solve_problem_11_greedy(truck_name)
    
    if not baseline_plans:
        return results
    
    baseline = baseline_plans[0]
    truck = TRUCKS[truck_name]
    sv_base, wv_base, fs_base = truck_score(truck, baseline.used_volume, baseline.used_weight)
    
    print(f"\n【货物关键性分析】{truck_name}")
    print(f"  基准fullness_score: {fs_base:.6f}\n")
    
    # 分析每种货物的装入比例
    total_items = baseline.item_count
    
    criticality_scores = []
    
    for cargo_id, count in baseline.actual_counts.items():
        ratio = count / max(1, total_items)
        cargo_type = CARGO_TYPES[cargo_id]
        volume_pct = (cargo_type.volume * count) / max(1, baseline.used_volume) * 100
        weight_pct = (cargo_type.weight * count) / max(1, baseline.used_weight) * 100
        
        # 去除该货物测试影响
        restore_cargo_types(original_backup)
        set_cargo_quantity(cargo_id, 0)
        
        try:
            plans, _ = solve_problem_11_greedy(truck_name)
            if plans:
                plan = plans[0]
                sv, wv, fs = truck_score(truck, plan.used_volume, plan.used_weight)
                fs_delta = fs - fs_base
            else:
                fs_delta = 0
        except:
            fs_delta = 0
        
        criticality = {
            "cargo_id": cargo_id,
            "count_in_baseline": count,
            "item_ratio": round(ratio * 100, 2),
            "volume_contribution_pct": round(volume_pct, 2),
            "weight_contribution_pct": round(weight_pct, 2),
            "fs_impact": round(fs_delta, 6),
        }
        
        results["criticality_analysis"][cargo_id] = criticality
        criticality_scores.append((cargo_id, abs(fs_delta), count, ratio))
        
        print(f"  {cargo_id}: 装入{count:2d}件 ({ratio*100:5.1f}%), "
              f"体积占{volume_pct:5.1f}%, 重量占{weight_pct:5.1f}%, "
              f"移除后fs变化{fs_delta:+.6f}")
    
    # 按重要性排序
    sorted_criticality = sorted(criticality_scores, key=lambda x: x[1], reverse=True)
    results["ranked_by_impact"] = [
        (cargo_id, round(impact, 6)) for cargo_id, impact, _, _ in sorted_criticality
    ]
    
    return results


def write_advanced_report(truck_name: str, zero_impact_results: Dict, criticality_results: Dict, outdir: str):
    """生成高级敏感性分析报告"""
    os.makedirs(outdir, exist_ok=True)
    
    # 保存JSON结果
    json_path = os.path.join(outdir, f"advanced_sensitivity_{truck_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json_data = {
            "zero_impact_analysis": zero_impact_results,
            "criticality_analysis": criticality_results,
        }
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"[报告] JSON数据已保存到：{json_path}")
    
    # 生成详细文本报告
    report_path = os.path.join(outdir, f"advanced_sensitivity_report_{truck_name}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"=== 问题1.1 高级敏感性分析 ({truck_name}) ===\n\n")
        
        f.write("【分析1：去除单种货物的影响】\n")
        f.write("此分析测试当完全移除某种货物时，对单车装箱方案的影响\n\n")
        
        if zero_impact_results.get("baseline"):
            baseline = zero_impact_results["baseline"]
            f.write(f"基准方案：装入 {baseline['loaded_count']} 件，fullness_score = {baseline['fullness_score']:.6f}\n\n")
        
        f.write("移除货物的影响：\n")
        for cargo_id, impact in zero_impact_results.get("cargo_impact", {}).items():
            if impact.get("success"):
                f.write(f"  {cargo_id}: 装入 {impact['loaded_count']} 件 "
                       f"(Δ{impact['loaded_count_delta']:+d}), "
                       f"fs {impact['fullness_score']:.6f} "
                       f"(Δ{impact['fullness_score_delta']:+.6f})\n")
            else:
                f.write(f"  {cargo_id}: 失败 - {impact.get('reason', 'unknown')}\n")
        
        f.write("\n【分析2：货物关键性评估】\n")
        f.write("此分析评估每种货物对装箱方案的重要程度\n\n")
        
        if criticality_results.get("criticality_analysis"):
            f.write("货物在基准方案中的贡献度：\n")
            for cargo_id, crit in criticality_results["criticality_analysis"].items():
                f.write(f"  {cargo_id}:\n")
                f.write(f"    - 装入件数: {crit['count_in_baseline']} ({crit['item_ratio']:.1f}%)\n")
                f.write(f"    - 体积贡献: {crit['volume_contribution_pct']:.1f}%\n")
                f.write(f"    - 重量贡献: {crit['weight_contribution_pct']:.1f}%\n")
                f.write(f"    - 移除后fs变化: {crit['fs_impact']:+.6f}\n")
        
        if criticality_results.get("ranked_by_impact"):
            f.write("\n按影响力排序（从大到小）：\n")
            for rank, (cargo_id, impact) in enumerate(criticality_results["ranked_by_impact"], 1):
                f.write(f"  {rank}. {cargo_id}: fs影响 {impact:+.6f}\n")
        
        f.write("\n【结论】\n")
        f.write("对于问题1.1单车满载：\n")
        f.write("- 如果所有货物数量充足，单车总能装满\n")
        f.write("- 关键是找出真正限制单车装载的关键货物\n")
        f.write("- 上方列出的货物若减少会对方案产生最大影响\n")
    
    print(f"[报告] 详细报告已保存到：{report_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="问题1.1 高级敏感性分析")
    parser.add_argument("--truck", choices=["车型1", "车型2", "all"], default="all")
    parser.add_argument("--outdir", type=str, default="../敏感性分析", help="输出目录")
    args = parser.parse_args()
    
    truck_list = ["车型1", "车型2"] if args.truck == "all" else [args.truck]
    original_backup = backup_cargo_types()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.normpath(os.path.join(base_dir, args.outdir))
    
    print("="*72)
    print("开始问题1.1 高级敏感性分析")
    print("="*72)
    
    for truck_name in truck_list:
        print(f"\n{'='*72}")
        print(f"开始分析：{truck_name}")
        print(f"{'='*72}")
        
        # 分析去除单种货物的影响
        zero_impact_results = analyze_cargo_zero_impact(truck_name, original_backup)
        
        # 分析货物关键性
        criticality_results = analyze_cargo_criticality(truck_name, original_backup)
        
        # 生成报告
        print("\n生成报告...")
        write_advanced_report(truck_name, zero_impact_results, criticality_results, outdir)
        
        # 恢复原始状态
        restore_cargo_types(original_backup)
        print()
    
    print(f"\n所有分析结果已保存到：{outdir}")
    print("="*72)


if __name__ == "__main__":
    main()
