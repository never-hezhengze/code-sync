import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# 优化后的模型参数
# 生产者1（作物1）
r_P1 = 2  # 生长速率
K_P1 = 10000  # 环境容量
alpha_P1_C1 = 0.0002  # 初级消费者1的影响
alpha_P1_C2 = 0.00015  # 初级消费者2的影响
alpha_P1_C3 = 0.0001  # 初级消费者3的影响
alpha_P1_W = 0.000001  # 杂草对生产者1的影响

# 生产者2（作物2）
r_P2 = 2  # 生长速率
K_P2 = 10000  # 环境容量
alpha_P2_C1 = 0.0001  # 初级消费者1的影响
alpha_P2_C2 = 0.00015  # 初级消费者2的影响
alpha_P2_C3 = 0.0001  # 初级消费者3的影响
alpha_P2_W = 0.000001

# 杂草
r_W = 4  # 生长速率
K_W = 7000 # 环境容量
alpha_W_C1 = 0.00005  # 初级消费者1对杂草的影响
alpha_W_C2 = 0.00001 # 初级消费者2对杂草的影响
alpha_W_C3 = 0.00002 # 初级消费者2对杂草的影响
alpha_W_P1 = 0.00018  # 生产者1对杂草的影响
alpha_W_P2 = 0.00018  # 生产者2对杂草的影响
gamma_W = 0.99 # 除草剂导致的死亡率

# 初级消费者1（草食动物1）
r_C1 = 0.9  # 生长速率
K_C1 = 800  # 环境容量
beta_P1_C1 = 0.5  # 作物1的贡献
beta_P2_C1 = 0.4  # 作物2的贡献
beta_W_C1 = 0.3   # 杂草的贡献
delta_C1 = 0.1  # 自然死亡率
gamma_C1 = 0.90  # 杀虫剂导致的死亡率

# 初级消费者2（草食动物2）
r_C2 = 1.0  # 生长速率
K_C2 = 800  # 环境容量
beta_P1_C2 = 0.4  # 作物1的贡献
beta_P2_C2 = 0.5  # 作物2的贡献
beta_W_C2 = 0.2   # 杂草的贡献
delta_C2 = 0.12  # 自然死亡率
gamma_C2 = 0.90  # 杀虫剂导致的死亡率

# 初级消费者3（草食动物3）
r_C3 = 0.8  # 生长速率
K_C3 = 800  # 环境容量
beta_P1_C3 = 0.0  # 作物1的贡献
beta_P2_C3 = 0.0  # 作物2的贡献
beta_W_C3 = 0.5   # 杂草的贡献
delta_C3 = 0.11  # 自然死亡率
gamma_C3 = 0.10  # 杀虫剂导致的死亡率

# 次级消费者1（捕食者1）
r_S1 = 0.2  # 生长速率
K_S1 = 100  # 环境容量
eta_C1_S1 = 0.0002  # 捕食消费者1的效率
eta_C2_S1 = 0.0002
eta_C3_S1 = 0.0002
mu_S1 = 0.09 # 自然死亡率

# 次级消费者2（捕食者2）
r_S2 = 0.2  # 生长速率
K_S2 = 120  # 环境容量
eta_C1_S2 = 0.0002
eta_C2_S2 = 0.0002  # 捕食消费者2的效率
eta_C3_S2 = 0.0002
mu_S2 = 0.10  # 自然死亡率

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

# 定义周期性函数 k_1
def periodic_k1(t):
    t_mod = t % 12  # 获取时间在周期内的位置
    if 1 <= t_mod <= 3:
        return 1.2
    elif 4 <= t_mod <= 6:
        return 1.0
    elif 7 <= t_mod <= 9:
        return 0.8
    elif 10 <= t_mod <= 12:
        return 0.6
    else:
        return 1.0  # 默认值

# 模型函数
def model(t, y):
    P1, P2, W, C1, C2, C3 , S1, S2 = y

    # 计算除草剂和杀虫剂浓度
    S_W = pesticide_concentration(t, peak_time=8, intensity=3650, duration=3)  # 除草剂
    S_C1 = pesticide_concentration(t, peak_time=15, intensity=8000, duration=30)  # 针对消费者1的杀虫剂
    S_C2 = pesticide_concentration(t, peak_time=15, intensity=8000, duration=30)  # 针对消费者2的杀虫剂
    S_C3 = pesticide_concentration(t, peak_time=15, intensity=8000, duration=30)  # 针对消费者3的杀虫剂

    # 生产者动态
    k_1 = periodic_k1(t)  # 调用周期性函数
    dP1dt = (r_P1 * P1 * (1 - P1 / K_P1) - alpha_P1_C1 * P1 * C1 - alpha_P1_C2 * P1 * C2 - alpha_P1_C3 * P1 * C3 - alpha_P1_W * P1 * W) * k_1
    dP2dt = r_P2 * P2 * (1 - P2 / K_P2) - alpha_P2_C1 * P2 * C1 - alpha_P2_C2 * P2 * C2 - alpha_P2_C3 * P2 * C3 - alpha_P2_W * P2 * W
    dWdt = r_W * W * (1 - W / K_W) - alpha_W_C1 * W * C1 - alpha_W_C2 * W * C2 - gamma_W * S_W - alpha_W_P1 * W * P1 - alpha_W_P2 * W * P2

    # 初级消费者动态
    dC1dt = r_C1 * C1 * (1 - C1 / K_C1) + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W - delta_C1 * C1 - gamma_C1 * S_C1 - eta_C1_S1 * C1 * S1 - eta_C1_S2 * C1 * S2
    dC2dt = r_C2 * C2 * (1 - C2 / K_C2) + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W - delta_C2 * C2 - gamma_C2 * S_C2 - eta_C2_S1 * C2 * S1 - eta_C2_S2 * C2 * S2
    dC3dt = r_C3 * C3 * (1 - C3 / K_C3) + beta_P1_C3 * P1 + beta_P2_C3 * P2 + beta_W_C3 * W - delta_C3 * C3 - gamma_C3 * S_C3 - eta_C3_S1 * C3 * S1 - eta_C3_S2 * C3 * S2

    # 次级消费者动态
    dS1dt = r_S1 * S1 * (1 - S1 / K_S1) + eta_C1_S1 * C1 * S1 - mu_S1 * S1
    dS2dt = r_S2 * S2 * (1 - S2 / K_S2) + eta_C2_S2 * C2 * S2 - mu_S2 * S2

    return [dP1dt, dP2dt, dWdt, dC1dt, dC2dt, dC3dt, dS1dt, dS2dt]

# 初始种群数量
y0 = [3, 3, 15000, 300, 400, 300, 50, 30]  # 初始条件

# 时间范围
t = np.linspace(0, 30, 1000)  # 从0到200天，划分为1000个点

# 解微分方程
solution = solve_ivp(model, [0, 200], y0, t_eval=t, method='BDF')

# 提取结果
P1, P2, W, C1, C2, C3, S1, S2 = solution.y

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
plt.plot(t, C3, label="Herbivore 3", color='r')
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
