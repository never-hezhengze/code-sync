"""
单变量多目标权衡分析
太空电梯 vs 火箭运输
方法：参数扫描 + Pareto 前沿
"""

import numpy as np
import matplotlib.pyplot as plt

# ==================== 参数定义 ====================
# 太空电梯
R_SES = 3 * 179_000        # 年吞吐量 (t/year)
C_E = 100                 # 成本 ($/kg)

# 火箭
Q_R = 150                 # 单次载荷 (t)
C_R = 500                 # 成本 ($/kg)

# 总任务
M = 100_000_000           # 总货物量 (t)

# ==================== 目标函数 ====================
def objective_time(x):
    """
    任务完成时间 T (年)
    """
    throughput = R_SES + x * Q_R
    if throughput <= 0:
        return np.inf
    return M / throughput


def objective_cost(x):
    """
    总成本 C (百万美元)
    """
    throughput = R_SES + x * Q_R
    if throughput <= 0:
        return np.inf

    T = M / throughput
    cost = (C_E * R_SES * T + C_R * Q_R * x * 1000) / 1_000_000
    return cost


# ==================== 参数扫描 ====================
def parameter_sweep(x_min=0, x_max=10000, num_points=2000):
    """
    对火箭年发射次数 x 进行扫描
    """
    xs = np.linspace(x_min, x_max, num_points)
    times = []
    costs = []

    for x in xs:
        times.append(objective_time(x))
        costs.append(objective_cost(x))

    return np.array(xs), np.array(times), np.array(costs)


# ==================== Pareto 前沿提取 ====================
def pareto_filter(times, costs, xs):
    """
    提取非支配解（Pareto 前沿）
    """
    pareto_idx = []
    n = len(times)

    for i in range(n):
        dominated = False
        for j in range(n):
            if (times[j] <= times[i] and costs[j] <= costs[i]) and \
               (times[j] < times[i] or costs[j] < costs[i]):
                dominated = True
                break
        if not dominated:
            pareto_idx.append(i)

    return xs[pareto_idx], times[pareto_idx], costs[pareto_idx]


# ==================== 可视化 ====================
def visualize(xs, times, costs, pxs, ptimes, pcosts):
    plt.figure(figsize=(10, 7))

    # 全部可行解
    plt.scatter(times, costs, s=10, alpha=0.3, label="Feasible solutions")

    # Pareto 前沿
    plt.plot(ptimes, pcosts, 'r-', linewidth=2, label="Pareto front")
    
    # 提取五个均匀分布的点，去掉两个端点，保留中间三个
    five_indices = np.linspace(0, len(pxs) - 1, 5, dtype=int)
    middle_three_indices = five_indices[1:4]  # 取中间三个（索引1, 2, 3）
    
    # 三个解的定义（与1.3.3.py保持一致）
    solutions = [
        {"label": "Cheaper", "color": "#1f77b4", "marker": "s", "idx": middle_three_indices[0]},   # 橙色
        {"label": "Balanced", "color": "#2ca02c", "marker": "o", "idx": middle_three_indices[1]},  # 绿色
        {"label": "Faster", "color": "#ff7f0e", "marker": "^", "idx": middle_three_indices[2]}    # 蓝色
    ]
    
    # 标注三个解
    for sol in solutions:
        idx = sol['idx']
        t_val = ptimes[idx]
        c_val = pcosts[idx]
        x_val = pxs[idx]
        
        # 绘制特殊点
        plt.scatter(t_val, c_val, c=sol['color'], marker=sol['marker'], s=200, 
                   edgecolors='black', linewidths=2, zorder=10, label=f"{sol['label']} ({int(x_val)} L/y)")
        
        # 添加文字标注
        plt.annotate(f"{sol['label']}\n({int(x_val)} L/y)\n{t_val:.1f}y / ${c_val:.1f}M", 
                    xy=(t_val, c_val), 
                    xytext=(t_val, c_val + c_val * 0.08),
                    ha='center', fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor=sol['color'], alpha=0.3),
                    arrowprops=dict(arrowstyle="->", color=sol['color'], lw=1.5))

    plt.xlabel("Task Completion Time T (years)", fontsize=12)
    plt.ylabel("Total Cost C (Million USD)", fontsize=12)
    plt.title("Time–Cost Pareto Trade-off\n(Three Optimal Solutions Highlighted)", fontsize=14, fontweight='bold')
    plt.grid(alpha=0.3)
    plt.legend(loc='upper right', fontsize=10)
    plt.tight_layout()

    plt.savefig(
        "/Users/hezhengze/Code/26美赛/latex论文/figures/pareto_scan.png",
        dpi=300,
        bbox_inches="tight"
    )
    print('Saved 2D Pareto figure with three solutions highlighted')


# ==================== 主程序 ====================
if __name__ == "__main__":
    xs, times, costs = parameter_sweep()
    pxs, ptimes, pcosts = pareto_filter(times, costs, xs)
    visualize(xs, times, costs, pxs, ptimes, pcosts)

    print("=" * 60)
    print("Pareto Front Key Solutions (Partial)")
    print("=" * 60)

    for i in np.linspace(0, len(pxs) - 1, 5, dtype=int):
        print(f"x = {pxs[i]:,.0f} times/year | "
              f"T = {ptimes[i]:.2f} years | "
              f"C = {pcosts[i]:.2f} million USD")
