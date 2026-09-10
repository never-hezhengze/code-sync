#!/usr/bin/env python3
"""Fig Q2(2): 绿电指标满足情况统计 (堆叠柱状图)"""
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

categories = ['问题二\n(离散调节)', '问题三\n(连续调节)']
full_pass = [data['problem2']['annual_stats']['full_pass_days'],
             data['problem3']['annual_stats']['full_pass_days']]
partial_pass = [data['problem2']['annual_stats']['partial_pass_days'],
                data['problem3']['annual_stats']['partial_pass_days']]
no_pass = [data['problem2']['annual_stats']['no_pass_days'],
           data['problem3']['annual_stats']['no_pass_days']]

fig, ax = plt.subplots(figsize=(7, 5))

x = np.arange(len(categories))
width = 0.5

bars1 = ax.bar(x, full_pass, width, color=PALETTE[2], edgecolor='white', lw=1.2, label='全满足')
bars2 = ax.bar(x, partial_pass, width, bottom=full_pass, color=PALETTE[0], edgecolor='white', lw=1.2, label='部分满足')
bars3 = ax.bar(x, no_pass, width, bottom=[f+p for f, p in zip(full_pass, partial_pass)],
               color=PALETTE[3], edgecolor='white', lw=1.2, label='全不满足')

for i in range(len(categories)):
    if full_pass[i] > 0:
        ax.text(x[i], full_pass[i]/2, f'{full_pass[i]}天', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
    if partial_pass[i] > 0:
        ax.text(x[i], full_pass[i] + partial_pass[i]/2, f'{partial_pass[i]}天', ha='center', va='center', fontsize=11, color='white', fontweight='bold')
    if no_pass[i] > 0:
        ax.text(x[i], full_pass[i] + partial_pass[i] + no_pass[i]/2, f'{no_pass[i]}天', ha='center', va='center', fontsize=11, color='white', fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=12)
ax.set_ylabel('天数 (天/年)', fontsize=13)
ax.set_ylim(0, 400)
ax.legend(fontsize=11, loc='upper right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q2_green_indicators.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q2_green_indicators.pdf")
