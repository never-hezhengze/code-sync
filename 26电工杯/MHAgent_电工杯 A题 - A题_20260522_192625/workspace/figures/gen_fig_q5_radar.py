#!/usr/bin/env python3
"""Fig Q5: 绿电园区对电力系统影响多维评价 (雷达图)"""
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

# Multi-dimensional evaluation of green power park impact on grid
categories = ['新能源消纳', '电网调峰\n压力缓解', '碳减排\n贡献', '电网投资\n节约', '供电可靠性', '电价稳定性']
N = len(categories)

# Scores (0-10 scale) for different penetration levels
low_penetration = [7, 6, 7, 5, 8, 7]   # 低渗透率
high_penetration = [9, 4, 9, 8, 5, 4]  # 高渗透率

angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]

low_penetration += low_penetration[:1]
high_penetration += high_penetration[:1]

fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

ax.plot(angles, low_penetration, 'o-', color=PALETTE[0], lw=2.5, markersize=8, label='低渗透率')
ax.fill(angles, low_penetration, alpha=0.15, color=PALETTE[0])
ax.plot(angles, high_penetration, 's-', color=PALETTE[1], lw=2.5, markersize=8, label='高渗透率')
ax.fill(angles, high_penetration, alpha=0.15, color=PALETTE[1])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=11)
ax.set_ylim(0, 10)
ax.set_yticks([2, 4, 6, 8, 10])
ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=9, color='#888888')
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)

fig.tight_layout(pad=1.0)
fig.savefig('figures/fig_q5_radar.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q5_radar.pdf")
