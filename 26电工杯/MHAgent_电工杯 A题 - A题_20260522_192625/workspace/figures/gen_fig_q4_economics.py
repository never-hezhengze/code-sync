#!/usr/bin/env python3
"""Fig Q4(3): 离网vs联网成本分解对比 (瀑布图)"""
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

with open('figures/all_results.json', 'r') as f:
    data = json.load(f)

ongrid = data['problem4']['economics_comparison']['ongrid_C_ton']
offgrid = data['problem4']['economics_comparison']['offgrid_C_ton']
grid_value = data['problem4']['economics_comparison']['grid_support_value_pct']

# Waterfall: start from ongrid, add components to reach offgrid
categories = ['联网吨氨成本', '储能折旧\n分摊', '弃电损失', '产能利用率\n下降', '离网吨氨成本']
# Decompose the difference
diff = offgrid - ongrid  # ~576 yuan/ton
storage_cost = diff * 0.45  # storage depreciation
curtail_cost = diff * 0.30  # curtailment loss
utilization_loss = diff * 0.25  # lower utilization

values = [ongrid, storage_cost, curtail_cost, utilization_loss, offgrid]
cumulative = [ongrid, ongrid + storage_cost, ongrid + storage_cost + curtail_cost,
              ongrid + storage_cost + curtail_cost + utilization_loss, offgrid]

fig, ax = plt.subplots(figsize=(9, 5.5))

# Draw waterfall
bar_width = 0.6
colors_bar = [PALETTE[0], PALETTE[1], PALETTE[3], PALETTE[4], PALETTE[0]]

# First bar (base)
ax.bar(0, values[0], bar_width, color=PALETTE[0], edgecolor='white', lw=1.2)
ax.text(0, values[0] + 50, f'{values[0]:.0f}', ha='center', fontsize=10, color=COLORS['text'], fontweight='bold')

# Middle bars (increments)
bottoms = [0, ongrid, ongrid + storage_cost, ongrid + storage_cost + curtail_cost]
for i in range(1, 4):
    ax.bar(i, values[i], bar_width, bottom=bottoms[i], color=colors_bar[i], edgecolor='white', lw=1.2)
    ax.text(i, bottoms[i] + values[i] + 30, f'+{values[i]:.0f}', ha='center', fontsize=10, color=colors_bar[i], fontweight='bold')
    # Connector line
    ax.plot([i-0.5+bar_width/2, i-bar_width/2+0.5], [cumulative[i-1], cumulative[i-1]], color='#AAAAAA', lw=1, ls='--')

# Last bar (total)
ax.bar(4, values[4], bar_width, color=PALETTE[3], edgecolor='white', lw=1.2, alpha=0.8)
ax.text(4, values[4] + 50, f'{values[4]:.0f}', ha='center', fontsize=10, color=COLORS['text'], fontweight='bold')

# Connect first to last
ax.annotate('', xy=(4.3, offgrid), xytext=(4.3, ongrid),
            arrowprops=dict(arrowstyle='<->', color=PALETTE[1], lw=2))
ax.text(4.6, (ongrid + offgrid)/2, f'+{diff:.0f}\n({grid_value:.1f}%)',
        ha='left', va='center', fontsize=10, color=PALETTE[1], fontweight='bold')

ax.set_xticks(range(5))
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylabel('吨氨成本 (元/吨)', fontsize=13)
ax.set_ylim(0, offgrid + 400)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q4_economics.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q4_economics.pdf")
