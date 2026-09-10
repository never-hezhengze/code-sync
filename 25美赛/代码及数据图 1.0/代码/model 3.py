import numpy as np
import matplotlib.pyplot as plt

def ecosystem_model(y, t, params):
 I, P, A, B, Bee = y
 r_I, K_I, r_P, K_P, r_B, K_B, r_Bee, K_Bee, beta_P, alpha_P, alpha_A, tau_B, eta_B, sigma_B, zeta_B, mu_B = params


 #昆虫种群变化方程
 dI_dt = r_I * I * (1 - I / K_I) + beta_P * P - alpha_P * P * I - alpha_A * P * A - eta_B * I - zeta_B * I * B
 #植物种群变化方程
 dP_dt = r_P * P * (1 - P / K_P) - alpha_P * P * I - alpha_A * P * A + tau_B * B * P
 # 捕食性动物种群变化方程
 dA_dt = 0 #
#蝙蝠种群变化方程
 dB_dt = r_B * B * (1 - B / K_B) + eta_B * I - mu_B * B
 # 蜜蜂种群变化方程
 dBee_dt = r_Bee * Bee * (1 - Bee / K_Bee) + sigma_B * P

 return [dI_dt, dP_dt, dA_dt, dB_dt, dBee_dt]

 def objective(params):
     #设置初始种群数量
     I0 = 50  #初始昆虫数量
     P0 = 100  #初始植物数量
     A0 = 30  #初始捕食性动物数量
     B0 = 5  #初始蝙蝠数量
     Bee0 = 5  #初始蜜蜂数量

     #设定初始状态
     y0 = [I0, P0, A0, B0, Bee0]
     # 时间范围
     t = np.linspace(0, 50, 500)
     #设置模型参数
     r_I, K_I = 0.1, 1000
     r_P, K_P = 0.2, 500
     r_B, K_B = 0.1, 100
     r_Bee, K_Bee = 0.1, 50
     beta_P, alpha_P, alpha_A = 0.05, 0.02, 0.01
     tau_B, eta_B, sigma_B = params[0], params[1], params[2]
     zeta_B, mu_B = 0.01, 0.1
     model_params = [r_I, K_I, r_P, K_P, r_B, K_B, r_Bee, K_Bee, beta_P, alpha_P, alpha_A, tau_B, eta_B, sigma_B, zeta_B, mu_B]

     # 求解ode模型
     result = odeint(ecosystem_model, y0, t, args=(model_params,))
     #目标：最大化植物数量
     P_final = result[:, 1][-1]  #最后时刻植物数量
     return -P_final  #最小化负植物数量（最大化植物数量）

 #使用最优参数运行模型
 optimal_params = result.x
 r_I, K_I = 0.1, 1000
 r_P, K_P = 0.2, 500
 r_B, K_B = 0.1, 100
 r_Bee, K_Bee = 0.1, 50
 beta_P, alpha_P, alpha_A = 0.05, 0.02, 0.01
 tau_B, eta_B, sigma_B = optimal_params[0], optimal_params[1], optimal_params[2]
 zeta_B, mu_B = 0.01, 0.1
 model_params = [r_I, K_I, r_P, K_P, r_B, K_B, r_Bee, K_Bee, beta_P,
                 alpha_P, alpha_A, tau_B, eta_B, sigma_B, zeta_B, mu_B]
 #初始种群数量
 y0 = [50, 100, 30, 5, 5]  #
 t = np.linspace(0, 50, 500)
 # 求解ode模型
 result = odeint(ecosystem_model, y0, t, args=(model_params,))
 #绘制物种种群随时间的变化
 plt.figure(figsize=(10, 6))
 plt.plot(t, result[:, 0], label='Insects (I)', color='blue')
 plt.plot(t, result[:, 1], label='Plants (P)', color='green')
 plt.plot(t, result[:, 2], label='Herbivores (A)', color='red')
 plt.plot(t, result[:, 3], label='Bats (B)', color='purple')
 plt.plot(t, result[:, 4], label='Bees (Bee)', color='orange')
 plt.xlabel('Time (Years)')
 plt.ylabel('Population')
 plt.title('Ecological System Dynamics with Bat and Bee Introduction')
 plt.legend()
 plt.grid(True)
 plt.show()