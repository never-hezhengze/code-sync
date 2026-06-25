# 概率论复习（二）—— 中文翻译

> 翻译自 `Review_of_probability2.pdf`，共 41 页。数学公式保留原样。

---

## 第 1 页：封面

**数据科学引论——概率论复习（二）**
*Review of Probability (Part 2)*

---

## 第 2 页：复习大纲

### 概率论复习第二部分内容

1. 常用离散分布（二项、泊松、几何等）
2. 常用连续分布（均匀、指数、正态、Gamma 等）
3. 联合分布与边缘分布
4. 条件分布与独立性
5. 协方差与相关系数
6. 条件期望
7. 大数定律与中心极限定理

---

## 第 3 页：伯努利分布

### 伯努利分布（Bernoulli Distribution）

最基础的离散分布，描述一次"成功/失败"试验。

$$X \sim \text{Bernoulli}(p), \quad 0 \leq p \leq 1$$

**概率质量函数（PMF）**：

$$P(X = 1) = p, \quad P(X = 0) = 1 - p$$

**期望与方差**：
$$\mathbb{E}[X] = 0 \cdot (1-p) + 1 \cdot p = p$$
$$\text{Var}(X) = \mathbb{E}[X^2] - (\mathbb{E}[X])^2 = p - p^2 = p(1-p)$$

**应用示例**：
- 抛一次硬币
- 一个产品是否合格
- 一次临床试验是否成功

---

## 第 4 页：二项分布

### 二项分布（Binomial Distribution）

$n$ 次独立伯努利试验中成功次数的分布。

$$X \sim \text{Binomial}(n, p)$$

**PMF**：
$$P(X = k) = \binom{n}{k} p^k (1-p)^{n-k}, \quad k = 0, 1, 2, \ldots, n$$

其中：
$$\binom{n}{k} = \frac{n!}{k!(n-k)!}$$

**期望与方差**：
$$\mathbb{E}[X] = np$$
$$\text{Var}(X) = np(1-p)$$

### 二项分布的性质

- 当 $p = 0.5$ 时，分布对称于 $n/2$
- 当 $n$ 很大时，二项分布近似于正态分布
- $n=1$ 时退化为伯努利分布

---

## 第 5 页：二项分布——计算示例

### 示例

一名篮球运动员的罚球命中率为 70%。他罚球 10 次，求恰好命中 8 次的概率。

$$X \sim \text{Binomial}(n=10, p=0.7)$$

$$P(X = 8) = \binom{10}{8} (0.7)^8 (0.3)^2$$

$$= \frac{10!}{8!2!} \times 0.7^8 \times 0.3^2$$

$$\approx 0.2335$$

所以恰好命中 8 次的概率约为 23.35%。

### 累积概率

命中 8 次或更多的概率：

$$P(X \geq 8) = P(X=8) + P(X=9) + P(X=10)$$

分别计算：
- $P(X=9) = \binom{10}{9}(0.7)^9(0.3)^1 \approx 0.1211$
- $P(X=10) = (0.7)^{10} \approx 0.0282$

$$P(X \geq 8) \approx 0.2335 + 0.1211 + 0.0282 = 0.3828$$

约 38.28% 的概率至少命中 8 次。

---

## 第 6 页：几何分布

### 几何分布（Geometric Distribution）

独立伯努利试验中，**首次成功**所需的试验次数。

$$X \sim \text{Geometric}(p)$$

**PMF**：
$$P(X = k) = (1-p)^{k-1}p, \quad k = 1, 2, 3, \ldots$$

（注意：有些教材定义几何分布为首次成功**之前**的失败次数，此时 $k = 0, 1, 2, \ldots$ 且 PMF 为 $(1-p)^k p$。）

**期望与方差**（首次成功所需次数版本）：
$$\mathbb{E}[X] = \frac{1}{p}, \quad \text{Var}(X) = \frac{1-p}{p^2}$$

### 无记忆性

几何分布具有无记忆性：
$$P(X > m + n \mid X > m) = P(X > n)$$

