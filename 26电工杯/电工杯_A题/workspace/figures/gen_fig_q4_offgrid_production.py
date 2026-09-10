#!/usr/bin/env python3
"""Fig Q4(1): 24场景离网制氨产量对比 (分组柱状图)"""
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

with open('figures/problem_4_results.json', 'r') as f:
    data = json.load(f)

scenarios = [s['scenario'] for s in data['offgrid_no_storage']]
q_no_sto = [s['Q_NH3'] for s in data['offgrid_no_storage']]
q_with_sto = [s['Q_NH3'] for s in data['with_storage']]

fig, ax = plt.subplots(figsize=(12, 5.5))

x = np.arange(len(scenarios))
width = 0.38

bars1 = ax.bar(x - width/2, q_no_sto, width, color=PALETTE[0], edgecolor='white', lw=0.8, label='无储能', alpha=0.85)
bars2 = ax.bar(x + width/2, q_with_sto, width, color=PALETTE[2], edgecolor='white', lw=0.8, label='有储能 (150 MWh)', alpha=0.85)

ax.axhline(72, color=PALETTE[3], ls='--', lw=1.5, alpha=0.7, label='额定产能 (72 吨/日)')

ax.set_xticks(x)
ax.set_xticklabels(scenarios, fontsize=9, rotation=45, ha='right')
ax.set_xlabel('风光场景', fontsize=12)
ax.set_ylabel('日产氨量 (吨/日)', fontsize=13)
ax.legend(fontsize=10, loc='upper right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, 80)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q4_offgrid_production.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q4_offgrid_production.pdf")
