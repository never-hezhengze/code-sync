import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ==========================================
# 1. 参数设定 (保持不变)
# ==========================================
TOTAL_MASS_TONS = 10**8
ELEVATOR_CAPACITY = 5.37 * 10**5
ELEVATOR_COST_PER_KG = 100

ROCKET_CAPACITY = 150
ROCKET_MFG_COST_PER_KG = 400
ROCKET_FUEL_COST_PER_KG = 100
COST_DECAY_RATE = 0.05
MAX_ROCKET_LAUNCHES_PER_YEAR = 10000

# 单位换算
ELEVATOR_COST_PER_TON = ELEVATOR_COST_PER_KG * 1000
ROCKET_MFG_COST_PER_TON = ROCKET_MFG_COST_PER_KG * 1000
ROCKET_FUEL_COST_PER_TON = ROCKET_FUEL_COST_PER_KG * 1000

# ==========================================
# 2. 核心算法
# ==========================================
def solve_min_cost_for_time(T):
    mass_remaining = TOTAL_MASS_TONS
    total_cost = 0
    rocket_schedule = np.zeros(T, dtype=int)
    
    # A. 电梯 (基础设施，优先满载)
    elevator_mass = ELEVATOR_CAPACITY * T
    mass_remaining -= elevator_mass
    total_cost += elevator_mass * ELEVATOR_COST_PER_TON
    
    if mass_remaining <= 0:
        real_cost = TOTAL_MASS_TONS * ELEVATOR_COST_PER_TON
        return real_cost, rocket_schedule

    # B. 火箭 (倒序填充)
    for t in range(T, 0, -1):
        if mass_remaining <= 0: break
        
        # 成本计算 (制造衰减 + 燃料固定)
        mfg_part = ROCKET_MFG_COST_PER_TON * ((1 - COST_DECAY_RATE) ** (t - 1))
        fuel_part = ROCKET_FUEL_COST_PER_TON
        current_year_cost = mfg_part + fuel_part
        
        max_mass = MAX_ROCKET_LAUNCHES_PER_YEAR * ROCKET_CAPACITY
        mass_to_transport = min(mass_remaining, max_mass)
        launches = np.ceil(mass_to_transport / ROCKET_CAPACITY)
        
        rocket_schedule[t-1] = launches
        total_cost += launches * ROCKET_CAPACITY * current_year_cost
        mass_remaining -= launches * ROCKET_CAPACITY
        
    if mass_remaining > 0: return float('inf'), []
    return total_cost, rocket_schedule

# ==========================================
# 3. 数据生成与最优解筛选
# ==========================================
max_annual_capacity = ELEVATOR_CAPACITY + (MAX_ROCKET_LAUNCHES_PER_YEAR * ROCKET_CAPACITY)
min_years = int(np.ceil(TOTAL_MASS_TONS / max_annual_capacity))
max_years = int(np.ceil(TOTAL_MASS_TONS / ELEVATOR_CAPACITY))

results_time = []
results_cost = []
all_schedules = {} # 存储所有方案以便后续调用

print(f"搜索范围: {min_years} - {max_years} 年")

for t in range(min_years, max_years + 1):
    c, s = solve_min_cost_for_time(t)
    if c != float('inf'):
        results_time.append(t)
        results_cost.append(c / 10**12) # 万亿美元
        all_schedules[t] = s

# --- 寻找“最优区间”逻辑 (肘部法则) ---
times = np.array(results_time)
costs = np.array(results_cost)

# 归一化数据到 [0, 1] 区间，以便计算距离
norm_time = (times - times.min()) / (times.max() - times.min())
norm_cost = (costs - costs.min()) / (costs.max() - costs.min())

# 计算每个点到“理想原点 (MinTime, MinCost)”的欧几里得距离
# 注意：理想原点在归一化坐标系中是 (0, 0)
distances = np.sqrt(norm_time**2 + norm_cost**2)

# 1. 均衡解 (Balanced): 距离原点最近的点
idx_balanced = np.argmin(distances)

