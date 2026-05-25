#!/usr/bin/env python3
"""Fig Q1: 三项绿电指标与阈值对比 (分组柱状图)"""
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

with open('figures/problem_1_results.json', 'r') as f:
    data = json.load(f)

indicators = data['indicators']
categories = ['自发自用比例', '绿电比例', '上网电量比例']
actual_vals = [indicators['R_self'] * 100, indicators['R_green'] * 100, indicators['R_grid'] * 100]
thresholds = [60, 30, 20]
pass_status = [indicators['R_self_pass'], indicators['R_green_pass'], indicators['R_grid_pass']]

fig, ax = plt.subplots(figsize=(8, 5))

x = np.arange(len(categories))
width = 0.35

bars1 = ax.bar(x - width/2, actual_vals, width, color=PALETTE[0], edgecolor='white', lw=1.2, label='实际值')
bars2 = ax.bar(x + width/2, thresholds, width, color=PALETTE[2], edgecolor='white', lw=1.2, alpha=0.7, label='阈值要求')

for i, (bar, val, passed) in enumerate(zip(bars1, actual_vals, pass_status)):
    color = COLORS['up'] if passed else PALETTE[3]
    symbol = 'PASS' if passed else 'FAIL'
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            f'{val:.1f}%\n({symbol})', ha='center', va='bottom', fontsize=10, color=color, fontweight='bold')

for bar, val in zip(bars2, thresholds):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            f'{val}%', ha='center', va='bottom', fontsize=10, color=COLORS['text'])

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=12)
ax.set_ylabel('比例 (%)', fontsize=13)
ax.set_ylim(0, 90)
ax.legend(fontsize=11, loc='upper left')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q1_indicators.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q1_indicators.pdf")
