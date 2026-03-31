"""
三目标扫描：时间 / 成本 / 环境影响（基于简化LCA）
- 火箭的环境影响（忽略电梯影响）作为第三个目标
- 使用参数扫描（x从0到26600，每100一档）计算每个点的三目标值
- 提取三目标的非支配（Pareto）解并保存图像
- 在Pareto前沿中找到均衡、激进、经济三种解
"""

import numpy as np
import matplotlib.pyplot as plt
import argparse

# ==================== 参数定义（与之前一致） ====================
R_SES = 3 * 179_000        # 太空电梯年吞吐量 (t/year)
C_E = 100                  # 太空电梯成本 ($/kg)
Q_R = 150                  # 火箭单次载荷 (t)
C_R = 500                  # 火箭成本 ($/kg)
M = 100_000_000            # 总货物量 (t)

# ==================== 成本迭代模型参数（从1.3.3.py） ====================
TOTAL_MASS_TONS = M
ELEVATOR_CAPACITY = R_SES  # t/year
ELEVATOR_COST_PER_KG = C_E
ROCKET_CAPACITY = Q_R  # t/launch
ROCKET_MFG_COST_PER_KG = 400
ROCKET_FUEL_COST_PER_KG = 100
COST_DECAY_RATE = 0.05
MAX_ROCKET_LAUNCHES_PER_YEAR = 10000

# 单位换算
ELEVATOR_COST_PER_TON = ELEVATOR_COST_PER_KG * 1000
ROCKET_MFG_COST_PER_TON = ROCKET_MFG_COST_PER_KG * 1000
ROCKET_FUEL_COST_PER_TON = ROCKET_FUEL_COST_PER_KG * 1000

# ==================== LCA 完整工程模型（基于文献参数） ====================
# 功能单位 (FU): 1 kg payload delivered to LEO (200-500 km)

# ========== 火箭制造阶段 ==========
# 典型火箭干质量 (kg), 以 Falcon 9 为参考
ROCKET_DRY_MASS_KG = 5_000  # kg (typical for 150 ton payload rocket)

# 制造材料成分与排放因子 (kg CO₂-eq / kg material)
MATERIALS = {
    'aluminum': {'fraction': 0.40, 'ef': 11.5},      # 铝合金 40%
    'titanium': {'fraction': 0.15, 'ef': 30.0},      # 钛合金 15%
    'steel':    {'fraction': 0.30, 'ef': 6.1},       # 不锈钢 30%
    'cfrp':     {'fraction': 0.10, 'ef': 29.0},      # 碳纤维 10%
    'avionics': {'fraction': 0.05, 'ef': 60.0},      # 电子设备 5%
}

# 制造阶段单次排放 (kg CO₂-eq / 单次发射)
def calc_manufacturing_emissions():
    total = 0.0
    for mat_name, mat_data in MATERIALS.items():
        mat_mass = ROCKET_DRY_MASS_KG * mat_data['fraction']
        total += mat_mass * mat_data['ef']
    return total

MANUFACTURING_EMISSIONS_PER_LAUNCH = calc_manufacturing_emissions()

# 可复用性修正参数
N_REUSE = 15  # 典型可复用次数 (10-30)
REFURBISHMENT_FACTOR = 0.10  # 翻修系数 (5%-15%)

# 平均制造排放（摊销）(kg CO₂-eq / 单次发射)
MFG_EMISSIONS_AMORTIZED = (
    MANUFACTURING_EMISSIONS_PER_LAUNCH / N_REUSE +
    REFURBISHMENT_FACTOR * MANUFACTURING_EMISSIONS_PER_LAUNCH
)

# ========== 燃料燃烧阶段 ==========
# 选择 LOX/RP-1 为主要推进剂（应用最广泛）
FUEL_MASS_PER_LAUNCH_KG = 120_000  # kg (estimated for 150 ton payload)

# LOX/RP-1 燃烧排放因子 (kg CO₂-eq / kg fuel)
EF_FUEL_CO2 = 3.15  # CO₂ direct
EF_FUEL_BC = 1.0e-3  # Black Carbon (kg / kg fuel)
EF_FUEL_NOX = 4.0e-3  # NOₓ (kg / kg fuel)

# 平流层高度修正因子 (火箭特有)
# RFI (Radiative Forcing Index) for emissions at 11 km altitude
HEIGHT_CORRECTION_CO2 = 1.0  # CO₂ 无修正
HEIGHT_CORRECTION_BC = 7.0  # Black Carbon 高度修正 (5-10倍，取中值7)
HEIGHT_CORRECTION_NOX = 1.5  # NOₓ 高度修正

