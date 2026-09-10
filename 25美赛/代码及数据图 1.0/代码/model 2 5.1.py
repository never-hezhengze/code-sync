import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# =============================
# 1. 更新后的生态系统参数
# =============================

# ---------- 生产者1（作物1） ----------
r_P1 = 2
K_P1 = 10000
alpha_P1_C1 = 0.0002
alpha_P1_C2 = 0.00015
alpha_P1_C3 = 0.0001
alpha_P1_W  = 0.000001

# ---------- 生产者2（作物2） ----------
r_P2 = 2
K_P2 = 10000
alpha_P2_C1 = 0.0001
alpha_P2_C2 = 0.00015
alpha_P2_C3 = 0.0001
alpha_P2_W  = 0.000001

# ---------- 杂草 ----------
r_W = 4
K_W = 7000
alpha_W_C1 = 0.00005
alpha_W_C2 = 0.00001
alpha_W_C3 = 0.00002
alpha_W_P1 = 0.00018
alpha_W_P2 = 0.00018
# 你将其改为 0.0，表示“除草剂导致死亡率”无效
gamma_W = 0.90
gamma1_W = 0.99
gamma2_W = 0.99
gamma3_W = 0.99


# ---------- 初级消费者1（草食动物1） ----------
r_C1 = 0.9
K_C1 = 800
beta_P1_C1 = 0.5
beta_P2_C1 = 0.4
beta_W_C1  = 0.3
delta_C1 = 0.1
# 改为 0.0，表示“杀虫剂导致死亡率”对 C1 无效
gamma_C1 = 0.90

# ---------- 初级消费者2（草食动物2） ----------
r_C2 = 1.0
K_C2 = 800
beta_P1_C2 = 0.4
beta_P2_C2 = 0.5
beta_W_C2  = 0.2
delta_C2 = 0.12
gamma_C2 = 0.80

# ---------- 初级消费者3（草食动物3） ----------
r_C3 = 0.8
K_C3 = 800
beta_P1_C3 = 0.0
beta_P2_C3 = 0.0
beta_W_C3  = 0.5
delta_C3 = 0.11
gamma_C3 = 0.10

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

# ---------- 新的次级消费者3（捕食者3） ----------
r_S3     = 0.25
K_S3     = 100
mu_S3    = 0.08
eta_C1_S3 = 0.0005   # 对 C1 的捕食效率
eta_C2_S3 = 0.0000   # 对 C2 的捕食效率（设为0表示不捕食C2）
eta_C3_S3 = 0.0005   # 对 C3 的捕食效率

# ---------- 新的三级消费者 T1 (顶级捕食者) ----------
r_T1     = 0.05
K_T1     = 50
mu_T1    = 0.12
eta_S1_T1 = 0.0005   # T1 捕食 S1 的效率
eta_S2_T1 = 0.0008   # T1 捕食 S2 的效率
eta_S3_T1 = 0.0004   # T1 捕食 S3 的效率

# ==========================
# 2. 农药浓度函数(保留即可)
#    由于 gamma_* 都为 0, 实际影响为0
# ==========================
def pesticide_concentration(t, peak_time, intensity, duration):
    """在给定时间 t 下，返回农药浓度（高斯脉冲）。"""
    if t < peak_time:
        return 0
    elif peak_time <= t <= peak_time + duration:
        exponent = -((t - peak_time) ** 2) / (2 * (duration / 2) ** 2)
        if exponent < -700:
            return 0
        return intensity * np.exp(exponent)
    else:
        return 0

