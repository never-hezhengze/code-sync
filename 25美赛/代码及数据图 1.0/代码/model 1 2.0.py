import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# 模型的参数
# 生产者1（农作物1）
r_P1 = 0.1  # 生长速率
K_P1 = 500  # 环境容量
alpha_P1_C1 = 0.004  # 初级消费者1对生产者1的影响
alpha_P1_C2 = 0.003  # 初级消费者2对生产者1的影响
alpha_P1_W = 0.002  #杂草对生产者1的影响


# 生产者2（农作物2）
r_P2 = 0.12  # 生长速率
K_P2 = 600  # 环境容量
alpha_P2_C1 = 0.005  # 初级消费者1对生产者2的影响
alpha_P2_C2 = 0.004  # 初级消费者2对生产者2的影响
alpha_P2_W = 0.001

# 杂草
r_W = 0.08  # 生长速率
K_W = 300  # 环境容量
alpha_W_C1 = 0.000  # 初级消费者1对杂草的影响
alpha_W_C2 = 0.002  # 初级消费者2对杂草的影响
alpha_W_P1 = 0.002  #生产者1对杂草的影响
alpha_W_P2 = 0.003  #生产者2对杂草的影响
gamma_W=0.1 #除草剂影响的死亡率
S_W=

# 初级消费者1（草食动物1）
r_C1 = 0.2  # 生长速率
K_C1 = 200  # 环境容量
beta_P1_C1 = 0.05  # 农作物1对消费者1的贡献
beta_P2_C1 = 0.04  # 农作物2对消费者1的贡献
beta_W_C1 = 0.03   # 杂草对消费者1的贡献
delta_C1 = 0.1  # 自然死亡率
gamma_C1 = 0.05  # 杀虫剂影响的死亡率
S_C1 =

# 初级消费者2（草食动物2）
r_C2 = 0.25  # 生长速率
K_C2 = 250  # 环境容量
beta_P1_C2 = 0.04  # 农作物1对消费者2的贡献
beta_P2_C2 = 0.05  # 农作物2对消费者2的贡献
beta_W_C2 = 0.02   # 杂草对消费者2的贡献
delta_C2 = 0.12  # 自然死亡率
gamma_C2 = 0.05  # 杀虫剂影响的死亡率
S_C2 =

# 次级消费者1（捕食者1）
r_S1 = 0.15  # 生长速率
K_S1 = 100  # 环境容量
eta_C1_S1 = 0.1  # 捕食者1对消费者1的捕食效率
mu_S1 = 0.05  # 自然死亡率

# 次级消费者2（捕食者2）
r_S2 = 0.18  # 生长速率
K_S2 = 120  # 环境容量
eta_C2_S2 = 0.1  # 捕食者2对消费者2的捕食效率
mu_S2 = 0.06  # 自然死亡率

# 模型函数
def model(y, t):
    P1, P2, W, C1, C2, S1, S2 = y

    # 生产者动态
    dP1dt = r_P1 * P1 * (1 - P1 / K_P1) - alpha_P1_C1 * P1 * C1 - alpha_P1_C2 * P1 * C2 - alpha_P1_W * P1 * W
    dP2dt = r_P2 * P2 * (1 - P2 / K_P2) - alpha_P2_C1 * P2 * C1 - alpha_P2_C2 * P2 * C2 - alpha_P2_W * P2 * W
    dWdt = r_W * W * (1 - W / K_W) - alpha_W_C1 * W * C1 - alpha_W_C2 * W * C2 - alpha_W_P1 * W * P1 - alpha_W_C2 * W * P2 - gamma_W * S_W

    # 初级消费者动态
    dC1dt = r_C1 * C1 * (1 - C1 / K_C1) + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W - delta_C1 * C1 - gamma_C1 * S_C1 - eta_C1_S1 * C1 * S1
    dC2dt = r_C2 * C2 * (1 - C2 / K_C2) + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W - delta_C2 * C2 - gamma_C2 * S_C2 - eta_C2_S2 * C2 * S2

    # 次级消费者动态
    dS1dt = r_S1 * S1 * (1 - S1 / K_S1) + eta_C1_S1 * C1 * S1 - mu_S1 * S1
    dS2dt = r_S2 * S2 * (1 - S2 / K_S2) + eta_C2_S2 * C2 * S2 - mu_S2 * S2

    return [dP1dt, dP2dt, dWdt, dC1dt, dC2dt, dS1dt, dS2dt]

# 初始种群数量
P1_0 = 100  # 农作物1的初始种群
P2_0 = 80   # 农作物2的初始种群
W_0 = 50    # 杂草的初始种群
C1_0 = 40   # 草食动物1的初始种群
C2_0 = 30   # 草食动物2的初始种群
S1_0 = 20   # 捕食者1的初始种群
S2_0 = 15   # 捕食者2的初始种群
y0 = [P1_0, P2_0, W_0, C1_0, C2_0, S1_0, S2_0]  # 初始条件

# 时间范围
t = np.linspace(0, 200, 1000)  # 从0到200天，划分为1000个点

# 解微分方程
solution = odeint(model, y0, t)

# 提取结果
P1, P2, W, C1, C2, S1, S2 = solution.T

# 绘制结果
plt.figure(figsize=(12, 12))

# 绘制生产者和杂草的动态
plt.subplot(3, 1, 1)
plt.plot(t, P1, label="农作物1", color='g', linewidth=2)
plt.plot(t, P2, label="农作物2", color='b', linewidth=2)
plt.plot(t, W, label="杂草", color='y', linewidth=2)
plt.title("生产者、杂草和消费者的种群动态")
plt.xlabel("时间（天）")
plt.ylabel("种群数量")
plt.legend(loc='best')

# 绘制初级消费者的动态
plt.subplot(3, 1, 2)
plt.plot(t, C1, label="草食动物1", color='c', linewidth=2)
plt.plot(t, C2, label="草食动物2", color='m', linewidth=2)
plt.xlabel("时间（天）")
plt.ylabel("种群数量")
plt.legend(loc='best')

# 绘制次级消费者的动态
plt.subplot(3, 1, 3)
plt.plot(t, S1, label="捕食者1", color='r', linewidth=2)
plt.plot(t, S2, label="捕食者2", color='k', linewidth=2)
plt.xlabel("时间（天）")
plt.ylabel("种群数量")
plt.legend(loc='best')

# 调整布局以防止重叠
plt.tight_layout()

# 显示图像
plt.show()
