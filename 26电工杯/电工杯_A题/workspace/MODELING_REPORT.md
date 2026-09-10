# 建模求解报告：绿电直连型电氢氨园区优化运行

## 一、模型假设

### 假设 1：电氢氨装置作为整体同步运行
- 理由：题目明确"电氢氨装置只有全额开机和停机两种运行方式"（问题二），制氢是为制氨服务，ALKEL、PEMEL、合成氨装置在运行时保持固定功率比例关系
- 参数化：`SYNC_OPERATION = True`（代码中的开关变量）
- 替代假设：三者独立调度（`SYNC_OPERATION = False`），但这与题目"电氢氨装置"整体表述矛盾

### 假设 2：产能扩容时仅电氢氨设备线性提升，风光装机不变
- 理由：题目说"配套电氢氨装置的额定功率将随产能规模呈线性同步提升"，未提及风光装机变化。72吨/日时：ALKEL=20MW, PEMEL=20MW, NH3=1.5MW
- 参数化：`SCALE_FACTOR = Q_target / 36`（产能缩放因子）
- 替代假设：风光也同步扩容（但题目未支持此解释）

### 假设 3：不计园区内部功率损耗
- 理由：题目明确"不计园区功率损耗"
- 参数化：`LOSS_FACTOR = 0`（内部损耗系数）
- 替代假设：考虑2-5%线损（`LOSS_FACTOR = 0.03`）

### 假设 4：每个时段内功率恒定
- 理由：题目"园区运行分析时段为1小时"，即以1小时为最小调度单元
- 参数化：`DT = 1`（小时）
- 替代假设：更细粒度（15分钟），但题目未要求

### 假设 5：制氢产氢速率与电解槽功率严格线性
- 理由：题目给出额定功率和额定产氢速率，在功率连续可调（下限10%）范围内假设线性关系
- 参数化：`H2_RATE_ALKEL = 140 / 10000`（kg/kWh），`H2_RATE_PEMEL = 160 / 10000`（kg/kWh）
- 替代假设：非线性效率曲线（但题目未给出效率-负荷曲线数据）

### 假设 6：合成氨耗氢与产氨严格线性
- 理由：题目给出"0.2 kgH₂/kgNH₃"为固定比例
- 参数化：`H2_PER_NH3 = 0.2`（kgH₂/kgNH₃）
- 替代假设：无（题目明确给出固定比例）

### 假设 7：储能初末状态相同（日循环约束）
- 理由：储能作为日内调度工具，一天结束时应恢复初始状态，避免跨日能量转移
- 参数化：`SOC_CYCLE = True`（日循环约束开关）
- 替代假设：允许跨日储能（`SOC_CYCLE = False`），但会使问题复杂化且不符合日调度框架

### 假设 8：24种场景各代表15天，全年共360天
- 理由：题目明确"假设每一种风光场景代表15天"，24×15=360天
- 参数化：`DAYS_PER_SCENARIO = 15`
- 替代假设：无（题目明确）

### 假设 9：吨氨成本计算包含风光度电成本、购电成本、运维成本，扣除售电收入
- 理由：题目要求计算"吨氨成本"，应包含所有与生产相关的可变成本
- 参数化：成本组成在代码中分项计算
- 替代假设：是否包含设备折旧（年化投资成本）——根据题目附件给出的度电成本已包含投资折旧

### 假设 10：问题二中产量递减时设备额定功率不变（仍为72吨/日配置）
- 理由：题目说"制氨产能增至72吨/日"后"产量从72吨/日起按9吨/日递减"，设备配置按72吨/日，只是运行时间/功率调整
- 参数化：设备参数固定为72吨/日配置
- 替代假设：无（产能=设备配置，产量=实际运行量）

## 二、符号说明

| 符号 | 含义 | 单位 | 取值范围 | 首次出现 |
|------|------|------|----------|----------|
| $T$ | 调度时段总数 | — | 24 | 全局 |
| $\Delta t$ | 时段长度 | h | 1 | 全局 |
| $P_{wind}(t)$ | 风电出力功率 | MW | [0, 40] | 问题一 |
| $P_{pv}(t)$ | 光伏出力功率 | MW | [0, 64] | 问题一 |
| $P_{load}(t)$ | 常规电负荷功率 | MW | [0.80, 4.20] | 问题一 |
| $P_{ALKEL}^{max}$ | ALKEL额定功率 | MW | 10(36t) / 20(72t) | 问题一 |
| $P_{PEMEL}^{max}$ | PEMEL额定功率 | MW | 10(36t) / 20(72t) | 问题一 |
| $P_{NH3}^{max}$ | 合成氨额定功率 | MW | 0.75(36t) / 1.5(72t) | 问题一 |
| $P_{H2NH3}^{max}$ | 电氢氨总额定功率 | MW | 20.75(36t) / 41.5(72t) | 问题一 |
| $P_{buy}(t)$ | 购电功率 | MW | $\geq 0$ | 问题一 |
| $P_{sell}(t)$ | 售电功率 | MW | $\geq 0$ | 问题一 |
| $u(t)$ | 开停机状态（问题二） | — | $\{0, 1\}$ | 问题二 |
| $\alpha(t)$ | 功率调节系数（问题三四） | — | $[0.1, 1]$ | 问题三 |
| $P_{sto,c}(t)$ | 储能充电功率 | MW | $\geq 0$ | 问题四 |
| $P_{sto,d}(t)$ | 储能放电功率 | MW | $\geq 0$ | 问题四 |
| $E_{sto}(t)$ | 储能荷电量（SOC） | MWh | $[0, C_{sto}]$ | 问题四 |
| $C_{sto}$ | 储能额定容量 | MWh | 待优化 | 问题四 |
| $P_{sto}^{max}$ | 储能最大充放电功率 | MW | 待优化 | 问题四 |
| $\eta_c$ | 储能充电效率 | — | 0.90 | 问题四 |
| $\eta_d$ | 储能放电效率 | — | 0.90 | 问题四 |
| $\sigma$ | 储能自损耗率 | /h | 0.002 | 问题四 |
| $E_{total}$ | 日总用电量 | MWh | — | 全局 |
| $E_{RE}$ | 新能源日发电量 | MWh | — | 全局 |
| $E_{buy}$ | 日网购电量 | MWh | — | 全局 |
| $E_{sell}$ | 日上网电量 | MWh | — | 全局 |
| $R_{self}$ | 自发自用比例 | — | 要求 > 0.6 | 全局 |
| $R_{green}$ | 绿电比例 | — | 要求 > 0.3 | 全局 |
| $R_{grid}$ | 上网电量比例 | — | 要求 < 0.2 | 全局 |
| $\lambda_{buy}(t)$ | 分时购电电价 | 元/kWh | 见电价表 | 全局 |
| $\lambda_{sell}$ | 售电电价 | 元/kWh | 0.3779 | 全局 |
| $c_{wind}$ | 风电度电成本 | 元/kWh | 0.15 | 全局 |
| $c_{pv}$ | 光伏度电成本 | 元/kWh | 0.12 | 全局 |
| $c_{ALKEL}$ | ALKEL运维系数 | 元/kWh | 0.10 | 全局 |
| $c_{PEMEL}$ | PEMEL运维系数 | 元/kWh | 0.15 | 全局 |
| $c_{NH3}$ | 合成氨运维系数 | 元/kWh | 0.002 | 全局 |
| $c_{sto}$ | 储能运维系数 | 元/kWh | 0.01 | 问题四 |
| $Q_{NH3}$ | 日制氨产量 | 吨/日 | [36, 72] | 问题二 |
| $C_{ton}$ | 吨氨成本 | 元/吨 | — | 全局 |
| $r_{H2,ALKEL}$ | ALKEL产氢速率 | kg/h | 140(36t) / 280(72t) | 全局 |
| $r_{H2,PEMEL}$ | PEMEL产氢速率 | kg/h | 160(36t) / 320(72t) | 全局 |
| $r_{NH3}$ | 合成氨速率 | 吨/h | 1.5(36t) / 3.0(72t) | 全局 |


## 三、问题一：典型风光场景下运行指标分析

### 3.1 方法选择

**选用方法：** 功率平衡直接计算（无优化）