# 2. 激进解 (Faster): 均衡点向左偏移一定比例 (牺牲成本换时间)
# 偏移量取总数据长度的 5% 左右，防止越界
offset = max(1, len(times) // 8) 
idx_fast = max(0, idx_balanced - offset)

# 3. 经济解 (Cheaper): 均衡点向右偏移一定比例 (牺牲时间换成本)
idx_cheap = min(len(times) - 1, idx_balanced + offset)

# 提取三个解的具体数据
solutions = [
    {"label": "Faster", "idx": idx_fast, "color": "#ff7f0e", "marker": "^"},  # 橙色
    {"label": "Balanced", "idx": idx_balanced, "color": "#2ca02c", "marker": "o"}, # 绿色
    {"label": "Cheaper", "idx": idx_cheap, "color": "#1f77b4", "marker": "s"}   # 蓝色
]

# ==========================================
# 4. 可视化 (美化版)
# ==========================================
# 设置画布布局：上面是帕累托图，下面是三个发射计划子图
fig = plt.figure(figsize=(12, 12))
gs = gridspec.GridSpec(2, 1, height_ratios=[1.2, 1]) # 上图高一些

# ---------------------------
# 子图 1: 帕累托前沿与最优区间
# ---------------------------
ax1 = plt.subplot(gs[0])

# 绘制主曲线
ax1.plot(results_time, results_cost, linewidth=3, color='#555555', alpha=0.6, label='Pareto Frontier')

# 绘制“最优区间”背景带
range_start_t = results_time[idx_fast]
range_end_t = results_time[idx_cheap]
ax1.axvspan(range_start_t, range_end_t, color='#ffd700', alpha=0.15, label='Optimal Trade-off Zone')

# 标注三个特定解
for sol in solutions:
    t_val = results_time[sol['idx']]
    c_val = results_cost[sol['idx']]
    # 画点
    ax1.scatter(t_val, c_val, s=150, color=sol['color'], marker=sol['marker'], edgecolors='white', zorder=5)
    # 画文字
    ax1.annotate(f"{sol['label']}\n{t_val}y / \${c_val:.1f}T", 
                 xy=(t_val, c_val), 
                 xytext=(t_val, c_val + 1.5),
                 ha='center', fontsize=10, fontweight='bold',
                 arrowprops=dict(arrowstyle="->", color=sol['color']))

ax1.set_title(f"Pareto Optimization: Transport Cost vs. Time\n(Cost Model: Mfg \$400 -5%/yr + Fuel \$100 fixed)", fontsize=14, fontweight='bold')
ax1.set_ylabel("Total Cost (Trillion USD)", fontsize=12)
ax1.set_xlabel("Total Project Time (Years)", fontsize=12)
ax1.grid(True, linestyle='--', alpha=0.5)
ax1.legend(loc='upper right')

# ---------------------------
# 子图 2: 三个方案的发射频次对比
# ---------------------------
# 在下半部分创建3个子图，共享X轴
gs_bottom = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[1], wspace=0.1)

axes_sched = []
max_launches_display = 0

for i, sol in enumerate(solutions):
    ax = plt.subplot(gs_bottom[i])
    axes_sched.append(ax)
    
    t_val = results_time[sol['idx']]
    schedule = all_schedules[t_val]
    years = np.arange(1, t_val + 1)
    
    # 绘制面积图
    ax.fill_between(years, schedule, color=sol['color'], alpha=0.6, step='mid')
    ax.plot(years, schedule, color=sol['color'], linewidth=2, drawstyle='steps-mid')
    
    # 标注
    ax.set_title(f"Option: {sol['label']}\n(Duration: {t_val} Years)", fontsize=11, color=sol['color'], fontweight='bold')
    ax.set_xlabel("Year", fontsize=10)
    if i == 0:
        ax.set_ylabel("Rocket Launches / Year", fontsize=10)
    
    # 记录最大值用于统一Y轴
    if schedule.max() > max_launches_display:
        max_launches_display = schedule.max()
    
    # 只显示最后几十年的变化，或者全显示但高亮最后部分
    ax.set_xlim(0, t_val + 2)
    ax.grid(True, linestyle=':', alpha=0.5)

# 统一Y轴刻度
for ax in axes_sched:
    ax.set_ylim(0, max_launches_display * 1.1)
    # 隐藏非第一列的Y轴标签
    if ax != axes_sched[0]:
        ax.set_yticklabels([])

plt.tight_layout()
plt.show()

# ==========================================
# 5. 打印详细数据
# ==========================================
print("-" * 50)
print(f"{'Option':<10} | {'Time (Yrs)':<10} | {'Cost (Trillion)':<15} | {'Note'}")
print("-" * 50)
for sol in solutions:
    t_val = results_time[sol['idx']]
    c_val = results_cost[sol['idx']]
    print(f"{sol['label']:<10} | {t_val:<10} | ${c_val:.2f} {'':<5} | Index {sol['idx']}")
print("-" * 50)