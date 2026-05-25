#!/usr/bin/env python3
"""Fig Q2(2): 24种风光场景×5种氨产量 吨氨成本热力图"""
import sys, os, json
sys.path.insert(0, '.')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from _utils.plot_utils import setup_style, PALETTE, COLORS

setup_style('science')

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

with open('figures/problem_2_results.json', 'r') as f:
    data = json.load(f)

productions = data.get('productions', [72, 63, 54, 45, 36])
cost_matrix_data = data.get('cost_matrix', [])

# 构建 24×5 矩阵 (行=场景, 列=产量)
n_scenarios = len(cost_matrix_data)
n_productions = len(productions)
cost_matrix = np.zeros((n_scenarios, n_productions))

scenario_labels = []
for i, item in enumerate(cost_matrix_data):
    scenario_labels.append(item['scenario'])
    for j, Q in enumerate(productions):
        val = item['costs'].get(str(Q), None)
        cost_matrix[i, j] = val if val is not None else np.nan

prod_labels = [f'{Q}t/d' for Q in productions]

fig, ax = plt.subplots(figsize=(9, 8))

im = ax.imshow(cost_matrix, cmap='YlOrRd', aspect='auto', interpolation='nearest')
cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
cbar.set_label('吨氨成本 (元/吨)', fontsize=11)

for i in range(n_scenarios):
    for j in range(n_productions):
        val = cost_matrix[i, j]
        if np.isnan(val):
            continue
        norm_val = (val - np.nanmin(cost_matrix)) / (np.nanmax(cost_matrix) - np.nanmin(cost_matrix))
        color = 'white' if norm_val > 0.6 else COLORS['text']
        ax.text(j, i, f'{val:.0f}', ha='center', va='center', fontsize=7, color=color, fontweight='bold')

ax.set_xticks(range(n_productions))
ax.set_xticklabels(prod_labels, fontsize=10)
ax.set_yticks(range(n_scenarios))
ax.set_yticklabels(scenario_labels, fontsize=9)
ax.set_xlabel('日产氨量', fontsize=12)
ax.set_ylabel('风光出力场景', fontsize=12)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q2_scenarios_heatmap.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q2_scenarios_heatmap.pdf")