**理由：** 问题一条件为"满负荷连续运行"，无决策变量，只需按功率平衡原则逐时段计算购电/售电功率，再累加得到日能量指标。与 PROBLEM_ANALYSIS.md 推荐方法一致。

### 3.2 数学模型

#### 3.2.1 功率平衡方程

在每个时段 $t \in \{1, 2, ..., 24\}$，园区功率平衡：

$$
P_{wind}(t) + P_{pv}(t) + P_{buy}(t) = P_{load}(t) + P_{ALKEL}^{max} + P_{PEMEL}^{max} + P_{NH3}^{max} + P_{sell}(t)
$$

由于满负荷运行，制氢氨设备功率为常数：

$$
P_{H2NH3} = P_{ALKEL}^{max} + P_{PEMEL}^{max} + P_{NH3}^{max} = 10 + 10 + 0.75 = 20.75 \text{ MW}
$$

定义净负荷（园区总用电减去新能源发电）：

$$
P_{net}(t) = P_{load}(t) + P_{H2NH3} - P_{wind}(t) - P_{pv}(t)
$$

则：

$$
P_{buy}(t) = \max(0, P_{net}(t))
$$

$$
P_{sell}(t) = \max(0, -P_{net}(t))
$$

约束条件：$P_{buy}(t) \geq 0$，$P_{sell}(t) \geq 0$，$P_{buy}(t) \cdot P_{sell}(t) = 0$（同一时段不能同时购售电）。

#### 3.2.2 日能量指标计算

$$
E_{total} = \sum_{t=1}^{24} [P_{load}(t) + P_{H2NH3}] \cdot \Delta t
$$

$$
E_{RE} = \sum_{t=1}^{24} [P_{wind}(t) + P_{pv}(t)] \cdot \Delta t
$$

$$
E_{buy} = \sum_{t=1}^{24} P_{buy}(t) \cdot \Delta t
$$

$$
E_{sell} = \sum_{t=1}^{24} P_{sell}(t) \cdot \Delta t
$$

#### 3.2.3 绿电直连指标

$$
R_{self} = \frac{E_{total} - E_{sell} - E_{buy}}{E_{RE}} = \frac{E_{RE} - E_{sell}}{E_{RE}} = 1 - \frac{E_{sell}}{E_{RE}}
$$

注：由功率平衡 $E_{total} = E_{RE} + E_{buy} - E_{sell}$，代入得上式。

实际按题目公式：

$$
R_{self} = \frac{E_{total} - E_{sell} - E_{buy}}{E_{RE}} \quad (\text{要求} > 60\%)
$$

$$
R_{green} = \frac{E_{RE} - E_{sell}}{E_{total}} \quad (\text{要求} > 30\%)
$$

$$
R_{grid} = \frac{E_{sell}}{E_{RE}} \quad (\text{要求} < 20\%)
$$

#### 3.2.4 吨氨成本模型

$$
C_{ton} = \frac{C_{RE} + C_{buy} + C_{OM} - I_{sell}}{Q_{NH3}}
$$

其中：

$$
C_{RE} = \sum_{t=1}^{24} [c_{wind} \cdot P_{wind}(t) + c_{pv} \cdot P_{pv}(t)] \cdot \Delta t
$$

$$
C_{buy} = \sum_{t=1}^{24} \lambda_{buy}(t) \cdot P_{buy}(t) \cdot \Delta t
$$

$$
C_{OM} = \sum_{t=1}^{24} [c_{ALKEL} \cdot P_{ALKEL}^{max} + c_{PEMEL} \cdot P_{PEMEL}^{max} + c_{NH3} \cdot P_{NH3}^{max}] \cdot \Delta t
$$

$$
I_{sell} = \lambda_{sell} \cdot E_{sell}
$$

**分时电价映射：**

| 时段 | 类型 | 电价(元/kWh) |
|------|------|-------------|
| 23:00-07:00 (t=24,1-7) | 低谷 | 0.3424 |
| 07:00-10:00, 15:00-18:00, 21:00-23:00 (t=8-10,16-18,22-23) | 平时 | 0.6074 |
| 10:00-15:00, 18:00-21:00 (t=11-15,19-21) | 高峰 | 0.8024 |

### 3.3 算法设计

```
输入: 附件1(负荷标幺), 附件2(风光标幺), 设备参数, 电价参数
输出: 24h功率曲线, 日能量指标, 绿电指标, 吨氨成本

for t = 1 to 24:
    P_load[t] = load_pu[t] * 6  # MW
    P_wind[t] = wind_pu[t] * 40  # MW
    P_pv[t] = pv_pu[t] * 64  # MW
    P_net[t] = P_load[t] + 20.75 - P_wind[t] - P_pv[t]
    P_buy[t] = max(0, P_net[t])
    P_sell[t] = max(0, -P_net[t])

计算日能量: E_total, E_RE, E_buy, E_sell
计算绿电指标: R_self, R_green, R_grid
计算吨氨成本: C_ton
```


## 四、问题二：基于离散制氨调节的运行优化

### 4.1 方法选择

**选用方法：** 0-1整数规划（MILP）+ 枚举验证

**理由：** 决策变量为24个二进制变量（每小时开/停），约束为线性，目标函数为线性（购电成本为分时电价加权）。问题规模小（24个0-1变量），可用MILP精确求解。同时由于 $C(24,k)$ 最大为 $C(24,12) \approx 270$ 万，枚举法也可行作为验证手段。与 PROBLEM_ANALYSIS.md 推荐方法一致。

**WebSearch调研确认：** 此类生产调度问题（unit commitment）在电力系统中广泛使用MILP求解，是成熟方法。

### 4.2 问题设置

产能72吨/日，设备参数线性扩容：
- ALKEL: 20MW, 280 kg H₂/h
- PEMEL: 20MW, 320 kg H₂/h  
- 合成氨: 1.5MW, 3.0 吨NH₃/h
- 电氢氨总功率: $P_{H2NH3}^{max} = 20 + 20 + 1.5 = 41.5$ MW

产量从72吨/日递减至36吨/日，步长9吨/日：
- 产量集合：$Q \in \{72, 63, 54, 45, 36\}$ 吨/日
- 对应开机时数：$k = Q / (3.0) = \{24, 21, 18, 15, 12\}$ 小时

### 4.3 数学模型

#### 4.3.1 决策变量

$$
u(t) \in \{0, 1\}, \quad t = 1, 2, ..., 24
$$

$u(t) = 1$ 表示时段 $t$ 电氢氨装置开机运行。

#### 4.3.2 约束条件

**产量约束（等式）：**

$$
\sum_{t=1}^{24} u(t) = k = \lceil Q_{NH3} / r_{NH3} \rceil
$$

其中 $r_{NH3} = 3.0$ 吨/h（72吨/日配置下的合成氨速率）。

**功率平衡：**

$$
P_{buy}(t) - P_{sell}(t) = P_{load}(t) + u(t) \cdot P_{H2NH3}^{max} - P_{wind}(t) - P_{pv}(t)
$$

$$
P_{buy}(t) \geq 0, \quad P_{sell}(t) \geq 0
$$

为避免双线性项，引入辅助变量处理：

$$
P_{net}(t) = P_{load}(t) + u(t) \cdot P_{H2NH3}^{max} - P_{wind}(t) - P_{pv}(t)
$$

$$
P_{buy}(t) \geq P_{net}(t), \quad P_{buy}(t) \geq 0
$$

$$
P_{sell}(t) = P_{buy}(t) - P_{net}(t)
$$

#### 4.3.3 目标函数

最小化日运行总成本：

$$
\min \quad C_{day} = C_{RE} + C_{buy} + C_{OM} - I_{sell}
$$

其中：

$$
C_{RE} = \sum_{t=1}^{24} [c_{wind} \cdot P_{wind}(t) + c_{pv} \cdot P_{pv}(t)] \cdot \Delta t
$$

$$
C_{buy} = \sum_{t=1}^{24} \lambda_{buy}(t) \cdot P_{buy}(t) \cdot \Delta t
$$

$$
C_{OM} = \sum_{t=1}^{24} u(t) \cdot [c_{ALKEL} \cdot P_{ALKEL}^{max} + c_{PEMEL} \cdot P_{PEMEL}^{max} + c_{NH3} \cdot P_{NH3}^{max}] \cdot \Delta t
$$

