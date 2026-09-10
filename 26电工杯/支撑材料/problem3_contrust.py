"""
问题三改进模型：独立建模碱性电解槽和PEM电解槽功率分配
- 功率连续可调，下限为额定功率的10%
- 考虑两种电解槽不同的产氢效率和运维成本
- 合成氨功率随产氨率线性变化
- 目标：最小化日总成本（购电+运维-售电+风光固定成本）
"""

import numpy as np
import pandas as pd
import pulp
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (
    load_load_profile, load_typical_wind_pv, load_electricity_prices,
    get_all_scenarios, get_scenario_labels
)

# ==================== 设备参数（基于产能72吨/日）====================
# 额定功率 (MW)
P_ALK_MAX = 20.0      # 碱性电解槽
P_PEM_MAX = 20.0      # PEM电解槽
P_NH3_RATED = 1.5     # 合成氨装置（对应3 t/h产率）

# 产氢系数 (kg/h per MW)
# 碱性：额定280 kg/h @20MW → 14 kg/h per MW，但36吨/日时是140kg/h@10MW=14，产能加倍后系数仍为14？
# 重新核算：36吨/日时，碱性10MW产氢140kg/h => 14 kg/h/MW。72吨/日时，20MW产氢280kg/h => 依然14 kg/h/MW。
# PEM：36吨/日时10MW产氢160kg/h => 16 kg/h/MW；72吨/日时20MW产氢320kg/h => 16 kg/h/MW。
H2_ALK_COEFF = 14.0    # kg/h per MW
H2_PEM_COEFF = 16.0    # kg/h per MW

# 合成氨参数：每吨氨需氢200 kg，每吨氨耗电0.5 MWh = 500 kWh
H2_PER_NH3 = 200.0     # kg H2 / t NH3
POWER_PER_NH3 = 0.5    # MW / (t/h)  （即产率1 t/h需要0.5 MW）

# 运维成本 (元/kWh)
C_OM_ALK = 0.10
C_OM_PEM = 0.15
C_OM_NH3 = 0.002

# 风光度电成本 (元/kWh)，用于计算固定成本
C_WIND = 0.15
C_PV = 0.12

# ==================== 辅助函数 ====================
def compute_nh3_rate(p_alk, p_pem):
    """根据电解槽功率计算氨产率 (t/h)"""
    h2_rate = H2_ALK_COEFF * p_alk + H2_PEM_COEFF * p_pem   # kg/h
    return h2_rate / H2_PER_NH3                             # t/h

def compute_nh3_power(nh3_rate):
    """根据氨产率计算合成氨装置功率 (MW)"""
    return nh3_rate * POWER_PER_NH3

def total_h2nh3_power(p_alk, p_pem, nh3_rate):
    """总电氢氨功率 (MW)"""
    return p_alk + p_pem + compute_nh3_power(nh3_rate)

