# Review_of_probability4 中文精讲版

> 对应原文件：`Review_of_probability4.pdf`  
> 定位：这是随机分析部分的中文学习资料，重点解释条件期望、鞅、布朗运动、Ito 积分、Ito 公式、SDE、Fokker-Planck 方程与 Langevin 动力学。

## 1. 学习主线

这份 review 的结构可以看成一条链：

```text
可测性
-> 条件期望
-> 鞅
-> 布朗运动
-> 随机积分
-> Ito 公式
-> SDE
-> Fokker-Planck 方程
-> Langevin / 生成模型
```

不要把这些概念当作孤立定义。它们都在回答同一个问题：

> 当系统受到随机噪声驱动时，我们如何描述样本路径、条件平均、分布演化和采样机制？

## 2. 可测性：能被当前信息看见

随机变量本质上是可测函数：

```text
X : (Omega, F) -> (R, B(R))
```

`X` 可测表示：

```text
X^{-1}(A) in F, for all A in B(R)
```

中文解释：`F` 是你能区分的事件集合。如果 `X` 可测，那么关于 `X` 的问题都能转化成 `F` 中的事件。

验证实值函数可测时，只需要检查：

```text
{X <= t} in F, for all t
```

因为所有 `(-infty,t]` 生成了 Borel sigma 代数。

在随机过程中，filtration `(Ft)` 表示随时间增长的信息流：

```text
Fs subset Ft, s < t
```

`Xt in Ft` 表示：时刻 `t` 的状态只能依赖截至 `t` 的信息，不能偷看未来。

## 3. 条件期望：在较少信息下重建 X

给定子 sigma 代数 `G subset F`，条件期望 `E[X|G]` 是唯一满足：

```text
E[X|G] is G-measurable
integral_A E[X|G] dP = integral_A X dP, for all A in G
```

的随机变量。

这两条分别表达：

1. `E[X|G]` 只能使用 `G` 的信息；
2. 在所有 `G` 能识别的事件上，`E[X|G]` 与 `X` 的平均效果一致。

### 分块平均理解

若：

```text
G = {empty, A, Ac, Omega}
```

那么：

```text
E[X|G]
= average(X on A) * 1_A
+ average(X on Ac) * 1_Ac
```

所以条件期望不是“代入一个条件得到一个数”，而是把 `X` 在 `G` 能区分的每个区域内平均。

### 投影理解

在 `L2` 空间中：

```text
E[X|G] = projection of X onto L2(Omega,G,P)
```

也就是说，在所有只依赖 `G` 信息的随机变量里，`E[X|G]` 是对 `X` 的最佳平方误差近似。

## 4. 鞅：公平游戏与条件期望

过程 `(Xt)` 是 martingale，如果：

```text
E[Xt | Fs] = Xs,  s < t
```

含义：用当前信息预测未来，平均来看就是现在。

super-martingale：

```text
E[Xt | Fs] <= Xs
```

sub-martingale：

```text
E[Xt | Fs] >= Xs
```

典型构造：

```text
Xt = E[Z | Ft]
```

则：

```text
E[Xt | Fs]
= E[E[Z|Ft] | Fs]
= E[Z|Fs]
= Xs
```

所以它是鞅。

## 5. 布朗运动：连续但极其粗糙的随机路径

标准布朗运动 `(Wt)` 满足：

1. `W0 = 0`；
2. 独立增量；
3. `Wt - Ws ~ N(0,t-s)`；
4. 样本路径几乎处处连续。

布朗运动是鞅，因为：

```text
E[Wt | Fs] = Ws + E[Wt-Ws | Fs] = Ws
```

关键性质：

```text
first variation = infinity
quadratic variation = t
```

也就是说，布朗路径连续但非常抖，不能用普通有界变差路径的积分理论处理；但它的二阶波动有稳定极限。

## 6. 为什么需要 Ito 积分

普通 Riemann-Stieltjes 积分：

```text
integral f dg
```

通常要求 `g` 有有界变差。但布朗运动没有有界一阶变差，因此不能直接把：

```text
integral sigma(Xt,t) dWt
```