$$
I_{sell} = \lambda_{sell} \cdot \sum_{t=1}^{24} P_{sell}(t) \cdot \Delta t
$$

运维成本展开：

$$
C_{OM,hour} = 0.10 \times 20000 + 0.15 \times 20000 + 0.002 \times 1500 = 2000 + 3000 + 3 = 5003 \text{ 元/h}
$$

#### 4.3.4 吨氨成本

$$
C_{ton} = \frac{C_{day}}{Q_{NH3}}
$$

#### 4.3.5 绿电指标计算

$$
E_{total} = \sum_{t=1}^{24} [P_{load}(t) + u(t) \cdot P_{H2NH3}^{max}] \cdot \Delta t
$$

$$
E_{RE} = \sum_{t=1}^{24} [P_{wind}(t) + P_{pv}(t)] \cdot \Delta t
$$

$$
E_{buy} = \sum_{t=1}^{24} P_{buy}(t) \cdot \Delta t, \quad E_{sell} = \sum_{t=1}^{24} P_{sell}(t) \cdot \Delta t
$$

三项指标按公式计算（同问题一）。

### 4.4 求解策略

**问题二(1) — 典型场景：**
- 对每个产量 $Q \in \{72, 63, 54, 45, 36\}$，用MILP求解最优开机时段
- 比较各产量的吨氨成本，找出最优日产量
- 分析最优产量对应的绿电指标合格情况

**问题二(2) — 24种场景：**
- 对每个场景 $s \in \{1,...,24\}$ 和每个产量 $Q$，求解MILP
- 统计各场景最优方案的绿电指标满足情况
- 全年统计：每种场景代表15天，分"全满足/部分满足/全不满足"三类
- 绘制全年吨氨成本分布曲线

**全年总吨氨成本：**

$$
C_{ton,year} = \frac{\sum_{s=1}^{24} C_{day,s}^* \times 15}{\sum_{s=1}^{24} Q_{NH3,s}^* \times 15} = \frac{\sum_{s=1}^{24} C_{day,s}^*}{\sum_{s=1}^{24} Q_{NH3,s}^*}
$$

### 4.5 算法伪代码

```
# 问题二(1): 典型场景
for Q in [72, 63, 54, 45, 36]:
    k = Q / 3.0  # 开机小时数
    model = MILP()
    u = model.binary_vars(24)
    model.add_constraint(sum(u) == k)
    # 功率平衡约束
    for t in range(24):
        P_net = P_load[t] + u[t]*41.5 - P_wind_typical[t] - P_pv_typical[t]
        P_buy[t] >= P_net
        P_buy[t] >= 0
        P_sell[t] = P_buy[t] - P_net
    # 目标函数
    model.minimize(sum(lambda_buy[t]*P_buy[t] + u[t]*5003 for t in range(24))
                   - lambda_sell * sum(P_sell[t]))
    solve(model)
    record(Q, C_ton, R_self, R_green, R_grid)

# 问题二(2): 24种场景
for s in range(24):
    wind_s, pv_s = get_scenario(s)
    for Q in [72, 63, 54, 45, 36]:
        solve_MILP(wind_s, pv_s, Q) -> best_cost
    select Q* with min C_ton
    record(s, Q*, schedule, indicators)
```


## 五、问题三：基于连续制氨调节的运行优化

### 5.1 方法选择

**选用方法：** 线性规划（LP）

**理由：** 功率连续可调（下限10%），决策变量为连续变量 $\alpha(t) \in [0.1, 1]$。目标函数（购电成本-售电收入）关于 $\alpha(t)$ 为线性，约束也为线性，因此是标准LP问题。与 PROBLEM_ANALYSIS.md 推荐方法一致。

### 5.2 数学模型

#### 5.2.1 决策变量

$$
\alpha(t) \in [0.1, 1.0], \quad t = 1, 2, ..., 24
$$

$\alpha(t)$ 为时段 $t$ 电氢氨装置的功率调节系数（相对于额定功率的比例）。

#### 5.2.2 约束条件

**产量约束：**

对于目标日产量 $Q_{NH3}$（吨/日），合成氨速率为 $r_{NH3} = 3.0$ 吨/h（72吨/日配置），则：

$$
\sum_{t=1}^{24} \alpha(t) \cdot r_{NH3} \cdot \Delta t = Q_{NH3}
$$

即：

$$
\sum_{t=1}^{24} \alpha(t) = \frac{Q_{NH3}}{3.0}
$$

**功率下限约束：**

$$
\alpha(t) \geq 0.1, \quad \forall t
$$

**功率上限约束：**

$$
\alpha(t) \leq 1.0, \quad \forall t
$$

**功率平衡：**

$$
P_{buy}(t) - P_{sell}(t) = P_{load}(t) + \alpha(t) \cdot P_{H2NH3}^{max} - P_{wind}(t) - P_{pv}(t)
$$

$$
P_{buy}(t) \geq 0, \quad P_{sell}(t) \geq 0
$$

**产量可行性约束：**

$$
Q_{NH3} \geq 0.1 \times 24 \times 3.0 = 7.2 \text{ 吨/日（最低产量）}
$$

$$
Q_{NH3} \leq 1.0 \times 24 \times 3.0 = 72 \text{ 吨/日（最高产量）}
$$

对于 $Q \in \{72, 63, 54, 45, 36\}$，对应 $\sum \alpha(t) = \{24, 21, 18, 15, 12\}$。

#### 5.2.3 目标函数

$$
\min \quad C_{day} = C_{RE} + C_{buy} + C_{OM} - I_{sell}
$$

其中运维成本随功率调节：

$$
C_{OM} = \sum_{t=1}^{24} \alpha(t) \cdot [c_{ALKEL} \cdot P_{ALKEL}^{max} + c_{PEMEL} \cdot P_{PEMEL}^{max} + c_{NH3} \cdot P_{NH3}^{max}] \cdot \Delta t
$$

$$
= \sum_{t=1}^{24} \alpha(t) \cdot 5003 \text{ 元}
$$

新能源成本 $C_{RE}$ 与调度无关（风光发电量固定），但计入吨氨成本。

**LP标准形式：**

令 $x = [\alpha(1),...,\alpha(24), P_{buy}(1),...,P_{buy}(24)]^T$，则：

$$
\min \quad \sum_{t=1}^{24} [\lambda_{buy}(t) \cdot P_{buy}(t) + 5003 \cdot \alpha(t)] - \lambda_{sell} \cdot \sum_{t=1}^{24} P_{sell}(t)
$$

其中 $P_{sell}(t) = P_{buy}(t) - P_{load}(t) - \alpha(t) \cdot 41.5 + P_{wind}(t) + P_{pv}(t)$

代入后目标函数为关于 $\alpha(t)$ 和 $P_{buy}(t)$ 的线性函数。

#### 5.2.4 LP求解的经济直觉

对于时段 $t$，增加 $\alpha(t)$ 的边际成本为：
- 增加运维成本：$5003$ 元/单位$\alpha$
- 增加用电需求 $41.5$ MW，若此时需购电则增加 $\lambda_{buy}(t) \times 41500$ 元
- 若此时有余电则减少售电收入 $\lambda_{sell} \times 41500$ 元

因此最优策略倾向于在**购电电价低**且**风光出力高**的时段提高 $\alpha(t)$。

### 5.3 与问题二的对比分析框架

| 维度 | 问题二（离散） | 问题三（连续） |
|------|-------------|-------------|
| 决策空间 | $\{0,1\}^{24}$ | $[0.1,1]^{24}$ |
| 灵活性 | 只能全开/全停 | 可部分负荷运行 |
| 预期成本 | 较高 | 较低（更灵活） |
| 绿电指标 | 可能不满足 | 更容易满足 |
| 设备利用率 | 开机时100%，停机时0% | 10%-100%连续 |

**预期结论：** 连续调节相比离散调节，吨氨成本应降低（因为可以在高电价时段降低功率而非完全停机），绿电指标应改善（可以更好地跟踪风光出力）。

### 5.4 算法伪代码

