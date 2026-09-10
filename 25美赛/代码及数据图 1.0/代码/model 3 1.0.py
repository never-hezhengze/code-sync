import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ==================================
# 1. 基础参数（不考虑除草剂/杀虫剂）
# ==================================
# ---------- 生产者 (作物1, 作物2) ----------
r_P1 = 2
K_P1 = 10000
alpha_P1_C1 = 0.0002
alpha_P1_C2 = 0.00015
alpha_P1_C3 = 0.0001
alpha_P1_W  = 0.000001

r_P2 = 2
K_P2 = 10000
alpha_P2_C1 = 0.0001
alpha_P2_C2 = 0.00015
alpha_P2_C3 = 0.0001
alpha_P2_W  = 0.000001

# ---------- 杂草 W ----------
r_W = 4
K_W = 7000
alpha_W_C1 = 0.00005
alpha_W_C2 = 0.00001
alpha_W_C3 = 0.00002
alpha_W_P1 = 0.00001
alpha_W_P2 = 0.00001

# ---------- 初级消费者 (C1, C2, C3) ----------
r_C1 = 0.9
K_C1 = 800
beta_P1_C1 = 0.5
beta_P2_C1 = 0.4
beta_W_C1  = 0.3
delta_C1 = 0.1

r_C2 = 1.0
K_C2 = 800
beta_P1_C2 = 0.4
beta_P2_C2 = 0.5
beta_W_C2  = 0.2
delta_C2 = 0.12

r_C3 = 0.8
K_C3 = 800
beta_P1_C3 = 0.0
beta_P2_C3 = 0.0
beta_W_C3  = 0.5
delta_C3 = 0.11

# ---------- 次级消费者 (S1, S2, S3) ----------
r_S1 = 0.2
K_S1 = 100
eta_C1_S1 = 0.0002
eta_C2_S1 = 0.0002
eta_C3_S1 = 0.0002
mu_S1 = 0.09

r_S2 = 0.2
K_S2 = 120
eta_C1_S2 = 0.0002
eta_C2_S2 = 0.0002
eta_C3_S2 = 0.0002
mu_S2 = 0.10

r_S3 = 0.25
K_S3 = 100
mu_S3 = 0.08
eta_C1_S3 = 0.0005
eta_C2_S3 = 0.0000
eta_C3_S3 = 0.0005

# ---------- 三级消费者 T1 ----------
r_T1 = 0.05
K_T1 = 50
mu_T1 = 0.12
eta_S1_T1 = 0.0005
eta_S2_T1 = 0.0008
eta_S3_T1 = 0.0004

# ---------- 蝙蝠 (B) ----------
r_B  = 0.1
K_B  = 60
mu_B = 0.05

# 让蝙蝠只捕食 C1, C2
eta_C1_B = 0.0005
eta_C2_B = 0.0005
# 不捕食 C3 => 不在方程中添加 C3*B，或设 eta_C3_B=0


