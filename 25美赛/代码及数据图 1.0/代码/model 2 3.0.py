import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

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
alpha_P2_W = 0.001  # 杂草对生产者2的影响

# 杂草
r_W = 0.8  # 生长速率
K_W = 15000  # 环境容量
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

# 物种A和B的参数
r_A = 0.5  # 物种A生长速率
K_A = 500  # 物种A环境容量
beta_W_A = 0.002  # 杂草对物种A的影响
beta_P1_A = 0.0015  # 作物1对物种A的贡献
beta_P2_A = 0.001  # 作物2对物种A的贡献
alpha_A_C1 = 0.003  # 物种A对消费者1的捕食效率

r_B = 0.4  # 物种B生长速率
K_B = 300  # 物种B环境容量
beta_C1_B = 0.004  # 消费者1对物种B的贡献
beta_C2_B = 0.003  # 消费者2对物种B的贡献
alpha_B_S1 = 0.005  # 物种B对捕食者1的贡献

# 模型函数
def model_with_species(t, y):
    P1, P2, W, C1, C2, S1, S2, A, B = y  # 包括物种A和B

    # 生产者动态
    dP1dt = r_P1 * P1 * (1 - P1 / K_P1) - alpha_P1_C1 * P1 * C1 - alpha_P1_C2 * P1 * C2 - alpha_P1_W * P1 * W
    dP2dt = r_P2 * P2 * (1 - P2 / K_P2) - alpha_P2_C1 * P2 * C1 - alpha_P2_C2 * P2 * C2 - alpha_P2_W * P2 * W
    dWdt = r_W * W * (1 - W / K_W) - alpha_A_C1 * W * C1 - alpha_A_C2 * W * C2 - gamma_W * W  # 使用物种A的影响

    # 初级消费者动态
    dC1dt = r_C1 * C1 * (1 - C1 / K_C1) + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W - delta_C1 * C1 - gamma_C1 * S1
    dC2dt = r_C2 * C2 * (1 - C2 / K_C2) + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W - delta_C2 * C2 - gamma_C2 * S2

    # 次级消费者动态
    dS1dt = r_S1 * S1 * (1 - S1 / K_S1) + eta_C1_S1 * C1 * S1 - mu_S1 * S1
    dS2dt = r_S2 * S2 * (1 - S2 / K_S2) + eta_C2_S2 * C2 * S2 - mu_S2 * S2

    # 物种A和B的动态
    dAdt = r_A * A * (1 - A / K_A) + beta_W_A * W + beta_P1_A * P1 + beta_P2_A * P2 - alpha_A_C1 * A * C1
    dBdt = r_B * B * (1 - B / K_B) + beta_C1_B * C1 + beta_C2_B * C2 - alpha_B_S1 * B * S1

    return [dP1dt, dP2dt, dWdt, dC1dt, dC2dt, dS1dt, dS2dt, dAdt, dBdt]

# 初始种群数量
y0 = [7000, 8000, 10000, 500, 600, 50, 30, 100, 50]  # [P1, P2, W, C1, C2, S1, S2, A, B]

# 时间范围
t = np.linspace(0, 200, 1000)

# 解微分方程
solution = solve_ivp(model_with_species, [0, 200], y0, t_eval=t, method='BDF')

# 提取结果
P1, P2, W, C1, C2, S1, S2, A, B = solution.y

# 绘制结果
plt.figure(figsize=(12, 15))

# 生产者和杂草
plt.subplot(4, 1, 1)
plt.plot(t, P1, label="Crop 1", color='g')
plt.plot(t, P2, label="Crop 2", color='b')
plt.plot(t, W, label="Weed", color='y')
plt.title("Producers and Weed Dynamics")
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

# 初级消费者
plt.subplot(4, 1, 2)
plt.plot(t, C1, label="Herbivore 1", color='c')
plt.plot(t, C2, label="Herbivore 2", color='m')
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

# 次级消费者
plt.subplot(4, 1, 3)
plt.plot(t, S1, label="Predator 1", color='r')
plt.plot(t, S2, label="Predator 2", color='k')
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

# 新物种
plt.subplot(4, 1, 4)
plt.plot(t, A, label="Species A", color='purple')
plt.plot(t, B, label="Species B", color='orange')
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend()

plt.tight_layout()
plt.show()
