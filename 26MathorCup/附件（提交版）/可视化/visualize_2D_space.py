import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(8, 6))

# 定义横纵坐标边界极限
x_max = 25
y_max = 13

# 生成数据
x = np.linspace(0, x_max, 200)
y_line = y_max - (y_max / x_max) * x

ax.plot(x, y_line, color='red', linewidth=2, linestyle='--', label='容载量理论下界线')
ax.fill_between(x, y_line, y_max, color='#1f77b4', alpha=0.3, label='异构车型有效可行解空间')

ax.plot([0, x_max], [y_max, y_max], color='#08306b', linewidth=1, linestyle='--')
ax.plot([x_max, x_max], [0, y_max], color='#08306b', linewidth=1, linestyle='--')

ax.scatter([0, x_max], [y_max, 0], color='red', s=60, zorder=5)

ax.text(-0.8, y_max, f'(0, {y_max})', fontsize=18, ha='right', va='center', fontweight='bold')
ax.text(x_max + 0.5, 0.5, f'({x_max}, 0)', fontsize=18, ha='left', va='bottom', fontweight='bold')
ax.set_xlim(-4, 32)
ax.set_ylim(-2, 16)

ax.set_xticks(np.arange(3, 31, 3))
ax.set_yticks(np.arange(2, 16, 2))
ax.text(-0.2, -0.2, '0', fontsize=18, ha='right', va='top')
ax.tick_params(axis='both', labelsize=18)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.spines['left'].set_position(('data', 0))
ax.spines['bottom'].set_position(('data', 0))

ax.spines['bottom'].set_bounds(0, 32)
ax.spines['left'].set_bounds(0, 16)

ax.legend(loc='upper right', framealpha=1, edgecolor='black', fontsize = 15)
# ax.grid(True, linestyle='-', color='#e0e0e0', alpha=0.7)

plt.tight_layout()
output_path = 'refined_feasible_space.png'
plt.savefig(output_path, dpi=600, bbox_inches='tight')
plt.show()