```
# 问题三: 连续调度LP
for s in range(24):  # 24种场景
    wind_s, pv_s = get_scenario(s)
    for Q in [72, 63, 54, 45, 36]:
        k_sum = Q / 3.0  # alpha之和
        
        # 构建LP
        model = LP()
        alpha = model.continuous_vars(24, lb=0.1, ub=1.0)
        P_buy = model.continuous_vars(24, lb=0)
        
        # 产量约束
        model.add_constraint(sum(alpha) == k_sum)
        
        # 功率平衡
        for t in range(24):
            P_net = P_load[t] + alpha[t]*41.5 - wind_s[t] - pv_s[t]
            model.add_constraint(P_buy[t] >= P_net)
            P_sell[t] = P_buy[t] - P_net  # 非负由P_buy>=P_net保证
        
        # 目标函数
        obj = sum(lambda_buy[t]*P_buy[t] + 5003*alpha[t] for t in range(24))
            - lambda_sell * sum(P_sell[t] for t in range(24))
        model.minimize(obj + C_RE)  # C_RE为常数
        
        solve(model)
        record(s, Q, C_ton, indicators)
    
    select Q* with min C_ton for scenario s
```


## 六、问题四：离网运行与储能配置

### 6.1 方法选择

**选用方法：** 
- 问题四(1)：线性规划（LP）— 离网无储能最大化产量
- 问题四(2)：混合整数线性规划（MILP）+ 参数扫描 — 储能容量优化配置
- 问题四(3)：年化成本分析 — 经济性对比

**理由：** 离网条件下无购售电，功率平衡约束更紧。储能引入后增加充放电决策变量和SOC状态方程，仍为线性约束。储能容量为待优化参数，可通过参数扫描或将其作为决策变量纳入MILP。与 PROBLEM_ANALYSIS.md 推荐方法一致。

### 6.2 问题四(1)：离网无储能运行

#### 6.2.1 数学模型

**离网约束：** $P_{buy}(t) = 0$，$P_{sell}(t) = 0$（无与电网交互）

但实际上离网时风光发电可能超过负荷需求，多余电力需要弃掉（弃电）：

$$
P_{curtail}(t) = P_{wind}(t) + P_{pv}(t) - P_{load}(t) - \alpha(t) \cdot P_{H2NH3}^{max} \geq 0
$$

**功率平衡约束（离网）：**

$$
\alpha(t) \cdot P_{H2NH3}^{max} + P_{load}(t) \leq P_{wind}(t) + P_{pv}(t), \quad \forall t
$$

即：

$$
\alpha(t) \leq \frac{P_{wind}(t) + P_{pv}(t) - P_{load}(t)}{P_{H2NH3}^{max}}, \quad \forall t
$$

**功率下限约束：**

$$
\alpha(t) \geq 0.1 \quad \text{或} \quad \alpha(t) = 0
$$

注意：题目说"功率连续可调（下限为10%）"，但离网时如果风光不足以支撑10%负荷，设备必须停机。因此引入二进制变量：

$$
\alpha(t) \geq 0.1 \cdot v(t), \quad v(t) \in \{0, 1\}
$$

$$
\alpha(t) \leq v(t)
$$

当 $v(t) = 0$ 时 $\alpha(t) = 0$（停机），当 $v(t) = 1$ 时 $\alpha(t) \in [0.1, 1]$。

**上界约束：**

$$
\alpha(t) \leq \frac{\max(0, P_{wind}(t) + P_{pv}(t) - P_{load}(t))}{P_{H2NH3}^{max}}
$$

如果 $P_{wind}(t) + P_{pv}(t) < P_{load}(t)$，则 $\alpha(t) = 0$（风光连常规负荷都不够）。

如果 $P_{wind}(t) + P_{pv}(t) - P_{load}(t) < 0.1 \times P_{H2NH3}^{max} = 4.15$ MW，则设备必须停机。

**目标函数：** 最大化日制氨产量

$$
\max \quad Q_{NH3} = r_{NH3} \cdot \sum_{t=1}^{24} \alpha(t) \cdot \Delta t = 3.0 \cdot \sum_{t=1}^{24} \alpha(t)
$$

**吨氨成本（离网）：**

$$
C_{ton} = \frac{C_{RE,used} + C_{OM}}{Q_{NH3}}
$$

其中 $C_{RE,used}$ 为实际使用的新能源成本（不含弃电部分）：

$$
C_{RE,used} = \sum_{t=1}^{24} \frac{P_{load}(t) + \alpha(t) \cdot P_{H2NH3}^{max}}{P_{wind}(t) + P_{pv}(t)} \cdot [c_{wind} \cdot P_{wind}(t) + c_{pv} \cdot P_{pv}(t)] \cdot \Delta t
$$

简化处理：离网时所有用电来自风光，按风光加权平均度电成本计算：

$$
C_{RE,used} = \sum_{t=1}^{24} [P_{load}(t) + \alpha(t) \cdot P_{H2NH3}^{max}] \cdot \bar{c}_{RE} \cdot \Delta t
$$

其中 $\bar{c}_{RE} = \frac{c_{wind} \cdot E_{wind} + c_{pv} \cdot E_{pv}}{E_{wind} + E_{pv}}$ 为风光加权平均度电成本。

#### 6.2.2 最小风光装机容量估算

要使园区能源自给（至少满足常规负荷+最低10%制氢氨），需要：

$$
P_{wind}^{cap} \cdot p_{wind}(t) + P_{pv}^{cap} \cdot p_{pv}(t) \geq P_{load}(t) + 0.1 \cdot P_{H2NH3}^{max}, \quad \forall t
$$

这是一个关于 $(P_{wind}^{cap}, P_{pv}^{cap})$ 的线性可行性问题。最小装机容量可通过求解：

$$
\min \quad c_{wind} \cdot P_{wind}^{cap} + c_{pv} \cdot P_{pv}^{cap}
$$

$$
\text{s.t.} \quad P_{wind}^{cap} \cdot p_{wind,min}(t) + P_{pv}^{cap} \cdot p_{pv,min}(t) \geq P_{load}(t) + 0.1 \cdot P_{H2NH3}^{max}, \quad \forall t, \forall s
$$

在所有24种场景中最严苛的时段确定最小装机。

### 6.3 问题四(2)：储能配置优化

#### 6.3.1 储能状态方程

$$
E_{sto}(t+1) = E_{sto}(t) \cdot (1 - \sigma) + \eta_c \cdot P_{sto,c}(t) \cdot \Delta t - \frac{P_{sto,d}(t) \cdot \Delta t}{\eta_d}
$$

其中 $\sigma = 0.002$（自损耗率/h），$\eta_c = 0.9$，$\eta_d = 0.9$。

#### 6.3.2 储能约束

$$
0 \leq E_{sto}(t) \leq C_{sto}, \quad \forall t
$$

$$
0 \leq P_{sto,c}(t) \leq P_{sto}^{max}, \quad \forall t
$$

$$
0 \leq P_{sto,d}(t) \leq P_{sto}^{max}, \quad \forall t
$$

$$
P_{sto,c}(t) \cdot P_{sto,d}(t) = 0 \quad \text{（不能同时充放电）}
$$

日循环约束：$E_{sto}(25) = E_{sto}(1)$

功率比约束（储能C-rate）：假设 $P_{sto}^{max} = C_{sto} / 2$（2小时储能，0.5C）

#### 6.3.3 离网+储能功率平衡

$$
\alpha(t) \cdot P_{H2NH3}^{max} + P_{load}(t) + P_{sto,c}(t) = P_{wind}(t) + P_{pv}(t) + P_{sto,d}(t) - P_{curtail}(t)
$$

$$
P_{curtail}(t) \geq 0
$$

#### 6.3.4 储能容量优化目标

针对最大弃电场景，最小化储能投资+运维的年化成本，同时最大化产量：

**方法：参数扫描**

对 $C_{sto} \in \{10, 20, 30, ..., 200\}$ MWh，求解LP得到最大产量和弃电量，绘制储能容量-产量-成本曲线，找到边际效益拐点作为最优配置。

**年化储能成本：**

$$
C_{sto,annual} = \frac{C_{sto} \times 1000}{15} + c_{sto} \cdot E_{sto,throughput,annual}
$$

其中 1000 元/kWh 为投资成本，15年寿命，$E_{sto,throughput,annual}$ 为年充放电量。

#### 6.3.5 24场景调度方案

确定最优储能容量后，对24种场景分别求解LP：

$$
\max \quad Q_{NH3} = 3.0 \cdot \sum_{t=1}^{24} \alpha(t)
$$