前面的失败不会影响后续还需要多少次试验。这是离散分布中唯一的无记忆分布。

---

## 第 7 页：泊松分布

### 泊松分布（Poisson Distribution）

描述单位时间/空间/面积内随机事件发生的次数。

$$X \sim \text{Poisson}(\lambda), \quad \lambda > 0$$

**PMF**：
$$P(X = k) = \frac{\lambda^k e^{-\lambda}}{k!}, \quad k = 0, 1, 2, 3, \ldots$$

**期望与方差**：
$$\mathbb{E}[X] = \lambda$$
$$\text{Var}(X) = \lambda$$

**重要特征**：期望和方差相等！

### 泊松分布的应用

- 一小时内到达某网站的访客数
- 一页书中的印刷错误数
- 一座城市一天内的火警次数
- 一平方公里内的树木数量

---

## 第 8 页：泊松分布——性质与近似

### 泊松分布作为二项分布的极限

当 $n \to \infty$，$p \to 0$，且 $np \to \lambda$（常数）时：

$$\text{Binomial}(n, p) \xrightarrow{d} \text{Poisson}(\lambda)$$

### 应用：稀有事件

当 $n$ 很大（$n \geq 20$）且 $p$ 很小（$p \leq 0.05$）时，可用泊松分布近似二项分布：

$$P(X = k) \approx \frac{(np)^k e^{-np}}{k!}$$

### 示例

某产品次品率为 0.1%。从 1000 个产品中随机抽取，求恰好有 2 个次品的概率。

- 精确计算（二项）：$\binom{1000}{2}(0.001)^2(0.999)^{998}$ — 难以手算！
- 泊松近似：$\lambda = np = 1000 \times 0.001 = 1$
  $$P(X = 2) \approx \frac{1^2 e^{-1}}{2!} = \frac{e^{-1}}{2} \approx 0.1839$$

---

## 第 9 页：负二项分布

### 负二项分布（Negative Binomial Distribution）

独立伯努利试验中，达到第 $r$ 次成功所需的试验次数。

$$X \sim \text{NegBin}(r, p)$$

**PMF**：
$$P(X = k) = \binom{k-1}{r-1} p^r (1-p)^{k-r}, \quad k = r, r+1, r+2, \ldots$$

**期望与方差**：
$$\mathbb{E}[X] = \frac{r}{p}, \quad \text{Var}(X) = \frac{r(1-p)}{p^2}$$

### 与几何分布的关系

当 $r = 1$ 时，负二项分布退化为几何分布：
$$\text{NegBin}(1, p) = \text{Geometric}(p)$$

### 应用示例

- 一名销售员需要完成 5 笔交易，每次推销成功概率为 0.3，需要打多少次电话？
- 棒球比赛中，需要多少次击球才能打出 3 支安打？

---

## 第 10 页：均匀分布

### 均匀分布（Uniform Distribution）

在区间 $[a, b]$ 内任意位置等可能。

$$X \sim \text{Uniform}(a, b)$$

**PDF**：
$$f_X(x) = \begin{cases} \frac{1}{b-a}, & a \leq x \leq b \\ 0, & \text{其他} \end{cases}$$

**期望与方差**：
$$\mathbb{E}[X] = \frac{a+b}{2}, \quad \text{Var}(X) = \frac{(b-a)^2}{12}$$

### CDF

$$F_X(x) = \begin{cases} 0, & x < a \\ \frac{x-a}{b-a}, & a \leq x \leq b \\ 1, & x > b \end{cases}$$

在 $[a, b]$ 内，CDF 是线性的——这就是为什么称它为"均匀"分布。

---

## 第 11 页：指数分布

### 指数分布（Exponential Distribution）

描述独立随机事件之间的**等待时间**。

$$X \sim \text{Exponential}(\lambda), \quad \lambda > 0$$

**PDF**：
$$f_X(x) = \lambda e^{-\lambda x}, \quad x \geq 0$$

**期望与方差**：
$$\mathbb{E}[X] = \frac{1}{\lambda}, \quad \text{Var}(X) = \frac{1}{\lambda^2}$$

