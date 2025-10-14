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
alpha_W_P1 = 0.00018
alpha_W_P2 = 0.00018

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

# ---------- 蜜蜂 Bee (只吃 C1, C2) ----------
r_B  = 0.1
K_B  = 80
mu_B = 0.05
eta_P1_B = 0.0001
eta_P2_B = 0.0001
sigma_P1_B =0.00018
sigma_P2_B =0.00018
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
             - alpha_P1_W *P1*W
             + sigma_P1_B*P1*B
             )

    dP2dt = (r_P2*P2*(1 - P2/K_P2)
             - alpha_P2_C1*P2*C1
             - alpha_P2_C2*P2*C2
             - alpha_P2_C3*P2*C3
             - alpha_P2_W *P2*W
             + sigma_P2_B*P2*B
             )

    dWdt = (r_W*W*(1 - W/K_W)
            - alpha_W_C1*W*C1
            - alpha_W_C2*W*C2
            - alpha_W_C3*W*C3
            - alpha_W_P1 * W * P1
            - alpha_W_P2 * W * P2
            )

    # ---------- 初级消费者 ----------
    dC1dt = (r_C1*C1*(1 - C1/K_C1)
             + beta_P1_C1*P1 + beta_P2_C1*P2 + beta_W_C1*W
             - delta_C1*C1
             - eta_C1_S1*C1*S1
             - eta_C1_S2*C1*S2
             - eta_C1_S3*C1*S3
             )

    dC2dt = (r_C2*C2*(1 - C2/K_C2)
             + beta_P1_C2*P1 + beta_P2_C2*P2 + beta_W_C2*W
             - delta_C2*C2
             - eta_C2_S1*C2*S1
             - eta_C2_S2*C2*S2
             - eta_C2_S3*C2*S3
             )


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
            + eta_P1_B*P1*B
            + eta_P2_B*P2*B
            - mu_B*B)

    return [dP1dt, dP2dt, dWdt,
            dC1dt, dC2dt, dC3dt,
            dS1dt, dS2dt, dS3dt,
            dT1dt, dBdt]


# ========================================================
# 3. 分段模拟：先 [0, t_b) 不引蝙蝠 => t_b 时刻一次性引入 B0 => [t_b, 20]
#    使用 dense_output=True 并用 sol.sol(t) 获取指定时刻解
# ========================================================
def simulate_with_bat_introduction(t_b, B0):
    """
    返回: (final_yield, (t_combined, y_combined))
    final_yield = P1(20)+P2(20)
    t_combined, y_combined 为拼接后的 0~20 全程解
    """
    # --------------- 第一段 0~t_b (B=0) ---------------
    y0_init = [3, 3, 3000, 300, 400, 300, 50, 30, 50, 10, 0]  # 初始 B=0
    sol1 = solve_ivp(model_bats_eat_C1C2,
                     [0, t_b], y0_init,
                     method='BDF',
                     dense_output=True)  # 可插值任意时刻

    # 若 t_b=0, 表示马上引入, 这时 sol1 可能只在起点就终止
    # 兼容: 如果 t_b>0, 说明至少做一小段
    # 取 [0, ...], 只要 sol1.success:

    # 这里 sol1.sol(t_b) => shape=(11,) 在 dense_output=True 下可用
    Y_tb = sol1.sol(t_b)  # 取得 t=t_b 时的解(1D array)
    # 一次性增加 B0
    Y_tb[-1] = B0

    # --------------- 第二段 t_b~20 ---------------
    sol2 = solve_ivp(model_bats_eat_C1C2,
                     [t_b, 20], Y_tb,
                     method='BDF',
                     dense_output=True)

    # (1) 为了做拼接，需要在某个网格取样,比如:
    #   sol1 在 [0, t_b] 上插值, sol2 在 [t_b, 20] 上插值
    #   并合并
    #   这里我们选 200 点插值(你可自己调节)

    # A. 如果 t_b>0:
    t_samples_1 = np.linspace(0, t_b, 200) if t_b>0 else np.array([0])
    Y_samples_1 = sol1.sol(t_samples_1)  # shape=(11, len_of t_samples_1)

    # B. 第二段 [t_b, 20]:
    t_samples_2 = np.linspace(t_b, 20, 200)
    Y_samples_2 = sol2.sol(t_samples_2)  # shape=(11, len_of t_samples_2)

    # 合并(去掉第二段第0个点 以免重复)
    t_combined = np.concatenate([t_samples_1, t_samples_2[1:]])
    y_combined = np.concatenate([Y_samples_1, Y_samples_2[:,1:]], axis=1)

    # 计算在 t=20 处的作物总量
    Y_end_20 = sol2.sol(20)  # shape=(11,)
    P1_20 = Y_end_20[0]
    P2_20 = Y_end_20[1]
    final_yield = float(P1_20 + P2_20)

    return final_yield, (t_combined, y_combined)