$$
\text{s.t.} \quad \text{功率平衡 + 储能约束 + 功率下限}
$$

### 6.4 问题四(3)：离网vs联网经济性对比

**联网模式（问题三结果）：**
- 年总成本 = $\sum_{s=1}^{24} C_{day,s}^{Q3} \times 15$
- 年总产量 = $\sum_{s=1}^{24} Q_{NH3,s}^{Q3} \times 15$

**离网模式（问题四结果）：**
- 年总成本 = $\sum_{s=1}^{24} (C_{day,s}^{Q4} + C_{sto,daily}) \times 15$
- 年总产量 = $\sum_{s=1}^{24} Q_{NH3,s}^{Q4} \times 15$

**系统支撑成本价值：**

$$
V_{grid} = \frac{C_{ton,offgrid} - C_{ton,ongrid}}{C_{ton,ongrid}} \times 100\%
$$

即联网相对离网的成本优势百分比，反映电网对园区的支撑价值。

### 6.5 算法伪代码

```
# 问题四(1): 离网无储能
for s in range(24):
    wind_s, pv_s = get_scenario(s)
    model = MILP()
    alpha = model.continuous_vars(24, lb=0, ub=1)
    v = model.binary_vars(24)  # 开停机状态
    
    for t in range(24):
        available = max(0, wind_s[t] + pv_s[t] - P_load[t])
        alpha_max = min(1.0, available / 41.5)
        model.add_constraint(alpha[t] <= alpha_max)
        model.add_constraint(alpha[t] >= 0.1 * v[t])
        model.add_constraint(alpha[t] <= v[t])
    
    model.maximize(sum(alpha))
    solve(model)
    Q_NH3 = 3.0 * sum(alpha_solution)
    
# 问题四(2): 储能配置
# 找最大弃电场景
max_curtail_scenario = argmax(curtailment across scenarios)

# 参数扫描储能容量
for C_sto in range(10, 210, 10):  # MWh
    P_sto_max = C_sto / 2  # 0.5C
    model = LP()
    # ... 含储能的离网调度LP ...
    solve(model)
    record(C_sto, Q_NH3, curtailment, cost)

# 选择最优C_sto（边际效益拐点）
optimal_C_sto = find_knee_point(results)

# 24场景调度
for s in range(24):
    solve_with_storage(s, optimal_C_sto)
```


## 七、问题五：绿电园区对电力系统的影响分析

### 7.1 方法选择

**选用方法：** 定性分析 + 半定量论证

**理由：** 问题五为开放性政策分析题，要求分析绿电园区容量渗透率提高对电力系统的影响（至少3种利弊），并提出政策建议。无需精确数学建模，但需要逻辑严密、有据可依。

### 7.2 分析框架

#### 7.2.1 利好影响

**利好1：促进新能源就地消纳，降低弃风弃光率**
- 机理：绿电直连将新能源发电直接供给本地负荷，减少远距离输送和调度压力
- 量化依据：本题园区风光装机104MW，自发自用比例>60%，相当于减少了104×60%=62.4MW的电网调度负担

**利好2：减轻电网输配电压力，延缓电网投资**
- 机理：园区内部自平衡，减少对外部电网的功率需求
- 量化依据：园区峰值负荷约47.5MW（41.5+6），若自给率高则电网只需承担差额

**利好3：推动氢能产业链发展，助力碳中和**
- 机理：绿电制氢制氨实现化工行业深度脱碳
- 量化依据：每吨氨减排CO₂约2.5吨（相比传统煤制氨）

#### 7.2.2 不利影响

**不利1：增加电网调峰调频难度**
- 机理：风光出力波动大，园区与电网交互功率随机性强，增加系统频率调节压力
- 量化依据：本题24种场景发电量变化5倍（170-877 MWh），购售电功率波动剧烈

**不利2：降低电网负荷率，影响电网资产利用效率**
- 机理：园区大部分时间自给自足，仅在风光不足时大量购电，导致电网负荷曲线"尖峰化"
- 量化依据：园区购电集中在夜间低风光时段，加剧电网峰谷差

**不利3：可能引发局部电压/潮流问题**
- 机理：大规模分布式新能源接入可能导致配电网电压越限、潮流反转
- 量化依据：园区风光装机104MW，在高出力时段可能向电网反送大量功率

### 7.3 政策建议

1. **建立绿电直连园区与电网的协调调度机制**：要求园区提前申报日前调度计划，配合电网调峰需求调整生产安排
2. **完善分时电价和需求响应机制**：通过价格信号引导园区在电网低谷时段增加用电，高峰时段减少用电
3. **强制配置一定比例储能**：要求绿电直连园区配置不低于装机容量10%的储能，平滑功率波动
4. **建立绿电直连园区容量渗透率上限管理**：根据电网承载能力设定区域内绿电园区总装机上限
5. **推动园区间互济和虚拟电厂聚合**：多个绿电园区联合参与电力市场，提供辅助服务

## 八、模型检验与灵敏度分析设计

### 8.1 模型检验方案

#### 8.1.1 功率平衡验证
- 每个时段：$P_{wind}(t) + P_{pv}(t) + P_{buy}(t) = P_{load}(t) + P_{H2NH3}(t) + P_{sell}(t) + P_{curtail}(t)$
- 日能量守恒：$E_{RE} + E_{buy} = E_{total} + E_{sell} + E_{curtail}$

#### 8.1.2 产量一致性验证
- 问题二：$Q_{NH3} = r_{NH3} \times \sum u(t) = 3.0 \times k$
- 问题三：$Q_{NH3} = r_{NH3} \times \sum \alpha(t) = 3.0 \times \sum \alpha(t)$
- 问题四：同问题三

#### 8.1.3 绿电指标交叉验证
- $R_{self} + R_{grid} = 1 - E_{buy}/E_{RE}$（由定义推导）
- $R_{green} = (E_{RE} - E_{sell}) / E_{total} = 1 - E_{buy}/E_{total}$（由功率平衡推导）

#### 8.1.4 递进性验证
- 问题三成本 ≤ 问题二成本（连续调节更灵活）
- 问题四(2)产量 ≥ 问题四(1)产量（储能增加了灵活性）

### 8.2 灵敏度分析方案

| 参数 | 基准值 | 扰动范围 | 影响指标 |
|------|--------|---------|---------|
| 风电装机容量 | 40 MW | ±20% | 绿电指标、吨氨成本 |
| 光伏装机容量 | 64 MW | ±20% | 绿电指标、吨氨成本 |
| 购电电价 | 见电价表 | ±30% | 吨氨成本 |
| 售电电价 | 0.3779 | ±30% | 吨氨成本 |
| 储能投资成本 | 1000元/kWh | ±50% | 最优储能容量 |
| 储能效率 | 90% | 85%-95% | 产量、成本 |

### 8.3 鲁棒性验证

- 24种风光场景本身构成了天然的鲁棒性验证（覆盖高/中/低出力）
- 对最优调度方案，在风光出力±10%扰动下验证可行性
- 统计全年360天中绿电指标满足率


## 九、合理性预验证与结果预期范围

### 9.1 结果约束清单

- $P_{buy}(t) \geq 0$，物理含义：购电功率不能为负
- $P_{sell}(t) \geq 0$，物理含义：售电功率不能为负
- $P_{buy}(t) \cdot P_{sell}(t) = 0$，物理含义：同一时段不能同时购售电
- $\alpha(t) \in [0.1, 1]$（开机时）或 $\alpha(t) = 0$（停机时），物理含义：功率调节范围
- $0 \leq E_{sto}(t) \leq C_{sto}$，物理含义：储能不能过充过放
- $R_{self} \in [0, 1]$，$R_{green} \in [0, 1]$，$R_{grid} \in [0, 1]$，物理含义：比例指标
- $C_{ton} > 0$，物理含义：吨氨成本必须为正
- $Q_{NH3} \leq 72$ 吨/日，物理含义：不能超过产能上限
- 能量守恒：$E_{RE} + E_{buy} = E_{total} + E_{sell}$（并网无弃电时）
- 能量守恒：$E_{RE} = E_{total} + E_{curtail}$（离网时）

### 9.2 预期行为

