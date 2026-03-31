"""
多目标优化求解：太空电梯与传统火箭货物运输
使用NSGA-II算法
"""

import sys
sys.path.append('/Users/hezhengze/Code/26美赛/latex论文/code/NSGA-II-master')

from nsga2.problem import Problem
from nsga2.evolution import Evolution
import matplotlib.pyplot as plt
import numpy as np

# ==================== 问题参数定义 ====================
# 太空电梯
R_SES = 3 * 179000  # 年吞吐量 (t/year)
C_E = 100  # 太空电梯成本 ($/kg)

# 火箭
Q_R = 125  # 火箭载荷 (t/次)
C_R = 500  # 火箭成本 ($/kg)

# 总任务
M = 100000000  # 总货物量 (t)

# ==================== 离散化x值 ====================
# 从0开始每隔100取一次值
DISCRETE_X_VALUES = list(range(0, 26601, 100))  # [0, 100, 200, ..., 26600]

# ==================== 目标函数定义 ====================
def objective_time(x_index):
    """
    目标1：任务完成时间 T (年)
    约束：(R_SES + x * Q_R) * T = M
    推导：T = M / (R_SES + x * Q_R)
    x_index: x值在DISCRETE_X_VALUES中的索引
    """
    x = DISCRETE_X_VALUES[int(round(x_index))]
    if R_SES + x * Q_R <= 0:
        return float('inf')
    return M / (R_SES + x * Q_R)


def objective_cost(x_index):
    """
    目标2：预估总成本 C_total (百万$)
    C_total = C_E * R_SES * T + C_R * Q_R * x * 1000
    代入 T = M / (R_SES + x * Q_R)：
    C_total = C_E * R_SES * M / (R_SES + x * Q_R) + C_R * Q_R * x * 1000
    转换为百万$为单位
    x_index: x值在DISCRETE_X_VALUES中的索引
    """
    x = DISCRETE_X_VALUES[int(round(x_index))]
    if R_SES + x * Q_R <= 0:
        return float('inf')
    
    T = M / (R_SES + x * Q_R)
    cost = (C_E * R_SES * T + C_R * Q_R * x * 1000) / 1_000_000
    return cost


# ==================== NSGA-II求解 ====================
def solve_multiobjective_optimization():
    """使用NSGA-II算法求解多目标优化问题"""
    
    # 定义问题
    # 变量：x_index (离散x值的索引)，范围：[0, 266]（对应0到26600每隔100）
    objectives = [objective_time, objective_cost]
    problem = Problem(
        objectives=objectives,
        num_of_variables=1,
        variables_range=[(0, len(DISCRETE_X_VALUES) - 1)],
        expand=True
    )
    
    # 创建进化算法
    evolution = Evolution(
        problem=problem,
        num_of_generations=500,
        num_of_individuals=100,
        num_of_tour_particips=2,
        tournament_prob=0.9,
        crossover_param=2,
        mutation_param=5
    )
    
    # 执行优化
    print("=" * 60)
    print("多目标优化求解：太空电梯与火箭货物运输（离散x值）")
    print("=" * 60)
    print(f"总货物量 M = {M:,} t")
    print(f"太空电梯年吞吐量 R_SES = {R_SES:,} t/year")
    print(f"火箭载荷 Q_R = {Q_R} t/次")
    print(f"离散x值范围：0, 100, 200, ..., {DISCRETE_X_VALUES[-1]} (共{len(DISCRETE_X_VALUES)}个值)")
    print("\n正在进行NSGA-II优化...\n")
    
    pareto_front = evolution.evolve()
    
    return pareto_front, problem


# ==================== 结果分析与展示 ====================
def calculate_crowding_distance(solutions):
    """计算解集的拥挤距离"""
    num_solutions = len(solutions)
    
    if num_solutions == 0:
        return []
    
    # 初始化拥挤距离
    for solution in solutions:
        solution['crowding_distance'] = 0
    
    # 对每个目标函数计算拥挤距离
    num_objectives = 2  # 时间和成本两个目标
    objectives = [
        [sol['time'] for sol in solutions],
        [sol['cost'] for sol in solutions]
    ]
    
    for m in range(num_objectives):
        # 按第m个目标函数排序
        sorted_solutions = sorted(enumerate(solutions), key=lambda x: objectives[m][x[0]])
        
        # 边界解的拥挤距离设为无穷大
        sorted_solutions[0][1]['crowding_distance'] = float('inf')
        sorted_solutions[-1][1]['crowding_distance'] = float('inf')
        
        # 计算目标函数的范围
        m_values = objectives[m]
        scale = max(m_values) - min(m_values)
        if scale == 0:
            scale = 1
        
        # 计算中间解的拥挤距离
        for i in range(1, num_solutions - 1):
            idx = sorted_solutions[i][0]
            distance_increment = (sorted_solutions[i + 1][1]['time'] if m == 0 else sorted_solutions[i + 1][1]['cost']) - \
                                (sorted_solutions[i - 1][1]['time'] if m == 0 else sorted_solutions[i - 1][1]['cost'])
            solutions[idx]['crowding_distance'] += distance_increment / scale
    
    return solutions


