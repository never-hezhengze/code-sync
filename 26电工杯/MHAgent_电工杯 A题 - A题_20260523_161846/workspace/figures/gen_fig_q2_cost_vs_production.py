#!/usr/bin/env python3
"""Fig Q2(1): 不同日产量下的吨氨成本变化 (折线图)"""
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

productions = [36, 45, 54, 63, 72]
costs = [data['typical'][str(q)]['C_ton'] for q in productions]

fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(productions, costs, 'o-', color=PALETTE[0], lw=2.5, markersize=10, markerfacecolor='white',
        markeredgewidth=2.5, markeredgecolor=PALETTE[0], zorder=5)

# Highlight minimum
min_idx = np.argmin(costs)
ax.scatter(productions[min_idx], costs[min_idx], s=200, color=PALETTE[1], zorder=6, edgecolors='white', linewidths=2)
ax.annotate(f'最低: {costs[min_idx]:.0f} 元/吨\n({productions[min_idx]} 吨/日)',
            xy=(productions[min_idx], costs[min_idx]),
            xytext=(productions[min_idx]+5, costs[min_idx]+200),
            fontsize=11, color=PALETTE[1], fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=PALETTE[1], lw=1.5))

for i, (p, c) in enumerate(zip(productions, costs)):
    if i != min_idx:
        ax.text(p, c + 80, f'{c:.0f}', ha='center', va='bottom', fontsize=9, color=COLORS['text'])

ax.set_xlabel('日产氨量 (吨/日)', fontsize=13)
ax.set_ylabel('吨氨成本 (元/吨)', fontsize=13)
ax.set_xticks(productions)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q2_cost_vs_production.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q2_cost_vs_production.pdf")
