"""
平推流反应器（PFR）数值模拟 - 体积流量对比分析
AI工具：使用Deepseek和Claude进行代码框架设计
功能：绘制不同体积流量下的浓度分布对比曲线
"""

import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import matplotlib
import math

# 配置matplotlib支持中文显示
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class PFRSimulator:
    """平推流反应器模拟器"""
    
    def __init__(self):
        # 反应器参数（给定条件）
        self.C_A0 = 1.0  # 入口浓度 mol/L
        self.D = 1.0  # 反应器直径 dm
        self.V_total = 10.0  # 反应器总体积 L
        
        # 计算截面积 dm^2
        self.A = math.pi * (self.D / 2) ** 2
        
        # 计算反应器长度 dm
        self.L_total = self.V_total / self.A
        
    def pfr_ode(self, C_A, z, k, n, v):
        """
        PFR微分方程
        dC_A/dz = -r_A / u
        其中：
        - r_A = k * C_A^n (反应速率)
        - u = v / A (线性速度，v为体积流速L/s，A为截面积dm^2)
        
        参数：
        - C_A: 浓度 mol/L
        - z: 反应器管长 dm
        - k: 速率常数
        - n: 反应级数
        - v: 体积流量 L/s
        """
        # 线性速度 dm/s
        # 注意: 1 L = 1 dm^3, 所以 v(L/s) = v(dm^3/s)
        u = v / self.A  # dm/s = (dm^3/s) / (dm^2) = dm/s
        
        # 反应速率 mol/(L·s)
        if C_A <= 0:
            r_A = 0
        else:
            r_A = k * (C_A ** n)
        
        # 返回浓度对管长的导数
        dC_A_dz = -r_A / u
        
        return dC_A_dz
    
    def simulate(self, v, k, n, num_points=100):
        """
        进行PFR数值求解
        
        返回：
        - L_array: 管长数组 dm
        - C_A_array: 浓度数组 mol/L
        - X_A: 出口转化率 %
        """
        # 生成管长数组 dm
        L_array = np.linspace(0, self.L_total, num_points)
        
        # 初始条件
        C_A_initial = [self.C_A0]
        
        # 使用ODE求解器求解
        C_A_array = odeint(self.pfr_ode, C_A_initial, L_array, args=(k, n, v))
        C_A_array = C_A_array.flatten()
        
        # 确保浓度非负
        C_A_array = np.maximum(C_A_array, 0)
        
        # 计算出口转化率
        C_A_exit = C_A_array[-1]
        X_A = (1 - C_A_exit / self.C_A0) * 100
        X_A = max(0, min(100, X_A))
        
        return L_array, C_A_array, X_A


def compare_n():
    """绘制不同反应级数的对比曲线"""
    # 初始化模拟器
    simulator = PFRSimulator()
    
    # 固定参数
    v = 0.5
    k = 0.1
    n_values = [0, 1, 2]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # 蓝色、橙色、绿色
    reaction_types = ['零级反应', '一级反应', '二级反应']
    
    # 创建图表
    plt.figure(figsize=(10, 6))
    
    # 存储对比数据
    comparison_data = []
    
    # 绘制三条曲线
    for n, color, reaction_type in zip(n_values, colors, reaction_types):
        L_array, C_A_array, X_A = simulator.simulate(v, k, n)
        plt.plot(L_array, C_A_array, color=color, linewidth=2.5, 
                label=f'n = {n} {reaction_type} (X_A = {X_A:.2f}%)', marker='o', markersize=3, markevery=10)
        comparison_data.append((n, reaction_type, X_A, C_A_array[-1]))
    
    # 设置图表样式
    plt.xlabel("管长 L (dm)", fontsize=12, fontweight='bold')
    plt.ylabel("浓度 $C_A$ (mol/L)", fontsize=12, fontweight='bold')
    plt.title(f"反应级数影响对比分析 (v = {v} L/s, k = {k})", fontsize=14, fontweight='bold', pad=20)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.legend(fontsize=11, loc='best', framealpha=0.9)
    
    # 设置轴范围
    plt.xlim(0, simulator.L_total)
    plt.ylim(0, 1.0)
    
    # 添加网格
    plt.tight_layout()
    
    # 显示对比数据表
    print("\n" + "="*70)
    print("反应级数对比分析结果（v=0.5 L/s, k=0.1）")
    print("="*70)
    print(f"{'反应级数 n':<15} {'反应类型':<15} {'出口浓度 (mol/L)':<20} {'转化率 X_A (%)':<20}")
    print("-"*70)
    for n, reaction_type, X_A, C_exit in comparison_data:
        print(f"{n:<15.0f} {reaction_type:<15} {C_exit:<20.6f} {X_A:<20.2f}")
    print("="*70)
    print("\n关键发现：")
    print(f"• 零级反应(n=0)转化率最高：{comparison_data[0][2]:.2f}%")
    print(f"• 二级反应(n=2)转化率最低：{comparison_data[2][2]:.2f}%")
    print(f"• 转化率差异：{comparison_data[0][2] - comparison_data[2][2]:.2f}%")
    print(f"• 反应级数越高，反应速率对浓度敏感性越强，转化率越低\n")
    
    # 显示图表
    plt.show()

if __name__ == "__main__":
    compare_n()
