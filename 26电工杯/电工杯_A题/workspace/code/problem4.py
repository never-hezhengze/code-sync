"""问题四：绿电直连型电氢氨园区离网运行分析及储能配置研究
条件：离网运行，产能72吨/日，功率连续可调(下限10%)
"""
import numpy as np
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (load_load_profile, load_electricity_prices, get_equipment_params,
                         get_all_scenarios, get_scenario_labels, get_storage_params)
import pulp


def solve_q4_offgrid_no_storage(P_wind, P_pv, P_load, params):
    """问题四(1): 离网无储能，最大化产量"""
    P_H2NH3 = params["P_H2NH3_max"]  # 41.5 MW
    r_NH3 = params["r_NH3"]  # 3.0 t/h

    model = pulp.LpProblem("Q4_offgrid", pulp.LpMaximize)

    alpha = [pulp.LpVariable(f"a_{t}", lowBound=0, upBound=1.0) for t in range(24)]
    v = [pulp.LpVariable(f"v_{t}", cat="Binary") for t in range(24)]

    for t in range(24):
        available = P_wind[t] + P_pv[t] - P_load[t]
        if available < 0:
            # Can't even power base load, must shut down H2NH3
            model += alpha[t] == 0
            model += v[t] == 0
        else:
            alpha_max = min(1.0, available / P_H2NH3)
            model += alpha[t] <= alpha_max
            model += alpha[t] >= 0.1 * v[t]
            model += alpha[t] <= v[t]
            if alpha_max < 0.1:
                model += v[t] == 0
                model += alpha[t] == 0

    # Maximize production
    model += pulp.lpSum(alpha)

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=60)
    model.solve(solver)

    if model.status != 1:
        return None

    alpha_sol = np.array([alpha[t].varValue for t in range(24)])
    v_sol = np.array([v[t].varValue for t in range(24)])

    Q_NH3 = r_NH3 * alpha_sol.sum()
    P_used = P_load + alpha_sol * P_H2NH3
    P_RE = P_wind + P_pv
    P_curtail = np.maximum(0, P_RE - P_used)
    E_curtail = P_curtail.sum()
    E_RE = P_RE.sum()
    E_used = P_used.sum()

    # Cost (off-grid: only RE cost + OM, no buy/sell)
    c_RE_avg = (params["c_wind"] * P_wind.sum() + params["c_pv"] * P_pv.sum()) / max(E_RE, 1)
    C_RE_used = c_RE_avg * E_used * 1000
    C_OM_hour = (params["c_ALKEL"] * params["P_ALKEL_max"] * 1000 +
                 params["c_PEMEL"] * params["P_PEMEL_max"] * 1000 +
                 params["c_NH3"] * params["P_NH3_max"] * 1000)
    C_OM = (alpha_sol * C_OM_hour).sum()
    C_day = C_RE_used + C_OM
    C_ton = C_day / Q_NH3 if Q_NH3 > 0 else float("inf")

    return {
        "alpha": alpha_sol.tolist(),
        "Q_NH3": round(Q_NH3, 2),
        "E_RE": round(E_RE, 2),
        "E_used": round(E_used, 2),
        "E_curtail": round(E_curtail, 2),
        "utilization": round(E_used / E_RE, 4) if E_RE > 0 else 0,
        "C_day": round(C_day, 2),
        "C_ton": round(C_ton, 2),
        "hours_on": int(v_sol.sum()),
    }