### 无记忆性

与几何分布类似，指数分布也具有无记忆性：
$$P(X > s + t \mid X > s) = P(X > t)$$

指数分布是唯一的具有无记忆性的**连续**分布。

### 与泊松过程的关系

若事件发生的次数服从参数为 $\lambda$ 的泊松过程，则相邻两次事件之间的时间间隔相互独立且服从 $\text{Exponential}(\lambda)$。

---

## 第 12 页：指数分布——应用示例

### 示例 1：等待时间

某客服中心的来电服从泊松过程，平均每小时 20 通来电（$\lambda = 20$）。刚刚接完一通电话，下一通电话的等待时间 $T$ 服从分布：

$$T \sim \text{Exponential}(20) \text{ （单位：小时）}$$

所以平均等待时间为 $\mathbb{E}[T] = 1/20$ 小时 = 3 分钟。

### 示例 2：寿命

指数分布常被用来建模电子元件的寿命。但需要注意的是，指数分布的无记忆性意味着元件"不会老化"——已经使用了 1000 小时和全新的元件，后续的寿命分布完全相同。这在很多实际场景中是**不现实**的。

### 示例 3：可靠度

$$P(T > t) = e^{-\lambda t}$$

这是指数分布的一个常用公式——元件存活时间超过 $t$ 的概率。

---

## 第 13 页：正态分布

### 正态分布（Normal / Gaussian Distribution）

统计学中最重要的连续分布。

$$X \sim \mathcal{N}(\mu, \sigma^2)$$

**PDF**：
$$f_X(x) = \frac{1}{\sqrt{2\pi\sigma^2}} \exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right), \quad x \in \mathbb{R}$$

**期望与方差**：
$$\mathbb{E}[X] = \mu, \quad \text{Var}(X) = \sigma^2$$

### 形状特征

- 钟形曲线，对称于 $\mu$
- $\mu$ 决定位置（中心），$\sigma$ 决定宽度（离散程度）
- 在 $x = \mu \pm \sigma$ 处有拐点

### 经验法则（68-95-99.7）

- $[\mu \pm 1\sigma]$：约 68.27%
- $[\mu \pm 2\sigma]$：约 95.45%
- $[\mu \pm 3\sigma]$：约 99.73%

---

## 第 14 页：标准正态分布

### 标准正态分布（Standard Normal Distribution）

$$\mathcal{N}(0, 1)$$

**PDF**：
$$\phi(z) = \frac{1}{\sqrt{2\pi}} e^{-z^2/2}$$

**CDF**：
$$\Phi(z) = P(Z \leq z) = \int_{-\infty}^{z} \frac{1}{\sqrt{2\pi}} e^{-t^2/2} \, dt$$

$\Phi(z)$ 没有闭式表达式，通常通过查表或计算机计算。

### 标准化变换

如果 $X \sim \mathcal{N}(\mu, \sigma^2)$，则：
$$Z = \frac{X - \mu}{\sigma} \sim \mathcal{N}(0, 1)$$

这是正态分布最重要的性质之一——任意正态分布都可以通过减去均值再除以标准差转化为标准正态分布。

---

## 第 15 页：正态分布——计算示例

### 示例

设 IQ 分数 $X \sim \mathcal{N}(100, 15^2)$。求一个人 IQ 超过 130 的概率。

**解答**：

标准化：
$$Z = \frac{130 - 100}{15} = \frac{30}{15} = 2$$

$$P(X > 130) = P(Z > 2) = 1 - \Phi(2) = 1 - 0.9772 = 0.0228$$

约 2.28% 的人 IQ 超过 130（这大约对应于 Mensa 的门槛）。

### 对称性

标准正态分布的 CDF 满足：
$$\Phi(-z) = 1 - \Phi(z)$$

利用这个性质可以简化双侧概率的计算：
$$P(|Z| > z) = 2 \cdot (1 - \Phi(z)) = 2\Phi(-z)$$

---

## 第 16 页：Gamma 分布