- **问题一**：典型日新能源发电603.45 MWh > 总用电558.72 MWh，但时序不匹配导致同时存在购电和售电。预期上网电量比例可能超过20%（因为白天光伏高峰时发电远超负荷）。
- **问题二**：最优策略应将开机时段集中在风光出力高的时段（白天），避开低谷时段。产量越低（开机时数越少），越容易选择高风光时段，绿电指标越好但产量下降。
- **问题三**：连续调节允许在高电价时段降低功率（而非停机），预期成本低于问题二5-15%。
- **问题四(1)**：离网时产量严重受限于风光出力最低时段。夜间光伏为0，仅靠风电，产量预计为联网时的40-70%。
- **问题四(2)**：储能可将白天多余光伏电力转移到夜间使用，预期产量提升10-30%。

### 9.3 异常处理预案

**异常1：** 问题一绿电指标全部满足
- 原因判断：可能是因为典型日风光出力恰好较高
- 唯一修正方法：无需修正，如实报告。但需验证计算正确性（检查功率平衡）
- 禁止：人为调整数据使指标不满足

**异常2：** 问题二MILP求解时间过长
- 原因判断：$C(24,12)=270$万种组合，MILP分支定界可能慢
- 唯一修正方法：设置求解时间上限（60秒），若未收敛则用枚举法验证
- 禁止：放弃精确求解直接用贪心

**异常3：** 问题三LP结果中所有$\alpha(t)$相同（均匀分配）
- 原因判断：可能是目标函数中运维成本项主导，购电成本差异不够大
- 唯一修正方法：检查目标函数系数是否正确，确认分时电价已正确映射
- 禁止：人为添加约束强制不均匀

**异常4：** 问题四离网产量为0
- 原因判断：某些场景风光出力极低（如风电2+光伏4），可能连常规负荷都不够
- 唯一修正方法：如实报告该场景无法生产，计算弃电量为0，吨氨成本为无穷大
- 禁止：忽略该场景或假设可以少量购电

**异常5：** 问题三成本高于问题二
- 原因判断：违反资源单调性（连续调节应优于离散），说明模型或代码有误
- 唯一修正方法：检查LP约束是否正确，特别是产量约束和功率下限约束
- 禁止：接受此结果并解释为"特殊情况"

### 9.4 方法指定

**步骤1：数据读取与预处理**
- 方法：pandas读取Excel，构建24×24的功率矩阵（24时段×24场景）
- 输入：附件1-4的xlsx文件
- 输出：P_load[24], P_wind[24][24], P_pv[24][24]（场景×时段）
- 禁止替代：不用手动输入数据

**步骤2：分时电价映射**
- 方法：按时段索引直接映射（t=1-7→低谷, t=8-10→平时, t=11-15→高峰, t=16-18→平时, t=19-21→高峰, t=22-23→平时, t=24→低谷）
- 输入：附件7
- 输出：lambda_buy[24]
- 禁止替代：不用插值或近似

**步骤3：问题一功率平衡计算**
- 方法：逐时段直接计算（numpy向量化）
- 输入：P_load, P_wind_typical, P_pv_typical, P_H2NH3=20.75
- 输出：P_buy[24], P_sell[24], 日能量指标, 绿电指标, 吨氨成本
- 禁止替代：不用优化求解器（无需优化）

**步骤4：问题二MILP求解**
- 方法：PuLP库构建MILP，CBC求解器
- 输入：场景功率数据, 产量列表[72,63,54,45,36], 电价
- 输出：每个(场景,产量)组合的最优开机方案u[24]和成本
- 禁止替代：不用scipy.optimize（不支持整数变量）

**步骤5：问题三LP求解**
- 方法：scipy.optimize.linprog 或 PuLP
- 输入：场景功率数据, 产量列表, 电价
- 输出：每个(场景,产量)组合的最优alpha[24]和成本
- 禁止替代：不用非线性求解器（问题是线性的）

**步骤6：问题四离网LP/MILP求解**
- 方法：PuLP（含二进制变量v[t]处理停机）
- 输入：场景功率数据, 储能参数
- 输出：最大产量, 弃电量, 储能调度方案
- 禁止替代：不用启发式算法（问题规模小，精确求解可行）

**步骤7：储能容量参数扫描**
- 方法：for循环遍历C_sto，每个值求解一次LP
- 输入：最大弃电场景数据, C_sto候选值
- 输出：C_sto-产量-成本曲线, 最优配置点
- 禁止替代：不用梯度优化（离散扫描更直观可靠）

### 9.5 验证检查点

- □ 功率平衡：每个时段 $|P_{RE}(t) + P_{buy}(t) - P_{load}(t) - P_{H2NH3}(t) - P_{sell}(t)| < 0.001$ MW，若 fail → 检查功率平衡方程
- □ 非负性：所有 $P_{buy}(t) \geq 0$, $P_{sell}(t) \geq 0$，若 fail → 检查max(0,...)逻辑
- □ 互斥性：$P_{buy}(t) \cdot P_{sell}(t) = 0$，若 fail → 检查LP约束
- □ 产量一致：$|Q_{NH3} - r_{NH3} \times \sum \alpha(t)| < 0.01$，若 fail → 检查产量约束
- □ 绿电指标范围：$R_{self}, R_{green}, R_{grid} \in [0, 1]$，若 fail → 检查能量计算
- □ 递进性：$C_{ton}^{Q3} \leq C_{ton}^{Q2}$（同场景同产量），若 fail → 异常预案5
- □ 储能SOC：$0 \leq E_{sto}(t) \leq C_{sto}$，若 fail → 检查SOC方程
- □ 储能日循环：$|E_{sto}(25) - E_{sto}(1)| < 0.01$ MWh，若 fail → 检查循环约束
- □ 最终：所有输出量均在约束清单范围内

### 9.6 结构性验证输入（供 comp-code 层级5使用）

#### 约束活跃性预期

**问题二：**
- 产量约束 $\sum u(t) = k$：预期活跃（等式约束必然活跃）
- 非负约束 $P_{buy}(t) \geq 0$：预期在风光高出力时段活跃（此时不需购电）
- 非负约束 $P_{sell}(t) \geq 0$：预期在风光低出力时段活跃（此时不需售电）

**问题三：**
- 产量约束 $\sum \alpha(t) = k_{sum}$：预期活跃
- 下限约束 $\alpha(t) \geq 0.1$：预期在高电价+低风光时段活跃（尽量降低功率）
- 上限约束 $\alpha(t) \leq 1.0$：预期在低电价+高风光时段活跃（尽量提高功率）
- 如果所有约束都不活跃 → 说明产量约束太松（产量太低），$\alpha$ 有很大自由度

**问题四：**
- 功率上限约束 $\alpha(t) \leq (P_{RE}(t)-P_{load}(t))/P_{H2NH3}^{max}$：预期在多数时段活跃（离网时风光是硬约束）
- 储能容量约束 $E_{sto}(t) \leq C_{sto}$：预期在光伏高峰时段活跃（储能充满）
- 储能下限约束 $E_{sto}(t) \geq 0$：预期在夜间放电末期活跃

#### 决策变量合理范围与预期行为

| 变量 | 物理含义 | bounds | 预期取值区间 | 若取到边界说明什么 |
|------|---------|--------|-------------|------------------|
| $u(t)$ | 开停机 | {0,1} | 白天多为1，夜间多为0 | 全1=满负荷，全0=不生产 |
| $\alpha(t)$ | 功率系数 | [0.1,1] | 0.3-0.8（多数时段） | 取1=满负荷，取0.1=最低运行 |
| $P_{buy}(t)$ | 购电 | [0,∞) | [0, 40] MW | 超过40MW说明计算有误 |
| $P_{sell}(t)$ | 售电 | [0,∞) | [0, 60] MW | 超过60MW说明计算有误 |
| $C_{sto}$ | 储能容量 | [0,∞) | [20, 150] MWh | 超过200MWh经济性差 |

#### 灵敏度方向表

| 决策变量 | 增大时目标函数方向 | 预期灵敏度量级 | 若方向相反说明什么 |
|----------|-------------------|---------------|------------------|
| $\alpha(t)$在低电价时段 | ↓（成本减小=更优） | 高 | 电价映射错误 |
| $\alpha(t)$在高电价时段 | ↑（成本增大=更差） | 高 | 电价映射错误 |
| $C_{sto}$ | ↓（产量增加→吨氨成本降低） | 中（边际递减） | 储能约束未正确建模 |