当作普通路径积分。

构造随机积分时，对每个小区间 `[tj,t_{j+1}]`，可以选：

- 左端点；
- 右端点；
- 中点。

Ito 积分选择左端点：

```text
sum f(tj) (W_{t_{j+1}} - W_{tj})
```

理由：左端点只依赖过去信息，不使用未来信息。这使得积分过程适合描述真实随机系统。

## 7. Ito isometry

Ito 积分最重要的估计工具是：

```text
E[ integral_S^T f(Xt,t) dWt ] = 0
```

以及：

```text
E[( integral_S^T f(Xt,t) dWt )^2]
= E[ integral_S^T f^2(Xt,t) dt ]
```

第二个公式叫 Ito isometry。

直观解释：

- 随机积分的均值为 0；
- 随机积分的方差等于被积函数平方的时间积分。

它是随机分析里估计二阶矩的核心工具。

## 8. 如何理解 `(dWt)^2 = dt`

这不是普通代数等式，而是由布朗运动二次变差来的计算口诀。

布朗运动满足：

```text
sum (W_{t_{j+1}} - W_{tj})^2 -> T
```

所以在 Ito 计算中，形式上写：

```text
(dWt)^2 = dt
dt dWt = 0
(dt)^2 = 0
```

记住：这是极限意义下的记号规则，用来帮助快速写 Ito 公式。

## 9. Ito 公式

设：

```text
dXt = b(Xt,t) dt + sigma(Xt,t) dWt
```

普通链式法则在随机微积分里不成立，因为 `(dWt)^2` 不是 0，而是 `dt`。

一维 Ito 公式：

```text
df(Xt)
= [ b f'(Xt) + 1/2 sigma^2 f''(Xt) ] dt
+ sigma f'(Xt) dWt
```

多维形式：

```text
df(Xt)
= [ b · grad f + 1/2 sigma sigma^T : Hessian f ] dt
+ grad f · sigma dWt
```

最重要的是多出来的二阶项：

```text
1/2 sigma^2 f''
```

这是随机微积分区别于普通微积分的核心。

## 10. OU 过程

Ornstein-Uhlenbeck 过程：

```text
dXt = -gamma Xt dt + sigma dWt
```

其中 `gamma > 0` 控制回拉强度，`sigma > 0` 控制噪声强度。

解法：乘以积分因子 `e^{gamma t}`。

最终解为：

```text
Xt = e^{-gamma t} X0
   + integral_0^t sigma e^{-gamma(t-s)} dWs
```

第二项记作 `Qt`，它是高斯随机变量，满足：

```text
E[Qt] = 0
Var(Qt) = sigma^2/(2 gamma) * (1 - e^{-2 gamma t})
```

当 `t -> infinity`：

```text
e^{-gamma t} X0 -> 0
Var(Qt) -> sigma^2/(2 gamma)
```

所以：

```text
Xt | X0 -> N(0, sigma^2/(2 gamma))
```

这说明 OU 过程会把很多初始分布推向高斯型稳定分布，因此常出现在扩散模型和采样理论中。

## 11. 其他 SDE 例子

### Arithmetic Brownian Motion

```text
dXt = v dt + sigma dWt
```

解为：

```text
Xt = X0 + vt + sigma Wt
```

`v` 控制平均方向，`sigma` 控制波动强度。

### Geometric Brownian Motion

```text
dXt = -a Xt dt + b Xt dWt
```

对 `log Xt` 用 Ito 公式：

```text
d log Xt = -(a + b^2/2) dt + b dWt
```

注意多出来的 `b^2/2` 正是 Ito 修正项。

## 12. Fokker-Planck 方程

SDE 描述单条随机路径：

```text
dXt = b(Xt,t) dt + sigma(Xt,t) dWt
```

Fokker-Planck 方程描述 `Xt` 的概率密度 `pt(x)` 如何随时间变化。

一维形式：

```text
partial_t pt(x)
= - partial_x( b(x,t) pt(x) )
+ 1/2 partial_xx( sigma^2(x,t) pt(x) )
```

