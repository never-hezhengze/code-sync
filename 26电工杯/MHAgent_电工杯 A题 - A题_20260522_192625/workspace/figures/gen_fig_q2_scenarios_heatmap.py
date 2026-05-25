#!/usr/bin/env python3
"""Fig Q2(2): 24场景×5产量吨氨成本矩阵 (热力图)"""
import sys, os, json
sys.path.insert(0, '.')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from _utils.plot_utils import setup_style, PALETTE, COLORS

setup_style('science')
from _utils.plot_utils import PALETTE, COLORS

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

with open('figures/problem_2_results.json', 'r') as f:
    data = json.load(f)

scenarios = [s['scenario'] for s in data['scenarios']]
# For each scenario, get cost at best_Q=36
costs_36 = [s['C_ton'] for s in data['scenarios']]

# Reshape into 6 wind x 4 PV matrix
cost_matrix = np.array(costs_36).reshape(6, 4)
wind_labels = [f'W{i+1}' for i in range(6)]
pv_labels = [f'P{i+1}' for i in range(4)]

fig, ax = plt.subplots(figsize=(7, 6))

im = ax.imshow(cost_matrix, cmap='YlOrRd', aspect='auto', interpolation='nearest')
cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
cbar.set_label('吨氨成本 (元/吨)', fontsize=11)

for i in range(6):
    for j in range(4):
        val = cost_matrix[i, j]
        norm_val = (val - cost_matrix.min()) / (cost_matrix.max() - cost_matrix.min())
        color = 'white' if norm_val > 0.6 else COLORS['text']
        ax.text(j, i, f'{val:.0f}', ha='center', va='center', fontsize=9, color=color, fontweight='bold')

ax.set_xticks(range(4))
ax.set_xticklabels(pv_labels, fontsize=11)
ax.set_yticks(range(6))
ax.set_yticklabels(wind_labels, fontsize=11)
ax.set_xlabel('光伏出力场景', fontsize=12)
ax.set_ylabel('风电出力场景', fontsize=12)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q2_scenarios_heatmap.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q2_scenarios_heatmap.pdf")
