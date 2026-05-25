#!/usr/bin/env python3
"""Fig Q2(2): 全年吨氨成本分布曲线 (面积图)"""
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

costs_q2 = sorted(data['problem2']['cost_distribution'])
costs_q3 = sorted(data['problem3']['cost_distribution'])

# Each scenario = 15 days
days_per_scenario = 15
n_scenarios = 24
total_days = n_scenarios * days_per_scenario  # 360

# Build cumulative days
x_q2 = np.arange(1, n_scenarios + 1) * days_per_scenario
x_q3 = np.arange(1, n_scenarios + 1) * days_per_scenario

fig, ax = plt.subplots(figsize=(9, 5))

ax.fill_between(x_q2, costs_q2, alpha=0.25, color=PALETTE[0])
ax.plot(x_q2, costs_q2, '-o', color=PALETTE[0], lw=2, markersize=4, label='问题二 (离散调节)')
ax.fill_between(x_q3, costs_q3, alpha=0.25, color=PALETTE[1])
ax.plot(x_q3, costs_q3, '-s', color=PALETTE[1], lw=2, markersize=4, label='问题三 (连续调节)')

ax.axhline(data['problem2']['annual_stats']['annual_C_ton'], color=PALETTE[0], ls='--', lw=1.5, alpha=0.7)
ax.axhline(data['problem3']['annual_stats']['annual_C_ton'], color=PALETTE[1], ls='--', lw=1.5, alpha=0.7)

ax.text(340, data['problem2']['annual_stats']['annual_C_ton'] + 80,
        f"年均: {data['problem2']['annual_stats']['annual_C_ton']:.0f}", fontsize=9, color=PALETTE[0])
ax.text(340, data['problem3']['annual_stats']['annual_C_ton'] - 150,
        f"年均: {data['problem3']['annual_stats']['annual_C_ton']:.0f}", fontsize=9, color=PALETTE[1])

ax.set_xlabel('累计天数 (天)', fontsize=13)
ax.set_ylabel('吨氨成本 (元/吨)', fontsize=13)
ax.legend(fontsize=11, loc='upper left')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q2_annual_cost.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q2_annual_cost.pdf")