# ==============================
# 3. 扩展后模型（10个物种）
# ==============================
def model_extended(t, y):
    """
    y = [P1, P2, W, C1, C2, C3, S1, S2, S3, T1]
    """
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1 = y

    # 计算农药浓度（你将 gamma_* 全部置0，因此这里计算不会起作用，但可保留）
    S_W  = pesticide_concentration(t, peak_time=8,  intensity=10000, duration=3)
    S1_W = pesticide_concentration(t, peak_time=12, intensity=10000, duration=3)  # 除草剂2
    S2_W = pesticide_concentration(t, peak_time=16, intensity=10000, duration=3)  # 除草剂2
    S3_W = pesticide_concentration(t, peak_time=20, intensity=10000, duration=3)  # 除草剂2
    S_C1 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=30)
    S_C2 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=30)
    S_C3 = pesticide_concentration(t, peak_time=15, intensity=10000, duration=30)

    # =========== 生产者1、2、杂草 ===========
    dP1dt = (r_P1 * P1 * (1 - P1 / K_P1)
             - alpha_P1_C1 * P1 * C1
             - alpha_P1_C2 * P1 * C2
             - alpha_P1_C3 * P1 * C3
             - alpha_P1_W  * P1 * W)

    dP2dt = (r_P2 * P2 * (1 - P2 / K_P2)
             - alpha_P2_C1 * P2 * C1
             - alpha_P2_C2 * P2 * C2
             - alpha_P2_C3 * P2 * C3
             - alpha_P2_W  * P2 * W)

    dWdt = (r_W * W * (1 - W / K_W)
            - alpha_W_C1 * W * C1
            - alpha_W_C2 * W * C2
            - gamma_W     * S_W
            - gamma1_W * S1_W
            - gamma2_W * S2_W
            - gamma3_W * S3_W
            )
    # gamma_W=0 => 此项为0

    # =========== 初级消费者 C1, C2, C3 ===========
    dC1dt = (r_C1 * C1 * (1 - C1 / K_C1)
             + beta_P1_C1 * P1 + beta_P2_C1 * P2 + beta_W_C1 * W
             - delta_C1 * C1
             - gamma_C1 * S_C1   # gamma_C1=0 => 无效
             - eta_C1_S1 * C1 * S1
             - eta_C1_S2 * C1 * S2
             - eta_C1_S3 * C1 * S3)

    dC2dt = (r_C2 * C2 * (1 - C2 / K_C2)
             + beta_P1_C2 * P1 + beta_P2_C2 * P2 + beta_W_C2 * W
             - delta_C2 * C2
             - gamma_C2 * S_C2   # gamma_C2=0 => 无效
             - eta_C2_S1 * C2 * S1
             - eta_C2_S2 * C2 * S2
             - eta_C2_S3 * C2 * S3)

    dC3dt = (r_C3 * C3 * (1 - C3 / K_C3)
             + beta_P1_C3 * P1 + beta_P2_C3 * P2 + beta_W_C3 * W
             - delta_C3 * C3
             - gamma_C3 * S_C3   # gamma_C3=0 => 无效
             - eta_C3_S1 * C3 * S1
             - eta_C3_S2 * C3 * S2
             - eta_C3_S3 * C3 * S3)

    # =========== 次级消费者 S1, S2, S3 ===========
    dS1dt = (r_S1 * S1 * (1 - S1 / K_S1)
             + eta_C1_S1 * C1 * S1
             + eta_C2_S1 * C2 * S1
             + eta_C3_S1 * C3 * S1
             - mu_S1 * S1
             - eta_S1_T1 * S1 * T1)

    dS2dt = (r_S2 * S2 * (1 - S2 / K_S2)
             + eta_C1_S2 * C1 * S2
             + eta_C2_S2 * C2 * S2
             + eta_C3_S2 * C3 * S2
             - mu_S2 * S2
             - eta_S2_T1 * S2 * T1)

    dS3dt = (r_S3 * S3 * (1 - S3 / K_S3)
             + eta_C1_S3 * C1 * S3
             + eta_C2_S3 * C2 * S3
             + eta_C3_S3 * C3 * S3
             - mu_S3 * S3
             - eta_S3_T1 * S3 * T1)

    # =========== 三级消费者 T1 ===========
    dT1dt = (r_T1 * T1 * (1 - T1 / K_T1)
             + eta_S1_T1 * S1 * T1
             + eta_S2_T1 * S2 * T1
             + eta_S3_T1 * S3 * T1
             - mu_T1 * T1)

    # 将 10 个方程的导数打包返回
    return [dP1dt, dP2dt, dWdt,
            dC1dt, dC2dt, dC3dt,
            dS1dt, dS2dt, dS3dt, dT1dt]

# ==========================
# 4. 主函数：求解 + 绘图
# ==========================
def main():
    # 10维初始值：P1, P2, W, C1, C2, C3, S1, S2, S3, T1
    y0 = [
        3,       # P1
        3,       # P2
        15000,   # W
        300,     # C1
        400,     # C2
        300,     # C3
        50,      # S1
        30,      # S2
        50,      # S3 (新次级消费者)
        10,      # T1 (新三级消费者)
    ]

    # 时间区间与采样
    t_span = (0, 20)
    t_eval = np.linspace(0, 20, 1000)

    # 求解扩展模型
    solution = solve_ivp(model_extended, t_span, y0, t_eval=t_eval, method='BDF')
    # 拆分结果
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1 = solution.y
    t = solution.t

    # 绘图
    plt.figure(figsize=(12, 16))

    # (1) 生产者 & 杂草
    ax1 = plt.subplot(4,1,1)
    ax1.plot(t, P1, 'g-', label="Crop 1")
    ax1.plot(t, P2, 'b-', label="Crop 2")
    ax1.plot(t, W,  'y-', label="Weed")
    ax1.set_title("Producers and Weed Dynamics (Extended Model)")
    ax1.set_xlabel("Time (days)")
    ax1.set_ylabel("Population")
    ax1.legend()

    # (2) 初级消费者
    ax2 = plt.subplot(4,1,2)
    ax2.plot(t, C1, 'c-', label="Herbivore 1")
    ax2.plot(t, C2, 'm-', label="Herbivore 2")
    ax2.plot(t, C3, 'r-', label="Herbivore 3")
    ax2.set_title("Primary Consumers")
    ax2.set_xlabel("Time (days)")
    ax2.set_ylabel("Population")
    ax2.legend()

    # (3) 次级消费者 (含新 S3)
    ax3 = plt.subplot(4,1,3)
    ax3.plot(t, S1, 'r-', label="Predator 1")
    ax3.plot(t, S2, 'k-', label="Predator 2")
    ax3.plot(t, S3, 'g-', label="Predator 3 (New)")
    ax3.set_title("Secondary Consumers")
    ax3.set_xlabel("Time (days)")
    ax3.set_ylabel("Population")
    ax3.legend()

    # (4) 三级消费者 (T1)
    ax4 = plt.subplot(4,1,4)
    ax4.plot(t, T1, 'm-', label="Tertiary Consumer (T1)")
    ax4.set_title("Tertiary Consumer")
    ax4.set_xlabel("Time (days)")
    ax4.set_ylabel("Population")
    ax4.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
