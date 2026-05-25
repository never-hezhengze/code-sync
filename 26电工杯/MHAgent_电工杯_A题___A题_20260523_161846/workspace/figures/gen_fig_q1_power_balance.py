#!/usr/bin/env python3
"""Fig Q1: 典型日功率平衡曲线 (面积图)"""
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

hours = np.arange(24)
P_load = np.array(data['power_curves']['P_total_load'])
P_RE = np.array(data['power_curves']['P_RE'])
P_buy = np.array(data['power_curves']['P_buy'])
P_sell = np.array(data['power_curves']['P_sell'])
P_wind = np.array(data['power_curves']['P_wind'])
P_pv = np.array(data['power_curves']['P_pv'])

fig, ax = plt.subplots(figsize=(10, 5.5))

ax.fill_between(hours, 0, P_wind, alpha=0.35, color=PALETTE[0], label='风电出力')
ax.fill_between(hours, P_wind, P_wind + P_pv, alpha=0.35, color=PALETTE[1], label='光伏出力')
ax.plot(hours, P_RE, color=PALETTE[0], lw=2.2, label='新能源总出力')
ax.plot(hours, P_load, color=PALETTE[3], lw=2.2, ls='--', label='总用电负荷')
ax.bar(hours, P_buy, width=0.4, alpha=0.7, color=PALETTE[4], label='购电功率', align='edge')
ax.bar(hours, -P_sell, width=0.4, alpha=0.7, color=PALETTE[2], label='售电功率', align='center')

ax.axhline(0, color='#888888', lw=0.8, ls='-')
ax.set_xlabel('时刻 (h)', fontsize=13)
ax.set_ylabel('功率 (MW)', fontsize=13)
ax.set_xlim(-0.5, 23.5)
ax.set_xticks(np.arange(0, 24, 2))
ax.legend(loc='upper right', fontsize=10, ncol=2, framealpha=0.9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout(pad=0.5)
fig.savefig('figures/fig_q1_power_balance.pdf', dpi=300, bbox_inches='tight')
plt.close(fig)
print("OK: fig_q1_power_balance.pdf")
