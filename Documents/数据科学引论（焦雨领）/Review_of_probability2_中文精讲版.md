# Review_of_probability2 中文精讲版

> 对应原文件：`Review_of_probability2.pdf`  
> 定位：这份资料不是页码导读，而是把课件内容改写成可以直接学习的中文讲义。公式保留英文/数学记号，中文负责解释“为什么这样定义、公式在说什么、考试或复习时该抓什么”。

## 1. 条件独立：独立不等于条件独立

课件一开始用 collider 结构说明一个很容易误会的事实：

```text
X -> Z <- Y
```

`Z` 同时受到 `X` 和 `Y` 的影响。即使 `X` 和 `Y` 在总体中独立，给定 `Z` 之后也可能变得相关。

例子是录取问题：

- `X = 1` 表示数学能力强；
- `Y = 1` 表示音乐能力强；
- `Z = 1` 表示被项目录取；
- 录取规则是：`Z = 1 iff X = 1 or Y = 1`。

在总体中，数学能力和音乐能力可以独立。但如果只看已经录取的人，那么知道某人数学不强，就会提高“他音乐强”的可能性。因为他必须靠另一个能力满足录取条件。

核心结论：

```text
X 独立于 Y
不推出
X 条件独立于 Y given Z
```

学习时要特别记住：**条件化不是无害操作**。在因果图里，对 collider 条件化会“打开”一条原本不存在的关联路径。

## 2. 集合极限与 Borel-Cantelli 引理

事件列 `{An}` 的长期行为通常通过 `lim sup` 和 `lim inf` 描述。

```text
lim sup An = intersection_n union_{k>=n} Ak
lim inf An = union_n intersection_{k>=n} Ak
```

直观解释：

- `lim sup An`：无穷多个 `An` 发生，也写作 `An i.o.`；
- `lim inf An`：从某个时刻开始，所有后续 `An` 都发生。

所以有：

```text
lim inf An subset lim sup An
```

因为“最终一直发生”当然意味着“无穷多次发生”。

### Borel-Cantelli 第一引理

如果：

```text
sum P(An) < infinity
```

那么：

```text
P(An i.o.) = 0
```

意思是：如果这些事件概率加起来有限，那么它们无穷多次发生的概率为 0。

证明思路：

令：

```text
Bm = union_{k>=m} Ak
```

则：

```text
lim sup An = intersection_m Bm
```

并且：

```text
P(Bm) <= sum_{k>=m} P(Ak)
```

因为总和收敛，尾和趋于 0，所以 `P(lim sup An)=0`。

### Borel-Cantelli 第二引理

如果 `{An}` 相互独立，并且：

```text
sum P(An) = infinity
```

那么：

```text
P(An i.o.) = 1
```

这里一定要注意：第二引理需要 **mutual independence（相互独立）**。证明时要处理“从某一时刻后再也不发生”的补事件：

```text
Cm = intersection_{k>=m} Ac_k
```

利用独立性：

```text
P(Cm) = product_{k>=m} (1 - P(Ak))
      <= exp(-sum_{k>=m} P(Ak))
      = 0
```

所以“最终不再发生”的概率为 0，即无穷多次发生的概率为 1。

## 3. Jensen 不等式与 Lp 范数比较

课件证明的结论是：

```text
0 < p <= q <= infinity  =>  ||X||_Lp <= ||X||_Lq
```

这说明在概率空间里，`q` 阶可积通常比 `p` 阶可积更强。

当 `q = infinity` 时，`L_infinity` 是本质上界，因此：

```text
|X| <= ess sup |X|
```

直接推出：

```text
||X||_Lp <= ||X||_L_infinity
```

当 `q < infinity` 时，令：

```text
phi(t) = t^(q/p)
```

因为 `q/p >= 1`，所以 `phi` 是凸函数。对 `|X|^p` 用 Jensen 不等式：

```text
(E|X|^p)^(q/p) <= E|X|^q
```

也就是：

```text
||X||_Lp <= ||X||_Lq
```

学习重点：这个结论经常用于“我已经控制了高阶矩，因此低阶矩也自动受控”。

## 4. 推前测度：随机变量的分布是什么

设随机变量：

```text
X : (Omega, F, P) -> (R, B(R))
```

它会把原概率测度 `P` 推到实数轴上，得到 `PX`：

```text
PX(A) = P(X in A) = P(X^{-1}(A))
```

这个 `PX` 就是 `X` 的分布，也叫 law 或 distribution。

因此对任意函数 `f`，下面三种写法本质相同：

```text
integral_Omega f(X(omega)) dP
= integral_R f(x) dPX
= integral_R f(x) PX(dx)
```

