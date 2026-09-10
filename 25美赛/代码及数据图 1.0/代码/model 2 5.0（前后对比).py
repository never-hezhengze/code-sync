import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# =======================
# 1. 原始模型参数设置
# =======================
# ---------- 生产者1（作物1） ----------
r_P1 = 2
K_P1 = 10000
alpha_P1_C1 = 0.0002
alpha_P1_C2 = 0.00015
alpha_P1_C3 = 0.0001
alpha_P1_W = 0.000001

# ---------- 生产者2（作物2） ----------
r_P2 = 2
K_P2 = 10000
alpha_P2_C1 = 0.0001
alpha_P2_C2 = 0.00015
alpha_P2_C3 = 0.0001
alpha_P2_W = 0.000001

# ---------- 杂草 ----------
r_W = 4
K_W = 7000
alpha_W_C1 = 0.00005
alpha_W_C2 = 0.00001
alpha_W_C3 = 0.00002
alpha_W_P1 = 0.00018
alpha_W_P2 = 0.00018
gamma_W = 0.00  # 除草剂导致死亡率

# ---------- 初级消费者1（草食动物1） ----------
r_C1 = 0.9
K_C1 = 800
beta_P1_C1 = 0.5
beta_P2_C1 = 0.4
beta_W_C1 = 0.3
delta_C1 = 0.1
gamma_C1 = 0.00  # 针对C1的杀虫剂死亡率

# ---------- 初级消费者2（草食动物2） ----------
r_C2 = 1.0
K_C2 = 800
beta_P1_C2 = 0.4
beta_P2_C2 = 0.5
beta_W_C2 = 0.2
delta_C2 = 0.12
gamma_C2 = 0.00  # 针对C2的杀虫剂死亡率

# ---------- 初级消费者3（草食动物3） ----------
r_C3 = 0.8
K_C3 = 800
beta_P1_C3 = 0.0
beta_P2_C3 = 0.0
beta_W_C3 = 0.5
delta_C3 = 0.11
gamma_C3 = 0.00  # 针对C3的杀虫剂死亡率

# ---------- 次级消费者1（捕食者1） ----------
r_S1 = 0.2
K_S1 = 100
eta_C1_S1 = 0.0002
eta_C2_S1 = 0.0002
eta_C3_S1 = 0.0002
mu_S1 = 0.09

# ---------- 次级消费者2（捕食者2） ----------
r_S2 = 0.2
K_S2 = 120
eta_C1_S2 = 0.0002
eta_C2_S2 = 0.0002
eta_C3_S2 = 0.0002
mu_S2 = 0.10


# =======================
# 2. 农药浓度模型
# =======================
def pesticide_concentration(t, peak_time, intensity, duration):
    """
    在给定时间点 t 下，返回农药浓度。
    - peak_time：达到峰值的时间
    - intensity：峰值强度
    - duration：从 peak_time 开始持续多久后衰减至 0
    这里用一个高斯型衰减来模拟。
    """
    if t < peak_time:
        return 0
    elif peak_time <= t <= peak_time + duration:
        exponent = -((t - peak_time) ** 2) / (2 * (duration / 2) ** 2)
        # 防止数值下溢：
        if exponent < -700:
            return 0
        return intensity * np.exp(exponent)
    else:
        return 0


