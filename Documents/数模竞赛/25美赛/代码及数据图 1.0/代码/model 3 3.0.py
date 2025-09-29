import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ==================================
# 1. 模型参数：蝙蝠只捕食 C1、C2
# ==================================
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

# ---------- 蝙蝠 B (只吃 C1, C2) ----------
r_B  = 0.1
K_B  = 60
mu_B = 0.05
eta_C1_B = 0.0005
eta_C2_B = 0.0005

# =========================
# 2. 定义模型函数 (11物种)
# =========================
def model_bats_eat_C1C2(t, y):
    """
    y = [P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B]
    """
    P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B = y

    # ---------- 生产者 ----------
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

    # ---------- 初级消费者 ----------
    dC1dt = (r_C1*C1*(1 - C1/K_C1)
             + beta_P1_C1*P1 + beta_P2_C1*P2 + beta_W_C1*W
             - delta_C1*C1
             - eta_C1_S1*C1*S1
             - eta_C1_S2*C1*S2
             - eta_C1_S3*C1*S3
             - eta_C1_B*C1*B)

    dC2dt = (r_C2*C2*(1 - C2/K_C2)
             + beta_P1_C2*P1 + beta_P2_C2*P2 + beta_W_C2*W
             - delta_C2*C2
             - eta_C2_S1*C2*S1
             - eta_C2_S2*C2*S2
             - eta_C2_S3*C2*S3
             - eta_C2_B*C2*B)

    dC3dt = (r_C3*C3*(1 - C3/K_C3)
             + beta_P1_C3*P1 + beta_P2_C3*P2 + beta_W_C3*W
             - delta_C3*C3
             - eta_C3_S1*C3*S1
             - eta_C3_S2*C3*S2
             - eta_C3_S3*C3*S3)

    # ---------- 次级消费者 ----------
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

    # ---------- 蝙蝠 B ----------
    dBdt = (r_B*B*(1 - B/K_B)
            + eta_C1_B*C1*B
            + eta_C2_B*C2*B
            - mu_B*B)

    return [dP1dt, dP2dt, dWdt,
            dC1dt, dC2dt, dC3dt,
            dS1dt, dS2dt, dS3dt,
            dT1dt, dBdt]


# ========================================================
# 3. 分段模拟：先在 [0, t_b) 没有蝙蝠, 后在 [t_b, 20] 引入蝙蝠B0
# ========================================================
def simulate_with_bat_introduction(t_b, B0):
    """
    在时间 0~t_b 内不引入蝙蝠(B=0)，
    在 t_b 时刻一次性引入 B0 只蝙蝠，
    然后模拟到 t=20。
    返回：最终作物 P1(20) + P2(20)。
    """
    # --- A. 在 0~t_b 模拟 (蝙蝠=0) ---
    y0_init = [3, 3, 15000, 300, 400, 300, 50, 30, 50, 10, 0]  # 11维,最后一项 B=0
    sol1 = solve_ivp(model_bats_eat_C1C2, [0, t_b], y0_init, method='BDF', dense_output=True)

    # 取 t_b 时刻的解  (states at time t_b)
    Y_tb = sol1.sol(t_b)  # shape=(11,)

    # --- B. 在 t_b 时刻，引入 B0 只蝙蝠 ---
    Y_tb[-1] = B0  # 第11个分量对应蝙蝠数量

    # --- C. 从 t_b~20 继续模拟 ---
    sol2 = solve_ivp(model_bats_eat_C1C2, [t_b, 20], Y_tb, method='BDF', dense_output=True)
    Y_20 = sol2.sol(20)  # 取 t=20 时刻的解

    P1_final = Y_20[0]
    P2_final = Y_20[1]
    return float(P1_final + P2_final)