# =========================================
# 4. 网格搜索 + 对比 "无蝙蝠" vs "最佳方案"
# =========================================
def main():
    # 时间只到20
    T_MAX = 20

    # ---------- A. "无蝙蝠"情景 ----------
    # 即全程 B=0, t_b=20, B0=0 => 直到最后都没投放
    nobat_yield, (t_nobat, Y_nobat) = simulate_with_bat_introduction(t_b=20, B0=0)
    print(f"[No Bee] final yield = {nobat_yield:.2f}")

    # ---------- B. 网格搜索 ----------
    t_b_candidates = np.arange(0, 21, 1)   # 0,1,2,...,20
    B0_candidates  = np.arange(0, 51, 5)   # 0,5,10,...,50

    best_tb   = None
    best_B0   = None
    best_yield = -1.0

    for tb in t_b_candidates:
        for B0 in B0_candidates:
            final_yield, _ = simulate_with_bat_introduction(tb, B0)
            if final_yield > best_yield:
                best_yield = final_yield
                best_tb    = tb
                best_B0    = B0

    print(f"[GridSearch] best_tb={best_tb}, best_B0={best_B0}, best_yield={best_yield:.2f}")

    # 再跑一次获取完整曲线
    best_yield_val, (t_best, Y_best) = simulate_with_bat_introduction(best_tb, best_B0)
    print(f"[Best Intro] final yield = {best_yield_val:.2f}")

    # ---------- C. 绘图对比 ----------
    P1_nb, P2_nb, W_nb, C1_nb, C2_nb, C3_nb, S1_nb, S2_nb, S3_nb, T1_nb, B_nb = Y_nobat
    P1_b,  P2_b,  W_b,  C1_b,  C2_b,  C3_b,  S1_b,  S2_b,  S3_b,  T1_b,  B_b  = Y_best

    plt.figure(figsize=(14,16))

    # (1) 作物+杂草
    ax1 = plt.subplot(5,1,1)
    ax1.plot(t_nobat, P1_nb, 'g--', label="Crop1(NoBee)")
    ax1.plot(t_nobat, P2_nb, 'b--', label="Crop2(NoBee)")
    ax1.plot(t_nobat, W_nb,  'y--', label="Weed(NoBee)")

    ax1.plot(t_best,  P1_b, 'g-', label=f"Crop1(t_b={best_tb}, B0={best_B0})")
    ax1.plot(t_best,  P2_b, 'b-', label=f"Crop2(t_b={best_tb}, B0={best_B0})")
    ax1.plot(t_best,  W_b,  'y-', label=f"Weed(t_b={best_tb}, B0={best_B0})")

    ax1.set_title("Producers & Weed: NoBee vs Best Intro")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Population")
    ax1.legend()

    # (2) 初级消费者
    ax2 = plt.subplot(5,1,2)
    ax2.plot(t_nobat, C1_nb, 'c--', label="C1(NoBee)")
    ax2.plot(t_nobat, C2_nb, 'm--', label="C2(NoBee)")
    ax2.plot(t_nobat, C3_nb, 'r--', label="C3(NoBee)")

    ax2.plot(t_best, C1_b, 'c-', label="C1(Best)")
    ax2.plot(t_best, C2_b, 'm-', label="C2(Best)")
    ax2.plot(t_best, C3_b, 'r-', label="C3(Best)")

    ax2.set_title("Primary Consumers")
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Population")
    ax2.legend()

    # (3) 次级消费者
    ax3 = plt.subplot(5,1,3)
    ax3.plot(t_nobat, S1_nb, 'r--', label="S1(NoBee)")
    ax3.plot(t_nobat, S2_nb, 'k--', label="S2(NoBee)")
    ax3.plot(t_nobat, S3_nb, 'g--', label="S3(NoBee)")

    ax3.plot(t_best, S1_b, 'r-', label="S1(Best)")
    ax3.plot(t_best, S2_b, 'k-', label="S2(Best)")
    ax3.plot(t_best, S3_b, 'g-', label="S3(Best)")

    ax3.set_title("Secondary Consumers")
    ax3.set_xlabel("Time")
    ax3.set_ylabel("Population")
    ax3.legend()

    # (4) 三级消费者+蝙蝠
    ax4 = plt.subplot(5,1,4)
    ax4.plot(t_nobat, T1_nb, 'm--', label="T1(NoBee)")
    #ax4.plot(t_nobat, B_nb,  'c--', label="B(NoBat=0)")

    ax4.plot(t_best, T1_b, 'm-', label="T1(Best)")
   # ax4.plot(t_best, B_b,  'c-', label="B(Best)")

    ax4.set_title("Tertiary Consumer")
    ax4.set_xlabel("Time")
    ax4.set_ylabel("Population")
    ax4.legend()

    ax5 = plt.subplot(5, 1, 5)
    ax5.plot(t_best, B_b, 'c-', label="B(Best)")
    ax5.set_title(" Bee")
    ax5.set_xlabel("Time")
    ax5.set_ylabel("Population")
    ax5.legend()

    plt.tight_layout()
    plt.show()

if __name__=="__main__":
    main()