#### 稳定性预期

- 问题二：MILP精确求解，结果唯一确定（无随机性）
- 问题三：LP精确求解，结果唯一确定（凸问题）
- 问题四：LP/MILP精确求解，结果唯一确定
- 无需多次运行验证稳定性（非启发式算法）

#### 资源利用率预期

- ALKEL：问题一100%，问题二50-100%（取决于产量），问题三10-100%连续
- PEMEL：同ALKEL
- 合成氨装置：同上
- 储能（问题四）：预期日充放电循环1-2次，利用率50-80%


## 十、编程实现要点

### 10.1 技术栈

- **语言：** Python 3
- **核心库：** numpy, pandas, scipy, PuLP (线性/整数规划)
- **绘图：** matplotlib, seaborn
- **数据读取：** openpyxl (Excel)

### 10.2 代码结构

```
code/
├── q1_power_balance.py      # 问题一：功率平衡计算
├── q2_discrete_schedule.py  # 问题二：离散调度MILP
├── q3_continuous_schedule.py # 问题三：连续调度LP
├── q4_offgrid_storage.py    # 问题四：离网+储能
├── q5_policy_analysis.py    # 问题五：政策分析（定性）
├── data_loader.py           # 数据加载模块
├── indicators.py            # 绿电指标计算模块
├── cost_model.py            # 成本计算模块
└── validate.py              # 验证模块
```

### 10.3 关键实现细节

#### 10.3.1 分时电价映射（关键易错点）

```python
# 时段索引 t=0 对应 0:00-1:00, t=23 对应 23:00-24:00
def get_electricity_price(t):
    """返回时段t的购电电价(元/kWh)"""
    if t in range(0, 7) or t == 23:  # 23:00-07:00 低谷
        return 0.3424
    elif t in range(7, 10) or t in range(15, 18) or t in range(21, 23):  # 平时
        return 0.6074
    else:  # 10:00-15:00, 18:00-21:00 高峰
        return 0.8024
```

#### 10.3.2 产能缩放

```python
def get_equipment_params(Q_capacity):
    """根据产能获取设备参数（线性缩放）"""
    scale = Q_capacity / 36.0
    return {
        'P_ALKEL_max': 10 * scale,   # MW
        'P_PEMEL_max': 10 * scale,   # MW
        'P_NH3_max': 0.75 * scale,   # MW
        'r_H2_ALKEL': 140 * scale,   # kg/h
        'r_H2_PEMEL': 160 * scale,   # kg/h
        'r_NH3': 1.5 * scale,        # 吨/h
    }
```

#### 10.3.3 PuLP建模模板（问题二）

```python
import pulp

def solve_q2(P_wind, P_pv, P_load, Q_target, params):
    """问题二MILP求解"""
    k = int(Q_target / params['r_NH3'])  # 开机小时数
    P_H2NH3 = params['P_ALKEL_max'] + params['P_PEMEL_max'] + params['P_NH3_max']
    
    model = pulp.LpProblem("Q2_Schedule", pulp.LpMinimize)
    u = [pulp.LpVariable(f"u_{t}", cat='Binary') for t in range(24)]
    P_buy = [pulp.LpVariable(f"Pbuy_{t}", lowBound=0) for t in range(24)]
    
    # 产量约束
    model += pulp.lpSum(u) == k
    
    # 功率平衡
    for t in range(24):
        P_net = P_load[t] + u[t] * P_H2NH3 - P_wind[t] - P_pv[t]
        model += P_buy[t] >= P_net
    
    # 售电 = 购电 - 净负荷
    P_sell = [P_buy[t] - (P_load[t] + u[t]*P_H2NH3 - P_wind[t] - P_pv[t]) 
              for t in range(24)]
    
    # 目标函数
    lambda_buy = [get_electricity_price(t) for t in range(24)]
    C_OM_hour = 0.1*params['P_ALKEL_max']*1000 + 0.15*params['P_PEMEL_max']*1000 + 0.002*params['P_NH3_max']*1000
    
    obj = pulp.lpSum([lambda_buy[t]*P_buy[t]*1000 + u[t]*C_OM_hour for t in range(24)]) \
        - 0.3779 * pulp.lpSum([P_sell[t]*1000 for t in range(24)])
    model += obj
    
    model.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
    return model, u, P_buy, P_sell
```

#### 10.3.4 验证函数（每个子问题末尾必须调用）

```python
def validate_constraints(results, problem_id):
    """验证结果是否满足物理约束"""
    errors = []
    
    # 非负性
    if any(results['P_buy'] < -1e-6):
        errors.append(f"P_buy has negative values: min={min(results['P_buy'])}")
    if any(results['P_sell'] < -1e-6):
        errors.append(f"P_sell has negative values: min={min(results['P_sell'])}")
    
    # 功率平衡
    balance = results['P_RE'] + results['P_buy'] - results['P_load'] - results['P_H2NH3'] - results['P_sell']
    if any(abs(balance) > 0.01):
        errors.append(f"Power balance violated: max error={max(abs(balance))}")
    
    # 绿电指标范围
    for name, val in [('R_self', results['R_self']), ('R_green', results['R_green']), ('R_grid', results['R_grid'])]:
        if val < 0 or val > 1:
            errors.append(f"{name} out of [0,1]: {val}")
    
    # 吨氨成本正值
    if results['C_ton'] <= 0:
        errors.append(f"C_ton non-positive: {results['C_ton']}")
    
    if errors:
        print(f"[FAIL] Problem {problem_id} validation:")
        for e in errors:
            print(f"  - {e}")
        raise ValueError(f"Validation failed for Problem {problem_id}")
    else:
        print(f"[PASS] Problem {problem_id} validation: all constraints satisfied")
```

### 10.4 输入输出格式

**输入：** Excel文件 → pandas DataFrame → numpy array

**输出：**
- 每个子问题的计算结果保存为JSON文件（供后续图表生成使用）
- 关键结果打印到控制台
- 图表保存为PNG文件（300dpi）

### 10.5 计算复杂度估计

| 问题 | 方法 | 单次求解时间 | 总调用次数 | 预计总时间 |
|------|------|------------|-----------|-----------|
| 问题一 | 直接计算 | <0.01s | 1 | <1s |
| 问题二 | MILP(CBC) | <1s | 24×5=120 | <2min |
| 问题三 | LP(linprog) | <0.1s | 24×5=120 | <15s |
| 问题四(1) | MILP | <1s | 24 | <30s |
| 问题四(2) | LP×参数扫描 | <0.1s×20 | 24×20=480 | <1min |

总计预计运行时间：< 5分钟


## 十一、图表预规划

### 数据图表清单

| 编号 | 文件名 | 图表类型 | 内容描述 | 所属章节 |
|------|--------|---------|---------|---------|
| 1 | fig_q1_power_balance | 面积图 | 典型日功率平衡曲线（负荷、风光、购售电） | 问题一 |
| 2 | fig_q1_indicators | 分组柱状图 | 三项绿电指标与阈值对比 | 问题一 |
| 3 | fig_q2_cost_vs_production | 折线图 | 不同日产量下的吨氨成本 | 问题二(1) |
| 4 | fig_q2_schedule_gantt | 甘特图 | 最优产量24h开停机安排 | 问题二(1) |
| 5 | fig_q2_scenarios_heatmap | 热力图 | 24场景×5产量吨氨成本矩阵 | 问题二(2) |
| 6 | fig_q2_annual_cost | 面积图 | 全年吨氨成本分布 | 问题二(2) |
| 7 | fig_q2_green_indicators | 堆叠柱状图 | 绿电指标满足情况统计 | 问题二(2) |
| 8 | fig_q3_dispatch | 双轴图 | 连续调度功率曲线 | 问题三(1) |
| 9 | fig_q3_annual_cost | 折线图 | 全年吨氨成本分布（对比问题二） | 问题三(1) |
| 10 | fig_q3_comparison | 发散柱状图 | 问题三vs问题二指标变化 | 问题三(3) |
| 11 | fig_q4_offgrid_production | 分组柱状图 | 24场景离网制氨产量 | 问题四(1) |
| 12 | fig_q4_storage_dispatch | 面积图 | 储能参与功率调度曲线 | 问题四(2) |
| 13 | fig_q4_economics | 瀑布图 | 离网vs联网成本分解 | 问题四(3) |
| 14 | fig_q5_radar | 雷达图 | 绿电园区影响多维评价 | 问题五 |

