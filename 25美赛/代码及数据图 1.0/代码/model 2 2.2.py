import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
import gc


# 定义微分方程系统
# 该函数表示一个四种群体（植物、昆虫、食草动物、捕食者）之间的相互作用
# t: 时间, y: 状态变量列表 [P, I, A, B], params: 参数列表
def system_equations(t, y, params):
    # 解包变量并确保群体数量不为负（使用 np.maximum 确保最小值为 1e-6）
    P, I, A, B = np.maximum(y, 1e-6)

    # 解包参数
    r_P, K_P, alpha_P, alpha_A, r_I, K_I, beta_P, delta_I, gamma_I, eta_B, r_A, K_A, beta_A, r_B, K_B, mu_B, eta_B_2 = params

    # 定义四个种群的微分方程
    dPdt = r_P * P * (1 - P / K_P) - alpha_P * P * I - alpha_A * P * A  # 植物增长和减少
    dIdt = r_I * I * (1 - I / K_I) + beta_P * P - delta_I * I - gamma_I * I - eta_B * I  # 昆虫的变化
    dAdt = r_A * A * (1 - A / K_A) - alpha_A * P - beta_A * I  # 食草动物的变化
    dBdt = r_B * B * (1 - B / K_B) + eta_B_2 * I - mu_B * B  # 捕食者的变化

    return [dPdt, dIdt, dAdt, dBdt]


# 初始条件设置
initial_conditions = [100, 30, 10, 5]  # 初始的四种群体数量 [植物, 昆虫, 食草动物, 捕食者]

# 定义时间范围
# 时间范围为从 0 到 20，分为 50 个点
# 用于模拟种群随时间的变化
t = np.linspace(0, 20, 50)

# 参数设置
# 参数列表包括种群的增长率、环境容量、捕食和竞争系数等
params = [0.08, 500, 0.007, 0.03, 0.12, 300, 0.013, 0.035, 0.06, 0.02, 0.07, 320, 0.025, 0.07, 130, 0.02, 0.025]

# 参数边界，用于优化时的约束条件
bounds = [
    (0.05, 0.1), (400, 600), (0.005, 0.01), (0.02, 0.03),
    (0.1, 0.15), (250, 350), (0.01, 0.015), (0.03, 0.04),
    (0.05, 0.08), (0.01, 0.03), (0.05, 0.08), (300, 350),
    (0.02, 0.03), (0.05, 0.08), (120, 140), (0.01, 0.03),
    (0.02, 0.03)
]


# 定义优化的目标函数
# 此函数的目标是最小化植物（P）的负累积数量，从而优化参数
# params: 优化过程中的参数组合
def objective(params):
    try:
        # 用当前参数求解微分方程
        solution = solve_ivp(
            lambda t, y: system_equations(t, y, params),
            [t[0], t[-1]],
            initial_conditions,
            t_eval=t,
            method='RK45',
            atol=1e-4,
            rtol=1e-2
        )
        if not solution.success:
            return 1e6  # 如果求解失败，返回一个大值
        P, _, _, _ = solution.y  # 提取植物的数量
        return -np.sum(P)  # 返回负的植物总量
    except Exception as e:
        print(f"Error with parameters {params}: {e}")
        return 1e6
    finally:
        gc.collect()  # 清理内存


# 优化参数并对比结果
# 该函数进行优化，并将原始结果与优化后的结果进行比较

def optimize_and_compare():
    try:
        # 用初始参数求解微分方程
        solution_original = solve_ivp(
            lambda t, y: system_equations(t, y, params),
            [t[0], t[-1]],
            initial_conditions,
            t_eval=t,
            method='RK45',
            atol=1e-4,
            rtol=1e-2
        )
        if solution_original.success:
            P, I, A, B = solution_original.y  # 提取原始的四个种群结果
        else:
            print("Initial solve failed:", solution_original.message)
            return
    except Exception as e:
        print("Error during initial solve:", e)
        return

    # 使用差分进化算法进行优化
    result = differential_evolution(objective, bounds, maxiter=10, tol=0.01, popsize=5, workers=1)
    print("Optimal parameters found: ", result.x)

    # 用优化后的参数求解微分方程
    solution_optimal = solve_ivp(
        lambda t, y: system_equations(t, y, result.x),
        [t[0], t[-1]],
        initial_conditions,
        t_eval=t,
        method='RK45',
        atol=1e-4,
        rtol=1e-2
    )
    if solution_optimal.success:
        P_opt, I_opt, A_opt, B_opt = solution_optimal.y  # 提取优化后的四个种群结果

        # 绘制对比图
        plt.figure(figsize=(12, 8))
        plt.plot(t, P, label='Plants (Original)', color='green', linestyle='-')
        plt.plot(t, I, label='Insects (Original)', color='orange', linestyle='-')
        plt.plot(t, A, label='Herbivores (Original)', color='blue', linestyle='-')
        plt.plot(t, B, label='Predators (Original)', color='red', linestyle='-')

        plt.plot(t, P_opt, label='Plants (Optimized)', color='green', linestyle='--')
        plt.plot(t, I_opt, label='Insects (Optimized)', color='orange', linestyle='--')
        plt.plot(t, A_opt, label='Herbivores (Optimized)', color='blue', linestyle='--')
        plt.plot(t, B_opt, label='Predators (Optimized)', color='red', linestyle='--')

        plt.title('Population Dynamics - Optimized vs Original')
        plt.xlabel('Time')
        plt.ylabel('Population Size')
        plt.legend(loc='best')
        plt.grid(True)
        plt.show()
    else:
        print("Optimal solve failed:", solution_optimal.message)


# 主程序入口
if __name__ == '__main__':
    optimize_and_compare()