# GWP100 特征化因子 (kg CO₂-eq 等当量)
GWP_BC = 1200  # Black Carbon (900-2000, 取中值1200)
GWP_NOX = 310  # NOₓ (235-431, 取中值)

# 燃烧阶段总排放 (kg CO₂-eq / 单次发射)
COMBUSTION_EMISSIONS_PER_LAUNCH = (
    FUEL_MASS_PER_LAUNCH_KG * (
        EF_FUEL_CO2 * HEIGHT_CORRECTION_CO2 +
        EF_FUEL_BC * HEIGHT_CORRECTION_BC * GWP_BC +
        EF_FUEL_NOX * HEIGHT_CORRECTION_NOX * GWP_NOX
    )
)

# ========== 总 LCA 排放因子 ==========
# 每次发射的全生命周期排放 (kg CO₂-eq / launch)
TOTAL_EMISSIONS_PER_LAUNCH = MFG_EMISSIONS_AMORTIZED + COMBUSTION_EMISSIONS_PER_LAUNCH

# 单位载荷排放 (kg CO₂-eq / kg payload)
PAYLOAD_PER_LAUNCH_KG = 150_000  # kg (150 tons)
EMISSIONS_PER_KG_PAYLOAD = TOTAL_EMISSIONS_PER_LAUNCH / PAYLOAD_PER_LAUNCH_KG

# 单位质量排放 (kg CO₂-eq / ton)
EMISSIONS_PER_TON = EMISSIONS_PER_KG_PAYLOAD * 1000

# ==================== 离散化 x 值 ====================
DISCRETE_X = np.arange(0, 10000, 50)  

# ==================== 火箭成本迭代优化模型（从1.3.3.py改进） ====================
def solve_min_cost_for_time(T):
    """
    给定完成时间T(年)，计算最小成本（火箭+电梯混合方案）
    返回: (total_cost_USD, rocket_schedule_array)
    """
    mass_remaining = TOTAL_MASS_TONS
    total_cost = 0
    rocket_schedule = np.zeros(T, dtype=int)
    
    # A. 电梯 (基础设施，优先满载)
    elevator_mass = ELEVATOR_CAPACITY * T
    mass_remaining -= elevator_mass
    total_cost += elevator_mass * ELEVATOR_COST_PER_TON
    
    if mass_remaining <= 0:
        # 电梯足以完成任务
        real_cost = TOTAL_MASS_TONS * ELEVATOR_COST_PER_TON
        return real_cost, rocket_schedule

    # B. 火箭 (倒序填充，成本衰减模型)
    for t in range(T, 0, -1):
        if mass_remaining <= 0: 
            break
        
        # 制造成本衰减 (t年前的火箭成本更低)
        mfg_part = ROCKET_MFG_COST_PER_TON * ((1 - COST_DECAY_RATE) ** (t - 1))
        fuel_part = ROCKET_FUEL_COST_PER_TON
        current_year_cost = mfg_part + fuel_part
        
        # 当年最大运输能力
        max_mass = MAX_ROCKET_LAUNCHES_PER_YEAR * ROCKET_CAPACITY
        mass_to_transport = min(mass_remaining, max_mass)
        launches = int(np.ceil(mass_to_transport / ROCKET_CAPACITY))
        
        rocket_schedule[t-1] = launches
        total_cost += launches * ROCKET_CAPACITY * current_year_cost
        mass_remaining -= launches * ROCKET_CAPACITY
        
    if mass_remaining > 0: 
        return float('inf'), []
    
    return total_cost, rocket_schedule  

# ==================== 目标函数（基于 x 为每年发射次数） ====================
def compute_time(x):
    throughput = R_SES + x * Q_R
    if throughput <= 0:
        return np.inf
    return M / throughput


def compute_cost(x):
    """
    给定每年发射次数x，计算最小总成本（使用迭代优化模型）
    返回单位：百万美元
    """
    # 计算完成任务所需的最少时间
    throughput = R_SES + x * Q_R
    if throughput <= 0:
        return np.inf
    
    T = int(np.ceil(M / throughput))
    
    # 使用成本迭代优化模型求解最小成本
    cost_usd, _ = solve_min_cost_for_time(T)
    
    if cost_usd == float('inf'):
        return np.inf
    
    # 转换为百万美元
    return cost_usd / 1_000_000


def compute_emissions(x):
    """
    仅考虑火箭运输的环境影响（忽略电梯）
    基于单位载荷排放因子：EMISSIONS_PER_KG_PAYLOAD (kg CO2-eq/kg payload)
    返回单位：百万吨 CO2-eq
    """
    T = compute_time(x)
    if not np.isfinite(T):
        return np.inf
    
    # 火箭在T年内运送的总质量 (kg)
    rocket_mass_kg = x * T * PAYLOAD_PER_LAUNCH_KG
    
    # 总排放 (kg CO2-eq) = 质量 * 单位排放因子
    total_kg_CO2 = rocket_mass_kg * EMISSIONS_PER_KG_PAYLOAD
    
    # 转换为百万吨（Mt CO2）便于数值尺度
    return total_kg_CO2 / 1e9  # kg -> Mt


