#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成问题1.1 / 1.2敏感性分析可视化图表。

问题1.1：使用高级敏感性分析结果（完全移除货物后的影响），通过摘要影响值绘制饼图，直观展示各货物的重要性。
问题1.2：使用P12高级敏感性结果，计算每种货物的综合影响分数，绘制饼图对比车辆变化和成本变化带来的敏感性。
"""

import json
import os
from pathlib import Path
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "Microsoft YaHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

CARGO_COLOR_MAP = {
    "G1": "#f8d4a0",
    "G2": "#bca6cd",
    "G3": "#f59694",
    "G4": "#9bc2ee",
    "G5": "#a6df91",
}


def get_pie_colors(labels):
    if all(label in CARGO_COLOR_MAP for label in labels):
        return [CARGO_COLOR_MAP[label] for label in labels]
    return plt.get_cmap("tab10")(range(len(labels)))


def save_pie_chart(labels, sizes, title, filename):
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = get_pie_colors(labels)
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
    print(f"Saved chart: {save_path}")


def plot_p11_criticality():
    for filename in ["advanced_sensitivity_车型1.json", "advanced_sensitivity_车型2.json"]:
        path = SCRIPT_DIR / filename
        if not path.exists():
            print(f"文件不存在：{path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        truck_name = data["criticality_analysis"]["truck_name"]
        items = data["criticality_analysis"]["criticality_analysis"]

        labels = []
        sizes = []
        for cargo_id, metric in items.items():
            impact = abs(metric.get("fs_impact", 0.0))
            labels.append(cargo_id)
            sizes.append(impact)

        if sum(sizes) == 0:
            labels = [cargo_id for cargo_id in items.keys()]
            scores = [metric.get("item_ratio", 1.0) for metric in items.values()]
            sizes = scores
            title = f"{truck_name} - Problem 1.1 Critical Cargo Importance (fallback to item ratio)"
        else:
            title = f"{truck_name} - Problem 1.1 Critical Cargo Importance (absolute fullness score impact)"

        save_pie_chart(labels, sizes, title, f"p11_{truck_name}_criticality_pie.png")


def plot_p12_advanced():
    candidate_paths = [
        SCRIPT_DIR / "p12" / "advanced_sensitivity_results_p12.json",
        SCRIPT_DIR / "p12" / "p12" / "advanced_sensitivity_results_p12.json",
    ]
    path = None
    for candidate in candidate_paths:
        if candidate.exists():
            path = candidate
            break

    if path is None:
        print("未找到P12高级敏感性分析结果文件，请检查以下路径：")
        for candidate in candidate_paths:
            print("  -", candidate)
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for truck_name in ["车型1", "车型2"]:
        truck_rows = [row for row in data if row["truck_name"] == truck_name]
        if not truck_rows:
            continue

        labels = []
        sizes = []
        for row in truck_rows:
            cargo_id = row["removed_cargo"]
            importance = abs(row.get("vehicle_diff", 0)) * 800 + abs(row.get("cost_diff", 0))
            labels.append(cargo_id)
            sizes.append(importance)

        if sum(sizes) == 0:
            labels = [row["removed_cargo"] for row in truck_rows]
            sizes = [row.get("volume_contribution", 0.0) for row in truck_rows]
            title = f"{truck_name} - Problem 1.2 Cargo Importance (based on volume contribution)"
        else:
            title = f"{truck_name} - Problem 1.2 Cargo Importance (combined vehicle and cost impact)"

        save_pie_chart(labels, sizes, title, f"p12_{truck_name}_importance_pie.png")

        # Additional cost-sensitivity pie chart
        labels = [row["removed_cargo"] for row in truck_rows]
        cost_sizes = [abs(row.get("cost_diff", 0.0)) for row in truck_rows]
        if sum(cost_sizes) > 0:
            save_pie_chart(
                labels,
                cost_sizes,
                f"{truck_name} - Problem 1.2 Cost Sensitivity (absolute cost change)",
                f"p12_{truck_name}_cost_impact_pie.png",
            )


def main():
    print("开始生成敏感性分析可视化图表...")
    plot_p11_criticality()
    plot_p12_advanced()
    print("可视化生成完成。图像保存在：", OUTPUT_DIR)


if __name__ == "__main__":
    main()
