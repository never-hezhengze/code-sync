#!/usr/bin/env python3
"""Fig Q4(2): 储能参与下的功率调度曲线 (面积图)"""
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
    p1_data = json.load(f)

# Simulate storage dispatch for W4P1 (max curtailment scenario)
# Use P_RE from typical day as base, scale for W4 wind scenario
P_RE = np.array(p1_data['power_curves']['P_RE'])
P_load_base = np.array(p1_data['power_curves']['P_load'])

# Scale wind up for W4 scenario (higher wind)
scale_factor = 1.35
P_RE_W4P1 = P_RE * scale_factor

# Storage parameters: 150 MWh, 75 MW max
C_sto = 150  # MWh
P_sto_max = 75  # MW

# Simple dispatch: charge when RE > load, discharge when RE < load
P_H2NH3_rated = 41.5
P_total_load = P_load_base + P_H2NH3_rated * 0.78  # avg utilization

P_surplus = P_RE_W4P1 - P_total_load
SOC = np.zeros(25)
SOC[0] = C_sto * 0.2  # start at 20%
P_charge = np.zeros(24)
P_discharge = np.zeros(24)

for h in range(24):
    if P_surplus[h] > 0:
        charge = min(P_surplus[h], P_sto_max, (C_sto - SOC[h]) / 0.95)
        P_charge[h] = charge
        SOC[h+1] = SOC[h] + charge * 0.95
    else:
        discharge = min(-P_surplus[h], P_sto_max, SOC[h] * 0.95)
        P_discharge[h] = discharge
        SOC[h+1] = SOC[h] - discharge / 0.95

hours = np.arange(24)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), height_ratios=[2, 1], sharex=True)

# Top: Power dispatch
ax1.fill_between(hours, 0, P_RE_W4P1, alpha=0.25, color=PALETTE[0], label='新能源出力')
ax1.plot(hours, P_RE_W4P1, color=PALETTE[0], lw=2)
ax1.plot(hours, P_total_load, color=PALETTE[3], lw=2, ls='--', label='总负荷')
ax1.bar(hours, P_charge, width=0.6, alpha=0.7, color=PALETTE[2], label='储能充电')
ax1.bar(hours, -P_discharge, width=0.6, alpha=0.7, color=PALETTE[1], label='储能放电')

ax1.axhline(0, color='#888888', lw=0.8)
ax1.set_ylabel('功率 (MW)', fontsize=12)
ax1.legend(fontsize=10, loc='upper right', ncol=2)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# Bottom: SOC
ax2.fill_between(hours, 0, SOC[:24]/C_sto*100, alpha=0.3, color=PALETTE[4])
ax2.plot(hours, SOC[:24]/C_sto*100, color=PALETTE[4], lw=2.5)
ax2.axhline(20, color='#AAAAAA', ls=':', lw=1)
ax2.axhline(90, color='#AAAAAA', ls=':', lw=1)
ax2.set_xlabel('时刻 (h)', fontsize=12)
ax2.set_ylabel('SOC (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.set_xlim(-0.5, 23.5)
ax2.set_xticks(np.arange(0, 24, 2))
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q4_storage_dispatch.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q4_storage_dispatch.pdf")