# ==================== 参数扫描 ====================
def scan_all(discrete_x=DISCRETE_X):
    xs = discrete_x
    times = np.array([compute_time(x) for x in xs])
    costs = np.array([compute_cost(x) for x in xs])
    ems = np.array([compute_emissions(x) for x in xs])
    return xs, times, costs, ems


# ==================== 三目标Pareto筛选 ====================
def pareto_nd_multiobj(objs_matrix):
    """返回非支配索引。objs_matrix shape = (N, M) N样本，M目标（越小越好）"""
    N = objs_matrix.shape[0]
    is_pareto = np.ones(N, dtype=bool)
    for i in range(N):
        if not is_pareto[i]:
            continue
        # 如果存在 j 使得 j 优于或等于 i 且至少一个严格优于，则 i 被支配
        dominated = np.any(np.all(objs_matrix <= objs_matrix[i], axis=1) & np.any(objs_matrix < objs_matrix[i], axis=1))
        if dominated:
            is_pareto[i] = False
    return np.where(is_pareto)[0]


# ==================== 三目标最优解筛选 ====================
def select_three_solutions(pareto_x, pareto_times, pareto_costs, pareto_ems):
    """
    在3维Pareto前沿中找到三种解：均衡、激进、经济
    方法：基于归一化欧几里得距离到理想原点(0,0,0)
    """
    # 获取Pareto点的目标值
    objs = np.vstack([pareto_times, pareto_costs, pareto_ems]).T
    
    # 归一化每个目标到 [0, 1]
    norm_objs = np.zeros_like(objs)
    for i in range(3):
        min_val = objs[:, i].min()
        max_val = objs[:, i].max()
        if max_val > min_val:
            norm_objs[:, i] = (objs[:, i] - min_val) / (max_val - min_val)
        else:
            norm_objs[:, i] = 0
    
    # 计算每个点到理想原点 (0,0,0) 的欧几里得距离
    distances = np.linalg.norm(norm_objs, axis=1)
    
    # 1. 均衡解：距离最近的点
    idx_balanced = np.argmin(distances)
    
    # 2. 激进解：在Pareto前沿中，在均衡点基础上时间更小的点
    # 策略：在距离最近的若干点中，选择时间最小的
    closest_indices = np.argsort(distances)[:max(1, len(distances)//8)]
    idx_fast = closest_indices[np.argmin(pareto_times[closest_indices])]
    
    # 3. 经济解：在Pareto前沿中，成本更小的点
    # 策略：在距离最近的若干点中，选择成本最小的
    idx_cheap = closest_indices[np.argmin(pareto_costs[closest_indices])]
    
    return idx_balanced, idx_fast, idx_cheap


# ==================== 主流程 ====================
if __name__ == '__main__':
    # 打印 LCA 参数汇总
    print('='*60)
    print('LCA Engineering Model Parameters (Based on Literature)')
    print('='*60)
    print(f'Rocket dry mass:                 {ROCKET_DRY_MASS_KG:,} kg')
    print(f'Reuse cycles:                    {N_REUSE}')
    print(f'Manufacturing (amortized):       {MFG_EMISSIONS_AMORTIZED:.1f} kg CO₂-eq/launch')
    print(f'Fuel mass per launch:            {FUEL_MASS_PER_LAUNCH_KG:,} kg')
    print(f'Combustion emissions:            {COMBUSTION_EMISSIONS_PER_LAUNCH:.1f} kg CO₂-eq/launch')
    print(f'Total per launch:                {TOTAL_EMISSIONS_PER_LAUNCH:.1f} kg CO₂-eq/launch')
    print(f'Per kg payload:                  {EMISSIONS_PER_KG_PAYLOAD:.4f} kg CO₂-eq/kg')
    print(f'Per ton payload:                 {EMISSIONS_PER_TON:.2f} kg CO₂-eq/ton')
    print('='*60)
    print()
    
    xs, times, costs, ems = scan_all()

    # 组合目标（小为好）： time (years), cost (million USD), emissions (Mt CO2)
    objs = np.vstack([times, costs, ems]).T

    pareto_idx = pareto_nd_multiobj(objs)

    pareto_x = xs[pareto_idx]
    pareto_times = times[pareto_idx]
    pareto_costs = costs[pareto_idx]
    pareto_ems = ems[pareto_idx]

    # 按时间排序
    order = np.argsort(pareto_times)
    pareto_x = pareto_x[order]
    pareto_times = pareto_times[order]
    pareto_costs = pareto_costs[order]
    pareto_ems = pareto_ems[order]
    
    # 找到三种解
    idx_balanced, idx_fast, idx_cheap = select_three_solutions(pareto_x, pareto_times, pareto_costs, pareto_ems)
    
    solutions = [
        {"label": "Faster (激进解)", "idx": idx_fast, "color": "#ff7f0e", "marker": "^"},
        {"label": "Balanced (均衡解)", "idx": idx_balanced, "color": "#2ca02c", "marker": "o"},
        {"label": "Cheaper (经济解)", "idx": idx_cheap, "color": "#1f77b4", "marker": "s"}
    ]

    # 保存图：3D 绘制 (Cost, Time, Emissions)
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    # 可行解 (灰色半透明点)
    ax.scatter(costs, times, ems, c='lightgray', alpha=0.4, s=20, label='Feasible Solutions')

    # Pareto 三目标点 (红色)
    ax.scatter(pareto_costs, pareto_times, pareto_ems, c='red', s=60, depthshade=True, label='Pareto Front (3D)')
    
    # 标注三种解
    for sol in solutions:
        idx = sol['idx']
        t_val = pareto_times[idx]
        c_val = pareto_costs[idx]
        e_val = pareto_ems[idx]
        
        # 绘制特殊点
        ax.scatter(c_val, t_val, e_val, c=sol['color'], marker=sol['marker'], s=200, edgecolors='black', linewidths=2, zorder=10)
        
        # 添加标注
        ax.text(c_val, t_val, e_val + 0.05, f"{sol['label']}\n({int(pareto_x[idx])} L/y)", 
               fontsize=10, ha='center', bbox=dict(boxstyle='round', facecolor=sol['color'], alpha=0.3))

    ax.set_xlabel('Cost (million USD)', fontsize=12)
    ax.set_ylabel('Time (years)', fontsize=12)
    ax.set_zlabel('Emissions (Mt CO2)', fontsize=12)
    ax.set_title('3D Pareto Front: Three-Objective Optimization\n(Cost vs Time vs Emissions)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left')
    plt.tight_layout()

    # CLI: 支持交互模式
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--interactive', action='store_true', help='Show interactive 3D plot (enable rotation)')
    args, _ = parser.parse_known_args()

    outpath = '/Users/hezhengze/Code/26美赛/latex论文/figures/pareto_3d_cost_time_emissions.png'
    
    # 始终保存图像
    plt.savefig(outpath, dpi=300, bbox_inches='tight')
    print(f'Saved 3D Pareto figure to {outpath}')
    
    # 仅当显式要求时才显示交互窗口
    if args.interactive:
        print('Interactive mode: a 3D window will open. Rotate with mouse; close window to continue.')
        try:
            plt.show()
        except Exception as e:
            print(f'Interactive display unavailable: {e}')
    else:
        plt.close()

    # 打印三种解的详细信息
    print('='*80)
    print('THREE OPTIMAL SOLUTIONS IN 3D PARETO FRONT')
    print('='*80)
    for sol in solutions:
        idx = sol['idx']
        print(f"\n{sol['label'].upper()}")
        print(f"  Launches per year:    {int(pareto_x[idx]):,} launches/year")
        print(f"  Project duration:     {pareto_times[idx]:,.2f} years")
        print(f"  Total cost:           ${pareto_costs[idx]:,.2f} million")
        print(f"  Total emissions:      {pareto_ems[idx]:,.6f} Mt CO₂-eq")
    print('='*80)

    # 打印部分Pareto解（最多20个）
    print('\n3-objective Pareto front (sample)')
    print('x (launches/yr), Time (yr), Cost (million USD), Emissions (Mt CO2)')
    print('-'*70)
    for i in range(min(20, len(pareto_x))):
        print(f"{int(pareto_x[i]):6d} , {pareto_times[i]:8.3f} , {pareto_costs[i]:10.3f} , {pareto_ems[i]:8.6f}")
    print('='*70)

    # 可选：将Pareto点保存为CSV
    try:
        import csv
        csv_path = '/Users/hezhengze/Code/26美赛/latex论文/figures/pareto_3obj.csv'
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['x_launches_per_year','time_years','cost_millionUSD','emissions_MtCO2'])
            for i in range(len(pareto_x)):
                writer.writerow([int(pareto_x[i]), f'{pareto_times[i]:.6f}', f'{pareto_costs[i]:.6f}', f'{pareto_ems[i]:.6f}'])
        print(f'Saved Pareto CSV to {csv_path}')
    except Exception as e:
        print('Failed to save CSV:', e)
