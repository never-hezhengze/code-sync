"""
单变量多目标权衡分析
太空电梯 vs 火箭运输
方法：参数扫描 + Pareto 前沿 + 归一化距离最小解
"""

import numpy as np
import matplotlib.pyplot as plt

# ==================== 参数定义 ====================
R_SES = 3 * 179_000        # 年吞吐量 (t/year)
C_E = 100                 # 成本 ($/kg)

Q_R = 125                 # 单次载荷 (t)
C_R = 500                 # 成本 ($/kg)

M = 100_000_000           # 总货物量 (t)


# ==================== 目标函数 ====================
def objective_time(x):
    throughput = R_SES + x * Q_R
    return np.inf if throughput <= 0 else M / throughput


def objective_cost(x):
    throughput = R_SES + x * Q_R
    if throughput <= 0:
        return np.inf
    T = M / throughput
    return (C_E * R_SES * T + C_R * Q_R * x * 1000) / 1_000_000


# ==================== 参数扫描 ====================
def parameter_sweep(x_min=0, x_max=26_600, num_points=2000):
    xs = np.linspace(x_min, x_max, num_points)
    times = np.array([objective_time(x) for x in xs])
    costs = np.array([objective_cost(x) for x in xs])
    return xs, times, costs


# ==================== Pareto 前沿 ====================
def pareto_filter(xs, times, costs):
    mask = np.ones(len(xs), dtype=bool)
    for i in range(len(xs)):
        for j in range(len(xs)):
            if (times[j] <= times[i] and costs[j] <= costs[i]) and \
               (times[j] < times[i] or costs[j] < costs[i]):
                mask[i] = False
                break
    return xs[mask], times[mask], costs[mask]


# ==================== 归一化距离最小解 ====================
def find_normalized_best(pxs, ptimes, pcosts):
    T_min, T_max = ptimes.min(), ptimes.max()
    C_min, C_max = pcosts.min(), pcosts.max()

    Tn = (ptimes - T_min) / (T_max - T_min)
    Cn = (pcosts - C_min) / (C_max - C_min)

    dist = np.sqrt(Tn**2 + Cn**2)
    idx = np.argmin(dist)

    return pxs[idx], ptimes[idx], pcosts[idx]


# ==================== 可视化 ====================
def visualize(xs, times, costs, pxs, ptimes, pcosts, best):
    bx, bT, bC = best

    plt.figure(figsize=(7, 5))
    plt.scatter(times, costs, s=10, alpha=0.25, label="Feasible solutions")
    plt.plot(ptimes, pcosts, 'r-', linewidth=2, label="Pareto front")

    plt.scatter(bT, bC, color="black", s=80, zorder=5, label="Normalized best")
    plt.annotate(
        "Normalized best",
        (bT, bC),
        xytext=(10, -10),
        textcoords="offset points",
        fontsize=11,
        fontweight="bold"
    )

    plt.xlabel("任务完成时间 T (年)", fontsize=12)
    plt.ylabel("总成本 C (百万美元)", fontsize=12)
    plt.title("时间–成本 Pareto 权衡（归一化最优解）", fontsize=14)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        "/Users/hezhengze/Code/26美赛/latex论文/figures/pareto_normalized.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.show()


# ==================== 主程序 ====================
if __name__ == "__main__":
    xs, times, costs = parameter_sweep()
    pxs, ptimes, pcosts = pareto_filter(xs, times, costs)

    best = find_normalized_best(pxs, ptimes, pcosts)
    visualize(xs, times, costs, pxs, ptimes, pcosts, best)

    print("=" * 60)
    print("归一化距离最小解（推荐方案）")
    print("=" * 60)
    print(f"x = {best[0]:,.0f} 次/年")
    print(f"T = {best[1]:.2f} 年")
    print(f"C = {best[2]:.2f} 百万美元")