def solve_q4_with_storage(P_wind, P_pv, P_load, params, C_sto, P_sto_max):
    """问题四(2): 离网有储能，最大化产量"""
    P_H2NH3 = params["P_H2NH3_max"]
    r_NH3 = params["r_NH3"]
    sto = get_storage_params()

    model = pulp.LpProblem("Q4_storage", pulp.LpMaximize)

    alpha = [pulp.LpVariable(f"a_{t}", lowBound=0, upBound=1.0) for t in range(24)]
    v = [pulp.LpVariable(f"v_{t}", cat="Binary") for t in range(24)]
    P_sto_c = [pulp.LpVariable(f"Pc_{t}", lowBound=0, upBound=P_sto_max) for t in range(24)]
    P_sto_d = [pulp.LpVariable(f"Pd_{t}", lowBound=0, upBound=P_sto_max) for t in range(24)]
    E_sto = [pulp.LpVariable(f"E_{t}", lowBound=0, upBound=C_sto) for t in range(25)]

    # Initial SOC = final SOC (cycle constraint)
    model += E_sto[0] == E_sto[24]

    for t in range(24):
        # SOC dynamics
        model += E_sto[t+1] == (E_sto[t] * (1 - sto["sigma"])
                                + sto["eta_c"] * P_sto_c[t]
                                - P_sto_d[t] / sto["eta_d"])

        # Power balance: load + H2NH3 + charge = RE + discharge
        available = P_wind[t] + P_pv[t]
        model += (P_load[t] + alpha[t] * P_H2NH3 + P_sto_c[t]
                  <= available + P_sto_d[t])

        # alpha constraints
        model += alpha[t] >= 0.1 * v[t]
        model += alpha[t] <= v[t]

        # Charge/discharge mutual exclusion
        w = pulp.LpVariable(f"w_{t}", cat="Binary")
        model += P_sto_c[t] <= P_sto_max * w
        model += P_sto_d[t] <= P_sto_max * (1 - w)

    model += pulp.lpSum(alpha)

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=120)
    model.solve(solver)

    if model.status != 1:
        return None

    alpha_sol = np.array([alpha[t].varValue for t in range(24)])
    P_sto_c_sol = np.array([P_sto_c[t].varValue for t in range(24)])
    P_sto_d_sol = np.array([P_sto_d[t].varValue for t in range(24)])
    E_sto_sol = np.array([E_sto[t].varValue for t in range(25)])

    Q_NH3 = r_NH3 * alpha_sol.sum()
    P_RE = P_wind + P_pv
    E_RE = P_RE.sum()
    P_used = P_load + alpha_sol * P_H2NH3 + P_sto_c_sol - P_sto_d_sol
    E_used = (P_load + alpha_sol * P_H2NH3).sum()
    E_curtail = max(0, E_RE - E_used - (P_sto_c_sol * sto["eta_c"]).sum()
                    + (P_sto_d_sol / sto["eta_d"]).sum())

    # Cost
    c_RE_avg = (params["c_wind"] * P_wind.sum() + params["c_pv"] * P_pv.sum()) / max(E_RE, 1)
    C_RE_used = c_RE_avg * E_used * 1000
    C_OM_hour = (params["c_ALKEL"] * params["P_ALKEL_max"] * 1000 +
                 params["c_PEMEL"] * params["P_PEMEL_max"] * 1000 +
                 params["c_NH3"] * params["P_NH3_max"] * 1000)
    C_OM = (alpha_sol * C_OM_hour).sum()
    # Storage OM cost
    E_throughput = P_sto_c_sol.sum() + P_sto_d_sol.sum()
    C_sto_om = sto["om_cost"] * E_throughput * 1000
    # Daily amortized storage investment (附件6: 1000元/kWh, 15年寿命)
    C_sto_invest_daily = C_sto * 1000 * sto["invest_cost"] / (sto["lifetime"] * 365)
    C_day = C_RE_used + C_OM + C_sto_om + C_sto_invest_daily
    C_ton = C_day / Q_NH3 if Q_NH3 > 0 else float("inf")

    return {
        "alpha": alpha_sol.tolist(),
        "P_sto_c": P_sto_c_sol.tolist(),
        "P_sto_d": P_sto_d_sol.tolist(),
        "E_sto": E_sto_sol.tolist(),
        "Q_NH3": round(Q_NH3, 2),
        "E_RE": round(E_RE, 2),
        "E_curtail": round(max(0, E_curtail), 2),
        "C_day": round(C_day, 2),
        "C_ton": round(C_ton, 2),
        "C_sto": C_sto,
        "P_sto_max": P_sto_max,
        "C_sto_invest_daily": round(C_sto_invest_daily, 2),
        "C_sto_om": round(C_sto_om, 2),
    }