### Gamma 分布

指数分布的推广，用于建模多个独立事件的等待时间。

$$X \sim \text{Gamma}(\alpha, \beta), \quad \alpha > 0, \beta > 0$$

**PDF**：
$$f_X(x) = \frac{\beta^\alpha}{\Gamma(\alpha)} x^{\alpha-1} e^{-\beta x}, \quad x > 0$$

其中 $\Gamma(\alpha) = \int_0^\infty t^{\alpha-1} e^{-t} \, dt$ 为 Gamma 函数。

若 $\alpha$ 为正整数，$\Gamma(\alpha) = (\alpha-1)!$。

**期望与方差**：
$$\mathbb{E}[X] = \frac{\alpha}{\beta}, \quad \text{Var}(X) = \frac{\alpha}{\beta^2}$$

### 与指数分布和 $\chi^2$ 分布的关系

- $\text{Gamma}(1, \beta) = \text{Exponential}(\beta)$
- $\text{Gamma}(\nu/2, 1/2) = \chi^2_\nu$（卡方分布）

---

## 第 17 页：Beta 分布

### Beta 分布

定义在 $[0, 1]$ 区间上的分布，广泛用于建模比例和概率。

$$X \sim \text{Beta}(\alpha, \beta), \quad \alpha > 0, \beta > 0$$

**PDF**：
$$f_X(x) = \frac{\Gamma(\alpha+\beta)}{\Gamma(\alpha)\Gamma(\beta)} x^{\alpha-1} (1-x)^{\beta-1}, \quad 0 < x < 1$$

**期望与方差**：
$$\mathbb{E}[X] = \frac{\alpha}{\alpha+\beta}, \quad \text{Var}(X) = \frac{\alpha\beta}{(\alpha+\beta)^2(\alpha+\beta+1)}$$

### Beta 分布在贝叶斯统计中的重要性

Beta 分布是二项分布的**共轭先验**（Conjugate Prior）。如果：
- 先验：$p \sim \text{Beta}(\alpha, \beta)$
- 似然：$X \mid p \sim \text{Binomial}(n, p)$

则后验分布为：
$$p \mid X = k \sim \text{Beta}(\alpha + k, \beta + n - k)$$

这是一个非常优美的数学性质——先验和后验属于同一分布族。

---

## 第 18 页：$\chi^2$ 分布、$t$ 分布与 $F$ 分布

### $\chi^2$（卡方）分布

若 $Z_1, Z_2, \ldots, Z_\nu \stackrel{\text{i.i.d.}}{\sim} \mathcal{N}(0, 1)$，则：
$$X = \sum_{i=1}^{\nu} Z_i^2 \sim \chi^2_\nu$$

$\nu$ 称为自由度。$\mathbb{E}[X] = \nu$，$\text{Var}(X) = 2\nu$。

### $t$ 分布

若 $Z \sim \mathcal{N}(0, 1)$，$U \sim \chi^2_\nu$，且 $Z$ 与 $U$ 独立，则：
$$T = \frac{Z}{\sqrt{U / \nu}} \sim t_\nu$$

$t$ 分布比正态分布尾部更厚。当 $\nu \to \infty$ 时，$t_\nu \to \mathcal{N}(0, 1)$。

### $F$ 分布

若 $U \sim \chi^2_{d_1}$，$V \sim \chi^2_{d_2}$，且 $U$ 与 $V$ 独立，则：
$$F = \frac{U / d_1}{V / d_2} \sim F_{d_1, d_2}$$

用于 ANOVA 和回归分析中的 F 检验。

---

## 第 19 页：联合分布

### 联合概率函数

对于两个离散随机变量 $X$ 和 $Y$：

**联合 PMF**：
$$p_{X,Y}(x, y) = P(X = x, Y = y)$$

满足：
1. $p_{X,Y}(x, y) \geq 0$
2. $\sum_x \sum_y p_{X,Y}(x, y) = 1$

对于两个连续随机变量：

**联合 PDF**：
$$P((X, Y) \in A) = \iint_A f_{X,Y}(x, y) \, dx \, dy$$

