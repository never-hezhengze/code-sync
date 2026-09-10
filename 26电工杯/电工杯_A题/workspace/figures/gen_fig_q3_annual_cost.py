#!/usr/bin/env python3
"""Fig Q3(1): 全年吨氨成本分布曲线 (折线图, 与问题二对比)"""
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

scenarios_sorted_idx = np.argsort(data['problem2']['cost_distribution'])
scenario_labels = [f'S{i+1}' for i in range(24)]

fig, ax = plt.subplots(figsize=(10, 5))

x = np.arange(1, 25)
ax.plot(x, costs_q2, 'o-', color=PALETTE[0], lw=2, markersize=5, label='问题二 (离散调节)', alpha=0.9)
ax.plot(x, costs_q3, 's-', color=PALETTE[1], lw=2, markersize=5, label='问题三 (连续调节)', alpha=0.9)

# Fill between to show improvement
ax.fill_between(x, costs_q3, costs_q2, where=np.array(costs_q2) > np.array(costs_q3),
                alpha=0.15, color=PALETTE[2], label='成本降低区间')

ax.axhline(data['problem2']['annual_stats']['annual_C_ton'], color=PALETTE[0], ls=':', lw=1.5, alpha=0.6)
ax.axhline(data['problem3']['annual_stats']['annual_C_ton'], color=PALETTE[1], ls=':', lw=1.5, alpha=0.6)

ax.set_xlabel('场景排序序号', fontsize=13)
ax.set_ylabel('吨氨成本 (元/吨)', fontsize=13)
ax.legend(fontsize=11, loc='upper left')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q3_annual_cost.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q3_annual_cost.pdf")
