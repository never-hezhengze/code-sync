import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import pandas as pd

# 传输矩阵方法计算反射率（带色散模型n1修正）
def tmm_reflectance(n0, n1_base, k1, n2, d, wavelengths, n1_params=None):
    """
    n1_params: [A, B, C] 用于n1的色散模型修正
    n1(wavelength) = n1_base + A / (wavelength^2 - B) + C * wavelength^2
    这是基于Sellmeier色散方程的简化形式
    """
    if n1_params is None:
        n1_params = [0, 0, 0]  # 默认无修正
    
    A, B, C = n1_params
    
    # 计算波长相关的折射率修正（色散模型）
    # 避免除零错误
    denominator = wavelengths**2 - B
    denominator = np.where(np.abs(denominator) < 1e-10, 1e-10, denominator)
    
    n1_variation = A / denominator + C * wavelengths**2
    n1 = n1_base + n1_variation
    
    # 计算复折射率
    n1_complex = n1 + 1j*k1
    n2_complex = n2 + 1j*0  # 假设衬底没有吸收
    theta1 = np.arcsin(n0 / n1_complex.real)  # 斯涅尔定律计算入射角

    # 计算相位厚度
    delta1 = (2 * np.pi / wavelengths) * n1_complex * d * np.cos(theta1)
    
    # 计算各层的特征矩阵
    eta1 = n1_complex * np.cos(theta1)
    M1 = np.array([[np.cos(delta1), -1j/eta1 * np.sin(delta1)], 
                   [-1j*eta1 * np.sin(delta1), np.cos(delta1)]])
    
    eta2 = n2_complex * np.cos(theta1)
    
    # 计算总矩阵
    M = M1  # 假设只有一层
    Y = (M[1,0] + M[1,1] * eta2) / (M[0,0] + M[0,1] * eta2)
    
    # 计算反射系数和反射率
    r = (n0 - Y) / (n0 + Y)
    R = np.abs(r)**2
    return R

# 传输矩阵方法计算反射率（带线性变换）
def fit_function_with_linear(wavelengths, n1_base, k1, d, A, B, C, a, b):
    """
    拟合函数参数：
    n1_base: 基础折射率
    k1: 消光系数
    d: 厚度
    A, B, C: 色散模型修正参数
    a, b: 线性变换参数
    """
    # 计算反射率
    R_fitted = tmm_reflectance(n0, n1_base, k1, n2, d, wavelengths, [A, B, C])
    
    # 在线性变换后返回反射率
    R_transformed = a * R_fitted + b
    return R_transformed

# 读取实验数据
try:
    # 尝试读取Excel文件
    df = pd.read_excel('附件3.xlsx')
    print("Excel文件读取成功！")
    print("数据形状:", df.shape)
    print("列名:", df.columns.tolist())
    print("前几行数据:")
    print(df.head())
    
    # 第一列是波数(cm-1)，第二列是反射率(%)
    wavenumbers = df.iloc[:, 0].values  # 波数 (cm-1)
    R_experimental = df.iloc[:, 1].values / 100.0  # 转换为小数形式
    
    # 将波数转换为波长 (μm)
    wavelengths = 10000.0 / wavenumbers  # 波长 = 10000/波数 (μm)
    
    print(f"波数范围: {wavenumbers.min():.1f} - {wavenumbers.max():.1f} cm⁻¹")
    print(f"波长范围: {wavelengths.min():.3f} - {wavelengths.max():.3f} μm")
    print(f"反射率范围: {R_experimental.min():.3f} - {R_experimental.max():.3f}")
    
except Exception as e:
    print(f"读取Excel文件时出错: {e}")
    print("使用模拟数据...")
    # 如果读取失败，使用模拟数据
    wavelengths = np.linspace(1, 2, 100)  # 波长范围（单位：微米）
    R_experimental = np.random.uniform(0.1, 0.9, len(wavelengths))  # 随机反射率数据

n0 = 1  # 空气的折射率
n2 = 2.4  # 衬底折射率（针对红外范围调整）

# 初始猜测参数：n1_base, k1, d, A, B, C, a, b
initial_guess_with_linear = [3.5, 0.01, 4.0, 0.1, 1.0, 0.001, 1.0, 0.0]  # 包括 a 和 b 的初始值

# 设置拟合参数边界
bounds_with_linear = ([1.0, 0.0, 0.1, -10.0, 0.1, -0.01, 0.0, -0.1], 
                      [5.0, 1.0, 10.0, 10.0, 100.0, 0.01, 2.0, 0.1])

# 执行拟合
params_opt, params_cov = curve_fit(fit_function_with_linear, wavelengths, R_experimental, 
                                   p0=initial_guess_with_linear, bounds=bounds_with_linear, maxfev=5000)

# 获取拟合参数
n1_base_fit, k1_fit, d_fit, A_fit, B_fit, C_fit, a_fit, b_fit = params_opt

# 计算拟合后的反射率
R_fitted_with_transform = fit_function_with_linear(wavelengths, *params_opt)

# 打印拟合结果
print(f"拟合的参数：")
print(f"n1_base = {n1_base_fit:.4f}, k1 = {k1_fit:.4f}, d = {d_fit:.4f} μm")
print(f"A = {A_fit:.4f}, B = {B_fit:.4f}, C = {C_fit:.6f}")
print(f"线性变换：a = {a_fit:.4f}, b = {b_fit:.4f}")

# 计算拟合误差
errors = np.sqrt(np.diag(params_cov))
print(f"\n参数误差：")
print(f"n1_base 误差 = ±{errors[0]:.4f}")
print(f"k1 误差 = ±{errors[1]:.4f}")
print(f"d 误差 = ±{errors[2]:.4f}")
print(f"A 误差 = ±{errors[3]:.4f}")
print(f"B 误差 = ±{errors[4]:.4f}")
print(f"C 误差 = ±{errors[5]:.6f}")

# 计算拟合优度
R_fitted = fit_function_with_linear(wavelengths, *params_opt)
r_squared = 1 - np.sum((R_experimental - R_fitted)**2) / np.sum((R_experimental - np.mean(R_experimental))**2)
print(f"\n拟合优度 R² = {r_squared:.4f}")

# 绘制拟合结果
plt.figure(figsize=(15, 10))

# 子图1：波数-反射率图
plt.subplot(3, 1, 1)
plt.plot(wavenumbers, R_experimental, 'bo', label="实验数据", markersize=2, alpha=0.6)
plt.plot(wavenumbers, R_fitted_with_transform, 'r-', label="拟合曲线", linewidth=2)
plt.xlabel("波数 (cm⁻¹)")
plt.ylabel("反射率")
plt.title("带线性变换的拟合结果")
plt.legend()
plt.grid(True, alpha=0.3)

# 子图2：残差图
plt.subplot(3, 1, 2)
residuals = R_experimental - R_fitted_with_transform
plt.plot(wavenumbers, residuals, 'go', markersize=2, alpha=0.6)
plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
plt.xlabel("波数 (cm⁻¹)")
plt.ylabel("残差")
plt