中文理解：

- drift 造成概率质量平移；
- diffusion 造成概率质量扩散；
- SDE 是路径层面的模型；
- FPE 是分布层面的模型。

最简单例子：

```text
dXt = dWt
```

则 `Xt ~ N(0,t)`，密度满足热方程：

```text
partial_t p = 1/2 partial_xx p
```

## 13. FPE 的推导思路

推导通常借助 Ito 公式和测试函数 `f`。

先对 `f(Xt)` 用 Ito 公式，得到生成元：

```text
L f = b · grad f + 1/2 sigma sigma^T : Hessian f
```

再取条件期望并写成密度积分：

```text
(f, partial_t p) = (L f, p)
```

为了让算子作用到 `p` 上，使用伴随算子：

```text
(L f, p) = (f, L* p)
```

于是：

```text
partial_t p = L* p
```

这就是 Fokker-Planck 方程。

学习时不必一开始背所有分部积分细节。先抓住三步：

1. Ito 公式给出生成元 `L`；
2. 期望把路径转成密度；
3. 伴随算子把 `L` 从测试函数移到密度上。

## 14. 不变分布

如果某个密度 `p` 使得：

```text
partial_t p = 0
```

则称它是不变分布。

对 OU 过程：

```text
dXt = -gamma Xt dt + sigma dWt
```

FPE 为：

```text
partial_t p
= gamma partial_x(xp) + 1/2 partial_xx(sigma^2 p)
```

令 `partial_t p = 0`，可以解出高斯型不变分布：

```text
p(x) proportional exp(- gamma x^2 / sigma^2)
```

这对应：

```text
N(0, sigma^2/(2 gamma))
```

## 15. Langevin 动力学与采样

Langevin SDE：

```text
dXt = -grad v(Xt) dt + sqrt(2) dWt
```

它的 FPE 是：

```text
partial_t p = div(grad v p) + Delta p
```

令稳态 `partial_t p = 0`，可得：

```text
p(x) proportional exp(-v(x))
```

所以如果想从目标分布 `pdata` 采样，可以令：

```text
v(x) = -log pdata(x)
```

则不变分布就是：

```text
exp(-v(x)) = pdata(x)
```

离散化得到采样算法：

```text
x_{n+1} = x_n - grad v(x_n) Delta t + sqrt(2 Delta t) xi_n
```

其中 `xi_n ~ N(0,1)`。

这就是很多采样算法和生成模型的理论来源。

## 16. 与生成模型的联系

生成模型要做的是学习数据分布 `p_data` 并从中采样。

SDE/FPE 视角提供了一个思路：

1. 设计一个正向过程，把复杂数据分布推到简单分布；
2. 学习反向过程或 score；
3. 从简单分布出发，逆向生成数据。

OU 过程、Langevin 动力学和扩散模型都可以放进这个框架里。

## 17. 必会公式清单

```text
E[X|G] is G-measurable
integral_A E[X|G] dP = integral_A X dP
```

```text
E[Xt | Fs] = Xs
```

```text
Wt - Ws ~ N(0,t-s)
```

```text
<W,W>_t = t
```

```text
E[(integral f dW)^2] = E[integral f^2 dt]
```

```text
df(Xt) = (b f' + 1/2 sigma^2 f'')dt + sigma f' dWt
```

```text
partial_t p = -partial_x(bp) + 1/2 partial_xx(sigma^2 p)
```

```text
dXt = -grad v(Xt)dt + sqrt(2)dWt
=> invariant p proportional exp(-v)
```

## 18. 自测题

1. 条件期望为什么是随机变量而不是普通数字？
2. 为什么 `E[X|G]` 可以看成投影？
3. 布朗运动为什么是鞅？
4. 为什么布朗运动不能用普通 Riemann-Stieltjes 积分处理？
5. Ito 积分为什么选左端点？
6. Ito 公式中为什么会多出二阶项？
7. OU 过程为什么会收敛到高斯分布？
8. SDE 和 FPE 分别描述什么？
9. 不变分布是什么意思？
10. Langevin 动力学为什么能用于采样？

