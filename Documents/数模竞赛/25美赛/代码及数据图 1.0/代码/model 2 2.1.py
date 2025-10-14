import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
import gc

# Define the system of equations
def system_equations(t, y, params):
    P, I, A, B = np.maximum(y, 1e-6)  # Ensure no negative populations
    r_P, K_P, alpha_P, alpha_A, r_I, K_I, beta_P, delta_I, gamma_I, eta_B, r_A, K_A, beta_A, r_B, K_B, mu_B, eta_B_2 = params

    dPdt = r_P * P * (1 - P / K_P) - alpha_P * P * I - alpha_A * P * A
    dIdt = r_I * I * (1 - I / K_I) + beta_P * P - delta_I * I - gamma_I * I - eta_B * I
    dAdt = r_A * A * (1 - A / K_A) - alpha_A * P - beta_A * I
    dBdt = r_B * B * (1 - B / K_B) + eta_B_2 * I - mu_B * B

    return [dPdt, dIdt, dAdt, dBdt]

# Initial conditions
initial_conditions = [100, 30, 10, 5]  # Adjusted initial conditions
t = np.linspace(0, 20, 50)  # Shortened time range

# Parameters
params = [0.08, 500, 0.007, 0.03, 0.12, 300, 0.013, 0.035, 0.06, 0.02, 0.07, 320, 0.025, 0.07, 130, 0.02, 0.025]

# Parameter bounds
bounds = [
    (0.05, 0.1), (400, 600), (0.005, 0.01), (0.02, 0.03),
    (0.1, 0.15), (250, 350), (0.01, 0.015), (0.03, 0.04),
    (0.05, 0.08), (0.01, 0.03), (0.05, 0.08), (300, 350),
    (0.02, 0.03), (0.05, 0.08), (120, 140), (0.01, 0.03),
    (0.02, 0.03)
]

# Define the objective function for optimization
def objective(params):
    try:
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
            return 1e6
        P, _, _, _ = solution.y
        return -np.sum(P)
    except Exception as e:
        print(f"Error with parameters {params}: {e}")
        return 1e6
    finally:
        gc.collect()

# Optimize and compare results
def optimize_and_compare():
    try:
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
            P, I, A, B = solution_original.y
        else:
            print("Initial solve failed:", solution_original.message)
            return
    except Exception as e:
        print("Error during initial solve:", e)
        return

    # Optimize
    result = differential_evolution(objective, bounds, maxiter=10, tol=0.01, popsize=5, workers=1)
    print("Optimal parameters found: ", result.x)

    # Solve the system with optimal parameters
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
        P_opt, I_opt, A_opt, B_opt = solution_optimal.y

        # Plot comparison for all populations
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

# Main execution
if __name__ == '__main__':
    optimize_and_compare()
