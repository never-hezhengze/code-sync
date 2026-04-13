"""
PFR数值求解与解析解的验证
用于检查数值计算的正确性
"""

import numpy as np
from scipy.integrate import odeint
import math

# 反应器参数
C_A0 = 1.0  # 入口浓度 mol/L
D = 1.0     # 直径 dm
V_total = 10.0  # 总体积 L
A = math.pi * (D / 2) ** 2  # 截面积 dm^2
L_total = V_total / A  # 总长度 dm

print("=" * 60)
print("PFR数值验证")
print("=" * 60)
print(f"截面积 A = {A:.4f} dm²")
print(f"总长度 L_total = {L_total:.2f} dm")
print()

# 测试参数
v = 0.5  # L/s
k = 0.1  # 1/s (假设一阶反应)
n = 1.0  # 反应级数

u = v / A  # 线性速度 dm/s
t_residence = L_total / u  # 平均停留时间 s

print(f"计算参数:")
print(f"体积流量 v = {v} L/s")
print(f"线性速度 u = v/A = {v}/{A:.4f} = {u:.4f} dm/s")
print(f"停留时间 τ = L_total/u = {L_total:.2f}/{u:.4f} = {t_residence:.2f} s")
print()

# ===== 一阶反应的解析解 =====
print("-" * 60)
print("一阶反应 (n=1) 的解析解:")
print("-" * 60)

# 解析解: C_A(z) = C_A0 * exp(-k*z/u)
z_array = np.linspace(0, L_total, 100)
C_A_analytical = C_A0 * np.exp(-k * z_array / u)
X_A_analytical = (1 - C_A_analytical[-1] / C_A0) * 100

print(f"特征参数 k*τ = {k}*{t_residence:.2f} = {k*t_residence:.4f}")
print(f"解析解出口浓度: C_A(exit) = {C_A_analytical[-1]:.6f} mol/L")
print(f"解析解转化率: X_A = {X_A_analytical:.2f}%")
print()

# ===== 数值求解 =====
print("-" * 60)
print("一阶反应数值求解 (ODE):")
print("-" * 60)

def pfr_ode(C_A, z, k, n, v, A):
    u = v / A
    if C_A <= 0:
        r_A = 0
    else:
        r_A = k * (C_A ** n)
    dC_A_dz = -r_A / u
    return dC_A_dz

C_A_numerical = odeint(pfr_ode, [C_A0], z_array, args=(k, n, v, A))
C_A_numerical = C_A_numerical.flatten()
X_A_numerical = (1 - C_A_numerical[-1] / C_A0) * 100

print(f"数值解出口浓度: C_A(exit) = {C_A_numerical[-1]:.6f} mol/L")
print(f"数值解转化率: X_A = {X_A_numerical:.2f}%")
print()

# 比较
print("-" * 60)
print("解析解 vs 数值解对比:")
print("-" * 60)
error_concentration = abs(C_A_analytical[-1] - C_A_numerical[-1]) / C_A_analytical[-1] * 100
error_conversion = abs(X_A_analytical - X_A_numerical)
print(f"出口浓度误差: {error_concentration:.4f}%")
print(f"转化率差异: {error_conversion:.4f}%")
print()

# ===== 验证参数影响 =====
print("-" * 60)
print("参数变化影响分析:")
print("-" * 60)

test_cases = [
    ("v增大", 1.0, k, n),
    ("v减小", 0.2, k, n),
    ("k增大", v, 0.3, n),
    ("k减小", v, 0.05, n),
]

for desc, v_test, k_test, n_test in test_cases:
    u_test = v_test / A
    C_A_exit_test = C_A0 * np.exp(-k_test * L_total / u_test)
    X_A_test = (1 - C_A_exit_test / C_A0) * 100
    print(f"{desc:8} (v={v_test}, k={k_test}): X_A = {X_A_test:6.2f}%, C_A_exit = {C_A_exit_test:.4f}")

print()
print("✓ 验证完成！如果数值解与解析解相符，说明计算逻辑正确。")