# ==================== 改进的优化模型 ====================
def solve_q3_improved(P_wind, P_pv, P_load, Q_target, buy_price, sell_price):
    """
    独立建模ALK和PEM的线性规划求解
    """
    model = pulp.LpProblem("Q3_Improved", pulp.LpMinimize)
    T = 24

    # 决策变量：电解槽功率 (MW)，连续可调，下限10%额定功率
    p_alk = [pulp.LpVariable(f"p_alk_{t}", lowBound=0.1*P_ALK_MAX, upBound=P_ALK_MAX) for t in range(T)]
    p_pem = [pulp.LpVariable(f"p_pem_{t}", lowBound=0.1*P_PEM_MAX, upBound=P_PEM_MAX) for t in range(T)]

    # 购售电变量
    p_buy = [pulp.LpVariable(f"p_buy_{t}", lowBound=0) for t in range(T)]
    p_sell = [pulp.LpVariable(f"p_sell_{t}", lowBound=0) for t in range(T)]

    # 产氨率 (t/h)
    nh3_rate = [pulp.LpVariable(f"nh3_rate_{t}", lowBound=0) for t in range(T)]

    # 购售电互斥二进制变量
    z = [pulp.LpVariable(f"z_{t}", cat="Binary") for t in range(T)]
    M = 200  # 大M

    # ---------- 约束条件 ----------
    # 1. 产氨率与电解槽功率的关系
    for t in range(T):
        model += nh3_rate[t] == (H2_ALK_COEFF * p_alk[t] + H2_PEM_COEFF * p_pem[t]) / H2_PER_NH3

    # 2. 每日总产量约束
    model += pulp.lpSum(nh3_rate) == Q_target   # Q_target单位为吨，nh3_rate为t/h，乘以1小时得到吨

    # 3. 功率平衡 + 购售电互斥
    for t in range(T):
        # 合成氨功率
        p_nh3 = nh3_rate[t] * POWER_PER_NH3
        total_h2nh3 = p_alk[t] + p_pem[t] + p_nh3
        # 功率平衡
        model += p_buy[t] - p_sell[t] == P_load[t] + total_h2nh3 - P_wind[t] - P_pv[t]
        # 互斥约束
        model += p_buy[t] <= M * z[t]
        model += p_sell[t] <= M * (1 - z[t])

    # ---------- 目标函数 ----------
    # 固定风光成本 (元)
    C_RE_fixed = (C_WIND * P_wind.sum() + C_PV * P_pv.sum()) * 1000

    # 购电成本
    C_buy = pulp.lpSum(buy_price[t] * p_buy[t] * 1000 for t in range(T))
    # 售电收入
    I_sell = sell_price * pulp.lpSum(p_sell[t] * 1000 for t in range(T))

    # 运维成本 (元)
    C_OM = pulp.lpSum(
        (C_OM_ALK * p_alk[t] + C_OM_PEM * p_pem[t] + C_OM_NH3 * (nh3_rate[t] * POWER_PER_NH3)) * 1000
        for t in range(T)
    )

    # 总目标
    model += C_RE_fixed + C_buy + C_OM - I_sell

    # 求解
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=120)
    model.solve(solver)

    if model.status != 1:
        return None

    # 提取结果
    p_alk_sol = np.array([p_alk[t].varValue for t in range(T)])
    p_pem_sol = np.array([p_pem[t].varValue for t in range(T)])
    nh3_rate_sol = np.array([nh3_rate[t].varValue for t in range(T)])
    p_buy_sol = np.array([p_buy[t].varValue for t in range(T)])
    p_sell_sol = np.array([p_sell[t].varValue for t in range(T)])

    # 总功率和产氨量验证
    total_power = p_alk_sol + p_pem_sol + nh3_rate_sol * POWER_PER_NH3
    total_nh3 = nh3_rate_sol.sum()

    # 计算绿电指标
    E_total = (P_load + total_power).sum()          # 总用电量 MWh
    E_RE = (P_wind + P_pv).sum()                   # 新能源发电量 MWh
    E_buy = p_buy_sol.sum()                        # 网购电量 MWh
    E_sell = p_sell_sol.sum()                      # 上网电量 MWh

    R_self = (E_total - E_sell - E_buy) / E_RE if E_RE > 0 else 0      # 自发自用比例
    R_green = (E_RE - E_sell) / E_total if E_total > 0 else 0           # 绿电比例
    R_grid = E_sell / E_RE if E_RE > 0 else 0                           # 上网电量比例

    # 成本细项
    C_RE = (C_WIND * P_wind.sum() + C_PV * P_pv.sum()) * 1000
    C_buy_val = (buy_price * p_buy_sol * 1000).sum()
    C_OM_val = ((C_OM_ALK * p_alk_sol + C_OM_PEM * p_pem_sol + C_OM_NH3 * (nh3_rate_sol * POWER_PER_NH3)) * 1000).sum()
    I_sell_val = sell_price * E_sell * 1000
    C_day = C_RE + C_buy_val + C_OM_val - I_sell_val
    C_ton = C_day / Q_target if Q_target > 0 else np.inf

    return {
        "p_alk": p_alk_sol.tolist(),
        "p_pem": p_pem_sol.tolist(),
        "nh3_rate": nh3_rate_sol.tolist(),
        "p_buy": p_buy_sol.tolist(),
        "p_sell": p_sell_sol.tolist(),
        "Q_NH3": Q_target,
        "E_total": round(E_total, 2),
        "E_RE": round(E_RE, 2),
        "E_buy": round(E_buy, 2),
        "E_sell": round(E_sell, 2),
        "R_self": round(R_self, 4),
        "R_green": round(R_green, 4),
        "R_grid": round(R_grid, 4),
        "C_RE": round(C_RE, 2),
        "C_buy": round(C_buy_val, 2),
        "C_OM": round(C_OM_val, 2),
        "I_sell": round(I_sell_val, 2),
        "C_day": round(C_day, 2),
        "C_ton": round(C_ton, 2),
    }

