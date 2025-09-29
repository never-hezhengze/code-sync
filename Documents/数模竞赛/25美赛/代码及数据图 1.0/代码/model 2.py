import numpy as np
import matplotlib.pyplot as plt


def system_equations(y, t, params):
 P, I, A, B = y
 r_P, K_P, alpha_P, alpha_A, r_I, K_I, beta_P, delta_I, gamma_I,
eta_B, r_A, K_A, beta_A, r_B, K_B, mu_B, eta_B_2 = params


 #Plant growth equation
 dPdt = r_P * P * (1 - P / K_P) - alpha_P * P * I - alpha_A * P * A


 # Insect population equation
 dIdt = r_I * I * (1 - I / K_I) + beta_P * P - delta_I * I - gamma_I * I - eta_B * I


 # Herbivore population equation
 dAdt = r_A * A * (1 - A / K_A) - alpha_A * P - beta_A * I


 # Predator population equation
 dBdt = r_B * B * (1 - B / K_B) + eta_B_2 * I - mu_B * B
 return [dPdt, dIdt, dAdt, dBdt]


# Initial conditions: [P, I, A, B]
initial_conditions = [100, 50, 30, 20] # Initial populations
# Time array
t = np.linspace(0, 100, 1000)

# Parameters: r_P, K_P, alpha_P, alpha_A, r_I, K_I, beta_P, delta_I, gamma_I, eta_B, r_A, K_A, beta_A, r_B, K_B, mu_B, eta_B_2
params = [0.1, 500, 0.01, 0.05, 0.1, 300, 0.02, 0.05, 0.1, 0.01, 0.1, 300, 0.05, 0.1, 100, 0.02, 0.05]
# Solve the differential equations
solution = odeint(system_equations, initial_conditions, t,
args=(params,))
# Extract the populations of each species
P, I, A, B = solution.T
# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(t, P, label='Plants (P)', color='green')
plt.plot(t, I, label='Insects (I)', color='orange')
plt.plot(t, A, label='Herbivores (A)', color='blue')
plt.plot(t, B, label='Predators (B)', color='red')
# Add labels and title
plt.title('Population Dynamics of the Agricultural Ecosystem')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.legend(loc='upper right')
plt.grid(True)
plt.show()
def objective(params):
 # Initial conditions and parameters for optimization
 initial_conditions = [100, 50, 30, 20]
 t = np.linspace(0, 100, 1000)
 # Solve the system with the new params
 solution = odeint(system_equations, initial_conditions, t,
args=(params,))
 P, I, A, B = solution.T

 # Objective function: maximize plant population while controlling insects and predators
 return -np.sum(P) + 0.1 * np.sum(I) + 0.1 * np.sum(A) + 0.1 * np.sum(B)


# Bounds for the parameters to optimize
bounds = [(0.01, 0.2), (100, 1000), (0.001, 0.05), (0.01, 0.1),
          (0.05, 0.2), (100, 500), (0.01, 0.1), (0.01, 0.1),
          (0.01, 0.1), (0.01, 0.1), (0.05, 0.2), (100, 500),
          (0.01, 0.1), (0.05, 0.2), (50, 200), (0.01, 0.1), (0.01,0.1)]

# Use differential evolution to find the optimal parameters
result = differential_evolution(objective, bounds, maxiter=50)


# Print the optimal parameters
print("Optimal parameters found: ", result.x)


# Get the optimal parameters from the result
optimal_params = result.x


# Solve the system again with the optimal parameters
solution_optimal = odeint(system_equations, initial_conditions, t,
args=(optimal_params,))


# Extract the populations of each species
P_opt, I_opt, A_opt, B_opt = solution_optimal.T


# Plot the results for optimal parameters
plt.figure(figsize=(10, 6))
plt.plot(t, P_opt, label='Plants (P) - Optimized' Optimized', color='green',
linestyle='--')
plt.plot(t, I_opt, label='Insects (I) - Optimized' 'Insects (I) - Optimized', color='orange',
linestyle='--')
plt.plot(t, A_opt, label='Herbivores (A) - Optimized' 'Herbivores (A) - Optimized',
color='blue', linestyle='--')
plt.plot(t, B_opt, label='Predators (B) - Optimized' 'Predators (B) Optimized', color='red',
linestyle='--' '--')


# Plot the original solution for comparison # Plot the original solution for comparison
plt.plot(t, P, label='Plants (P) - Original' 'Plants (P) , color='green')
plt.plot(t, I, label='Insects (I) - Original', color='orange')
plt.plot(t, A, label='Herbivores (A) - Original', color='blue')
plt.plot(t, B, label='Predators (B) - Original', color='red')


# Add labels and title
plt.title('Population Dynamics - Optimized vs Original')
plt.xlabel('Time')
plt.ylabel('Population Size')
plt.legend(loc='upper right')
plt.grid(True)
plt.show()