满足：
1. $f_{X,Y}(x, y) \geq 0$
2. $\int_{-\infty}^{\infty} \int_{-\infty}^{\infty} f_{X,Y}(x, y) \, dx \, dy = 1$

---

## 第 20 页：边缘分布

### 边缘分布（Marginal Distribution）

从联合分布中获得单个变量的分布，称为"边际化"（Marginalization）。

**离散**：
$$p_X(x) = \sum_y p_{X,Y}(x, y), \quad p_Y(y) = \sum_x p_{X,Y}(x, y)$$

**连续**：
$$f_X(x) = \int_{-\infty}^{\infty} f_{X,Y}(x, y) \, dy, \quad f_Y(y) = \int_{-\infty}^{\infty} f_{X,Y}(x, y) \, dx$$

### 边缘分布的名称由来

"边缘"（Marginal）一词来源于早年的手动计算——人们会在联合分布表格的**边缘**（最右侧和最下方）写上求和结果，这就是边缘概率。

---

## 第 21 页：条件分布

### 条件分布（Conditional Distribution）

给定 $Y = y$ 的条件下，$X$ 的条件分布为：

**离散**：
$$p_{X \mid Y}(x \mid y) = \frac{p_{X,Y}(x, y)}{p_Y(y)}, \quad \text{当 } p_Y(y) > 0$$

**连续**：
$$f_{X \mid Y}(x \mid y) = \frac{f_{X,Y}(x, y)}{f_Y(y)}, \quad \text{当 } f_Y(y) > 0$$

### 条件期望

$$\mathbb{E}[X \mid Y = y] = \begin{cases} \sum_x x \cdot p_{X \mid Y}(x \mid y), & \text{离散} \\ \int x \cdot f_{X \mid Y}(x \mid y) \, dx, & \text{连续} \end{cases}$$

### 直观理解

条件分布就是将联合分布在"某条切片"上的形状重新归一化。想象一个三维的联合密度曲面：给定 $Y = y_0$，条件分布 $f_{X \mid Y}(x \mid y_0)$ 就是曲面在 $Y = y_0$ 处的横截面。

---

## 第 22 页：随机变量的独立性

### 定义

两个随机变量 $X$ 和 $Y$ 称为**独立的**，如果对于任意集合 $A$ 和 $B$：
$$P(X \in A, Y \in B) = P(X \in A) \cdot P(Y \in B)$$

### 等价条件

**离散**：$p_{X,Y}(x, y) = p_X(x) \cdot p_Y(y)$ 对所有 $x, y$

**连续**：$f_{X,Y}(x, y) = f_X(x) \cdot f_Y(y)$ 对所有 $x, y$

### 独立性的推论

如果 $X$ 和 $Y$ 独立：
- $\mathbb{E}[XY] = \mathbb{E}[X] \cdot \mathbb{E}[Y]$
- $\text{Var}(X + Y) = \text{Var}(X) + \text{Var}(Y)$
- $g(X)$ 和 $h(Y)$ 也相互独立，对于任意函数 $g$ 和 $h$

### 重要提醒

- **独立 ⇒ 不相关**（$\text{Cov} = 0$）
- 但**不相关 ⇏ 独立**

---

## 第 23 页：协方差

### 协方差的定义

两个随机变量 $X$ 和 $Y$ 之间的协方差（Covariance）度量它们的**线性共变**程度：

$$\text{Cov}(X, Y) = \mathbb{E}[(X - \mathbb{E}[X])(Y - \mathbb{E}[Y])]$$

### 计算协方差的简便公式

$$\text{Cov}(X, Y) = \mathbb{E}[XY] - \mathbb{E}[X]\mathbb{E}[Y]$$

**推导**：
$$\begin{aligned} \text{Cov}(X, Y) &= \mathbb{E}[(X - \mu_X)(Y - \mu_Y)] \\ &= \mathbb{E}[XY - \mu_X Y - \mu_Y X + \mu_X \mu_Y] \\ &= \mathbb{E}[XY] - \mu_X \mathbb{E}[Y] - \mu_Y \mathbb{E}[X] + \mu_X \mu_Y \\ &= \mathbb{E}[XY] - \mu_X \mu_Y \end{aligned}$$