def analyze_results(pareto_front, problem):
    """分析优化结果"""
    
    print("=" * 60)
    print("Pareto最优前沿解 (前50个)")
    print("=" * 60)
    
    results = []
    for i, individual in enumerate(sorted(pareto_front, key=lambda x: x.objectives[0])[:50]):
        x_index = int(round(individual.features[0]))
        x = DISCRETE_X_VALUES[x_index]
        T = objective_time(x_index)
        C = objective_cost(x_index)
        
        results.append({
            'rank': i + 1,
            'x_rockets': x,
            'time': T,
            'cost': C,
            'crowding_distance': 0
        })
    
    # 计算拥挤距离
    results = calculate_crowding_distance(results)
    
    # 按拥挤距离排序
    results_sorted_by_cd = sorted(results, key=lambda x: x['crowding_distance'], reverse=True)
    
    # 输出所有50个解
    print("\n按时间排序的所有解：\n")
    for sol in results:
        print(f"解 #{sol['rank']}:")
        print(f"  火箭发射次数 (x) = {sol['x_rockets']:,.0f} 次/年")
        print(f"  任务完成时间 (T) = {sol['time']:,.2f} 年")
        print(f"  预估总成本 (C) = ${sol['cost']:,.2f} 百万")
        if sol['crowding_distance'] == float('inf'):
            print(f"  拥挤距离 (CD) = ∞ (边界解)")
        else:
            print(f"  拥挤距离 (CD) = {sol['crowding_distance']:.6f}")
        
        # 计算吞吐量验证
        throughput = R_SES + sol['x_rockets'] * Q_R
        print(f"  总吞吐量验证 = {throughput:,.0f} t/year\n")
    
    # 输出拥挤距离最大的5个解
    print("=" * 60)
    print("拥挤距离最大的5个解")
    print("=" * 60)
    
    for i, sol in enumerate(results_sorted_by_cd[:5]):
        print(f"\n最大CD解 #{i+1}:")
        print(f"  原始排名 = {sol['rank']}")
        print(f"  火箭发射次数 (x) = {sol['x_rockets']:,.0f} 次/年")
        print(f"  任务完成时间 (T) = {sol['time']:,.2f} 年")
        print(f"  预估总成本 (C) = ${sol['cost']:,.2f} 百万")
        print(f"  拥挤距离 (CD) = {sol['crowding_distance']:.6f}")
        
        # 计算吞吐量验证
        throughput = R_SES + sol['x_rockets'] * Q_R
        print(f"  总吞吐量验证 = {throughput:,.0f} t/year")
    
    return results


# ==================== 可视化 ====================
def visualize_results(pareto_front):
    """可视化Pareto前沿"""
    
    times = []
    costs = []
    xs = []
    
    for individual in sorted(pareto_front, key=lambda x: x.objectives[0])[:50]:
        x_index = int(round(individual.features[0]))
        x = DISCRETE_X_VALUES[x_index]
        T = objective_time(x_index)
        C = objective_cost(x_index)
        
        times.append(T)
        costs.append(C)
        xs.append(x)
    
    # 创建图表
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Pareto前沿
    ax1 = axes[0]
    ax1.scatter(times, costs, color='red', s=50, alpha=0.7)
    ax1.set_xlabel('任务完成时间 (年)', fontsize=12)
    ax1.set_ylabel('预估总成本 (百万$)', fontsize=12)
    ax1.set_title('Pareto最优前沿', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 成本-火箭次数
    ax2 = axes[1]
    ax2.scatter(xs, costs, color='blue', s=50, alpha=0.7)
    ax2.set_xlabel('火箭发射次数 (次/年)', fontsize=12)
    ax2.set_ylabel('预估总成本 (百万$)', fontsize=12)
    ax2.set_title('成本-火箭发射次数关系', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/Users/hezhengze/Code/26美赛/latex论文/figures/pareto_front.png', dpi=300, bbox_inches='tight')
    print("\n图表已保存至: /Users/hezhengze/Code/26美赛/latex论文/figures/pareto_front.png")
    plt.close()


# ==================== 主程序 ====================
if __name__ == '__main__':
    # 求解
    pareto_front, problem = solve_multiobjective_optimization()
    
    # 分析结果
    results = analyze_results(pareto_front, problem)
    
    # 可视化
    visualize_results(pareto_front)
    
    print("\n" + "=" * 60)
    print("优化完成！")
    print("=" * 60)