# =======================
# 3. 原模型（8 个物种）
# =======================
def model_original(t, y):
    # y = [P1, P2, W, C1, C2, C3, S1, S2]
    P1, P2, W, C1, C2, C3, S1, S2 = y

    # 计算除草剂和杀虫剂浓度
    S_W = pesticide_concentration(t, peak_time=8, intensity=10000, duration=10)
    S_C1 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=10)
    S_C2 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=10)
    S_C3 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=10)

    # =========== 生产者1、2、杂草 ===========
    dP1dt = (r_P1 * P1 * (1 - P1 / K_P1)
             - alpha_P1_C1 * P1 * C1
             - alpha_P1_C2 * P1 * C2
             - alpha_P1_C3 * P1 * C3
             - alpha_P1_W * P1 * W)

    dP2dt = (r_P2 * P2 * (1 - P2 / K_P2)
             - alpha_P2_C1 * P2 * C1
             - alpha_P2_C2 * P2 * C2
             - alpha_P2_C3 * P2 * C3
             - alpha_P2_W * P2 * W)

    dWdt = (r_W * W * (1 - W / K_W)
            - alpha_W_C1 * W * C1
            - alpha_W_C2 * W * C2
            - gamma_W * S_W
            - alpha_W_P1 * W * P1 - alpha_W_P2 * W * P2
            )

    # =========== 初级消费者 C1, C2, C3 ===========
    dC1dt = (r_C1 * C1 * (1 - C1 / K_C1)
             + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W
             - delta_C1 * C1
             - gamma_C1 * S_C1
             - eta_C1_S1 * C1 * S1
             - eta_C1_S2 * C1 * S2)

    dC2dt = (r_C2 * C2 * (1 - C2 / K_C2)
             + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W
             - delta_C2 * C2
             - gamma_C2 * S_C2
             - eta_C2_S1 * C2 * S1
             - eta_C2_S2 * C2 * S2)

    dC3dt = (r_C3 * C3 * (1 - C3 / K_C3)
             + beta_P1_C3 * P1 + beta_P2_C3 * P2 + beta_W_C3 * W
             - delta_C3 * C3
             - gamma_C3 * S_C3
             - eta_C3_S1 * C3 * S1
             - eta_C3_S2 * C3 * S2)

    # =========== 次级消费者 S1, S2 ===========
    # 注意：原代码中只在 dS1dt 中写了对 C1 的捕食收益演示，实际上可以加上对 C2, C3 的捕食收益
    dS1dt = (r_S1 * S1 * (1 - S1 / K_S1)
             + eta_C1_S1 * C1 * S1
             + eta_C2_S1 * C2 * S1
             + eta_C3_S1 * C3 * S1
             - mu_S1 * S1)

    dS2dt = (r_S2 * S2 * (1 - S2 / K_S2)
             + eta_C1_S2 * C1 * S2
             + eta_C2_S2 * C2 * S2
             + eta_C3_S2 * C3 * S2
             - mu_S2 * S2)

    return [dP1dt, dP2dt, dWdt, dC1dt, dC2dt, dC3dt, dS1dt, dS2dt]


# =========================
# 4. 扩展模型 (10个物种)
#    + 新次级消费者S3
#    + 新三级消费者T1
# =========================
# 先定义一些新的参数（自行调整数值以观察差异）
r_S3 = 0.25  # 新的次级消费者 内禀增长率
K_S3 = 100  # 新的次级消费者 环境容量
mu_S3 = 0.08  # 新的次级消费者 自然死亡率

# 与 C1, C2, C3 的捕食效率
eta_C1_S3 = 0.0005
eta_C2_S3 = 0.00000
eta_C3_S3 = 0.0005

# 三级消费者 T1 (顶级捕食者)
r_T1 = 0.05
K_T1 = 50
mu_T1 = 0.12
# T1 捕食 S1, S2, S3 的效率
eta_S1_T1 = 0.0005
eta_S2_T1 = 0.0008
eta_S3_T1 = 0.0004


