# ============================
# MathorCup D - Problem 2 FIXED
# 混合车型 + 保底单车型最优
# ============================

import random
from typing import List, Dict, Tuple

# ============================
# 基础数据（你可以替换成真实数据读取）
# ============================

TYPE_ORDER = ["G1", "G2", "G3", "G4", "G5"]

TRUCKS = {
    "车型1": {"cost": 450, "capacity": 64},
    "车型2": {"cost": 700, "capacity": 120}
}

TOTAL_DEMAND = {
    "G1": 800,
    "G2": 1000,
    "G3": 300,
    "G4": 400,
    "G5": 500
}

# ============================
# 已知问题1.2结果（关键！！！）
# ============================

KNOWN_SOLUTIONS = {
    "车型1": {"vehicles": 27, "cost": 27 * 450},
    "车型2": {"vehicles": 13, "cost": 13 * 700}
}

# ============================
# 简化装箱可行性（占位版本）
# 实际你可以替换成你的pack函数
# ============================

def is_feasible(n1, n2):
    total_capacity = n1 * TRUCKS["车型1"]["capacity"] + n2 * TRUCKS["车型2"]["capacity"]
    total_items = sum(TOTAL_DEMAND.values())
    return total_capacity >= total_items

# ============================
# 生成候选车队结构
# ============================

def generate_structures(max_k=40):
    structures = []
    for k in range(1, max_k + 1):
        for n1 in range(k + 1):
            n2 = k - n1
            structures.append((n1, n2))
    return structures

# ============================
# 主求解函数（带保底）
# ============================

def solve_problem2(objective="min_vehicle"):

    print(f"\n==============================")
    print(f"求解目标: {objective}")
    print(f"==============================")

    best = None

    # ============================
    # 1️⃣ 先加入“单车型保底解”
    # ============================

    candidates = []

    # 车型1
    candidates.append({
        "n1": KNOWN_SOLUTIONS["车型1"]["vehicles"],
        "n2": 0,
        "vehicles": KNOWN_SOLUTIONS["车型1"]["vehicles"],
        "cost": KNOWN_SOLUTIONS["车型1"]["cost"]
    })

    # 车型2
    candidates.append({
        "n1": 0,
        "n2": KNOWN_SOLUTIONS["车型2"]["vehicles"],
        "vehicles": KNOWN_SOLUTIONS["车型2"]["vehicles"],
        "cost": KNOWN_SOLUTIONS["车型2"]["cost"]
    })

    # ============================
    # 2️⃣ 搜索混合车型
    # ============================

    structures = generate_structures(30)

    for n1, n2 in structures:

        if not is_feasible(n1, n2):
            continue

        vehicles = n1 + n2
        cost = n1 * TRUCKS["车型1"]["cost"] + n2 * TRUCKS["车型2"]["cost"]

        candidates.append({
            "n1": n1,
            "n2": n2,
            "vehicles": vehicles,
            "cost": cost
        })

    # ============================
    # 3️⃣ 选最优
    # ============================

    if objective == "min_vehicle":
        best = min(candidates, key=lambda x: x["vehicles"])
    else:
        best = min(candidates, key=lambda x: x["cost"])

    # ============================
    # 4️⃣ 输出
    # ============================

    result = {
        "objective": objective,
        "fleet_structure": {
            "车型1": best["n1"],
            "车型2": best["n2"]
        },
        "vehicle_count": best["vehicles"],
        "total_cost": best["cost"]
    }

    print(result)
    return result


# ============================
# 主函数
# ============================

def main():
    solve_problem2("min_vehicle")
    solve_problem2("min_cost")


if __name__ == "__main__":
    main()