### 协方差的符号含义

- $\text{Cov}(X, Y) > 0$：$X$ 大时 $Y$ 也倾向于大（正相关）
- $\text{Cov}(X, Y) < 0$：$X$ 大时 $Y$ 倾向于小（负相关）
- $\text{Cov}(X, Y) \approx 0$：没有线性相关关系（但可能存在非线性关系）

---

## 第 24 页：协方差的性质

1. **对称性**：$\text{Cov}(X, Y) = \text{Cov}(Y, X)$
2. **与自身**：$\text{Cov}(X, X) = \text{Var}(X)$
3. **双线性（Bilinearity）**：
   $$\text{Cov}(aX + bY, Z) = a \cdot \text{Cov}(X, Z) + b \cdot \text{Cov}(Y, Z)$$
4. **常数的协方差为零**：$\text{Cov}(X, c) = 0$（$c$ 为常数）

利用双线性性质，可以方便地计算线性组合的方差：
$$\text{Var}\left(\sum_{i=1}^{n} X_i\right) = \sum_{i=1}^{n} \text{Var}(X_i) + 2 \sum_{i<j} \text{Cov}(X_i, X_j)$$

---

## 第 25 页：相关系数

相关系数将协方差标准化为 $[-1, 1]$ 之间的值：

$$\rho_{X,Y} = \frac{\text{Cov}(X, Y)}{\sigma_X \sigma_Y}$$

性质：
- $-1 \leq \rho_{X,Y} \leq 1$
- $\rho = 1$：完全正线性相关；$\rho = -1$：完全负线性相关
- $\rho = 0$：不线性相关（但不一定独立）
- $\rho$ 只度量**线性**关系，对异常值敏感

---

## 第 26 页：条件期望

$$\mathbb{E}[Y] = \mathbb{E}\left[\mathbb{E}[Y \mid X]\right]$$

这是**迭代期望法则**：先计算每层的子均值，再对各层加权平均，结果等于总体均值。

---

## 第 27 页：条件方差——方差分解

$$\text{Var}(Y) = \mathbb{E}[\text{Var}(Y \mid X)] + \text{Var}(\mathbb{E}[Y \mid X])$$

- $\mathbb{E}[\text{Var}(Y \mid X)]$：组内方差（不可被 $X$ 解释的部分）
- $\text{Var}(\mathbb{E}[Y \mid X])$：组间方差（可被 $X$ 解释的部分）

---

## 第 28 页：条件期望——示例

设 $\mathbb{E}[Y \mid X] = 50 + 5X$，$\text{Var}(Y \mid X) = 100$，$X$ 的分布：$P(X=2)=0.3, P(X=4)=0.4, P(X=6)=0.3$

$$\mathbb{E}[X] = 4, \quad \mathbb{E}[Y] = 50 + 5(4) = 70$$
$$\text{Var}(Y) = 100 + 25 \times 2.4 = 160$$

---

## 第 29 页：随机变量函数的分布

**CDF 法**（最通用）：
$$F_Y(y) = P(Y \leq y) = P(g(X) \leq y)$$

**变换公式**（$g$ 严格单调）：
$$f_Y(y) = f_X(g^{-1}(y)) \cdot \left| \frac{d}{dy} g^{-1}(y) \right|$$

---

## 第 30 页：两个随机变量之和的分布

**卷积公式**（独立连续）：
$$f_Z(z) = \int_{-\infty}^{\infty} f_X(x) \cdot f_Y(z - x) \, dx$$

重要结果：
- 独立正态的和仍为正态
- 独立泊松的和仍为泊松
- 独立二项的和仍为二项（同 $p$）

---

## 第 31 页：协方差矩阵

