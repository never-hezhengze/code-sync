"""主程序：串联所有子问题，汇总结果"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("绿电直连型电氢氨园区优化运行 - 主程序")
print("=" * 60)

# Run all problems
from problem1 import solve_problem1
from problem2 import solve_problem2
from problem3 import solve_problem3
from problem4 import solve_problem4
from sensitivity_analysis import run_sensitivity

print("\n\n>>> Running Problem 1...")
r1 = solve_problem1()

print("\n\n>>> Running Problem 2...")
r2 = solve_problem2()

print("\n\n>>> Running Problem 3...")
r3 = solve_problem3()

print("\n\n>>> Running Problem 4...")
r4 = solve_problem4()

print("\n\n>>> Running Sensitivity Analysis...")
r5 = run_sensitivity()

# Aggregate all results
all_results = {
    "problem1": {
        "energy": r1["energy"],
        "indicators": r1["indicators"],
        "cost": r1["cost"],
    },
    "problem2": {
        "best_Q_typical": r2["best_Q_typical"],
        "annual_stats": r2["annual_stats"],
        "cost_distribution": r2["cost_distribution"],
    },
    "problem3": {
        "annual_stats": r3["annual_stats"],
        "cost_distribution": r3["cost_distribution"],
    },
    "problem4": {
        "annual_no_storage": r4["annual_no_storage"],
        "optimal_storage": r4["optimal_storage"],
        "annual_with_storage": r4["annual_with_storage"],
        "economics_comparison": r4["economics_comparison"],
    },
    "sensitivity": {
        "tornado": r5["tornado"],
        "baseline_C_ton": r5["baseline_C_ton"],
    },
}

with open("figures/all_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("ALL DONE - Results saved to figures/all_results.json")
print("=" * 60)
