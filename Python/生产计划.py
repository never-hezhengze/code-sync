from pulp import *

# 创建问题实例
prob = LpProblem("Production_Planning_Optimization", LpMaximize)

# 定义时间段
periods = [1, 2, 3, 4, 5, 6]

# 参数设置
D = {1:20000, 2:40000, 3:42000, 4:35000, 5:19000, 6:18500}  # 需求量
c = 90    # 原材料单价
th = 5    # 单位产品工时(小时/件)
w = 300   # 产品单价
sn = 30   # 正常时薪
so = 40   # 加班时薪
o = 200   # 外包成本
b = 35    # 缺货成本
i = 15    # 库存成本
Ec = 5000 # 雇佣成本
Fc = 8000 # 解雇成本
H0 = 1000 # 初始工人数
I0 = 15000 # 初始库存

# 定义决策变量
P = LpVariable.dicts("Production", periods, lowBound=0, cat='Integer')  # 生产量
O = LpVariable.dicts("Outsource", periods, lowBound=0, cat='Integer')  # 外包量
I = LpVariable.dicts("Inventory", periods, lowBound=0, cat='Integer')  # 库存量
B = LpVariable.dicts("Backorder", periods, lowBound=0, cat='Integer')  # 缺货量
H = LpVariable.dicts("Workers", periods, lowBound=0, cat='Integer')    # 工人数
E = LpVariable.dicts("Hire", periods, lowBound=0, cat='Integer')      # 雇佣人数
F = LpVariable.dicts("Fire", periods, lowBound=0, cat='Integer')      # 解雇人数
Tn = LpVariable.dicts("NormalTime", periods, lowBound=0)              # 正常工时
To = LpVariable.dicts("Overtime", periods, lowBound=0)                # 加班工时

# 设置目标函数
prob += lpSum([w * (D[t] - B[t]) - c * P[t] - sn * Tn[t] - so * To[t] - 
               o * O[t] - i * I[t] - b * B[t] - Ec * E[t] - Fc * F[t] 
               for t in periods])

# 约束条件

# 库存平衡约束
for t in periods:
    if t == 1:
        prob += I0 + P[t] + O[t] - D[t] + B[t] == I[t]
    else:
        prob += I[t-1] + P[t] + O[t] - D[t] + B[t] == I[t]

# 产能与工时约束
for t in periods:
    prob += Tn[t] + To[t] == th * P[t]       # 总工时=生产量×单位工时
    prob += Tn[t] == 160 * H[t]              # 正常工时=160×工人数
    prob += To[t] <= 20 * H[t]               # 加班工时≤20×工人数

# 工人数动态变化
for t in periods:
    if t == 1:
        prob += H[t] == H0 + E[t] - F[t]
    else:
        prob += H[t] == H[t-1] + E[t] - F[t]

# 6月末库存要求(可选)
# prob += I[6] >= 10000

# 求解问题
prob.solve()

# 输出结果
print("Status:", LpStatus[prob.status])
print("Maximum Profit = $", value(prob.objective))
print("\nOptimal Solution:")

# 打印各期决策变量值
for t in periods:
    print(f"\nPeriod {t}:")
    print(f"Production: {P[t].varValue} units")
    print(f"Outsource: {O[t].varValue} units")
    print(f"Inventory: {I[t].varValue} units")
    print(f"Backorder: {B[t].varValue} units")
    print(f"Workers: {H[t].varValue} people")
    print(f"Hire: {E[t].varValue}, Fire: {F[t].varValue}")
    print(f"Normal Hours: {Tn[t].varValue}, Overtime: {To[t].varValue}")