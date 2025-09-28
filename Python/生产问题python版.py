from pyomo.environ import *
from pyomo.opt import SolverFactory
import pandas as pd

# ========== 构建模型 ==========
model = ConcreteModel()

# === Sets ===
T = range(1, 7)
model.T = Set(initialize=T)

# === Parameters ===
w, c, sn, so, oc = 300, 90, 30, 40, 200
ic, bc, Ec, Fc, th = 15, 35, 5000, 8000, 5
I0, H0 = 15000, 1000
D_data = {1: 20000, 2: 40000, 3: 42000, 4: 35000, 5: 19000, 6: 18500}
model.D = Param(model.T, initialize=D_data)

# === Variables ===
model.P = Var(model.T, domain=NonNegativeReals)
model.O = Var(model.T, domain=NonNegativeReals)
model.I = Var(model.T, domain=NonNegativeReals)
model.B = Var(model.T, domain=NonNegativeReals)
model.H = Var(model.T, domain=NonNegativeIntegers)
model.E = Var(model.T, domain=NonNegativeIntegers)
model.F = Var(model.T, domain=NonNegativeIntegers)
model.Tn = Var(model.T, domain=NonNegativeReals)
model.To = Var(model.T, domain=NonNegativeReals)
model.S = Var(model.T, domain=NonNegativeReals)

# === Objective ===
def obj_rule(model):
    return sum(
        w * model.S[t]
        - c * model.P[t]
        - sn * model.Tn[t]
        - so * model.To[t]
        - oc * model.O[t]
        - ic * model.I[t]
        - bc * model.B[t]
        - Ec * model.E[t]
        - Fc * model.F[t]
        for t in model.T
    )
model.obj = Objective(rule=obj_rule, sense=maximize)

# === Constraints ===
def sales_limit_rule(model, t):
    return model.S[t] <= (I0 if t == 1 else model.I[t - 1]) + model.P[t] + model.O[t]
model.sales_limit = Constraint(model.T, rule=sales_limit_rule)

def inventory_balance_rule(model, t):
    if t == 1:
        return model.I[t] == I0 + model.P[t] + model.O[t] - model.S[t] + model.B[t]
    else:
        return model.I[t] == model.I[t - 1] + model.P[t] + model.O[t] - model.S[t] + model.B[t]
model.inventory_balance = Constraint(model.T, rule=inventory_balance_rule)

def labor_flow_rule(model, t):
    if t == 1:
        return model.H[t] == H0 + model.E[t] - model.F[t]
    else:
        return model.H[t] == model.H[t - 1] + model.E[t] - model.F[t]
model.labor_flow = Constraint(model.T, rule=labor_flow_rule)

model.production_constraints = ConstraintList()
for t in model.T:
    model.production_constraints.add(model.P[t] == (model.Tn[t] + model.To[t]) / th)
    model.production_constraints.add(model.Tn[t] == 160 * model.H[t])
    model.production_constraints.add(model.To[t] <= 20 * model.H[t])

model.backorder_limit = ConstraintList()
for t in model.T:
    model.backorder_limit.add(model.B[t] <= model.D[t])

model.final_inventory = Constraint(expr=model.I[6] >= 10000)

# ========== 求解 ==========
solver = SolverFactory('cbc')  # 或 'gurobi', 'glpk'
result = solver.solve(model, tee=True)

# ========== 提取结果 ==========
data = {
    'Period': [],
    'P(生产)': [],
    'O(外包)': [],
    'I(库存)': [],
    'B(缺货)': [],
    'S(销售)': [],
    'H(工人)': [],
    'E(雇佣)': [],
    'F(解雇)': [],
    'Tn(正常工时)': [],
    'To(加班工时)': [],
}

for t in model.T:
    data['Period'].append(t)
    data['P(生产)'].append(value(model.P[t]))
    data['O(外包)'].append(value(model.O[t]))
    data['I(库存)'].append(value(model.I[t]))
    data['B(缺货)'].append(value(model.B[t]))
    data['S(销售)'].append(value(model.S[t]))
    data['H(工人)'].append(value(model.H[t]))
    data['E(雇佣)'].append(value(model.E[t]))
    data['F(解雇)'].append(value(model.F[t]))
    data['Tn(正常工时)'].append(value(model.Tn[t]))
    data['To(加班工时)'].append(value(model.To[t]))

df = pd.DataFrame(data)
pd.set_option('display.float_format', '{:.2f}'.format)
print("\n=== 优化结果表格 ===")
print(df)

print(f"\n总利润: {value(model.obj):,.2f}")
