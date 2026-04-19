from __future__ import annotations

import time

from problem1_1 import solve_problem_1_1, save_problem_1_1_results, print_problem_1_1_summary
from problem1_2_improved import solve_problem_1_2_improved, save_problem_1_2_results, print_problem_1_2_summary


if __name__ == "__main__":
    print("========== 开始运行问题1.1 ==========")
    t1 = time.time()
    results = solve_problem_1_1()
    save_problem_1_1_results(results)
    print_problem_1_1_summary(results, time.time() - t1)

    print("\n========== 开始运行问题1.2(改进版） ==========")
    t2 = time.time()
    plans, best_id = solve_problem_1_2_improved()
    save_problem_1_2_results(plans, best_id)
    print_problem_1_2_summary(plans, best_id, time.time() - t2)