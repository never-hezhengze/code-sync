import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# 优化后的模型参数
# 生产者1（作物1）
r_P1 = 0.6  # 生长速率
K_P1 = 10000  # 环境容量
alpha_P1_C1 = 0.002  # 初级消费者1的影响
alpha_P1_C2 = 0.0015  # 初级消费者2的影响
alpha_P1_W = 0.001  # 杂草对生产者1的影响

# 生产者2（作物2）
r_P2 = 0.6  # 生长速率
K_P2 = 10000  # 环境容量
alpha_P2_C1 = 0.002  # 初级消费者1的影响
alpha_P2_C2 = 0.0015  # 初级消费者2的影响
alpha_P2_W = 0.001

# 杂草
r_W = 0.8  # 生长速率
K_W = 15000  # 环境容量
alpha_W_C1 = 0.0005  # 初级消费者1对杂草的影响
alpha_W_C2 = 0.001  # 初级消费者2对杂草的影响
alpha_W_P1 = 0.001  # 生产者1对杂草的影响
alpha_W_P2 = 0.001  # 生产者2对杂草的影响
gamma_W = 0.01  # 除草剂导致的死亡率

# 初级消费者1（草食动物1）
r_C1 = 0.2  # 生长速率
K_C1 = 800  # 环境容量
beta_P1_C1 = 0.05  # 作物1的贡献
beta_P2_C1 = 0.04  # 作物2的贡献
beta_W_C1 = 0.03   # 杂草的贡献
delta_C1 = 0.1  # 自然死亡率
gamma_C1 = 0.01  # 杀虫剂导致的死亡率

# 初级消费者2（草食动物2）
r_C2 = 0.2  # 生长速率
K_C2 = 800  # 环境容量
beta_P1_C2 = 0.04  # 作物1的贡献
beta_P2_C2 = 0.05  # 作物2的贡献
beta_W_C2 = 0.02   # 杂草的贡献
delta_C2 = 0.12  # 自然死亡率
gamma_C2 = 0.01  # 杀虫剂导致的死亡率

# 次级消费者1（捕食者1）
r_S1 = 0.05  # 生长速率
K_S1 = 100  # 环境容量
eta_C1_S1 = 0.02  # 捕食消费者1的效率
mu_S1 = 0.07  # 自然死亡率

# 次级消费者2（捕食者2）
r_S2 = 0.05  # 生长速率
K_S2 = 120  # 环境容量
eta_C2_S2 = 0.02  # 捕食消费者2的效率
mu_S2 = 0.08  # 自然死亡率

# 定义随时间变化的除草剂和杀虫剂浓度函数
def pesticide_concentration(t, peak_time, intensity, duration):
    if t < peak_time:
        return 0  # 峰值之前浓度为零
    elif peak_time <= t <= peak_time + duration:
        exponent = -((t - peak_time) ** 2) / (2 * (duration / 2) ** 2)
        if exponent < -700:  # 防止溢出
            return 0
        return intensity * np.exp(exponent)
    else:
        return 0

# 模型函数
def model(t, y):
    P1, P2, W, C1, C2, S1, S2 = y

    # 计算除草剂和杀虫剂浓度
    S_W = pesticide_concentration(t, peak_time=50, intensity=1.0, duration=10)  # 除草剂
    S_C1 = pesticide_concentration(t, peak_time=70, intensity=0.8, duration=15)  # 针对消费者1的杀虫剂
    S_C2 = pesticide_concentration(t, peak_time=90, intensity=0.9, duration=12)  # 针对消费者2的杀虫剂

    # 生产者动态
    dP1dt = r_P1 * P1 * (1 - P1 / K_P1) - alpha_P1_C1 * P1 * C1 - alpha_P1_C2 * P1 * C2 - alpha_P1_W * P1 * W
    dP2dt = r_P2 * P2 * (1 - P2 / K_P2) - alpha_P2_C1 * P2 * C1 - alpha_P2_C2 * P2 * C2 - alpha_P2_W * P2 * W
    dWdt = r_W * W * (1 - W / K_W) - alpha_W_C1 * W * C1 - alpha_W_C2 * W * C2 - gamma_W * S_W

    # 初级消费者动态
    dC1dt = r_C1 * C1 * (1 - C1 / K_C1) + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W - delta_C1 * C1 - gamma_C1 * S_C1 - eta_C1_S1 * C1 * S1
    dC2dt = r_C2 * C2 * (1 - C2 / K_C2) + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W - delta_C2 * C2 - gamma_C2 * S_C2 - eta_C2_S2 * C2 * S2

    # 次级消费者动态
    dS1dt = r_S1 * S1 * (1 - S1 / K_S1) + eta_C1_S1 * C1 * S1 - mu_S1 * S1
    dS2dt = r_S2 * S2 * (1 - S2 / K_S2) + eta_C2_S2 * C2 * S2 - mu_S2 * S2

    return [dP1dt, dP2dt, dWdt, dC1dt, dC2dt, dS1dt, dS2dt]

# 初始种群数量
y0 = [7000, 8000, 10000, 500, 600, 50, 30]  # 初始条件

# 时间范围
t = np.linspace(0, 200, 1000)  # 从0到200天，划分为1000个点

# 解微分方程
solution = solve_ivp(model, [0, 200], y0, t_eval=t, method='BDF')

# 提取结果
P1, P2, W, C1, C2, S1, S2 = solution.y

# 绘制结果
plt.figure(figsize=(12, 12))

# 生产者和杂草
plt.subplot(3, 1, 1)
plt.plot(t, P1, label="Crop 1", color='g')
plt.plot(t, P2, label="Crop 2", color='b')
plt.plot(t, W, label="Weed", color='y')
plt.title("Producers and Weed Dynamics")
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

# 初级消费者
plt.subplot(3, 1, 2)
plt.plot(t, C1, label="Herbivore 1", color='c')
plt.plot(t, C2, label="Herbivore 2", color='m')
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

# 次级消费者
plt.subplot(3, 1, 3)
plt.plot(t, S1, label="Predator 1", color='r')
plt.plot(t, S2, label="Predator 2", color='k')
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

plt.tight_layout()
plt.show()