def model_extended(t, y):
    """
    扩展版：在原8个物种基础上，增加了 S3 (次级消费者3) 和 T1 (三级消费者)。
    y = [P1, P2, W, C1, C2, C3, S1, S2, S3, T1]
    """
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1 = y

    # 计算除草剂和杀虫剂浓度（保持和原模型一致，也可自行调整）
    S_W = pesticide_concentration(t, peak_time=8, intensity=10000, duration=3)
    S_C1 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=30)
    S_C2 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=30)
    S_C3 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=30)
    # 这里假设新加入的 S3, T1 不受既有杀虫剂直接影响，若想模拟，可以再加上 gamma_S3 * pesticide 等

    # =========== 生产者1、2、杂草 ===========
    dP1dt = (r_P1 * P1 * (1 - P1 / K_P1)
             - alpha_P1_C1 * P1 * C1
             - alpha_P1_C2 * P1 * C2
             - alpha_P1_C3 * P1 * C3
             - alpha_P1_W * P1 * W)

    dP2dt = (r_P2 * P2 * (1 - P2 / K_P2)
             - alpha_P2_C1 * P2 * C1
             - alpha_P2_C2 * P2 * C2
             - alpha_P2_C3 * P2 * C3
             - alpha_P2_W * P2 * W)

    dWdt = (r_W * W * (1 - W / K_W)
            - alpha_W_C1 * W * C1
            - alpha_W_C2 * W * C2
            - gamma_W * S_W
            - alpha_W_P1 * W * P1 - alpha_W_P2 * W * P2
            )

    # =========== 初级消费者 C1, C2, C3 ===========
    dC1dt = (r_C1 * C1 * (1 - C1 / K_C1)
             + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W
             - delta_C1 * C1
             - gamma_C1 * S_C1
             - eta_C1_S1 * C1 * S1
             - eta_C1_S2 * C1 * S2
             - eta_C1_S3 * C1 * S3)  # 还要考虑被新次级消费者S3捕食

    dC2dt = (r_C2 * C2 * (1 - C2 / K_C2)
             + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W
             - delta_C2 * C2
             - gamma_C2 * S_C2
             - eta_C2_S1 * C2 * S1
             - eta_C2_S2 * C2 * S2
             - eta_C2_S3 * C2 * S3)  # 被S3捕食

    dC3dt = (r_C3 * C3 * (1 - C3 / K_C3)
             + beta_P1_C3 * P1 + beta_P2_C3 * P2 + beta_W_C3 * W
             - delta_C3 * C3
             - gamma_C3 * S_C3
             - eta_C3_S1 * C3 * S1
             - eta_C3_S2 * C3 * S2
             - eta_C3_S3 * C3 * S3)  # 被S3捕食

    # =========== 次级消费者 S1, S2 (同原版) ===========
    dS1dt = (r_S1 * S1 * (1 - S1 / K_S1)
             + eta_C1_S1 * C1 * S1
             + eta_C2_S1 * C2 * S1
             + eta_C3_S1 * C3 * S1
             - mu_S1 * S1
             # 还可能被T1捕食
             - eta_S1_T1 * S1 * T1)

    dS2dt = (r_S2 * S2 * (1 - S2 / K_S2)
             + eta_C1_S2 * C1 * S2
             + eta_C2_S2 * C2 * S2
             + eta_C3_S2 * C3 * S2
             - mu_S2 * S2
             # 还可能被T1捕食
             - eta_S2_T1 * S2 * T1)

    # =========== 新的次级消费者 S3 ===========
    # 主要捕食 C1, C2, C3
    dS3dt = (r_S3 * S3 * (1 - S3 / K_S3)
             + eta_C1_S3 * C1 * S3
             + eta_C2_S3 * C2 * S3
             + eta_C3_S3 * C3 * S3
             - mu_S3 * S3
             # 还可能被T1捕食
             - eta_S3_T1 * S3 * T1)

    # =========== 新的三级消费者 T1 ===========
    # 主要捕食 S1, S2, S3
    dT1dt = (r_T1 * T1 * (1 - T1 / K_T1)
             + eta_S1_T1 * S1 * T1
             + eta_S2_T1 * S2 * T1
             + eta_S3_T1 * S3 * T1
             - mu_T1 * T1)

    return [dP1dt, dP2dt, dWdt,
            dC1dt, dC2dt, dC3dt,
            dS1dt, dS2dt, dS3dt, dT1dt]


