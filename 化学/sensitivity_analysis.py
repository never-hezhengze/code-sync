"""
PFR参数敏感性分析
基础条件：v=0.5, k=0.1, n=1
进行±20%的参数变化，计算转化率的相对变化和灵敏度
"""

import numpy as np
from scipy.integrate import odeint
import math

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
        """PFR微分方程"""
        u = v / self.A
        
        if C_A <= 0:
            r_A = 0
        else:
            r_A = k * (C_A ** n)
        
        dC_A_dz = -r_A / u
        
        return dC_A_dz
    
    def simulate(self, v, k, n, num_points=100):
        """进行PFR数值求解"""
        L_array = np.linspace(0, self.L_total, num_points)
        C_A_initial = [self.C_A0]
        
        C_A_array = odeint(self.pfr_ode, C_A_initial, L_array, args=(k, n, v))
        C_A_array = C_A_array.flatten()
        C_A_array = np.maximum(C_A_array, 0)
        
        C_A_exit = C_A_array[-1]
        X_A = (1 - C_A_exit / self.C_A0) * 100
        X_A = max(0, min(100, X_A))
        
        return X_A


def sensitivity_analysis():
    """进行参数敏感性分析"""
    simulator = PFRSimulator()
    
    # 基础条件
    v_base = 0.5
    k_base = 0.1
    n_base = 1.0
    
    X_A_base = simulator.simulate(v_base, k_base, n_base)
    
    print("="*80)
    print("PFR参数敏感性分析")
    print("="*80)
    print(f"基础条件：v = {v_base} L/s, k = {k_base}, n = {n_base}")
    print(f"基础转化率：X_A = {X_A_base:.2f}%\n")
    
    # 参数变化列表：(参数名, 基础值, 变化倍数)
    parameters = [
        ('v', v_base, 0.8),  # v减小20%
        ('v', v_base, 1.2),  # v增大20%
        ('k', k_base, 0.8),  # k减小20%
        ('k', k_base, 1.2),  # k增大20%
        ('n', n_base, 0.8),  # n减小20%
        ('n', n_base, 1.2),  # n增大20%
    ]
    
    results = []
    
    for param, base_val, ratio in parameters:
        if param == 'v':
            new_val = base_val * ratio
            X_A_new = simulator.simulate(new_val, k_base, n_base)
            param_change = (ratio - 1) * 100
            param_relative_change = param_change
            
        elif param == 'k':
            new_val = base_val * ratio
            X_A_new = simulator.simulate(v_base, new_val, n_base)
            param_change = (ratio - 1) * 100
            param_relative_change = param_change
            
        elif param == 'n':
            new_val = base_val * ratio
            X_A_new = simulator.simulate(v_base, k_base, new_val)
            param_change = new_val - base_val
            param_relative_change = param_change / base_val * 100
        
        # 转化率的相对变化
        X_A_relative_change = X_A_new - X_A_base
        X_A_relative_change_percent = X_A_relative_change
        
        # 灵敏度 = 转化率相对变化 / 参数相对变化
        if param == 'n':
            sensitivity = X_A_relative_change_percent / (param_change / base_val * 100) if param_change != 0 else 0
        else:
            sensitivity = X_A_relative_change_percent / param_relative_change if param_relative_change != 0 else 0
        
        results.append({
            'param': param,
            'ratio': ratio,
            'base_val': base_val,
            'new_val': new_val,
            'X_A_new': X_A_new,
            'param_change': param_change,
            'X_A_change': X_A_relative_change_percent,
            'sensitivity': sensitivity
        })
    
    # 打印结果表格
    print("| 参数变化    | 相对变化量 | 转化率相对变化 | 灵敏度（%/%) |")
    print("| ----------- | ---------- | -------------- | ------------ |")
    
    for i, result in enumerate(results):
        param = result['param']
        ratio = result['ratio']
        param_change = result['param_change']
        X_A_change = result['X_A_change']
        sensitivity = result['sensitivity']
        
        if param == 'v':
            if ratio < 1:
                param_str = f"${param}$ 减小20%"
                param_change_str = "-20%"
            else:
                param_str = f"${param}$ 增大20%"
                param_change_str = "+20%"
        elif param == 'k':
            if ratio < 1:
                param_str = f"${param}$ 减小20%"
                param_change_str = "-20%"
            else:
                param_str = f"${param}$ 增大20%"
                param_change_str = "+20%"
        elif param == 'n':
            if ratio < 1:
                param_str = f"${param}$ 减小20%"
                param_change_str = f"{param_change:.1f}"
            else:
                param_str = f"${param}$ 增大20%"
                param_change_str = f"{param_change:+.1f}"
        
        # 格式化转化率变化
        if X_A_change >= 0:
            X_A_change_str = f"+{X_A_change:.2f}%"
        else:
            X_A_change_str = f"{X_A_change:.2f}%"
        
        print(f"| {param_str:<11} | {param_change_str:<10} | {X_A_change_str:<14} | {sensitivity:>12.3f} |")
    
    # 详细数据输出
    print("\n" + "="*80)
    print("详细计算结果")
    print("="*80)
    for i, result in enumerate(results):
        param = result['param']
        ratio = result['ratio']
        base_val = result['base_val']
        new_val = result['new_val']
        X_A_new = result['X_A_new']
        X_A_change = result['X_A_change']
        sensitivity = result['sensitivity']
        
        if param == 'v':
            print(f"\n{i+1}. 体积流量变化：${param}$ = {new_val:.3f} (基础值: {base_val})")
        elif param == 'k':
            print(f"\n{i+1}. 速率常数变化：${param}$ = {new_val:.4f} (基础值: {base_val})")
        elif param == 'n':
            print(f"\n{i+1}. 反应级数变化：${param}$ = {new_val:.2f} (基础值: {base_val})")
        
        print(f"   新转化率：X_A = {X_A_new:.2f}%")
        print(f"   转化率变化：ΔX_A = {X_A_change:+.2f}%")
        print(f"   灵敏度：S = {sensitivity:.3f}")


if __name__ == "__main__":
    sensitivity_analysis()
