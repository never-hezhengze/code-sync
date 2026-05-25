#!/usr/bin/env python3
"""Fig Q2(1): 最优产量下的24h开停机时段安排 (甘特图)"""
import sys, os, json
sys.path.insert(0, '.')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from _utils.plot_utils import setup_style, PALETTE, COLORS

setup_style('science')
from _utils.plot_utils import PALETTE, COLORS

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

with open('figures/problem_2_results.json', 'r') as f:
    data = json.load(f)

productions = [36, 45, 54, 63, 72]
fig, ax = plt.subplots(figsize=(12, 5))

for idx, q in enumerate(productions):
    u = data['typical'][str(q)]['u']
    y = len(productions) - 1 - idx
    for h in range(24):
        if u[h] > 0.5:
            ax.barh(y, 1, left=h, height=0.6, color=PALETTE[idx % len(PALETTE)],
                    edgecolor='white', lw=0.5, alpha=0.85)
        else:
            ax.barh(y, 1, left=h, height=0.6, color='#F0F0F0',
                    edgecolor='#DDDDDD', lw=0.5)

    k = int(sum(u))
    ax.text(24.5, y, f'{k}h 开机', va='center', fontsize=10, color=COLORS['text'])

ax.set_yticks(range(len(productions)))
ax.set_yticklabels([f'{q} 吨/日' for q in reversed(productions)], fontsize=11)
ax.set_xlabel('时刻 (h)', fontsize=13)
ax.set_xlim(0, 27)
ax.set_xticks(np.arange(0, 25, 2))
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add time-of-use shading
ax.axvspan(0, 7, alpha=0.05, color='blue', zorder=0)
ax.axvspan(7, 11, alpha=0.05, color='orange', zorder=0)
ax.axvspan(11, 17, alpha=0.05, color='red', zorder=0)
ax.axvspan(17, 21, alpha=0.05, color='orange', zorder=0)
ax.axvspan(21, 24, alpha=0.05, color='blue', zorder=0)

ax.text(3.5, -0.8, '谷时', ha='center', fontsize=9, color='#666666')
ax.text(9, -0.8, '平时', ha='center', fontsize=9, color='#666666')
ax.text(14, -0.8, '峰时', ha='center', fontsize=9, color='#666666')
ax.text(19, -0.8, '平时', ha='center', fontsize=9, color='#666666')
ax.text(22.5, -0.8, '谷时', ha='center', fontsize=9, color='#666666')

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q2_schedule_gantt.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q2_schedule_gantt.pdf")