def solve_problem4():
    print("=" * 60)
    print("问题四：离网运行分析及储能配置")
    print("=" * 60)

    P_load = load_load_profile()
    params = get_equipment_params(72)
    wind_all, pv_all = get_all_scenarios()
    labels = get_scenario_labels()
    sto_params = get_storage_params()

    # ===== 问题四(1): 离网无储能 =====
    print("\n--- 问题四(1): 离网无储能 ---")
    offgrid_results = []
    max_curtail = 0
    max_curtail_idx = 0

    for s in range(24):
        result = solve_q4_offgrid_no_storage(wind_all[s], pv_all[s], P_load, params)
        if result is None:
            result = {"Q_NH3": 0, "E_curtail": 0, "C_ton": float("inf"),
                      "E_RE": 0, "hours_on": 0, "utilization": 0, "C_day": 0}
        offgrid_results.append(result)
        if result["E_curtail"] > max_curtail:
            max_curtail = result["E_curtail"]
            max_curtail_idx = s

    total_annual_production = sum(r["Q_NH3"] for r in offgrid_results) * 15
    max_possible = 72 * 360
    avg_utilization = total_annual_production / max_possible

    print(f"  Annual production: {total_annual_production:.0f} tons (max possible: {max_possible})")
    print(f"  Avg capacity utilization: {avg_utilization*100:.1f}%")
    print(f"  Max curtailment scenario: {labels[max_curtail_idx]} ({max_curtail:.1f} MWh)")

    # Min wind/PV capacity estimation
    print("\n  Estimating minimum wind/PV capacity...")
    P_H2NH3 = params["P_H2NH3_max"]
    min_demand = np.zeros(24)
    for t in range(24):
        min_demand[t] = P_load[t] + 0.1 * P_H2NH3  # minimum: base load + 10% H2NH3

    # Find worst-case RE per unit capacity across all scenarios
    wind_pu_all = wind_all / 40.0  # back to per-unit
    pv_pu_all = pv_all / 64.0

    # LP to find min capacity: min c_wind*Pcap_w + c_pv*Pcap_pv
    # s.t. Pcap_w*wind_pu[s,t] + Pcap_pv*pv_pu[s,t] >= min_demand[t] for all s,t
    from scipy.optimize import linprog
    c_obj = np.array([params["c_wind"], params["c_pv"]])
    A_ub = []
    b_ub = []
    for s in range(24):
        for t in range(24):
            A_ub.append([-wind_pu_all[s, t], -pv_pu_all[s, t]])
            b_ub.append(-min_demand[t])
    result_cap = linprog(c_obj, A_ub=A_ub, b_ub=b_ub,
                         bounds=[(0, None), (0, None)], method='highs')
    if result_cap.success:
        min_wind_cap = result_cap.x[0]
        min_pv_cap = result_cap.x[1]
        print(f"  Min wind capacity: {min_wind_cap:.1f} MW")
        print(f"  Min PV capacity: {min_pv_cap:.1f} MW")
    else:
        min_wind_cap = None
        min_pv_cap = None
        print("  Min capacity estimation failed (some scenarios have zero RE at night)")

    # ===== 问题四(2): 储能配置优化 =====
    print(f"\n--- 问题四(2): 储能配置(最大弃电场景: {labels[max_curtail_idx]}) ---")

    # Parameter sweep for storage capacity
    storage_sweep = []
    C_sto_candidates = [10, 20, 30, 50, 75, 100, 150, 200]

    for C_sto in C_sto_candidates:
        P_sto_max = C_sto / 2.0  # 0.5C rate
        result = solve_q4_with_storage(wind_all[max_curtail_idx], pv_all[max_curtail_idx],
                                       P_load, params, C_sto, P_sto_max)
        if result:
            storage_sweep.append({
                "C_sto": C_sto, "P_sto_max": P_sto_max,
                "Q_NH3": result["Q_NH3"], "C_ton": result["C_ton"],
                "E_curtail": result["E_curtail"],
            })
            print(f"  C_sto={C_sto}MWh: Q={result['Q_NH3']:.1f}t, "
                  f"C_ton={result['C_ton']:.0f}, curtail={result['E_curtail']:.1f}MWh")

    # Find optimal: best marginal benefit (knee point)
    if len(storage_sweep) >= 2:
        # Choose capacity where marginal production gain drops below threshold
        best_idx = 0
        for i in range(1, len(storage_sweep)):
            if storage_sweep[i]["Q_NH3"] > storage_sweep[best_idx]["Q_NH3"]:
                best_idx = i
            marginal = (storage_sweep[i]["Q_NH3"] - storage_sweep[i-1]["Q_NH3"])
            if marginal < 0.5:  # less than 0.5 ton gain
                best_idx = i - 1
                break
        optimal_C_sto = storage_sweep[best_idx]["C_sto"]
    else:
        optimal_C_sto = 50

    optimal_P_sto_max = optimal_C_sto / 2.0
    print(f"\n  Optimal storage: {optimal_C_sto} MWh / {optimal_P_sto_max} MW")

    # Solve all 24 scenarios with optimal storage
    print("\n  Solving 24 scenarios with storage...")
    storage_results = []
    for s in range(24):
        result = solve_q4_with_storage(wind_all[s], pv_all[s], P_load, params,
                                       optimal_C_sto, optimal_P_sto_max)
        if result:
            storage_results.append(result)
        else:
            storage_results.append({"Q_NH3": 0, "C_ton": float("inf"),
                                    "C_day": 0, "E_curtail": 0, "C_sto": optimal_C_sto})
        if (s + 1) % 8 == 0:
            print(f"    completed {s+1}/24")

    total_prod_with_sto = sum(r["Q_NH3"] for r in storage_results) * 15
    avg_util_with_sto = total_prod_with_sto / max_possible

    print(f"\n  With storage - Annual production: {total_prod_with_sto:.0f} tons")
    print(f"  With storage - Avg utilization: {avg_util_with_sto*100:.1f}%")
    print(f"  Improvement over no-storage: {(total_prod_with_sto - total_annual_production)/total_annual_production*100:.1f}%")

    # ===== 问题四(3): 离网vs联网经济性对比 =====
    print("\n--- 问题四(3): 离网vs联网经济性对比 ---")
    # Load Q3 results for comparison
    q3_path = "figures/problem_3_results.json"
    if os.path.exists(q3_path):
        with open(q3_path, "r", encoding="utf-8") as f:
            q3_data = json.load(f)
        q3_annual_C_ton = q3_data["annual_stats"]["annual_C_ton"]
    else:
        q3_annual_C_ton = 4209.48  # fallback

    # Off-grid annual cost with storage
    valid_sto_results = [r for r in storage_results if r["Q_NH3"] > 0]
    if valid_sto_results:
        offgrid_annual_cost = sum(r["C_day"] for r in storage_results) * 15
        offgrid_annual_prod = total_prod_with_sto
        offgrid_C_ton = offgrid_annual_cost / offgrid_annual_prod if offgrid_annual_prod > 0 else float("inf")
    else:
        offgrid_C_ton = float("inf")

    grid_support_value = (offgrid_C_ton - q3_annual_C_ton) / q3_annual_C_ton * 100

    print(f"  On-grid (Q3) annual C_ton: {q3_annual_C_ton:.2f}")
    print(f"  Off-grid (with storage) annual C_ton: {offgrid_C_ton:.2f}")
    print(f"  Grid support cost value: {grid_support_value:.1f}%")

    # Save all results
    all_results = {
        "offgrid_no_storage": [{
            "scenario": labels[s],
            "Q_NH3": offgrid_results[s]["Q_NH3"],
            "E_curtail": offgrid_results[s].get("E_curtail", 0),
            "C_ton": offgrid_results[s]["C_ton"],
            "hours_on": offgrid_results[s].get("hours_on", 0),
            "utilization": offgrid_results[s].get("utilization", 0),
        } for s in range(24)],
        "annual_no_storage": {
            "total_production": round(total_annual_production, 2),
            "avg_utilization": round(avg_utilization, 4),
            "max_curtail_scenario": labels[max_curtail_idx],
            "max_curtail_MWh": round(max_curtail, 2),
        },
        "min_capacity": {
            "wind_MW": round(min_wind_cap, 1) if min_wind_cap else None,
            "pv_MW": round(min_pv_cap, 1) if min_pv_cap else None,
        },
        "storage_sweep": storage_sweep,
        "optimal_storage": {
            "C_sto_MWh": optimal_C_sto,
            "P_sto_max_MW": optimal_P_sto_max,
            "invest_cost_yuan_per_kWh": sto_params["invest_cost"],
            "lifetime_years": sto_params["lifetime"],
            "daily_invest_cost_yuan": round(optimal_C_sto * 1000 * sto_params["invest_cost"] / (sto_params["lifetime"] * 365), 2),
        },
        "with_storage": [{
            "scenario": labels[s],
            "Q_NH3": storage_results[s]["Q_NH3"],
            "C_ton": storage_results[s]["C_ton"],
            "C_sto": storage_results[s].get("C_sto", optimal_C_sto),
        } for s in range(24)],
        "annual_with_storage": {
            "total_production": round(total_prod_with_sto, 2),
            "avg_utilization": round(avg_util_with_sto, 4),
        },
        "economics_comparison": {
            "ongrid_C_ton": round(q3_annual_C_ton, 2),
            "offgrid_C_ton": round(offgrid_C_ton, 2),
            "grid_support_value_pct": round(grid_support_value, 2),
        },
    }

    with open("figures/problem_4_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n>>> Problem 4 results saved")
    return all_results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    solve_problem4()
