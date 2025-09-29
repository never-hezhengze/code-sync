import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ==============================
# 1. 参数设置：蝙蝠只捕食C1, C2
# ==============================
# (同你之前的参数，去掉除草剂/杀虫剂)

# ---------- 作物1, 作物2 ----------
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

# ---------- 蝙蝠 B (只吃C1, C2) ----------
r_B  = 0.1
K_B  = 60
mu_B = 0.05
eta_C1_B = 0.0005  # 捕食C1效率
eta_C2_B = 0.0005  # 捕食C2效率
# C3不在蝙蝠的捕食列表 => 不捕食C3

# =========================
# 2. 模型函数 (11个物种)
# =========================
def model_bats_eat_C1C2(t, y):
    """
    y = [P1, P2, W,  C1, C2, C3,  S1, S2, S3,  T1, B]
    """
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B = y

    # ---------- 生产者1,2, 杂草 ----------
    dP1dt = (r_P1*P1*(1 - P1/K_P1)
             - alpha_P1_C1*P1*C1
             - alpha_P1_C2*P1*C2
             - alpha_P1_C3*P1*C3
             - alpha_P1_W *P1*W)

    dP2dt = (r_P2*P2*(1 - P2/K_P2)
             - alpha_P2_C1*P2*C1
             - alpha_P2_C2*P2*C2
             - alpha_P2_C3*P2*C3
             - alpha_P2_W *P2*W)

    dWdt = (r_W*W*(1 - W/K_W)
            - alpha_W_C1*W*C1
            - alpha_W_C2*W*C2
            - alpha_W_C3*W*C3)

    # ---------- 初级消费者 C1, C2, C3 ----------
    dC1dt = (r_C1*C1*(1 - C1/K_C1)
             + beta_P1_C1*P1 + beta_P2_C1*P2 + beta_W_C1*W
             - delta_C1*C1
             # 被S1, S2, S3捕食
             - eta_C1_S1*C1*S1
             - eta_C1_S2*C1*S2
             - eta_C1_S3*C1*S3
             # 被蝙蝠捕食
             - eta_C1_B*C1*B)

    dC2dt = (r_C2*C2*(1 - C2/K_C2)
             + beta_P1_C2*P1 + beta_P2_C2*P2 + beta_W_C2*W
             - delta_C2*C2
             - eta_C2_S1*C2*S1
             - eta_C2_S2*C2*S2
             - eta_C2_S3*C2*S3
             # 被蝙蝠捕食
             - eta_C2_B*C2*B)

    dC3dt = (r_C3*C3*(1 - C3/K_C3)
             + beta_P1_C3*P1 + beta_P2_C3*P2 + beta_W_C3*W
             - delta_C3*C3
             - eta_C3_S1*C3*S1
             - eta_C3_S2*C3*S2
             - eta_C3_S3*C3*S3
             # 不被蝙蝠捕食
            )

    # ---------- 次级消费者 S1, S2, S3 ----------
    dS1dt = (r_S1*S1*(1 - S1/K_S1)
             + eta_C1_S1*C1*S1
             + eta_C2_S1*C2*S1
             + eta_C3_S1*C3*S1
             - mu_S1*S1
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
             - eta_S3_T1*S3*T1)

    # ---------- 三级消费者 T1 ----------
    dT1dt = (r_T1*T1*(1 - T1/K_T1)
             + eta_S1_T1*S1*T1
             + eta_S2_T1*S2*T1
             + eta_S3_T1*S3*T1
             - mu_T1*T1)

    # ---------- 蝙蝠 B (吃C1,C2) ----------
    dBdt = (r_B*B*(1 - B/K_B)
            + eta_C1_B*C1*B
            + eta_C2_B*C2*B
            - mu_B*B)

    return [dP1dt, dP2dt, dWdt,
            dC1dt, dC2dt, dC3dt,
            dS1dt, dS2dt, dS3dt,
            dT1dt, dBdt]