# ==================== 主函数：问题三改进版求解 ====================
def solve_problem3_improved():
    print("=" * 60)
    print("问题三改进模型：独立ALK/PEM功率分配")
    print("=" * 60)

    P_load = load_load_profile()
    P_wind_typ, P_pv_typ = load_typical_wind_pv()
    buy_price, sell_price = load_electricity_prices()

    productions = [72, 63, 54, 45, 36]
    wind_all, pv_all = get_all_scenarios()
    labels = get_scenario_labels()

    # 问题三(1): 24种场景分析
    print("\n--- 场景优化中 ---")
    scenario_summary = []

    for s in range(24):
        best_cost = float("inf")
        best_q = None
        best_result = None

        for Q in productions:
            result = solve_q3_improved(wind_all[s], pv_all[s], P_load, Q, buy_price, sell_price)
            if result is None:
                continue
            if result["C_ton"] < best_cost:
                best_cost = result["C_ton"]
                best_q = Q
                best_result = result

        if best_result is None:
            continue

        scenario_summary.append({
            "scenario": labels[s],
            "best_Q": best_q,
            "C_ton": best_result["C_ton"],
            "R_self": best_result["R_self"],
            "R_green": best_result["R_green"],
            "R_grid": best_result["R_grid"],
            "E_buy": best_result["E_buy"],
            "E_sell": best_result["E_sell"],
            "C_day": best_result["C_day"],
            "p_alk_avg": np.mean(best_result["p_alk"]),
            "p_pem_avg": np.mean(best_result["p_pem"]),
        })

        if (s+1) % 8 == 0:
            print(f"  已完成 {s+1}/24 场景")

    # 统计绿电指标满足情况
    full_pass = partial_pass = no_pass = 0
    for item in scenario_summary:
        pass_self = item["R_self"] > 0.6
        pass_green = item["R_green"] > 0.3
        pass_grid = item["R_grid"] < 0.2
        n_pass = sum([pass_self, pass_green, pass_grid])
        if n_pass == 3:
            full_pass += 1
            item["status"] = "全满足"
        elif n_pass == 0:
            no_pass += 1
            item["status"] = "全不满足"
        else:
            partial_pass += 1
            item["status"] = "部分满足"

    total_annual_cost = sum(item["C_day"] for item in scenario_summary) * 15
    total_annual_production = sum(item["best_Q"] for item in scenario_summary) * 15
    annual_C_ton = total_annual_cost / total_annual_production if total_annual_production > 0 else 0

    print(f"\n--- 全年统计 ---")
    print(f"  全满足场景: {full_pass} 个 ({full_pass*15}天)")
    print(f"  部分满足: {partial_pass} 个 ({partial_pass*15}天)")
    print(f"  全不满足: {no_pass} 个 ({no_pass*15}天)")
    print(f"  全年平均吨氨成本: {annual_C_ton:.2f} 元/吨")
    print(f"  全年总产量: {total_annual_production:.0f} 吨")

    # 问题三(2): 典型场景详细分析（不同产量）
    print("\n--- 典型场景 (典型日风光) 不同产量结果 ---")
    typical_results = {}
    for Q in productions:
        result = solve_q3_improved(P_wind_typ, P_pv_typ, P_load, Q, buy_price, sell_price)
        if result:
            typical_results[str(Q)] = result
            print(f"  Q={Q} t/d: 成本={result['C_ton']:.2f}元/t, "
                  f"自用率={result['R_self']*100:.1f}%, 绿电比={result['R_green']*100:.1f}%, "
                  f"上网比={result['R_grid']*100:.1f}%, 碱性均功率={np.mean(result['p_alk']):.1f}MW, "
                  f"PEM均功率={np.mean(result['p_pem']):.1f}MW")

    # 保存结果
    all_results = {
        "typical": typical_results,
        "scenarios": scenario_summary,
        "annual_stats": {
            "full_pass": full_pass,
            "partial_pass": partial_pass,
            "no_pass": no_pass,
            "full_pass_days": full_pass * 15,
            "partial_pass_days": partial_pass * 15,
            "no_pass_days": no_pass * 15,
            "annual_C_ton": round(annual_C_ton, 2),
            "total_annual_production": total_annual_production,
        },
        "cost_distribution": [item["C_ton"] for item in scenario_summary],
    }

    with open("figures/problem_3_improved_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n>>> 改进模型结果已保存至 figures/problem_3_improved_results.json")
    return all_results

if __name__ == "__main__":
    # 确保工作目录正确
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    solve_problem3_improved()