中文理解：原来我们在样本空间 `Omega` 上积分；知道 `X` 的分布之后，就可以把积分搬到实数轴上。这就是“只关心随机变量的分布，不关心它来自哪个样本空间”的原因。

## 5. 用尾概率表示期望

如果 `X >= 0`，则：

```text
E[X] = integral_0^infty P(X > t) dt
```

这个公式非常重要。它把期望变成尾概率曲线下面积。

证明思路：

```text
x = integral_0^x 1 dt
```

所以：

```text
E[X] = integral integral_0^x 1 dt mu(dx)
```

交换积分顺序，就得到：

```text
E[X] = integral_0^infty P(X > t) dt
```

对高阶矩也类似：

```text
E[X^p] = p integral_0^infty t^(p-1) P(X > t) dt
```

这在证明矩有限时很好用。例如如果：

```text
P(X > t) <= c t^(-alpha)
```

且 `alpha > p`，那么：

```text
E[X^p] < infinity
```

因为积分尾部的指数小于 `-1`。

## 6. 条件期望：信息变粗后的平均

条件期望最容易误解的地方是：`E[X | Y]` 不是一个数，而是一个随机变量。

严格来说：

```text
E[X | Y] = E[X | sigma(Y)]
```

其中 `sigma(Y)` 表示观察 `Y` 能得到的全部信息。

如果 `g` 不是单射，那么 `g(Y)` 会丢失信息。例如：

```text
Y = 具体分数
g(Y) = 是否及格
```

知道具体分数比知道是否及格更细。因此一般：

```text
E[X | Y] != E[X | g(Y)]
```

但是：

```text
E[X | Y, g(Y)] = E[X | Y]
```

因为知道 `Y` 以后，`g(Y)` 没有提供新信息。

## 7. 可测性与 sigma 代数

一个函数：

```text
f : (Omega, F) -> (R, B(R))
```

可测，意思是：

```text
for any B in B(R), f^{-1}(B) in F
```

中文理解：`F` 表示你在样本空间中“能观察/能区分”的事件。`f` 可测，表示 `f` 的取值事件都能被 `F` 识别。

验证实值函数可测时，不需要检查所有 Borel 集，只要检查：

```text
{omega : f(omega) <= t} in F, for all t in R
```

因为所有 `(-infty, t]` 生成了 `B(R)`。

sigma 代数越细，能定义的可测函数越复杂：

- `F = {empty, Omega}`：只能定义常数函数；
- `F = {empty, A, Ac, Omega}`：函数只能在 `A` 和 `Ac` 上分别取常数；
- 有限划分生成的 sigma 代数：函数在每个划分块上取常数。

这就是后面 filtration 的直观来源：时间越往后，信息越多，随机过程能依赖的信息也越多。

## 8. 条件期望的严格定义

设 `G subset F` 是子 sigma 代数，`X` 可积。条件期望 `E[X|G]` 是唯一满足下面两条的随机变量：

1. `E[X|G]` 是 `G`-可测；
2. 对任意 `A in G`，

```text
integral_A E[X|G] dP = integral_A X dP
```

第一条说明：它只能使用 `G` 中的信息。

第二条说明：在任何 `G` 能识别的事件上，它和原随机变量 `X` 的平均效果一致。

### 例子 1：最粗 sigma 代数

如果：

```text
G = {empty, Omega}
```

那么 `G`-可测随机变量只能是常数，所以：

```text
E[X|G] = E[X]
```

### 例子 2：二分 sigma 代数

如果：

```text
G = {empty, A, Ac, Omega}
```

那么：

```text
E[X|G] = average of X on A * 1_A
        + average of X on Ac * 1_Ac
```

即条件期望就是“在 `G` 能区分的每个格子里取平均”。

## 9. 条件期望的性质

常用性质：

1. 如果 `X` 已经是 `G`-可测，则：

```text
E[X|G] = X
```

2. 如果 `G1 subset G2`，则 tower property：

```text
E[E[X|G2] | G1] = E[X|G1]
```

3. 如果 `X` 与 `G` 独立，则：

```text
E[X|G] = E[X]
```

4. 取全期望：

```text
E[E[X|G]] = E[X]
```

5. 如果 `X` 是 `G`-可测，则：

```text
E[XY|G] = X E[Y|G]
```

记忆方式：能被 `G` 看见的东西可以从条件期望里“拿出来”。

## 10. 条件期望作为 L2 投影

在 `L2` 空间中，所有 `G`-可测随机变量构成一个闭子空间：

```text
L2(Omega, G, P) subset L2(Omega, F, P)
```

条件期望：