# =========================================
# 3. 在主函数里做“无蝙蝠 vs 有蝙蝠”前后对比
# =========================================
def main():
    # 11维初始：[P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B]
    # (1) 无蝙蝠：B=0
    y0_nobat = [3, 3, 15000, 300, 400, 300, 50, 30, 50, 10, 0]

    # (2) 有蝙蝠：给B一个大于0的初始值
    y0_withbat = y0_nobat.copy()
    y0_withbat[-1] = 20  # B=20

    t_span = (0, 20)
    t_eval = np.linspace(0, 20, 1000)

    # 求解(1) 无蝙蝠
    sol_nobat = solve_ivp(model_bats_eat_C1C2, t_span, y0_nobat, t_eval=t_eval, method='BDF')
    # 求解(2) 有蝙蝠
    sol_withbat = solve_ivp(model_bats_eat_C1C2, t_span, y0_withbat, t_eval=t_eval, method='BDF')

    # 拆分结果
    # 无蝙蝠
    P1_nb, P2_nb, W_nb, C1_nb, C2_nb, C3_nb, S1_nb, S2_nb, S3_nb, T1_nb, B_nb = sol_nobat.y
    # 有蝙蝠
    P1_wb, P2_wb, W_wb, C1_wb, C2_wb, C3_wb, S1_wb, S2_wb, S3_wb, T1_wb, B_wb = sol_withbat.y

    t_nb = sol_nobat.t
    t_wb = sol_withbat.t

    # ================
    # 4. 对比绘图
    # ================
    plt.figure(figsize=(14, 16))

    # (1) 作物+杂草
    ax1 = plt.subplot(4,1,1)
    ax1.plot(t_nb, P1_nb, 'g--', label="Crop1(no bat)")
    ax1.plot(t_nb, P2_nb, 'b--', label="Crop2(no bat)")
    ax1.plot(t_nb, W_nb,  'y--', label="Weed(no bat)")

    ax1.plot(t_wb, P1_wb, 'g-', label="Crop1(with bat)")
    ax1.plot(t_wb, P2_wb, 'b-', label="Crop2(with bat)")
    ax1.plot(t_wb, W_wb,  'y-', label="Weed(with bat)")

    ax1.set_title("Producers & Weed (No Bat vs With Bat)")
    ax1.set_xlabel("Time (days)")
    ax1.set_ylabel("Population")
    ax1.legend()

    # (2) 初级消费者
    ax2 = plt.subplot(4,1,2)
    ax2.plot(t_nb, C1_nb, 'c--', label="C1(no bat)")
    ax2.plot(t_nb, C2_nb, 'm--', label="C2(no bat)")
    ax2.plot(t_nb, C3_nb, 'r--', label="C3(no bat)")

    ax2.plot(t_wb, C1_wb, 'c-', label="C1(with bat)")
    ax2.plot(t_wb, C2_wb, 'm-', label="C2(with bat)")
    ax2.plot(t_wb, C3_wb, 'r-', label="C3(with bat)")

    ax2.set_title("Primary Consumers")
    ax2.set_xlabel("Time (days)")
    ax2.set_ylabel("Population")
    ax2.legend()

    # (3) 次级消费者
    ax3 = plt.subplot(4,1,3)
    ax3.plot(t_nb, S1_nb, 'r--', label="S1(no bat)")
    ax3.plot(t_nb, S2_nb, 'k--', label="S2(no bat)")
    ax3.plot(t_nb, S3_nb, 'g--', label="S3(no bat)")

    ax3.plot(t_wb, S1_wb, 'r-', label="S1(with bat)")
    ax3.plot(t_wb, S2_wb, 'k-', label="S2(with bat)")
    ax3.plot(t_wb, S3_wb, 'g-', label="S3(with bat)")

    ax3.set_title("Secondary Consumers")
    ax3.set_xlabel("Time (days)")
    ax3.set_ylabel("Population")
    ax3.legend()

    # (4) 三级消费者T1 & 蝙蝠B
    ax4 = plt.subplot(4,1,4)
    ax4.plot(t_nb, T1_nb, 'm--', label="T1(no bat)")
    ax4.plot(t_nb, B_nb,  'c--', label="B(no bat => 0)")

    ax4.plot(t_wb, T1_wb, 'm-', label="T1(with bat)")
    ax4.plot(t_wb, B_wb,  'c-', label="B(with bat)")

    ax4.set_title("Tertiary Consumer + Bats")
    ax4.set_xlabel("Time (days)")
    ax4.set_ylabel("Population")
    ax4.legend()

    plt.tight_layout()
    plt.show()

    # ====== 额外：可打印最终产量比较 ======
    P1_final_nb = P1_nb[-1]
    P2_final_nb = P2_nb[-1]
    P1_final_wb = P1_wb[-1]
    P2_final_wb = P2_wb[-1]

    print("====== Final Crop Yields at t=100 ======")
    print(f"No Bat : P1={P1_final_nb:.2f}, P2={P2_final_nb:.2f},  sum={P1_final_nb + P2_final_nb:.2f}")
    print(f"WithBat: P1={P1_final_wb:.2f}, P2={P2_final_wb:.2f}, sum={P1_final_wb + P2_final_wb:.2f}")


if __name__ == "__main__":
    main()
