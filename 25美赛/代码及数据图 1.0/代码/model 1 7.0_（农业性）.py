import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# 模型参数定义
# 生产者、杂草、消费者的模型参数，包括增长率、环境容量和交互系数。
r_P1, r_P2, r_W = 2, 2, 4
K_P1, K_P2, K_W = 10000, 10000, 7000
alpha_P1_C1, alpha_P1_C2, alpha_P1_C3 = 0.0002, 0.00015, 0.0001
alpha_P2_C1, alpha_P2_C2, alpha_P2_C3 = 0.0001, 0.00015, 0.0001
alpha_P1_W, alpha_P2_W = 0.000001, 0.000001
alpha_W_P1, alpha_W_P2,= 0.00018, 0.00018
alpha_W_C1, alpha_W_C2, alpha_W_C3 = 0.00005, 0.00001, 0.00002
gamma_W = 0.0
r_C1, r_C2, r_C3 = 0.9, 1.0, 0.8
K_C1, K_C2, K_C3 = 800, 800, 800
beta_P1_C1, beta_P2_C1, beta_W_C1 = 0.5, 0.4, 0.3
beta_P1_C2, beta_P2_C2, beta_W_C2 = 0.4, 0.5, 0.2
beta_P1_C3, beta_P2_C3, beta_W_C3 = 0.0, 0.0, 0.5
delta_C1, delta_C2, delta_C3 = 0.1, 0.12, 0.11
gamma_C1, gamma_C2, gamma_C3 = 0.0, 0.0, 0.0
r_S1, r_S2 = 0.2, 0.2
K_S1, K_S2 = 100, 120
eta_C1_S1, eta_C2_S1, eta_C3_S1 = 0.0002, 0.0002, 0.0002
eta_C1_S2, eta_C2_S2, eta_C3_S2 = 0.0002, 0.0002, 0.0002
mu_S1, mu_S2 = 0.09, 0.10

# 收割时间点及影响因子
harvest_time = 10  # 收割时间点（天）
harvest_factor = 0.3  # 收割后作物数量变为原来的 0.5

# 定义模型函数：描述种群动态的微分方程
def model(t, y):
    P1, P2, W, C1, C2, C3, S1, S2 = y

    # 作物和杂草动态
    dP1dt = r_P1 * P1 * (1 - P1 / K_P1) - alpha_P1_C1 * P1 * C1 - alpha_P1_C2 * P1 * C2 - alpha_P1_C3 * P1 * C3 - alpha_P1_W * P1 * W
    dP2dt = r_P2 * P2 * (1 - P2 / K_P2) - alpha_P2_C1 * P2 * C1 - alpha_P2_C2 * P2 * C2 - alpha_P2_C3 * P2 * C3 - alpha_P2_W * P2 * W
    dWdt = r_W * W * (1 - W / K_W) - alpha_W_C1 * W * C1 - alpha_W_C2 * W * C2 - alpha_W_P1 * W * P1 - alpha_W_P2 * W * P2

    # 初级消费者动态
    dC1dt = r_C1 * C1 * (1 - C1 / K_C1) + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W - delta_C1 * C1
    dC2dt = r_C2 * C2 * (1 - C2 / K_C2) + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W - delta_C2 * C2
    dC3dt = r_C3 * C3 * (1 - C3 / K_C3) + beta_P1_C3 * P1 + beta_P2_C3 * P2 + beta_W_C3 * W - delta_C3 * C3

    # 次级消费者动态
    dS1dt = r_S1 * S1 * (1 - S1 / K_S1) + eta_C1_S1 * C1 * S1 - mu_S1 * S1
    dS2dt = r_S2 * S2 * (1 - S2 / K_S2) + eta_C2_S2 * C2 * S2 - mu_S2 * S2

    return [dP1dt, dP2dt, dWdt, dC1dt, dC2dt, dC3dt, dS1dt, dS2dt]

# 定义事件函数：检测收割时间点
def harvest_event(t, y):
    return t - harvest_time  # 触发收割事件

harvest_event.terminal = True  # 收割事件触发时停止积分
harvest_event.direction = 0  # 无方向限制

# 初始种群数量
y0 = [3, 3, 15000, 300, 400, 300, 50, 30]

# 时间范围
t_span = [0, 20]  # 初始模拟时间范围为 0 到 20 天

# 第一步：积分到收割时间点
solution_pre_harvest = solve_ivp(
    model, t_span, y0, t_eval=np.linspace(0, harvest_time, 500), events=harvest_event, method='BDF'
)

# 收割前的解
t_values_pre = solution_pre_harvest.t
y_values_pre = solution_pre_harvest.y

# 收割时调整种群数量
y_post_harvest = y_values_pre[:, -1]  # 收割前的最后一个状态
y_post_harvest[0] *= harvest_factor  # 调整作物1数量
y_post_harvest[1] *= harvest_factor  # 调整作物2数量

# 第二步：继续积分收割后的状态
solution_post_harvest = solve_ivp(
    model, [harvest_time, 20], y_post_harvest, t_eval=np.linspace(harvest_time, 20, 500), method='BDF'
)

# 合并解
t_values = np.concatenate((t_values_pre, solution_post_harvest.t))
y_values = np.concatenate((y_values_pre, solution_post_harvest.y), axis=1)

# 提取各变量的动态
P1, P2, W, C1, C2, C3, S1, S2 = y_values

# 绘制结果
plt.figure(figsize=(12, 12))

# 作物和杂草动态
plt.subplot(3, 1, 1)
plt.plot(t_values, P1, label="Crop 1", color='g')
plt.plot(t_values, P2, label="Crop 2", color='b')
plt.plot(t_values, W, label="Weed", color='y')
plt.axvline(x=harvest_time, color='red', linestyle='--', label='Harvest Time')  # 标记收割时间点
plt.title("Producers and Weed Dynamics")
plt.xlabel("Time (months)")  # x 轴标签
plt.ylabel("Population")  # y 轴标签
plt.legend()

# 初级消费者动态
plt.subplot(3, 1, 2)
plt.plot(t_values, C1, label="Herbivore 1", color='c')
plt.plot(t_values, C2, label="Herbivore 2", color='m')
plt.plot(t_values, C3, label="Herbivore 3", color='r')
plt.xlabel("Time (months)")  # x 轴标签
plt.ylabel("Population")  # y 轴标签
plt.legend()

# 次级消费者动态
plt.subplot(3, 1, 3)
plt.plot(t_values, S1, label="Predator 1", color='r')
plt.plot(t_values, S2, label="Predator 2", color='k')
plt.xlabel("Time (months)")  # x 轴标签
plt.ylabel("Population")  # y 轴标签
plt.legend()

plt.tight_layout()
plt.show()
