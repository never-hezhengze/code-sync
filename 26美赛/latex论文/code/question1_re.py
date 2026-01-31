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
    plt.figure(figsize=(7, 5))

    # 全部可行解
    plt.scatter(times, costs, s=10, alpha=0.3, label="Feasible solutions")

    # Pareto 前沿
    plt.plot(ptimes, pcosts, 'r-', linewidth=2, label="Pareto front")

    plt.xlabel("任务完成时间 T (年)", fontsize=12)
    plt.ylabel("总成本 C (百万美元)", fontsize=12)
    plt.title("时间–成本 Pareto 权衡", fontsize=14)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        "/Users/hezhengze/Code/26美赛/latex论文/figures/pareto_scan.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.show()


# ==================== 主程序 ====================
if __name__ == "__main__":
    xs, times, costs = parameter_sweep()
    pxs, ptimes, pcosts = pareto_filter(times, costs, xs)
    visualize(xs, times, costs, pxs, ptimes, pcosts)

    print("=" * 60)
    print("Pareto 前沿关键解（部分）")
    print("=" * 60)

    for i in np.linspace(0, len(pxs) - 1, 5, dtype=int):
        print(f"x = {pxs[i]:,.0f} 次/年 | "
              f"T = {ptimes[i]:.2f} 年 | "
              f"C = {pcosts[i]:.2f} 百万美元")
