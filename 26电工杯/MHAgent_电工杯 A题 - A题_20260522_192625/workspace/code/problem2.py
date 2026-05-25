"""问题二：基于离散制氨调节的绿电直连型电氢氨园区运行优化
条件：产能72吨/日，产量72->36吨/日(步长9)，设备只有开/停两种状态
"""
import numpy as np
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (load_load_profile, load_typical_wind_pv,
                         load_electricity_prices, get_equipment_params,
                         get_all_scenarios, get_scenario_labels)
import pulp


def solve_q2_milp(P_wind, P_pv, P_load, Q_target, params, buy_price, sell_price):
    """用MILP求解问题二单个(场景,产量)组合"""
    P_H2NH3 = params["P_H2NH3_max"]
    r_NH3 = params["r_NH3"]
    k = int(round(Q_target / r_NH3))

    C_OM_hour = (params["c_ALKEL"] * params["P_ALKEL_max"] * 1000 +
                 params["c_PEMEL"] * params["P_PEMEL_max"] * 1000 +
                 params["c_NH3"] * params["P_NH3_max"] * 1000)

    model = pulp.LpProblem("Q2", pulp.LpMinimize)
    u = [pulp.LpVariable(f"u_{t}", cat="Binary") for t in range(24)]
    P_buy_var = [pulp.LpVariable(f"Pb_{t}", lowBound=0) for t in range(24)]

    model += pulp.lpSum(u) == k

    P_sell_var = [pulp.LpVariable(f"Ps_{t}", lowBound=0) for t in range(24)]
    # Big-M for mutual exclusion of buy/sell
    M = 200  # MW upper bound (larger than any possible power)

    for t in range(24):
        # Power balance: P_buy - P_sell = net_load - RE
        P_net_t = P_load[t] + u[t] * P_H2NH3 - P_wind[t] - P_pv[t]
        model += P_buy_var[t] - P_sell_var[t] == P_net_t
        # Mutual exclusion via binary indicator
        # When net > 0: buy > 0, sell = 0
        # When net < 0: buy = 0, sell > 0
        # Use auxiliary binary z[t]: z=1 means buying mode
        z = pulp.LpVariable(f"z_{t}", cat="Binary")
        model += P_buy_var[t] <= M * z
        model += P_sell_var[t] <= M * (1 - z)

    C_RE = (params["c_wind"] * P_wind.sum() + params["c_pv"] * P_pv.sum()) * 1000

    obj = pulp.lpSum([buy_price[t] * P_buy_var[t] * 1000 for t in range(24)])
    obj += pulp.lpSum([u[t] * C_OM_hour for t in range(24)])
    obj -= sell_price * pulp.lpSum([P_sell_var[t] * 1000 for t in range(24)])
    model += obj

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=60)
    model.solve(solver)

    if model.status != 1:
        return None

    u_sol = np.array([u[t].varValue for t in range(24)])
    P_buy_sol = np.array([P_buy_var[t].varValue for t in range(24)])
    P_sell_sol = np.array([P_sell_var[t].varValue for t in range(24)])

    P_total_load = P_load + u_sol * P_H2NH3
    E_total = P_total_load.sum()
    E_RE = (P_wind + P_pv).sum()
    E_buy = P_buy_sol.sum()
    E_sell = P_sell_sol.sum()

    R_self = (E_total - E_sell - E_buy) / E_RE
    R_green = (E_RE - E_sell) / E_total
    R_grid = E_sell / E_RE

    C_buy = (buy_price * P_buy_sol * 1000).sum()
    C_OM = u_sol.sum() * C_OM_hour
    I_sell = sell_price * E_sell * 1000
    C_day = C_RE + C_buy + C_OM - I_sell
    C_ton = C_day / Q_target

    return {
        "u": u_sol.tolist(), "P_buy": P_buy_sol.tolist(), "P_sell": P_sell_sol.tolist(),
        "k": k, "Q_NH3": Q_target,
        "E_total": round(E_total, 2), "E_RE": round(E_RE, 2),
        "E_buy": round(E_buy, 2), "E_sell": round(E_sell, 2),
        "R_self": round(R_self, 4), "R_green": round(R_green, 4), "R_grid": round(R_grid, 4),
        "C_RE": round(C_RE, 2), "C_buy": round(C_buy, 2),
        "C_OM": round(C_OM, 2), "I_sell": round(I_sell, 2),
        "C_day": round(C_day, 2), "C_ton": round(C_ton, 2),
    }


