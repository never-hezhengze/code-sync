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

# 拟合模型（定义拟合函数，包含色散模型n1修正）
def fit_function(wavelengths, n1_base, k1, d, A, B, C):
    """
    拟合函数参数：
    n1_base: 基础折射率
    k1: 消光系数
    d: 厚度
    A, B, C: 色散模型修正参数
    """
    n1_params = [A, B, C]
    return tmm_reflectance(n0, n1_base, k1, n2, d, wavelengths, n1_params)

# 初始猜测参数（包含色散模型n1修正）
initial_guess = [3.5, 0.01, 4.0, 0.1, 1.0, 0.001]  # n1_base, k1, d, A, B, C

# 拟合数据（优化波峰波谷拟合）
try:
    # 计算数据的一阶导数来识别波峰波谷区域
    R_diff = np.gradient(R_experimental)
    R_diff_smooth = np.convolve(R_diff, np.ones(5)/5, mode='same')  # 平滑处理
    
    # 计算权重：波峰波谷区域权重更高
    weights = np.ones_like(R_experimental)
    # 在导数变化大的地方增加权重
    weights += 2.0 * np.abs(R_diff_smooth) / np.max(np.abs(R_diff_smooth))
    # 在反射率变化大的地方增加权重
    R_variation = np.abs(R_experimental - np.mean(R_experimental))
    weights += 1.5 * R_variation / np.max(R_variation)
    
    # 归一化权重
    weights = weights / np.mean(weights)
    
    print(f"权重统计: 最小={weights.min():.3f}, 最大={weights.max():.3f}, 平均={weights.mean():.3f}")
    
    # 设置参数边界：放宽A和B的范围以更好地捕捉幅度变化
    bounds = ([1.0, 0.0, 0.1, -20.0, 0.01, -0.02], 
              [5.0, 1.0, 10.0, 20.0, 200.0, 0.02])
    
    # 多次迭代优化
    best_params = None
    best_r2 = -np.inf
    
    for iteration in range(3):
        # 添加随机扰动到初始猜测
        if iteration > 0:
            noise = np.random.normal(0, 0.1, len(initial_guess))
            p0_iter = initial_guess + noise
        else:
            p0_iter = initial_guess
            
        try:
            params_opt, params_cov = curve_fit(fit_function, wavelengths, R_experimental, 
                                              p0=p0_iter, bounds=bounds, maxfev=10000,
                                              sigma=1/weights, absolute_sigma=False)
            
            # 计算当前拟合的R²
            R_fitted_iter = fit_function(wavelengths, *params_opt)
            r2_iter = 1 - np.sum((R_experimental - R_fitted_iter)**2) / np.sum((R_experimental - np.mean(R_experimental))**2)
            
            if r2_iter > best_r2:
                best_r2 = r2_iter
                best_params = params_opt
                print(f"迭代 {iteration+1}: R² = {r2_iter:.4f}")
                
        except Exception as e:
            print(f"迭代 {iteration+1} 失败: {e}")
            continue
    
    if best_params is not None:
        params_opt = best_params
        print(f"最佳拟合 R² = {best_r2:.4f}")
    else:
        # 如果所有迭代都失败，使用标准拟合
        params_opt, params_cov = curve_fit(fit_function, wavelengths, R_experimental, 
                                          p0=initial_guess, bounds=bounds, maxfev=5000)
    
    # 拟合结果
    n1_base_fit, k1_fit, d_fit, A_fit, B_fit, C_fit = params_opt
    print(f"\n拟合的参数：")
    print(f"n1_base (基础折射率) = {n1_base_fit:.4f}")
    print(f"k1 (消光系数) = {k1_fit:.4f}")
    print(f"d (厚度) = {d_fit:.4f} μm")
    print(f"\n色散模型修正：")
    print(f"A (色散系数) = {A_fit:.4f}")
    print(f"B (共振波长平方) = {B_fit:.4f}")
    print(f"C (高阶色散系数) = {C_fit:.6f}")
    
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
    R_fitted = fit_function(wavelengths, *params_opt)
    r_squared = 1 - np.sum((R_experimental - R_fitted)**2) / np.sum((R_experimental - np.mean(R_experimental))**2)
    print(f"\n拟合优度 R² = {r_squared:.4f}")
    
    # 绘制拟合结果
    plt.figure(figsize=(15, 10))
    
    # 子图1：波数-反射率图
    plt.subplot(3, 1, 1)
    plt.plot(wavenumbers, R_experimental, 'bo', label="实验数据", markersize=2, alpha=0.6)
    plt.plot(wavenumbers, R_fitted, 'r-', label="拟合曲线", linewidth=2)
    plt.xlabel("波数 (cm⁻¹)")
    plt.ylabel("反射率")
    plt.title("传输矩阵方法拟合结果（带n1浮动修正）")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 子图2：残差图
    plt.subplot(3, 1, 2)
    residuals = R_experimental - R_fitted
    plt.plot(wavenumbers, residuals, 'go', markersize=2, alpha=0.6)
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
    plt.xlabel("波数 (cm⁻¹)")
    plt.ylabel("残差")
    plt.title("拟合残差")
    plt.grid(True, alpha=0.3)
    
    # 子图3：n1的波长变化（色散模型）
    plt.subplot(3, 1, 3)
    denominator = wavelengths**2 - B_fit
    denominator = np.where(np.abs(denominator) < 1e-10, 1e-10, denominator)
    n1_variation = A_fit / denominator + C_fit * wavelengths**2
    n1_total = n1_base_fit + n1_variation
    
    plt.plot(wavenumbers, n1_total, 'm-', linewidth=2, 
             label=f"n1(λ) = {n1_base_fit:.3f} + {A_fit:.3f}/(λ²-{B_fit:.3f}) + {C_fit:.6f}×λ²")
    plt.axhline(y=n1_base_fit, color='k', linestyle='--', alpha=0.5, label=f"基础折射率 = {n1_base_fit:.3f}")
    plt.xlabel("波数 (cm⁻¹)")
    plt.ylabel("折射率 n1")
    plt.title("折射率的波长变化（色散模型）")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 波峰波谷拟合质量分析
    print(f"\n=== 波峰波谷拟合质量分析 ===")
    
    # 找到实验数据的局部极值点
    from scipy.signal import find_peaks
    peaks_exp, _ = find_peaks(R_experimental, height=np.mean(R_experimental), distance=50)
    valleys_exp, _ = find_peaks(-R_experimental, height=-np.mean(R_experimental), distance=50)
    
    # 找到拟合曲线的局部极值点
    peaks_fit, _ = find_peaks(R_fitted, height=np.mean(R_fitted), distance=50)
    valleys_fit, _ = find_peaks(-R_fitted, height=-np.mean(R_fitted), distance=50)
    
    print(f"实验数据波峰数量: {len(peaks_exp)}")
    print(f"拟合曲线波峰数量: {len(peaks_fit)}")
    print(f"实验数据波谷数量: {len(valleys_exp)}")
    print(f"拟合曲线波谷数量: {len(valleys_fit)}")
    
    # 计算波峰波谷的幅度误差
    if len(peaks_exp) > 0 and len(peaks_fit) > 0:
        # 找到最近的拟合波峰
        peak_errors = []
        for peak_exp in peaks_exp:
            if len(peaks_fit) > 0:
                closest_fit_idx = np.argmin(np.abs(peaks_fit - peak_exp))
                closest_fit_peak = peaks_fit[closest_fit_idx]
                error = abs(R_experimental[peak_exp] - R_fitted[closest_fit_peak])
                peak_errors.append(error)
        
        if peak_errors:
            print(f"波峰幅度平均误差: {np.mean(peak_errors):.4f}")
            print(f"波峰幅度最大误差: {np.max(peak_errors):.4f}")
    
    if len(valleys_exp) > 0 and len(valleys_fit) > 0:
        # 找到最近的拟合波谷
        valley_errors = []
        for valley_exp in valleys_exp:
            if len(valleys_fit) > 0:
                closest_fit_idx = np.argmin(np.abs(valleys_fit - valley_exp))
                closest_fit_valley = valleys_fit[closest_fit_idx]
                error = abs(R_experimental[valley_exp] - R_fitted[closest_fit_valley])
                valley_errors.append(error)
        
        if valley_errors:
            print(f"波谷幅度平均误差: {np.mean(valley_errors):.4f}")
            print(f"波谷幅度最大误差: {np.max(valley_errors):.4f}")
    
    # 打印更详细的分析结果
    print(f"\n=== 详细分析结果 ===")
    print(f"数据点数: {len(wavelengths)}")
    print(f"波长范围: {wavelengths.min():.3f} - {wavelengths.max():.3f} μm")
    print(f"波数范围: {wavenumbers.min():.1f} - {wavenumbers.max():.1f} cm⁻¹")
    print(f"平均反射率: {R_experimental.mean():.3f}")
    print(f"反射率标准差: {R_experimental.std():.3f}")
    print(f"最大残差: {np.abs(residuals).max():.4f}")
    print(f"平均绝对残差: {np.abs(residuals).mean():.4f}")
    print(f"均方根误差: {np.sqrt(np.mean(residuals**2)):.4f}")
    
except Exception as e:
    print(f"拟合过程中出错: {e}")
    print("可能的原因：")
    print("1. 数据格式不正确")
    print("2. 初始参数猜测不合适")
    print("3. 数据范围超出模型适用范围")