# ==============================
# 2. 模型方程：引入蝙蝠
# ==============================
def model_bats_eat_C1C2(t, y):
    """
    共有 11 个物种:
    y = [P1, P2, W,  C1, C2, C3,  S1, S2, S3,  T1, B]
    """
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B = y

    # ---------- 生产者1, 2, 杂草 ----------
    dP1dt = (r_P1 * P1 * (1 - P1/K_P1)
             - alpha_P1_C1*P1*C1
             - alpha_P1_C2*P1*C2
             - alpha_P1_C3*P1*C3
             - alpha_P1_W *P1*W)

    dP2dt = (r_P2 * P2 * (1 - P2/K_P2)
             - alpha_P2_C1*P2*C1
             - alpha_P2_C2*P2*C2
             - alpha_P2_C3*P2*C3
             - alpha_P2_W *P2*W)

    dWdt = (r_W * W * (1 - W/K_W)
            - alpha_W_C1*W*C1
            - alpha_W_C2*W*C2
            - alpha_W_C3*W*C3)

    # ---------- 初级消费者 C1, C2, C3 ----------
    dC1dt = (r_C1*C1*(1 - C1/K_C1)
             + beta_P1_C1*P1 + beta_P2_C1*P2 + beta_W_C1*W
             - delta_C1*C1
             # 被其他捕食者消耗
             - eta_C1_S1*C1*S1
             - eta_C1_S2*C1*S2
             - eta_C1_S3*C1*S3
             # 被蝙蝠B捕食
             - eta_C1_B*C1*B)

    dC2dt = (r_C2*C2*(1 - C2/K_C2)
             + beta_P1_C2*P1 + beta_P2_C2*P2 + beta_W_C2*W
             - delta_C2*C2
             - eta_C2_S1*C2*S1
             - eta_C2_S2*C2*S2
             - eta_C2_S3*C2*S3
             # 被蝙蝠B捕食
             - eta_C2_B*C2*B)

    dC3dt = (r_C3*C3*(1 - C3/K_C3)
             + beta_P1_C3*P1 + beta_P2_C3*P2 + beta_W_C3*W
             - delta_C3*C3
             - eta_C3_S1*C3*S1
             - eta_C3_S2*C3*S2
             - eta_C3_S3*C3*S3
             # 不被蝙蝠捕食 => 无蝙蝠项
            )

    # ---------- 次级消费者 S1, S2, S3 ----------
    dS1dt = (r_S1*S1*(1 - S1/K_S1)
             + eta_C1_S1*C1*S1
             + eta_C2_S1*C2*S1
             + eta_C3_S1*C3*S1
             - mu_S1*S1
             # 可能被T1捕食
             - eta_S1_T1*S1*T1)

    dS2dt = (r_S2*S2*(1 - S2/K_S2)
             + eta_C1_S2*C1*S2
             + eta_C2_S2*C2*S2
             + eta_C3_S2*C3*S2
             - mu_S2*S2
             - eta_S2_T1*S2*T1)

    dS3dt = (r_S3*S3*(1 - S3/K_S3)
             + eta_C1_S3*C1*S3
             + eta_C3_S3*C3*S3
             - mu_S3*S3
             - eta_S3_T1*S3*T1
             # 不被蝙蝠捕食 => 无项
            )

    # ---------- 三级消费者 T1 ----------
    dT1dt = (r_T1*T1*(1 - T1/K_T1)
             + eta_S1_T1*S1*T1
             + eta_S2_T1*S2*T1
             + eta_S3_T1*S3*T1
             - mu_T1*T1)

    # ---------- 蝙蝠 B (只吃C1, C2) ----------
    dBdt = (r_B*B*(1 - B/K_B)
            + eta_C1_B*C1*B
            + eta_C2_B*C2*B
            - mu_B*B)

    return [dP1dt, dP2dt, dWdt,
            dC1dt, dC2dt, dC3dt,
            dS1dt, dS2dt, dS3dt,
            dT1dt, dBdt]

# ============================
# 3. 主函数：示例求解 + 绘图
# ============================
def main():
    # 11维初始条件: [P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B]
    y0 = [
        3,        # P1
        3,        # P2
        15000,    # W
        300,      # C1
        400,      # C2
        300,      # C3
        50,       # S1
        30,       # S2
        50,       # S3
        10,       # T1
        20,       # B (蝙蝠)
    ]

    t_span = (0, 120)
    t_eval = np.linspace(0, 20, 1000)

    solution = solve_ivp(model_bats_eat_C1C2, t_span, y0, t_eval=t_eval, method='BDF')
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B = solution.y
    t = solution.t

    # -- 绘图 --
    plt.figure(figsize=(14, 14))

    # (1) 作物 + 杂草
    ax1 = plt.subplot(4,1,1)
    ax1.plot(t, P1, 'g-', label='Crop1')
    ax1.plot(t, P2, 'b-', label='Crop2')
    ax1.plot(t, W,  'y-', label='Weed')
    ax1.legend()
    ax1.set_xlabel('Time (days)')
    ax1.set_ylabel('Population')
    ax1.set_title('Producers & Weed')

    # (2) 初级消费者 C1, C2, C3
    ax2 = plt.subplot(4,1,2)
    ax2.plot(t, C1, 'c-', label='C1')
    ax2.plot(t, C2, 'm-', label='C2')
    ax2.plot(t, C3, 'r-', label='C3')
    ax2.legend()
    ax2.set_xlabel('Time (days)')
    ax2.set_ylabel('Population')
    ax2.set_title('Primary Consumers')

    # (3) 次级消费者 S1, S2, S3
    ax3 = plt.subplot(4,1,3)
    ax3.plot(t, S1, 'r-', label='S1')
    ax3.plot(t, S2, 'k-', label='S2')
    ax3.plot(t, S3, 'g-', label='S3')
    ax3.legend()
    ax3.set_xlabel('Time (days)')
    ax3.set_ylabel('Population')
    ax3.set_title('Secondary Consumers')

    # (4) 三级消费者 T1 & 蝙蝠 B
    ax4 = plt.subplot(4,1,4)
    ax4.plot(t, T1, 'm-', label='T1')
    ax4.plot(t, B,  'c-', label='Bats (Only eat C1,C2)')
    ax4.legend()
    ax4.set_xlabel('Time (days)')
    ax4.set_ylabel('Population')
    ax4.set_title('Tertiary Consumer & Bats')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