def solve_problem2():
    print("=" * 60)
    print("问题二：基于离散制氨调节的运行优化")
    print("=" * 60)

    P_load = load_load_profile()
    P_wind_typ, P_pv_typ = load_typical_wind_pv()
    buy_price, sell_price = load_electricity_prices()
    params = get_equipment_params(72)

    productions = [72, 63, 54, 45, 36]

    # 问题二(1): 典型场景
    print("\n--- 问题二(1): 典型场景各产量最优方案 ---")
    typical_results = {}

    for Q in productions:
        result = solve_q2_milp(P_wind_typ, P_pv_typ, P_load, Q, params, buy_price, sell_price)
        if result is None:
            print(f"  Q={Q}: solve failed")
            continue
        typical_results[str(Q)] = result
        on_hours = [t for t in range(24) if result["u"][t] > 0.5]
        print(f"  Q={Q}t/d: k={result['k']}h, C_ton={result['C_ton']:.2f}")
        print(f"    on_hours={on_hours}")
        print(f"    R_self={result['R_self']*100:.1f}% R_green={result['R_green']*100:.1f}% R_grid={result['R_grid']*100:.1f}%")

    best_Q = min(typical_results.keys(), key=lambda q: typical_results[q]["C_ton"])
    print(f"\n  Best: Q={best_Q}t/d, C_ton={typical_results[best_Q]['C_ton']:.2f}")

    # 问题二(2): 24种场景
    print("\n--- 问题二(2): 24种场景分析 ---")
    wind_all, pv_all = get_all_scenarios()
    labels = get_scenario_labels()

    scenario_results = {}
    for s in range(24):
        scenario_results[labels[s]] = {}
        best_cost = float("inf")
        best_q = None
        for Q in productions:
            result = solve_q2_milp(wind_all[s], pv_all[s], P_load, Q, params, buy_price, sell_price)
            if result is None:
                continue
            scenario_results[labels[s]][str(Q)] = result
            if result["C_ton"] < best_cost:
                best_cost = result["C_ton"]
                best_q = Q
        scenario_results[labels[s]]["best_Q"] = best_q
        scenario_results[labels[s]]["best_C_ton"] = round(best_cost, 2)
        if (s + 1) % 8 == 0:
            print(f"  completed {s+1}/24 scenarios")

    # 统计
    full_pass = partial_pass = no_pass = 0
    scenario_summary = []

    for s in range(24):
        label = labels[s]
        best_q = scenario_results[label]["best_Q"]
        r = scenario_results[label][str(best_q)]

        pass_self = r["R_self"] > 0.6
        pass_green = r["R_green"] > 0.3
        pass_grid = r["R_grid"] < 0.2
        n_pass = sum([pass_self, pass_green, pass_grid])

        if n_pass == 3:
            full_pass += 1
            status = "全满足"
        elif n_pass == 0:
            no_pass += 1
            status = "全不满足"
        else:
            partial_pass += 1
            status = "部分满足"

        scenario_summary.append({
            "scenario": label, "best_Q": best_q, "C_ton": r["C_ton"],
            "R_self": r["R_self"], "R_green": r["R_green"], "R_grid": r["R_grid"],
            "status": status, "E_buy": r["E_buy"], "E_sell": r["E_sell"],
            "C_day": r["C_day"],
        })

    total_annual_cost = sum(item["C_day"] for item in scenario_summary) * 15
    total_annual_production = sum(item["best_Q"] for item in scenario_summary) * 15
    annual_C_ton = total_annual_cost / total_annual_production

    print(f"\n--- Annual stats ---")
    print(f"  Full pass: {full_pass} scenarios ({full_pass*15} days)")
    print(f"  Partial: {partial_pass} scenarios ({partial_pass*15} days)")
    print(f"  No pass: {no_pass} scenarios ({no_pass*15} days)")
    print(f"  Annual C_ton: {annual_C_ton:.2f}")
    print(f"  Annual production: {total_annual_production:.0f} tons")

    all_results = {
        "typical": typical_results,
        "best_Q_typical": int(best_Q),
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

    with open("figures/problem_2_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n>>> Problem 2 results saved")
    return all_results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    solve_problem2()
