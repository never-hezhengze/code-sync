import numpy as np
import matplotlib.pyplot as plt
# Parameters for the model
r_P = 0.1 # Growth rate of plants
K_P = 500 # Carrying capacity of plants K_P = 500 # Carrying capacity of plants
alpha_P = 0.005 # Effect of insects on plant population insects on plant population
r_I = 0.2 # Growth rate of insects r_I = 0.2 # Growth rate of insects
K_I = 200 # Carrying capacity of insects K_I = 200 # Carrying capacity of insects
beta_P = 0.05 # Effect of plants on insect population beta_P = 0.05 # Effect of plants on insect population
delta_I = 0.1 # Natural mortality rate of insects delta_I = 0.1 # Natural mortality rate of insects
gamma_I = 0.1 # Death rate of insects due to pesticide gamma_I = 0.1 # Death rate of insects due to pesticide
r_C = 0.1 # Growth rate of birds/bats r_C = 0.1 # Growth rate of birds/bats
K_C = 100 # Carrying capacity of birds/bats K_C = 100 # Carrying capacity of birds/bats K_C = 100 # Carrying capacity of birds/bats
eta_I = 0.1 # Efficiency of insect consumption by birds/bats eta_I = 0.1 # Efficiency of insect consumption by birds/bats
mu_C = 0.05 # Natural mortality rate of birds/bats mu_C = 0.05 # Natural mortality rate of birds/bats mu_C = 0.05 # Natural mortality rate of birds/bats
# Create a figure with subplots # Create a figure with subplots
plt.figure(figsize=(10, 6))
# Plot for Plants
plt.subplot(3, 1, 1)
plt.plot(t, P, label="Plants", color='g', linewidth=2)
plt.title("Population Dynamics of Plants, Insects, and Birds/Bats")
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend(loc='best')
# Plot for Insects
plt.subplot(3, 1, 2)
plt.plot(t, I, label="Insects", color='b', linewidth=2)
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend(loc='best')


# Plot for Birds/Bats
plt.subplot(3, 1, 3)
plt.plot(t, C, label="Birds/Bats", color='r', linewidth=2)
plt.xlabel("Time (days)")
plt.ylabel("Population")
plt.legend(loc='best')

# Adjust layout to prevent overlap

plt.tight_layout()


# Show the plot
plt.show()
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint


# Parameters for the model
r_P = 0.1 # Growth rate of plants 植物生长速率
K_P = 500 # Carrying capacity of plants 植物环境容量
alpha_P = 0.005 # Effect of insects on plant population  植物对昆虫的抗性系数
r_I = 0.2 # Growth rate of insects 昆虫增长率
K_I = 200 # Carrying capacity of insects 昆虫环境承载量
beta_P = 0.05 # Effect of plants on insect population 昆虫对植物的食害效应
delta_I = 0.1 # Natural mortality rate of insects  昆虫的自然死亡率
gamma_I = 0.1 # Death rate of insects due to pesticide 昆虫受到杀虫剂影响都死亡率
r_C = 0.1 # Growth rate of birds/bats 鸟类或蝙蝠自然增长率
K_C = 100 # Carrying capacity of birds/bats 蝙蝠或鸟类的环境承载量
eta_I = 0.1 # Efficiency of insect consumption by birds/bats 鸟类或蝙蝠从昆虫中获得的食物
mu_C = 0.05 # Natural mortality rate of birds/bats 蝙蝠或鸟类的自然死亡率



# Model function
def model(y, t, r_P, K_P, alpha_P, r_I, K_I, beta_P, delta_I,gamma_I, r_C, K_C, eta_I, mu_C):
 P, I, C = y # P: Plants, I: Insects, C: Birds/Bats

 # Plant growth (Logistic growth and insect effect)
 dPdt = r_P * P * (1 - P / K_P) - alpha_P * P * I
 # Insect population dynamics (Logistic growth, plant consumption, pesticide effect)
 dIdt = r_I * I * (1 - I / K_I) + beta_P * P - delta_I * I - gamma_I * I
 # Birds/Bats population dynamics (Logistic growth, insect consumption)
 return [dPdt, dIdt, dCdt]

# Initial populations
P0 = 100 # Initial plant population
I0 = 50 # Initial insect population
C0 = 10 # Initial bird/bat population
y0 = [P0, I0, C0] # Initial conditions for the populations
# Time grid
t = np.linspace(0, 100, 1000) # Time from 0 to 100, with 1000 points
# Solve the differential equations
solution = odeint(model, y0, t, args=(r_P, K_P, alpha_P, r_I, K_I,
beta_P, delta_I, gamma_I, r_C, K_C, eta_I, mu_C))
# Extract the results
P = solution[:, 0] # Plant population over time
I = solution[:, 1] # Insect population over time 
C = solution[:, 2] # Bird/bat population over time
# Create a figure with subplots
plt.figure(figsize=(10, 6))
# Plot for Plants
plt.subplot(3, 1, 1)
plt.plot(t, P, label="Plants", color='g', linewidth=2)
plt.title("Population Dynamics of Plants, Insects, and Birds/Bats")
plt.xlabel("Time (days)")
plt