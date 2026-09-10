"""问题三：基于连续制氨调节的绿电直连型电氢氨园区运行优化
条件：产能72吨/日，产量72->36吨/日(步长9)，功率连续可调(下限10%)
"""
import numpy as np
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (load_load_profile, load_typical_wind_pv,
                         load_electricity_prices, get_equipment_params,
                         get_all_scenarios, get_scenario_labels)
import pulp


def solve_q3_lp(P_wind, P_pv, P_load, Q_target, params, buy_price, sell_price):
    """用MILP求解问题三(含购售电互斥约束)"""
    P_H2NH3 = params["P_H2NH3_max"]  # 41.5 MW
    r_NH3 = params["r_NH3"]  # 3.0 t/h
    alpha_sum = Q_target / r_NH3

    C_OM_hour = (params["c_ALKEL"] * params["P_ALKEL_max"] * 1000 +
                 params["c_PEMEL"] * params["P_PEMEL_max"] * 1000 +
                 params["c_NH3"] * params["P_NH3_max"] * 1000)

    model = pulp.LpProblem("Q3", pulp.LpMinimize)

    alpha = [pulp.LpVariable(f"a_{t}", lowBound=0.1, upBound=1.0) for t in range(24)]
    P_buy_var = [pulp.LpVariable(f"Pb_{t}", lowBound=0) for t in range(24)]
    P_sell_var = [pulp.LpVariable(f"Ps_{t}", lowBound=0) for t in range(24)]

    # Production constraint
    model += pulp.lpSum(alpha) == alpha_sum

    # Power balance + mutual exclusion
    M = 200
    for t in range(24):
        model += P_buy_var[t] - P_sell_var[t] == (P_load[t] + alpha[t] * P_H2NH3
                                                   - P_wind[t] - P_pv[t])
        z = pulp.LpVariable(f"z_{t}", cat="Binary")
        model += P_buy_var[t] <= M * z
        model += P_sell_var[t] <= M * (1 - z)

    # Objective
    C_RE = (params["c_wind"] * P_wind.sum() + params["c_pv"] * P_pv.sum()) * 1000
    obj = pulp.lpSum([buy_price[t] * P_buy_var[t] * 1000 for t in range(24)])
    obj += pulp.lpSum([alpha[t] * C_OM_hour for t in range(24)])
    obj -= sell_price * pulp.lpSum([P_sell_var[t] * 1000 for t in range(24)])
    model += obj

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=60)
    model.solve(solver)

    if model.status != 1:
        return None

    alpha_sol = np.array([alpha[t].varValue for t in range(24)])
    P_buy_sol = np.array([P_buy_var[t].varValue for t in range(24)])
    P_sell_sol = np.array([P_sell_var[t].varValue for t in range(24)])

    # Calculate indicators
    P_total_load = P_load + alpha_sol * P_H2NH3
    E_total = P_total_load.sum()
    E_RE = (P_wind + P_pv).sum()
    E_buy = P_buy_sol.sum()
    E_sell = P_sell_sol.sum()

    R_self = (E_total - E_sell - E_buy) / E_RE
    R_green = (E_RE - E_sell) / E_total
    R_grid = E_sell / E_RE

    # Cost
    C_RE = (params["c_wind"] * P_wind.sum() + params["c_pv"] * P_pv.sum()) * 1000
    C_buy = (buy_price * P_buy_sol * 1000).sum()
    C_OM = (alpha_sol * C_OM_hour).sum()
    I_sell = sell_price * E_sell * 1000
    C_day = C_RE + C_buy + C_OM - I_sell
    C_ton = C_day / Q_target

    return {
        "alpha": alpha_sol.tolist(),
        "P_buy": P_buy_sol.tolist(),
        "P_sell": P_sell_sol.tolist(),
        "Q_NH3": Q_target,
        "E_total": round(E_total, 2),
        "E_RE": round(E_RE, 2),
        "E_buy": round(E_buy, 2),
        "E_sell": round(E_sell, 2),
        "R_self": round(R_self, 4),
        "R_green": round(R_green, 4),
        "R_grid": round(R_grid, 4),
        "C_RE": round(C_RE, 2),
        "C_buy": round(C_buy, 2),
        "C_OM": round(C_OM, 2),
        "I_sell": round(I_sell, 2),
        "C_day": round(C_day, 2),
        "C_ton": round(C_ton, 2),
    }


def solve_problem3():
    print("=" * 60)
    print("问题三：基于连续制氨调节的运行优化")
    print("=" * 60)

    P_load = load_load_profile()
    P_wind_typ, P_pv_typ = load_typical_wind_pv()
    buy_price, sell_price = load_electricity_prices()
    params = get_equipment_params(72)

    productions = [72, 63, 54, 45, 36]
    wind_all, pv_all = get_all_scenarios()
    labels = get_scenario_labels()

    # 问题三(1): 24种场景最优调度
    print("\n--- 问题三(1): 24种场景分析 ---")
    scenario_summary = []

    for s in range(24):
        best_cost = float("inf")
        best_q = None
        best_result = None

        for Q in productions:
            result = solve_q3_lp(wind_all[s], pv_all[s], P_load, Q, params, buy_price, sell_price)
            if result is None:
                continue
            if result["C_ton"] < best_cost:
                best_cost = result["C_ton"]
                best_q = Q
                best_result = result

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
            "alpha": best_result["alpha"],
        })

        if (s + 1) % 8 == 0:
            print(f"  completed {s+1}/24 scenarios")

    # 统计绿电指标
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
    annual_C_ton = total_annual_cost / total_annual_production

    print(f"\n--- Annual stats ---")
    print(f"  Full pass: {full_pass} scenarios ({full_pass*15} days)")
    print(f"  Partial: {partial_pass} scenarios ({partial_pass*15} days)")
    print(f"  No pass: {no_pass} scenarios ({no_pass*15} days)")
    print(f"  Annual C_ton: {annual_C_ton:.2f}")
    print(f"  Annual production: {total_annual_production:.0f} tons")

    # 问题三(2): 典型场景详细分析
    print("\n--- 问题三(2): 典型场景详细 ---")
    typical_results = {}
    for Q in productions:
        result = solve_q3_lp(P_wind_typ, P_pv_typ, P_load, Q, params, buy_price, sell_price)
        if result:
            typical_results[str(Q)] = result
            print(f"  Q={Q}t/d: C_ton={result['C_ton']:.2f}, "
                  f"R_self={result['R_self']*100:.1f}%, "
                  f"R_green={result['R_green']*100:.1f}%, "
                  f"R_grid={result['R_grid']*100:.1f}%")

    all_results = {
        "typical": typical_results,
        "scenarios": scenario_summary,
        "annual_stats": {
            "full_pass": full_pass, "partial_pass": partial_pass, "no_pass": no_pass,
            "full_pass_days": full_pass * 15, "partial_pass_days": partial_pass * 15,
            "no_pass_days": no_pass * 15,
            "annual_C_ton": round(annual_C_ton, 2),
            "total_annual_production": total_annual_production,
        },
        "cost_distribution": [item["C_ton"] for item in scenario_summary],
    }

    with open("figures/problem_3_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n>>> Problem 3 results saved")
    return all_results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    solve_problem3()