# =========================================
# 4. 网格搜索：找 (t_b, B0) 使作物 P1+P2 最大
# =========================================
def main():
    # 时间轴只要 0~20
    T_MAX = 20

    # 设定搜索步长
    # 例如 t_b 在 [0,20] 间步长=1.0
    # B0 在 [0,50] 间步长=5.0
    # 可以更细或更粗，也可用更高级算法
    t_b_candidates = np.arange(0, T_MAX+1, 1.0)    # 0,1,2,...,20
    B0_candidates  = np.arange(0, 51, 5.0)        # 0,5,10,...,50

    best_t_b  = None
    best_B0   = None
    best_yield = -1.0

    # --- 执行网格搜索 ---
    for t_b in t_b_candidates:
        for B0 in B0_candidates:
            final_yield = simulate_with_bat_introduction(t_b, B0)
            # 如果更高，则更新最佳解
            if final_yield > best_yield:
                best_yield = final_yield
                best_t_b   = t_b
                best_B0    = B0

    print("=== Grid Search Result ===")
    print(f"Best introduction time t_b = {best_t_b}")
    print(f"Best introduction number B0 = {best_B0}")
    print(f"Max Crop Yield (P1+P2 at t=20) = {best_yield:.2f}")

    # ============== 验证最佳解并画图 ==============
    # 用最优 (t_b, B0) 再跑一次分段模拟，把每段的解拼接
    # 以便整段时间(0~20)中作图

    # a) 第1段 (0~best_t_b)
    y0_init = [3, 3, 15000, 300, 400, 300, 50, 30, 50, 10, 0]
    sol1 = solve_ivp(model_bats_eat_C1C2, [0, best_t_b], y0_init, t_eval=np.linspace(0, best_t_b, 200), method='BDF')
    # b) 第2段 (best_t_b ~ 20)
    Y_tb = sol1.y[:, -1].copy()  # y at time best_t_b
    Y_tb[-1] = best_B0           # introduce B0
    sol2 = solve_ivp(model_bats_eat_C1C2, [best_t_b, 20], Y_tb, t_eval=np.linspace(best_t_b, 20, 200), method='BDF')

    # 拼接两段
    t_combined = np.concatenate([sol1.t, sol2.t[1:]])  # 去掉第二段首点避免重复
    y_combined = np.concatenate([sol1.y, sol2.y[:,1:]], axis=1)

    P1, P2, W, C1, C2, C3, S1, S2, S3, T1, B = y_combined

    # ============== 作图展示完整演变 ==============
    plt.figure(figsize=(12, 12))

    # (1) 作物 + 杂草
    ax1 = plt.subplot(4,1,1)
    ax1.plot(t_combined, P1, 'g-', label='Crop1')
    ax1.plot(t_combined, P2, 'b-', label='Crop2')
    ax1.plot(t_combined, W,  'y-', label='Weed')
    ax1.legend()
    ax1.set_title(f"Producers & Weed (Best t_b={best_t_b}, B0={best_B0}, Final Yield={best_yield:.2f})")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Population")

    # (2) 初级消费者 C1, C2, C3
    ax2 = plt.subplot(4,1,2)
    ax2.plot(t_combined, C1, 'c-', label='C1')
    ax2.plot(t_combined, C2, 'm-', label='C2')
    ax2.plot(t_combined, C3, 'r-', label='C3')
    ax2.legend()
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Population")
    ax2.set_title("Primary Consumers")

    # (3) 次级消费者 S1, S2, S3
    ax3 = plt.subplot(4,1,3)
    ax3.plot(t_combined, S1, 'r-', label='S1')
    ax3.plot(t_combined, S2, 'k-', label='S2')
    ax3.plot(t_combined, S3, 'g-', label='S3')
    ax3.legend()
    ax3.set_xlabel("Time")
    ax3.set_ylabel("Population")
    ax3.set_title("Secondary Consumers")

    # (4) 三级消费者 T1 & 蝙蝠 B
    ax4 = plt.subplot(4,1,4)
    ax4.plot(t_combined, T1, 'm-', label='T1')
    ax4.plot(t_combined, B,  'c-', label='Bats')
    ax4.legend()
    ax4.set_xlabel("Time")
    ax4.set_ylabel("Population")
    ax4.set_title("Tertiary Consumer & Bats")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
