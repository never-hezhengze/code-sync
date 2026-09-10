import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution

# 定义系统方程
def system_equations(y, t, params):
    P, I, A, B = y
    (r_P, K_P, alpha_P, alpha_A, r_I, K_I, beta_P, delta_I, gamma_I,
     eta_B, r_A, K_A, beta_A, r_B, K_B, mu_B, eta_B_2) = params

    # 确保变量非负
    P = max(P, 1e-6)
    I = max(I, 1e-6)
    A = max(A, 1e-6)
    B = max(B, 1e-6)

    # 方程
    dPdt = r_P * P * (1 - P / K_P) - alpha_P * P * I - alpha_A * P * A
    dIdt = r_I * I * (1 - I / K_I) + beta_P * P - delta_I * I - gamma_I * I - eta_B * I
    dAdt = r_A * A * (1 - A / K_A) - alpha_A * P - beta_A * I
    dBdt = r_B * B * (1 - B / K_B) + eta_B_2 * I - mu_B * B

    return [dPdt, dIdt, dAdt, dBdt]

# 初始条件和时间网格
initial_conditions = [100, 50, 30, 20]  # P, I, A, B
t = np.linspace(0, 100, 1000)  # 时间范围，1000个采样点

# 参数
params = [0.1, 1000, 0.01, 0.005, 0.2, 500, 0.02, 0.1, 0.1, 0.05, 0.1, 200, 0.01, 0.05, 100, 0.05, 0.1]

# 包装系统方程
def system_ivp(t, y, params):
    return system_equations(y, t, params)

# 求解原始系统
solution = solve_ivp(system_ivp, [0, 100], initial_conditions, args=(params,), method='BDF', t_eval=t)

# 提取解
P, I, A, B = solution.y

# 绘制原始种群动态曲线
plt.figure(figsize=(10, 6))
plt.plot(t, P, label='Plants (P)', color='green')
plt.plot(t, I, label='Insects (I)', color='orange')
plt.plot(t, A, label='Herbivores (A)', color='blue')
plt.plot(t, B, label='Predators (B)', color='red')
plt.title('Population Dynamics of the Agricultural Ecosystem')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.legend(loc='upper right')
plt.grid(True)
plt.show()

# 定义目标函数（优化）
def objective(params):
    # Solve the system with the new params
    solution = solve_ivp(system_ivp, [0, 100], initial_conditions, args=(params,), method='BDF', t_eval=t)
    P, I, A, B = solution.y
    # Objective function: maximize plant population while controlling insects and predators
    return -np.sum(P) + 0.1 * np.sum(I) + 0.1 * np.sum(A) + 0.1 * np.sum(B)

# 参数优化范围
bounds = [(0.01, 0.2), (500, 1500), (0.001, 0.05), (0.001, 0.05),
          (0.1, 0.3), (300, 700), (0.01, 0.05), (0.01, 0.1),
          (0.01, 0.1), (0.01, 0.1), (0.05, 0.2), (100, 300),
          (0.01, 0.05), (0.05, 0.1), (50, 200), (0.01, 0.05), (0.05, 0.15)]

# 使用差分进化算法优化参数
result = differential_evolution(objective, bounds, maxiter=50)

# 打印优化后的参数
print("Optimal parameters found: ", result.x)

# 使用优化后的参数求解系统
optimal_params = result.x
solution_optimal = solve_ivp(system_ivp, [0, 100], initial_conditions, args=(optimal_params,), method='BDF', t_eval=t)

# 提取优化后的解
P_opt, I_opt, A_opt, B_opt = solution_optimal.y

# 绘制优化前后的种群动态对比
plt.figure(figsize=(10, 6))
plt.plot(t, P_opt, label='Plants (P) - Optimized', color='green', linestyle='--')
plt.plot(t, I_opt, label='Insects (I) - Optimized', color='orange', linestyle='--')
plt.plot(t, A_opt, label='Herbivores (A) - Optimized', color='blue', linestyle='--')
plt.plot(t, B_opt, label='Predators (B) - Optimized', color='red', linestyle='--')

# 绘制原始解
plt.plot(t, P, label='Plants (P) - Original', color='green')
plt.plot(t, I, label='Insects (I) - Original', color='orange')
plt.plot(t, A, label='Herbivores (A) - Original', color='blue')
plt.plot(t, B, label='Predators (B) - Original', color='red')

# 添加图例和标题
plt.title('Population Dynamics - Optimized vs Original')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.legend(loc='upper right')
plt.grid(True)
plt.show()