### 表格清单

| 编号 | 标识 | 内容 | 所属章节 |
|------|------|------|---------|
| 1 | TABLE_q1_daily_energy | 典型日能量平衡汇总 | 问题一 |
| 2 | TABLE_q1_indicators | 绿电指标计算结果 | 问题一 |
| 3 | TABLE_q2_optimal | 各产量最优方案汇总 | 问题二(1) |
| 4 | TABLE_q2_annual | 全年绿电指标统计 | 问题二(2) |
| 5 | TABLE_q3_scenarios | 24场景调度结果 | 问题三(1) |
| 6 | TABLE_q3_vs_q2 | 问题三与问题二对比 | 问题三(3) |
| 7 | TABLE_q4_offgrid | 离网各场景产量与成本 | 问题四(1) |
| 8 | TABLE_q4_storage | 储能配置方案及效果 | 问题四(2) |

### DrawIO 架构图清单

| 编号 | 文件名 | 内容 | 所属章节 |
|------|--------|------|---------|
| 1 | fig_roadmap.drawio | 技术路线图 | 问题重述 |
| 2 | fig_flow_q1.drawio | 问题一求解流程 | 问题一 |
| 3 | fig_flow_q2.drawio | 问题二求解流程 | 问题二 |
| 4 | fig_flow_q3.drawio | 问题三求解流程 | 问题三 |
| 5 | fig_flow_q4.drawio | 问题四求解流程 | 问题四 |
| 6 | fig_energy_flow.drawio | 园区能量流向架构 | 问题重述 |

## 十二、升级审视与防错审查

### 12.1 赛题分析升级结论审视

| 升级建议 | 审视结果 | 采纳情况 |
|---------|---------|---------|
| 功率平衡→带分时电价 | 已在目标函数中体现分时电价加权 | ✅ 完全采纳 |
| 简单调度→0-1整数规划 | 问题二使用MILP精确求解 | ✅ 完全采纳 |
| 连续优化→带下界LP | 问题三LP中 $\alpha(t) \geq 0.1$ | ✅ 完全采纳 |
| 离网调度→含储能SOC约束 | 问题四完整建模储能状态方程 | ✅ 完全采纳 |
| 产能扩容线性同步 | 72吨/日时设备功率翻倍 | ✅ 完全采纳 |
| 每种场景代表15天 | 全年统计使用24×15=360天 | ✅ 完全采纳 |
| 氢氨耦合约束 | 产氢速率与制氨速率匹配验证 | ✅ 完全采纳 |
| 储能自损耗 | SOC方程中 $(1-0.002)$ 因子 | ✅ 完全采纳 |

### 12.2 防错审查

本题涉及题型：**优化类（规划/调度）**，已对照防错手册审查。

**逐条确认：**
- ✅ 目标函数优化方向明确（min成本）
- ✅ 所有约束条件有完整数学表达式
- ✅ 决策变量类型标注（u为0-1，alpha为连续[0.1,1]，P_buy为连续≥0）
- ✅ 非负约束显式写出
- ✅ 可行域非空验证：问题二中k=12时，选择风光最高的12个时段必然可行
- ✅ 问题为凸（LP/MILP），无需多起点
- ✅ 约束耦合分析：产量约束与功率平衡约束耦合，但可行域充分（24时段选k个）
- ✅ 灵敏度方向预判已完成
- ✅ 资源单调性：问题三（连续）应优于问题二（离散），问题四(2)（有储能）应优于问题四(1)（无储能）

### 12.3 约束耦合分析

**问题二约束耦合：**
- 产量约束 $\sum u(t) = k$ 与功率平衡约束独立（产量约束只限制开机时数，不限制具体时段）
- 可行域体积：$C(24,k)$ 种组合，全部可行（功率平衡通过购电自动满足）
- 结论：约束不紧，优化器容易找到可行解

**问题三约束耦合：**
- 产量约束 $\sum \alpha(t) = k_{sum}$ 与下限约束 $\alpha(t) \geq 0.1$ 耦合
- 当 $k_{sum} < 24 \times 0.1 = 2.4$ 时不可行（但最小产量36吨对应k=12 > 2.4）
- 当 $k_{sum} > 24 \times 1.0 = 24$ 时不可行（但最大产量72吨对应k=24）
- 结论：所有产量水平均可行

**问题四约束耦合：**
- 离网功率约束 $\alpha(t) \leq (P_{RE}(t)-P_{load}(t))/P_{H2NH3}^{max}$ 与下限约束 $\alpha(t) \geq 0.1$ 耦合
- 当 $P_{RE}(t) - P_{load}(t) < 0.1 \times 41.5 = 4.15$ MW 时，该时段必须停机
- 在极端低风光场景（风电2+光伏4），可能大部分时段无法开机
- 结论：离网时可行域可能很小，产量受限是正常现象

## 十三、吨氨成本计算详细说明

### 13.1 成本组成明细

吨氨成本 = (新能源发电成本 + 购电成本 + 设备运维成本 - 售电收入) / 日产量

**新能源发电成本：** 按实际发电量×度电成本计算（不论是否被使用）

$$
C_{RE} = c_{wind} \times E_{wind} + c_{pv} \times E_{pv} = 0.15 \times P_{wind}^{cap} \times \sum p_{wind}(t) + 0.12 \times P_{pv}^{cap} \times \sum p_{pv}(t)
$$

注：风光度电成本已包含投资折旧和运维，是全生命周期度电成本（LCOE）。

**购电成本：** 按分时电价计算

$$
C_{buy} = \sum_{t=1}^{24} \lambda_{buy}(t) \times P_{buy}(t) \times 1000 \times \Delta t \quad \text{(元)}
$$

**设备运维成本：**

$$
C_{OM} = (c_{ALKEL} \times P_{ALKEL}(t) + c_{PEMEL} \times P_{PEMEL}(t) + c_{NH3} \times P_{NH3}(t)) \times 1000 \times \Delta t
$$

**售电收入：**

$$
I_{sell} = \lambda_{sell} \times E_{sell} \times 1000 \quad \text{(元)}
$$

### 13.2 问题一预估

- $C_{RE} = 0.15 \times 245.05 \times 1000 + 0.12 \times 358.40 \times 1000 = 36757.5 + 43008 = 79765.5$ 元
- $C_{OM} = (0.10 \times 10 + 0.15 \times 10 + 0.002 \times 0.75) \times 1000 \times 24 = 2501.5 \times 24 = 60036$ 元
- $C_{buy}$ 和 $I_{sell}$ 需要逐时段计算
- $Q_{NH3} = 36$ 吨
- 预估 $C_{ton} \approx (79766 + C_{buy} + 60036 - I_{sell}) / 36$


## 十四、问题一预验算结果

通过Python直接计算验证模型正确性：

| 指标 | 计算值 | 要求 | 是否满足 |
|------|--------|------|---------|
| 日总用电量 | 558.72 MWh | — | — |
| 新能源发电量 | 603.45 MWh | — | — |
| 网购电量 | 172.04 MWh | — | — |
| 上网电量 | 216.77 MWh | — | — |
| 自发自用比例 | 28.16% | >60% | ❌ 不满足 |
| 绿电比例 | 69.21% | >30% | ✅ 满足 |
| 上网电量比例 | 35.92% | <20% | ❌ 不满足 |
| 吨氨成本 | 4322.34 元/吨 | — | — |

**分析：** 虽然新能源总发电量(603.45 MWh)大于总用电量(558.72 MWh)，但由于时序不匹配——白天(6:00-15:00)光伏大发时段风光总出力远超负荷导致大量上网，而夜间(16:00-次日5:00)仅靠风电无法满足负荷需要大量购电——导致自发自用比例和上网电量比例均不满足绿电直连要求。这正是问题二、三需要通过调度优化解决的核心矛盾。

**能量守恒验证：** $E_{RE} + E_{buy} - E_{total} - E_{sell} = 603.45 + 172.04 - 558.72 - 216.77 = 0.00$ ✅

本题涉及题型：[优化类（调度/规划）]，已对照防错手册审查。