# =======================
# 5. 求解 + 可视化
# =======================
def main():
    # --------- A. 原模型初始条件 (8维) ----------
    y0_original = [3,  # P1
                   3,  # P2
                   15000,  # W
                   300,  # C1
                   400,  # C2
                   300,  # C3
                   50,  # S1
                   30]  # S2

    # --------- B. 扩展模型初始条件 (10维) ----------
    # 在原基础上给新物种 S3, T1 一个初始值(可以是很小的值，表示刚刚回归/引入)
    y0_extended = [3,  # P1
                   3,  # P2
                   15000,  # W
                   300,  # C1
                   400,  # C2
                   300,  # C3
                   50,  # S1
                   30,  # S2
                   50,  # S3 (新次级消费者)
                   10]  # T1 (新三级消费者)

    # 时间区间
    t_span = (0, 20)
    # 希望输出的时间点
    t_eval = np.linspace(0, 20, 1000)

    # --------- C. 求解原模型 ---------
    sol_original = solve_ivp(model_original, t_span, y0_original, t_eval=t_eval, method='BDF')

    # --------- D. 求解扩展模型 ---------
    sol_extended = solve_ivp(model_extended, t_span, y0_extended, t_eval=t_eval, method='BDF')

    # 提取结果
    P1_o, P2_o, W_o, C1_o, C2_o, C3_o, S1_o, S2_o = sol_original.y
    # 扩展模型前 8 个与上面名称对应，第9、10个是S3和T1
    P1_e, P2_e, W_e, C1_e, C2_e, C3_e, S1_e, S2_e, S3_e, T1_e = sol_extended.y

    # =======================
    # 6. 前后对比绘图
    # =======================
    plt.figure(figsize=(12, 16))

    # ---- (1) 生产者 & 杂草 ----
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(sol_original.t, P1_o, 'g--', label="Crop1 (original)")
    ax1.plot(sol_original.t, P2_o, 'b--', label="Crop2 (original)")
    ax1.plot(sol_original.t, W_o, 'y--', label="Weed  (original)")

    ax1.plot(sol_extended.t, P1_e, 'g-', label="Crop1 (extended)")
    ax1.plot(sol_extended.t, P2_e, 'b-', label="Crop2 (extended)")
    ax1.plot(sol_extended.t, W_e, 'y-', label="Weed  (extended)")

    ax1.set_title("Producers and Weed Dynamics (Before vs After New Species)")
    ax1.set_xlabel("Time (days)")
    ax1.set_ylabel("Population")
    ax1.legend()

    # ---- (2) 初级消费者 C1, C2, C3 ----
    ax2 = plt.subplot(4, 1, 2)
    ax2.plot(sol_original.t, C1_o, 'c--', label="Herbivore1 (original)")
    ax2.plot(sol_original.t, C2_o, 'm--', label="Herbivore2 (original)")
    ax2.plot(sol_original.t, C3_o, 'r--', label="Herbivore3 (original)")

    ax2.plot(sol_extended.t, C1_e, 'c-', label="Herbivore1 (extended)")
    ax2.plot(sol_extended.t, C2_e, 'm-', label="Herbivore2 (extended)")
    ax2.plot(sol_extended.t, C3_e, 'r-', label="Herbivore3 (extended)")

    ax2.set_title("Primary Consumers (Before vs After)")
    ax2.set_xlabel("Time (days)")
    ax2.set_ylabel("Population")
    ax2.legend()

    # ---- (3) 次级消费者 S1, S2, 以及 新的 S3 ----
    ax3 = plt.subplot(4, 1, 3)
    ax3.plot(sol_original.t, S1_o, 'r--', label="Predator1 (original)")
    ax3.plot(sol_original.t, S2_o, 'k--', label="Predator2 (original)")

    ax3.plot(sol_extended.t, S1_e, 'r-', label="Predator1 (extended)")
    ax3.plot(sol_extended.t, S2_e, 'k-', label="Predator2 (extended)")

    # 新加入的S3只在extended中才有
    ax3.plot(sol_extended.t, S3_e, 'g-', label="Predator3 (new)")

    ax3.set_title("Secondary Consumers (Before vs After + New S3)")
    ax3.set_xlabel("Time (days)")
    ax3.set_ylabel("Population")
    ax3.legend()

    # ---- (4) 新的三级消费者 T1 (只在extended中才有)----
    ax4 = plt.subplot(4, 1, 4)
    ax4.plot(sol_extended.t, T1_e, 'm-', label="Tertiary Consumer (T1)")
    ax4.set_title("Tertiary Consumer (Newly Introduced)")
    ax4.set_xlabel("Time (days)")
    ax4.set_ylabel("Population")
    ax4.legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