```text
E[X|G]
```

就是把 `X` 正交投影到这个子空间上。

直观理解：

- `X` 可能依赖完整信息 `F`；
- 但我们只允许使用较少的信息 `G`；
- 在所有只依赖 `G` 的随机变量中，`E[X|G]` 是最接近 `X` 的那个。

这解释了为什么条件期望也可以看成“最佳预测”。

## 11. 鞅：公平游戏的数学表达

设 `(Ft)` 是 filtration，表示随时间增加的信息。过程 `(Xt)` 是 adapted，意思是：

```text
Xt is Ft-measurable
```

即在时刻 `t`，`Xt` 可以由当前信息确定。

鞅定义：

```text
E[Xt | Fs] = Xs,  for s < t
```

这表示：在已知当前信息的情况下，未来的条件平均等于现在。

三类过程：

- martingale：公平游戏；
- super-martingale：平均趋势下降；
- sub-martingale：平均趋势上升。

经典例子：

```text
Xt = E[Z | Ft]
```

这是鞅，因为：

```text
E[Xt | Fs] = E[E[Z|Ft] | Fs] = E[Z|Fs] = Xs
```

## 12. 布朗运动

标准布朗运动 `(Bt)` 满足：

1. `B0 = 0`；
2. 独立增量；
3. 平稳正态增量：

```text
Bt - Bs ~ N(0, t-s)
```

4. 样本路径几乎处处连续。

令：

```text
Ft = sigma(Bs : s <= t)
```

则：

```text
E[Bt | Fs] = Bs
```

所以布朗运动是鞅。

布朗运动的关键矛盾：

- 路径连续，看起来像普通函数；
- 但它的一阶变差几乎处处无穷；
- 它的二次变差却等于时间：

```text
<B,B>_t = t
```

这正是随机积分不能直接用普通 Riemann-Stieltjes 积分定义的原因。

## 13. SDE：随机微分方程

一般形式：

```text
dXt = b(Xt,t) dt + sigma(Xt,t) dWt
```

其中：

- `b(Xt,t) dt` 是 drift term（漂移项）；
- `sigma(Xt,t) dWt` 是 diffusion term（扩散项）。

严格理解要写成积分形式：

```text
Xt = X0
   + integral_0^t b(Xs,s) ds
   + integral_0^t sigma(Xs,s) dWs
```

难点在最后一项：如何定义对布朗运动的积分？

普通 Riemann-Stieltjes 积分要求积分器有有界变差，但布朗运动一阶变差无穷，所以需要新的定义。

## 14. Ito 积分

在分割区间 `[tj, t_{j+1}]` 时，可以选左端点、右端点或中点：

```text
sum sigma(Xtj,tj) (W_{t_{j+1}} - W_{tj})       left
sum sigma(Xt_{j+1},tj) (W_{t_{j+1}} - W_{tj})  right
sum sigma(Xmid,tmid) (W_{t_{j+1}} - W_{tj})    midpoint
```

Ito 积分选择 **左端点**。

原因很重要：左端点只使用当前及过去信息，不使用未来信息。这与 adapted process 的思想一致。

因此：

```text
integral_0^t sigma(Xs,s) dWs
```

就是左端点和的极限。

## 15. 生成式建模中的 SDE 视角

生成式学习可以理解为分布学习：

- 数据样本来自未知分布 `p0`；
- 我们希望学习一个近似分布 `p_hat`；
- 然后从中生成新样本。

扩散模型/SDE 视角：

1. 正向过程：把复杂数据分布逐渐推向简单分布，例如高斯；
2. 反向过程：从简单分布出发，沿反向 SDE 回到数据分布。

正向 SDE：

```text
dXt = f(Xt,t) dt + g(t) dWt
```

反向 SDE 中会出现 score：

```text
grad_x log pt(Xt)
```

如果终点 `pT` 接近高斯，那么采样就容易：先从高斯采样，再运行反向过程得到数据样本。

## 16. 自测题

1. 为什么 `X` 与 `Y` 独立，不代表给定 `Z` 后仍独立？
2. `lim sup An` 为什么对应 “infinitely often”？
3. Borel-Cantelli 第二引理为什么需要相互独立？
4. 为什么 `E[X|G]` 必须是 `G`-可测的？
5. 条件期望为什么可以看成分块平均？
6. tower property 的直观含义是什么？
7. 为什么布朗运动不能直接作为普通 Riemann-Stieltjes 积分的积分器？
8. Ito 积分为什么选左端点？
9. SDE 中 drift 和 diffusion 分别控制什么？
10. 扩散模型为什么希望把数据分布推向高斯分布？

