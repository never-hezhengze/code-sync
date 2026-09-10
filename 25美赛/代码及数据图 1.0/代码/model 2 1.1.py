import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
import gc

# Define the system of equations
def system_equations(t, y, params):
    P, I, A, B = y
    r_P, K_P, alpha_P, alpha_A, r_I, K_I, beta_P, delta_I, gamma_I, eta_B, r_A, K_A, beta_A, r_B, K_B, mu_B, eta_B_2 = params

    dPdt = r_P * P * (1 - P / K_P) - alpha_P * P * I - alpha_A * P * A
    dIdt = r_I * I * (1 - I / K_I) + beta_P * P - delta_I * I - gamma_I * I - eta_B * I
    dAdt = r_A * A * (1 - A / K_A) - alpha_A * P - beta_A * I
    dBdt = r_B * B * (1 - B / K_B) + eta_B_2 * I - mu_B * B

    return [dPdt, dIdt, dAdt, dBdt]

# Initial conditions
initial_conditions = [100, 50, 30, 20]
t = np.linspace(0, 50, 100)  # 降低时间分辨率

# Parameters
params = [0.1, 500, 0.01, 0.05, 0.1, 300, 0.02, 0.05, 0.1, 0.01, 0.1, 300, 0.05, 0.1, 100, 0.02, 0.05]

# Solve the system with RK45
solution = solve_ivp(
    lambda t, y: system_equations(t, y, params),
    [t[0], t[-1]],
    initial_conditions,
    t_eval=t,
    method='RK45'
)

if solution.success:
    P, I, A, B = solution.y
    plt.figure(figsize=(10, 6))
    plt.plot(t, P, label='Plants (P)', color='green')
    plt.plot(t, I, label='Insects (I)', color='orange')
    plt.plot(t, A, label='Herbivores (A)', color='blue')
    plt.plot(t, B, label='Predators (B)', color='red')
    plt.title('Population Dynamics - Initial Parameters')
    plt.xlabel('Time')
    plt.ylabel('Population Size')
    plt.legend(loc='upper right')
    plt.grid(True)
    plt.show()
else:
    print("Initial solve failed:", solution.message)

# Define the objective function for optimization
def objective(params):
    try:
        solution = solve_ivp(
            lambda t, y: system_equations(t, y, params),
            [t[0], t[-1]],
            initial_conditions,
            t_eval=t,
            method='RK45'
        )
        if not solution.success:
            return 1e6
        P, _, _, _ = solution.y
        return -np.sum(P)
    except Exception as e:
        print(f"Error with parameters {params}: {e}")
        return 1e6
    finally:
        gc.collect()  # 强制释放内存

# Parameter bounds
bounds = [
    (0.01, 0.1), (200, 800), (0.001, 0.02), (0.01, 0.05),
    (0.05, 0.2), (100, 400), (0.01, 0.05), (0.01, 0.05),
    (0.01, 0.05), (0.01, 0.05), (0.05, 0.1), (200, 400),
    (0.01, 0.05), (0.05, 0.1), (50, 150), (0.01, 0.05), (0.01, 0.05)
]

# Optimize
result = differential_evolution(objective, bounds, maxiter=10, tol=0.01, popsize=5, workers=1)
print("Optimal parameters found: ", result.x)
