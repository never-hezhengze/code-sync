"""问题一：典型风光场景下绿电直连电氢氨园区运行指标分析
条件：电解槽与合成氨装置满负荷连续运行，不计功率损耗，36吨/日产能
"""
import numpy as np
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (load_load_profile, load_typical_wind_pv, 
                         load_electricity_prices, get_equipment_params)

def solve_problem1():
    print("=" * 60)
    print("问题一：典型风光场景下运行指标分析")
    print("=" * 60)
    
    # 加载数据
    P_load = load_load_profile()  # 24h常规负荷 (MW)
    P_wind, P_pv = load_typical_wind_pv()  # 24h风光功率 (MW)
    buy_price, sell_price = load_electricity_prices()
    params = get_equipment_params(36)  # 36吨/日产能
    
    P_H2NH3 = params['P_H2NH3_max']  # 20.75 MW (满负荷)
    
    # (1) 功率平衡计算
    P_total_load = P_load + P_H2NH3  # 总用电功率 (MW)
    P_RE = P_wind + P_pv  # 新能源发电功率 (MW)
    P_net = P_total_load - P_RE  # 净负荷
    
    P_buy = np.maximum(0, P_net)   # 购电功率
    P_sell = np.maximum(0, -P_net)  # 售电功率
    
    # (2) 日能量指标
    E_total = P_total_load.sum()  # 日总用电量 (MWh)
    E_RE = P_RE.sum()             # 新能源发电量 (MWh)
    E_buy = P_buy.sum()           # 网购电量 (MWh)
    E_sell = P_sell.sum()         # 上网电量 (MWh)
    
    # 能量守恒验证
    balance_err = abs(E_RE + E_buy - E_total - E_sell)
    assert balance_err < 0.01, f"能量守恒违反: {balance_err:.4f} MWh"
    
    # 绿电直连指标
    R_self = (E_total - E_sell - E_buy) / E_RE  # 自发自用比例
    R_green = (E_RE - E_sell) / E_total          # 绿电比例
    R_grid = E_sell / E_RE                       # 上网电量比例
    
    # 吨氨成本计算
    Q_NH3 = 36.0  # 吨/日
    
    # 新能源发电成本 (元) - 按实际发电量计算
    C_RE = (params['c_wind'] * P_wind.sum() + params['c_pv'] * P_pv.sum()) * 1000  # kWh
    
    # 购电成本 (元)
    C_buy = (buy_price * P_buy * 1000).sum()  # kWh
    
    # 设备运维成本 (元) - 满负荷24h
    C_OM_hour = (params['c_ALKEL'] * params['P_ALKEL_max'] * 1000 + 
                 params['c_PEMEL'] * params['P_PEMEL_max'] * 1000 + 
                 params['c_NH3'] * params['P_NH3_max'] * 1000)
    C_OM = C_OM_hour * 24
    
    # 售电收入 (元)
    I_sell = sell_price * E_sell * 1000
    
    # 吨氨成本
    C_day = C_RE + C_buy + C_OM - I_sell
    C_ton = C_day / Q_NH3
    
    # 打印结果
    print(f"\n--- 功率平衡结果 ---")
    print(f"电氢氨总功率: {P_H2NH3:.2f} MW (满负荷)")
    print(f"常规负荷范围: {P_load.min():.2f} ~ {P_load.max():.2f} MW")
    print(f"风电范围: {P_wind.min():.2f} ~ {P_wind.max():.2f} MW")
    print(f"光伏范围: {P_pv.min():.2f} ~ {P_pv.max():.2f} MW")
    print(f"购电范围: {P_buy.min():.2f} ~ {P_buy.max():.2f} MW")
    print(f"售电范围: {P_sell.min():.2f} ~ {P_sell.max():.2f} MW")
    
    print(f"\n--- 日能量指标 ---")
    print(f"日总用电量: {E_total:.2f} MWh")
    print(f"新能源发电量: {E_RE:.2f} MWh")
    print(f"网购电量: {E_buy:.2f} MWh")
    print(f"上网电量: {E_sell:.2f} MWh")
    print(f"能量守恒误差: {balance_err:.6f} MWh")
    
    print(f"\n--- 绿电直连指标 ---")
    print(f"自发自用比例: {R_self*100:.2f}% (要求>60%) {'✅' if R_self > 0.6 else '❌'}")
    print(f"绿电比例: {R_green*100:.2f}% (要求>30%) {'✅' if R_green > 0.3 else '❌'}")
    print(f"上网电量比例: {R_grid*100:.2f}% (要求<20%) {'✅' if R_grid < 0.2 else '❌'}")
    
    print(f"\n--- 吨氨成本 ---")
    print(f"新能源发电成本: {C_RE:.2f} 元")
    print(f"购电成本: {C_buy:.2f} 元")
    print(f"设备运维成本: {C_OM:.2f} 元")
    print(f"售电收入: {I_sell:.2f} 元")
    print(f"日总成本: {C_day:.2f} 元")
    print(f"吨氨成本: {C_ton:.2f} 元/吨")
    
    # 约束验证
    print(f"\n--- 约束验证 ---")
    violations = []
    if np.any(P_buy < -1e-6):
        violations.append(f"P_buy有负值: min={P_buy.min()}")
    if np.any(P_sell < -1e-6):
        violations.append(f"P_sell有负值: min={P_sell.min()}")
    if not (0 <= R_self <= 1):
        violations.append(f"R_self超出[0,1]: {R_self}")
    if not (0 <= R_green <= 1):
        violations.append(f"R_green超出[0,1]: {R_green}")
    if not (0 <= R_grid <= 1):
        violations.append(f"R_grid超出[0,1]: {R_grid}")
    if C_ton <= 0:
        violations.append(f"C_ton非正: {C_ton}")
    
    if violations:
        for v in violations:
            print(f"  ❌ {v}")
        raise ValueError("约束验证失败")
    else:
        print("  ✅ 所有约束验证通过")
    
    # 保存结果
    results = {
        'power_curves': {
            'P_load': P_load.tolist(),
            'P_wind': P_wind.tolist(),
            'P_pv': P_pv.tolist(),
            'P_RE': P_RE.tolist(),
            'P_total_load': P_total_load.tolist(),
            'P_buy': P_buy.tolist(),
            'P_sell': P_sell.tolist(),
            'P_net': P_net.tolist(),
        },
        'energy': {
            'E_total': round(E_total, 2),
            'E_RE': round(E_RE, 2),
            'E_buy': round(E_buy, 2),
            'E_sell': round(E_sell, 2),
        },
        'indicators': {
            'R_self': round(R_self, 4),
            'R_green': round(R_green, 4),
            'R_grid': round(R_grid, 4),
            'R_self_pass': bool(R_self > 0.6),
            'R_green_pass': bool(R_green > 0.3),
            'R_grid_pass': bool(R_grid < 0.2),
        },
        'cost': {
            'C_RE': round(C_RE, 2),
            'C_buy': round(C_buy, 2),
            'C_OM': round(C_OM, 2),
            'I_sell': round(I_sell, 2),
            'C_day': round(C_day, 2),
            'C_ton': round(C_ton, 2),
            'Q_NH3': Q_NH3,
        },
        'params': {
            'P_H2NH3': P_H2NH3,
            'Q_capacity': 36,
        }
    }
    
    os.makedirs('figures', exist_ok=True)
    with open('figures/problem_1_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 问题一结果已保存到 figures/problem_1_results.json")
    return results

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    solve_problem1()