对于随机向量 $\mathbf{X} = (X_1, \ldots, X_p)^T$：
$$\boldsymbol{\Sigma} = \mathbb{E}[(\mathbf{X} - \boldsymbol{\mu})(\mathbf{X} - \boldsymbol{\mu})^T]$$

对角元素为方差，非对角元素为协方差。若 $\mathbf{Y} = \mathbf{A}\mathbf{X} + \mathbf{b}$，则 $\text{Cov}(\mathbf{Y}) = \mathbf{A}\boldsymbol{\Sigma}\mathbf{A}^T$。

---

## 第 32 页：多元正态分布

$$\mathbf{X} \sim \mathcal{N}_p(\boldsymbol{\mu}, \boldsymbol{\Sigma})$$

重要性质：**不相关 ⇔ 独立**（这是多元正态特有的）。条件分布仍为正态。

---

## 第 33 页：大数定律（LLN）

**弱大数定律**：$\bar{X}_n \xrightarrow{P} \mu$

**强大数定律**：$\bar{X}_n \to \mu$ 几乎必然

直觉：长期平均会趋近于期望值。解释了频率为什么能近似概率。

---

## 第 34 页：大数定律——图示与启示

大数定律解释了赌场盈利、保险公司的运作模式。但与赌徒谬误不同——它说的是长期极限，不意味短期会"回归均值"。

---

## 第 35 页：中心极限定理（CLT）

$$Z_n = \frac{\bar{X}_n - \mu}{\sigma / \sqrt{n}} \xrightarrow{d} \mathcal{N}(0, 1)$$

**无论原始分布是什么**，标准化后的样本均值在大样本下近似标准正态分布。

---

## 第 36 页：CLT——深入理解

"足够大"的经验法则：
- 总体接近正态：$n \geq 15$
- 总体明显偏态：$n \geq 30$
- 总体极度偏态：$n \geq 50$

等价表述：$\bar{X}_n \approx \mathcal{N}(\mu, \sigma^2/n)$

---

## 第 37 页：CLT——应用示例

某工厂螺丝钉重量均值为 10g、标准差为 2g。抽取 100 枚，平均重量介于 9.8 到 10.2 的概率：

$$\bar{X}_{100} \approx \mathcal{N}(10, 0.04)$$
$$P(9.8 < \bar{X} < 10.2) \approx 0.6827$$

---

## 第 38 页：LLN 与 CLT 总结

| | LLN | CLT |
|--|-----|-----|
| 问题 | $\bar{X}_n$ 趋近于什么？ | $\bar{X}_n$ 的分布形状？ |
| 结论 | $\bar{X}_n \to \mu$ | 近似正态 |
| 用途 | 一致性基础 | 置信区间/检验基础 |

---

## 第 39 页：本章习题 (1)

识别分布：
- (a) 抛硬币 20 次，正面次数 → $\text{Binomial}(20, 0.5)$
- (b) 网站每小时注册人数 → $\text{Poisson}(5)$
- (c) 抛硬币直到正面 → $\text{Geometric}(0.5)$
- (d) 公交等待时间 → $\text{Exponential}(6)$

---

## 第 40 页：本章习题 (2)

$X \sim \mathcal{N}(170, 6.5^2)$ 为身高（cm）：
- (a) $P(X > 180) \approx 0.062$
- (b) $P(160 < X < 175) \approx 0.718$
- (c) 25 人平均身高 $> 172$：$P(\bar{X} > 172) \approx 0.062$

---

## 第 41 页：本章小结

### 概率论复习（二）要点回顾

1. 常用离散分布：伯努利、二项、几何、泊松、负二项
2. 常用连续分布：均匀、指数、正态、Gamma、Beta
3. 联合分布与边缘分布——联合 PMF/PDF 及其边际化
4. 条件分布与独立性——条件 PMF/PDF、独立的条件
5. 协方差与相关系数——度量和标准化线性关系
6. 条件期望与方差分解——迭代期望法则
7. LLN 与 CLT——统计推断的两大理论基石

---

> **翻译完成**：`Review_of_probability2.pdf` 共 41 页，逐页翻译完毕。
