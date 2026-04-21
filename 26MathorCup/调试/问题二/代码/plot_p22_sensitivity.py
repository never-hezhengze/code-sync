#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成问题2.2敏感性分析可视化图表。

分析货物数量变化（50%-200%）对混合车队成本优化的影响。
"""

import json
import os
import csv
from pathlib import Path
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "Microsoft YaHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def save_pie_chart(labels, sizes, title, filename):
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.get_cmap("tab10")(range(len(labels)))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%.1f%%",
        startangle=140,
        colors=colors,
        textprops={"fontsize": 10},
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
    )
    ax.set_title(title, fontsize=14)
    ax.axis("equal")
    plt.tight_layout()
    save_path = OUTPUT_DIR / filename
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"保存图像：{save_path}")


def plot_p22_sensitivity():
    """生成问题2.2敏感性分析饼图"""
    csv_path = SCRIPT_DIR / "p22_sensitivity" / "sensitivity_analysis_p22.csv"
    if not csv_path.exists():
        print(f"文件不存在：{csv_path}")
        return

    data = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    # 按货物类型分组
    cargo_groups = {}
    for row in data:
        cargo_type = row["cargo_type"]
        if cargo_type not in cargo_groups:
            cargo_groups[cargo_type] = []
        cargo_groups[cargo_type].append(row)

    # 为每个货物类型生成饼图
    for cargo_type, rows in cargo_groups.items():
        # 计算每个比例变化的成本影响
        base_cost = None
        impacts = []

        for row in rows:
            scale = float(row["scale"])
            cost = float(row["total_cost"])

            if scale == 1.0:  # 基准情况
                base_cost = cost
                continue

            if base_cost is not None:
                cost_impact = abs(cost - base_cost)
                impacts.append({
                    "scale": scale,
                    "cost_impact": cost_impact,
                    "label": f"{scale:.1f}x ({int(float(row['new_quantity']))}件)"
                })

        if not impacts:
            continue

        # 按成本影响排序
        impacts.sort(key=lambda x: x["cost_impact"], reverse=True)

        labels = [impact["label"] for impact in impacts]
        sizes = [impact["cost_impact"] for impact in impacts]

        title = f"货物{cargo_type} - 问题2.2 数量变化对成本的影响\n(基准成本: {base_cost:.0f})"
        filename = f"p22_{cargo_type}_cost_sensitivity_pie.png"

        save_pie_chart(labels, sizes, title, filename)


def plot_p22_vehicle_sensitivity():
    """生成车辆配置变化的饼图"""
    csv_path = SCRIPT_DIR / "p22_sensitivity" / "sensitivity_analysis_p22.csv"
    if not csv_path.exists():
        print(f"文件不存在：{csv_path}")
        return

    data = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    # 按货物类型分组
    cargo_groups = {}
    for row in data:
        cargo_type = row["cargo_type"]
        if cargo_type not in cargo_groups:
            cargo_groups[cargo_type] = []
        cargo_groups[cargo_type].append(row)

    # 为每个货物类型生成车辆变化饼图
    for cargo_type, rows in cargo_groups.items():
        base_vehicles = None
        impacts = []

        for row in rows:
            scale = float(row["scale"])
            vehicles = int(row["vehicle_count"])

            if scale == 1.0:  # 基准情况
                base_vehicles = vehicles
                continue

            if base_vehicles is not None:
                vehicle_impact = abs(vehicles - base_vehicles)
                impacts.append({
                    "scale": scale,
                    "vehicle_impact": vehicle_impact,
                    "label": f"{scale:.1f}x ({vehicles}辆)"
                })

        if not impacts:
            continue

        # 按车辆变化排序
        impacts.sort(key=lambda x: x["vehicle_impact"], reverse=True)

        labels = [impact["label"] for impact in impacts]
        sizes = [impact["vehicle_impact"] for impact in impacts]

        title = f"货物{cargo_type} - 问题2.2 数量变化对车辆数的影响\n(基准车辆: {base_vehicles}辆)"
        filename = f"p22_{cargo_type}_vehicle_sensitivity_pie.png"

        save_pie_chart(labels, sizes, title, filename)


def main():
    print("开始生成问题2.2敏感性分析可视化图表...")
    plot_p22_sensitivity()
    plot_p22_vehicle_sensitivity()
    print("可视化生成完成。图像保存在：", OUTPUT_DIR)


if __name__ == "__main__":
    main()