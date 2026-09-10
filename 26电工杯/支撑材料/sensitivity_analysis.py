"""灵敏度分析：关键参数对吨氨成本和绿电指标的影响"""
import numpy as np
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_loader import (load_load_profile, load_typical_wind_pv,
                         load_electricity_prices, get_equipment_params)
from problem3 import solve_q3_lp


def run_sensitivity():
    print("=" * 60)
    print("灵敏度分析")
    print("=" * 60)

    P_load = load_load_profile()
    P_wind_typ, P_pv_typ = load_typical_wind_pv()
    buy_price_base, sell_price_base = load_electricity_prices()
    params_base = get_equipment_params(72)
    Q_target = 54  # Use middle production level

    # Baseline
    baseline = solve_q3_lp(P_wind_typ, P_pv_typ, P_load, Q_target,
                           params_base, buy_price_base, sell_price_base)
    print(f"Baseline: C_ton={baseline['C_ton']:.2f}, R_self={baseline['R_self']:.4f}")

    results = {}

    # 1. Wind capacity sensitivity (+-20%)
    print("\n--- Wind capacity +-20% ---")
    wind_factors = [0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2]
    wind_results = {"factors": wind_factors, "C_ton": [], "R_self": [], "R_grid": []}
    for f in wind_factors:
        r = solve_q3_lp(P_wind_typ * f, P_pv_typ, P_load, Q_target,
                        params_base, buy_price_base, sell_price_base)
        if r:
            wind_results["C_ton"].append(r["C_ton"])
            wind_results["R_self"].append(r["R_self"])
            wind_results["R_grid"].append(r["R_grid"])
        else:
            wind_results["C_ton"].append(None)
            wind_results["R_self"].append(None)
            wind_results["R_grid"].append(None)
    results["wind_capacity"] = wind_results
    print(f"  C_ton range: {min(x for x in wind_results['C_ton'] if x):.0f} ~ "
          f"{max(x for x in wind_results['C_ton'] if x):.0f}")

    # 2. PV capacity sensitivity (+-20%)
    print("\n--- PV capacity +-20% ---")
    pv_factors = [0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2]
    pv_results = {"factors": pv_factors, "C_ton": [], "R_self": [], "R_grid": []}
    for f in pv_factors:
        r = solve_q3_lp(P_wind_typ, P_pv_typ * f, P_load, Q_target,
                        params_base, buy_price_base, sell_price_base)
        if r:
            pv_results["C_ton"].append(r["C_ton"])
            pv_results["R_self"].append(r["R_self"])
            pv_results["R_grid"].append(r["R_grid"])
        else:
            pv_results["C_ton"].append(None)
            pv_results["R_self"].append(None)
            pv_results["R_grid"].append(None)
    results["pv_capacity"] = pv_results
    print(f"  C_ton range: {min(x for x in pv_results['C_ton'] if x):.0f} ~ "
          f"{max(x for x in pv_results['C_ton'] if x):.0f}")

    # 3. Buy price sensitivity (+-30%)
    print("\n--- Buy price +-30% ---")
    price_factors = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    price_results = {"factors": price_factors, "C_ton": []}
    for f in price_factors:
        r = solve_q3_lp(P_wind_typ, P_pv_typ, P_load, Q_target,
                        params_base, buy_price_base * f, sell_price_base)
        if r:
            price_results["C_ton"].append(r["C_ton"])
        else:
            price_results["C_ton"].append(None)
    results["buy_price"] = price_results
    print(f"  C_ton range: {min(x for x in price_results['C_ton'] if x):.0f} ~ "
          f"{max(x for x in price_results['C_ton'] if x):.0f}")

    # 4. Sell price sensitivity (+-30%)
    print("\n--- Sell price +-30% ---")
    sell_factors = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    sell_results = {"factors": sell_factors, "C_ton": []}
    for f in sell_factors:
        r = solve_q3_lp(P_wind_typ, P_pv_typ, P_load, Q_target,
                        params_base, buy_price_base, sell_price_base * f)
        if r:
            sell_results["C_ton"].append(r["C_ton"])
        else:
            sell_results["C_ton"].append(None)
    results["sell_price"] = sell_results
    print(f"  C_ton range: {min(x for x in sell_results['C_ton'] if x):.0f} ~ "
          f"{max(x for x in sell_results['C_ton'] if x):.0f}")

    # 5. Production level sensitivity
    print("\n--- Production level ---")
    prod_levels = [36, 40, 45, 50, 54, 58, 63, 67, 72]
    prod_results = {"levels": prod_levels, "C_ton": [], "R_self": [], "R_grid": []}
    for Q in prod_levels:
        r = solve_q3_lp(P_wind_typ, P_pv_typ, P_load, Q,
                        params_base, buy_price_base, sell_price_base)
        if r:
            prod_results["C_ton"].append(r["C_ton"])
            prod_results["R_self"].append(r["R_self"])
            prod_results["R_grid"].append(r["R_grid"])
        else:
            prod_results["C_ton"].append(None)
            prod_results["R_self"].append(None)
            prod_results["R_grid"].append(None)
    results["production_level"] = prod_results

    # Summary: tornado chart data
    baseline_C_ton = baseline["C_ton"]
    tornado = []
    for name, data in [("wind_capacity", wind_results),
                       ("pv_capacity", pv_results),
                       ("buy_price", price_results),
                       ("sell_price", sell_results)]:
        valid = [x for x in data["C_ton"] if x is not None]
        if valid:
            low = min(valid) - baseline_C_ton
            high = max(valid) - baseline_C_ton
            tornado.append({"param": name, "low": round(low, 2), "high": round(high, 2),
                           "range": round(high - low, 2)})

    tornado.sort(key=lambda x: x["range"], reverse=True)
    results["tornado"] = tornado
    results["baseline_C_ton"] = round(baseline_C_ton, 2)

    print("\n--- Tornado chart (sensitivity ranking) ---")
    for item in tornado:
        print(f"  {item['param']}: [{item['low']:+.0f}, {item['high']:+.0f}] range={item['range']:.0f}")

    with open("figures/sensitivity_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n>>> Sensitivity results saved")
    return results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_sensitivity()
