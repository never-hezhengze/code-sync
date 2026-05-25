#!/usr/bin/env python3
"""Fig Q3(3): 问题三vs问题二各指标变化量 (发散柱状图)"""
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

# Compare Q3 vs Q2
q2 = data['problem2']['annual_stats']
q3 = data['problem3']['annual_stats']

metrics = ['年均吨氨成本', '全满足天数', '部分满足天数', '全不满足天数']
q2_vals = [q2['annual_C_ton'], q2['full_pass_days'], q2['partial_pass_days'], q2['no_pass_days']]
q3_vals = [q3['annual_C_ton'], q3['full_pass_days'], q3['partial_pass_days'], q3['no_pass_days']]

# Compute percentage change
pct_change = []
for v2, v3 in zip(q2_vals, q3_vals):
    if v2 == 0:
        if v3 > 0:
            pct_change.append(100)
        else:
            pct_change.append(0)
    else:
        pct_change.append((v3 - v2) / abs(v2) * 100)

fig, ax = plt.subplots(figsize=(8, 5))

y = np.arange(len(metrics))
colors = [COLORS['up'] if p < 0 else PALETTE[1] if p > 0 else COLORS['neutral'] for p in pct_change]
# For "全不满足天数", decrease is good; for "全满足天数", increase is good
# Adjust color logic
good_direction = [-1, 1, 0, -1]  # cost down=good, full_pass up=good, partial=neutral, no_pass down=good
for i, (p, gd) in enumerate(zip(pct_change, good_direction)):
    if gd == -1:
        colors[i] = COLORS['up'] if p < 0 else PALETTE[3]
    elif gd == 1:
        colors[i] = COLORS['up'] if p > 0 else PALETTE[3]
    else:
        colors[i] = PALETTE[0]

bars = ax.barh(y, pct_change, height=0.6, color=colors, edgecolor='white', lw=1.2)

ax.axvline(0, color='#888888', lw=1, ls='-')

for i, (bar, val) in enumerate(zip(bars, pct_change)):
    offset = 2 if val >= 0 else -2
    ha = 'left' if val >= 0 else 'right'
    if abs(val) == float('inf') or abs(val) > 1000:
        label = '+inf' if val > 0 else '-inf'
    else:
        label = f'{val:+.1f}%'
    ax.text(val + offset, i, label, va='center', ha=ha, fontsize=11, color=COLORS['text'], fontweight='bold')

ax.set_yticks(y)
ax.set_yticklabels(metrics, fontsize=12)
ax.set_xlabel('变化率 (%)', fontsize=13)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q3_comparison.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q3_comparison.pdf")
