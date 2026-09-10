#!/usr/bin/env python3
"""Fig Q3(1): 典型场景连续调度功率曲线与风光出力 (双轴图)"""
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

with open('figures/problem_3_results.json', 'r') as f:
    data = json.load(f)
with open('figures/problem_1_results.json', 'r') as f:
    p1_data = json.load(f)

# Use typical scenario Q=54 (mid-range) for dispatch visualization
typical = data['typical']['54']
alpha = np.array(typical['alpha'])
P_RE = np.array(p1_data['power_curves']['P_RE'])
P_load_base = np.array(p1_data['power_curves']['P_load'])

hours = np.arange(24)
# H2NH3 rated power = 20.75 MW per unit (scaled for 72t capacity = 2x)
P_H2NH3_rated = 41.5  # 72t/day capacity
P_H2NH3 = alpha * P_H2NH3_rated

fig, ax1 = plt.subplots(figsize=(10, 5.5))

ax1.fill_between(hours, 0, P_RE, alpha=0.2, color=PALETTE[0], label='新能源出力')
ax1.plot(hours, P_RE, color=PALETTE[0], lw=2, label='新能源出力')
ax1.plot(hours, P_H2NH3 + P_load_base, color=PALETTE[3], lw=2, ls='--', label='总负荷')
ax1.fill_between(hours, P_load_base, P_H2NH3 + P_load_base, alpha=0.3, color=PALETTE[1], label='制氢氨负荷')
ax1.fill_between(hours, 0, P_load_base, alpha=0.2, color=PALETTE[4], label='常规负荷')

ax2 = ax1.twinx()
ax2.bar(hours, alpha * 100, width=0.4, alpha=0.4, color=PALETTE[2], label='负荷率 (%)')
ax2.set_ylabel('制氢氨负荷率 (%)', fontsize=12, color=PALETTE[2])
ax2.set_ylim(0, 120)
ax2.tick_params(axis='y', labelcolor=PALETTE[2])

ax1.set_xlabel('时刻 (h)', fontsize=13)
ax1.set_ylabel('功率 (MW)', fontsize=13)
ax1.set_xlim(-0.5, 23.5)
ax1.set_xticks(np.arange(0, 24, 2))

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9, ncol=2)

ax1.spines['top'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q3_dispatch.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q3_dispatch.pdf")
