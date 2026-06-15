# Review_of_math5 中文精讲版

> 对应原文件：`Review_of_math5.pdf`  
> 定位：这是“补充证明”课件的中文学习资料。重点不是逐字翻译，而是把证明背后的数学结构讲清楚：对象是什么、结论为什么合理、证明通常从哪里下手。

## 1. 这份资料在补什么

这份 review 覆盖的主题很杂，但可以分成五条主线：

1. 线性代数：SVD、最佳低秩近似、条件数、核范数；
2. 矩阵微积分：Frechet 导数、矩阵函数求导、`log det`；
3. 凸分析：凸集、凸函数、强凸、保凸操作；
4. 非光滑优化：次梯度、normal cone、Fermat rule、prox；
5. 对偶与约束优化：Fenchel 共轭、线性规划对偶、KKT、约束资格条件。

学习时建议把它当作“机器学习理论课的数学工具箱”。

## 2. 矩阵内积与范数

矩阵空间 `R^{m x n}` 上常用 Frobenius 内积：

```text
<X,Y> = tr(X^T Y) = sum_{i,j} X_ij Y_ij
```

对应 Frobenius 范数：

```text
||X||_F = sqrt(<X,X>)
```

它把矩阵当作长向量来度量大小。

矩阵分析中最常见的三类范数：

- operator norm / spectral norm：最大奇异值；
- Frobenius norm：奇异值平方和再开根；
- nuclear norm：奇异值之和。

如果 `sigma(A) = (sigma_1,...,sigma_r)` 是奇异值向量，那么 Schatten `q` 范数是：

```text
||A||_q = ||sigma(A)||_q
```

特别地：

```text
||A||_2 = sigma_1
||A||_F = sqrt(sum sigma_i^2)
||A||_* = sum sigma_i
```

## 3. SVD 与最佳低秩近似

SVD 分解：

```text
A = U Sigma V^T
```

如果奇异值按降序排列：

```text
sigma_1 >= sigma_2 >= ... >= sigma_r > 0
```

那么秩为 `q` 的截断矩阵：

```text
A_q = sum_{i=1}^q sigma_i u_i v_i^T
```

是最好的 `rank <= q` 近似。

在谱范数下：

```text
min_{rank(B)<=q} ||A-B||_2 = sigma_{q+1}
```

在 Frobenius 范数下：

```text
min_{rank(B)<=q} ||A-B||_F
= sqrt(sum_{i>q} sigma_i^2)
```

直观理解：

SVD 把矩阵拆成一组互相正交的“能量方向”。最大的奇异值对应最重要的方向。做低秩近似时，保留前 `q` 个方向就是最优压缩。

这就是 PCA、图像压缩、低维编码器和线性表示学习的数学基础。

## 4. 最佳线性编码器和解码器

课件中的 homework corollary 可以理解为：

给定高维数据 `x_i in R^d`，想找：

```text
E in R^{s x d}
D in R^{d x s}
```

其中 `s << d`，使得：

```text
D E x_i ≈ x_i
```

`E` 是 encoder，把高维数据压到低维；`D` 是 decoder，把低维表示还原。

如果使用平方误差，最优线性压缩本质上由数据矩阵的前 `s` 个主方向给出。这就是 PCA 的线性自编码器解释。

## 5. 条件数

对可逆矩阵 `A`，条件数：

```text
Cond(A) = ||A|| ||A^{-1}||
```

在谱范数下：

```text
Cond(A) = sigma_max(A) / sigma_min(A)
```

它衡量线性系统：

```text
Ax = b
```

对扰动的敏感程度。

如果条件数大，说明某些方向被 `A` 压得很扁，反解时微小噪声会被放大。机器学习里这会导致优化不稳定、数值误差放大、梯度下降收敛变慢。

## 6. 核范数为什么重要

rank 是非凸的：

```text
rank(A)
```

直接优化很难。核范数：

```text
||A||_* = sum sigma_i(A)
```

是矩阵秩常用的凸替代。

它和向量里的 `l1` 范数类似：

- `l0` 表示非零元素个数，非凸；
- `l1` 是稀疏性的凸替代；
- rank 表示非零奇异值个数，非凸；
- nuclear norm 是低秩性的凸替代。

常见变分表示：

```text
||Z||_* = min_{Z=LR^T} 1/2 (||L||_F^2 + ||R||_F^2)
```

这说明核范数可以通过矩阵分解形式理解，也常用于低秩矩阵恢复。

## 7. 矩阵函数的 Frechet 导数

对函数：

```text
f : R^{m x n} -> R
```

在点 `X` 可微，意思是存在矩阵 `G`，使得：

```text
f(X+H) - f(X) = <G,H> + o(||H||)
```

这个 `G` 就是梯度：

```text
grad f(X) = G
```

矩阵求导最稳的方法是：

1. 写出扰动 `X -> X + H`；
2. 保留一阶项；
3. 把一阶项整理成 `<G,H>`；
4. 读出 `G`。

### 例子：`log det X`

若 `X` 是正定矩阵：

```text
f(X) = log det X
```

利用：

```text
d log det X = tr(X^{-1} dX)
```

得到：

```text
grad f(X) = X^{-T}
```

若 `X` 对称正定，则就是 `X^{-1}`。

## 8. 凸集

集合 `C` 是凸的，如果：

```text
x,y in C, theta in [0,1]
=> theta x + (1-theta)y in C
```

也就是任意两点连线仍在集合里。

常见凸集：

- 超平面；
- 半空间；
- 范数球；
- 椭球；
- PSD cone；
- 多面体。

锥 cone 的特点是：

```text
x in C, t >= 0 => tx in C
```

如果同时凸，就是凸锥。

## 9. 凸函数

函数 `f` 是凸的，如果：

```text
f(theta x + (1-theta)y)
<= theta f(x) + (1-theta) f(y)
```

几何意义：函数图像下方没有“凹进去”的地方。

等价地，epigraph 是凸集：

```text
epi(f) = {(x,t) : f(x) <= t}
```

如果 `f` 可微，凸性等价于一阶条件：

```text
f(y) >= f(x) + <grad f(x), y-x>
```

这句话非常重要：凸函数永远在任意切平面之上。

如果二阶可微，则：

```text
f convex <=> Hessian f(x) positive semidefinite
```

## 10. 强凸函数

`f` 是 `m`-strongly convex，如果：

```text
f(y) >= f(x) + <grad f(x), y-x> + m/2 ||y-x||^2
```

强凸比凸多了一个二次增长项。

好处：

- 最优解唯一；
- 离最优点越远函数值越高；
- 梯度下降可以得到更快收敛率。

常用技巧：如果 `f` 是 `m`-strongly convex，则：

```text
g(x) = f(x) - m/2 ||x||^2
```

是凸函数。很多强凸证明可以转化为普通凸函数证明。

## 11. 保凸操作

常见保凸操作：

- 非负加权和；
- 仿射变换复合；
- pointwise supremum；
- perspective transform；
- 与单调凸函数复合。

例如：

```text
f(x) = h(g(x))
```

若 `h` 凸且对每个坐标单调非减，`g_i` 凸，则 `f` 凸。

学习这部分要记住：很多复杂目标函数的凸性不是直接验证 Hessian，而是用保凸规则搭出来。

## 12. 光滑凸函数与 co-coercivity

若 `f` 凸且梯度 Lipschitz：

```text
||grad f(x) - grad f(y)|| <= L ||x-y||
```

则 Baillon-Haddad 定理给出：

```text
<grad f(x)-grad f(y), x-y>
>= 1/L ||grad f(x)-grad f(y)||^2
```

这叫 co-coercivity。

它在梯度下降分析中非常常用，因为它把“梯度差”和“点差”联系起来。

## 13. 次梯度和次微分

对凸函数 `f`，向量 `g` 是 `x` 处的次梯度，如果：

```text
f(y) >= f(x) + <g, y-x>, for all y
```

所有次梯度构成集合：

```text
partial f(x)
```

如果 `f` 可微，则：

```text
partial f(x) = {grad f(x)}
```

如果不可微，次微分可能是一个集合。

例子：

```text
f(x) = |x|
```

则：

```text
partial |x| =
{1}, x>0
[-1,1], x=0
{-1}, x<0
```

## 14. Normal cone 与指示函数

集合 `C` 的指示函数：

```text
I_C(x) = 0, x in C
       = +infinity, x notin C
```

其次微分为 normal cone：

```text
partial I_C(x) = N_C(x), x in C
```

其中：

```text
N_C(x) = {g : <g, y-x> <= 0, for all y in C}
```

这把约束优化：

```text
min f(x), x in C
```

改写成无约束形式：

```text
min f(x) + I_C(x)
```

然后最优性条件变为：

```text
0 in partial f(x*) + N_C(x*)
```

## 15. Fermat 法则

凸函数最优点满足：

```text
x* minimizes f <=> 0 in partial f(x*)
```

如果可微，这退化为：

```text
grad f(x*) = 0
```

这就是非光滑优化的一阶最优性条件。

## 16. Prox 与 soft-thresholding

课件里出现：

```text
min_x 1/2 (x-t)^2 + lambda |x|
```

这是 `l1` 正则的近端算子。解是 soft-thresholding：

```text
prox_{lambda |.|}(t)
= sign(t) max(|t|-lambda, 0)
```

中文解释：

- 如果 `t` 很小，直接压到 0；
- 如果 `t` 大于阈值，往 0 方向缩小 `lambda`。

这解释了为什么 `l1` 正则会产生稀疏解。

## 17. Bregman divergence

给定严格凸可微函数 `f`，Bregman divergence 定义为：

```text
D_f(x,z) = f(x) - f(z) - <grad f(z), x-z>
```

它表示 `f` 在 `z` 处的一阶线性近似低估 `f(x)` 的误差。

注意它不是普通距离：

- 一般不对称；
- 不一定满足三角不等式。

但它非常适合凸优化和信息几何。

例子：

```text
f(x) = sum x_i log x_i
```

对应的 Bregman divergence 是 KL divergence。

## 18. Bregman 投影与广义勾股定理

Bregman 投影：

```text
Pi_C^f(z) = argmin_{x in C} D_f(x,z)
```

它是普通欧氏投影的推广。

广义勾股不等式大致表达：

```text
D_f(x,z) >= D_f(x,Pi) + D_f(Pi,z)
```

其中 `Pi` 是 `z` 到凸集 `C` 的 Bregman 投影。

这在镜像下降和约束优化中很重要。

## 19. Legendre-Fenchel 共轭

Fenchel 共轭：

```text
f*(y) = sup_x { <y,x> - f(x) }
```

它把函数 `f` 转换到“斜率/对偶变量”空间。

直观理解：`f*(y)` 衡量斜率为 `y` 的线性函数最多能超过 `f` 多少。

常见例子：

如果：

```text
f(x) = ||x||
```

则：

```text
f*(y) = I_{||y||_* <= 1}(y)
```

也就是说，范数的共轭是对偶范数单位球的指示函数。

如果 `f` 是闭凸函数，则：

```text
f** = f
```

这就是双共轭定理。

## 20. Quasi-convex 与 log-concave

quasi-convex 函数要求所有 sublevel set 凸：

```text
S_alpha = {x : f(x) <= alpha}
```

都是凸集。

它比凸函数弱：函数值本身不一定满足 Jensen 型不等式，但低于某个水平的区域是凸的。

log-concave 函数满足：

```text
log f is concave
```

很多概率密度是 log-concave，例如高斯分布。log-concavity 在采样、优化和统计学习中都很重要。

## 21. 线性规划与对偶

线性规划 primal 通常形如：

```text
min c^T x
s.t. Ax = b
     x >= 0
```

对偶问题通过 Lagrangian 构造。

核心关系：

```text
dual optimum <= primal optimum
```

叫弱对偶。

在适当条件下：

```text
dual optimum = primal optimum
```

叫强对偶。

## 22. KKT 条件

约束优化：

```text
min f(x)
s.t. c_i(x) <= 0
     h_j(x) = 0
```

KKT 条件包括：

1. primal feasibility：

```text
c_i(x*) <= 0, h_j(x*) = 0
```

2. dual feasibility：

```text
lambda_i >= 0
```

3. stationarity：

```text
grad f(x*) + sum lambda_i grad c_i(x*) + sum nu_j grad h_j(x*) = 0
```

4. complementary slackness：

```text
lambda_i c_i(x*) = 0
```

对凸优化问题，在合适的 constraint qualification 下，KKT 条件通常是最优性的充要条件。

## 23. 约束资格条件

为什么需要 constraint qualification？

因为没有正则性条件时，KKT 乘子可能不存在，即使点是最优解。

常见条件包括：

- Slater condition；
- LICQ；
- MFCQ；
- tangent cone 与 linearized cone 的关系。

直观理解：约束边界不能太病态，否则线性化的一阶信息无法正确描述可行方向。

## 24. 总结表

| 主题 | 要掌握的核心 |
|---|---|
| SVD | 矩阵的正交方向分解 |
| 低秩近似 | 保留最大奇异值最优 |
| 条件数 | 扰动敏感性 |
| 核范数 | rank 的凸替代 |
| Frechet 导数 | 一阶扰动写成内积 |
| 凸函数 | 切平面全局低估 |
| 强凸 | 唯一解与二次增长 |
| 次梯度 | 非光滑的一阶工具 |
| Bregman | 凸函数线性化误差 |
| Fenchel 共轭 | 对偶空间表示 |
| KKT | 约束优化一阶条件 |

## 25. 自测题

1. 为什么截断 SVD 是最佳低秩近似？
2. 条件数大为什么代表问题病态？
3. 核范数为什么可以看作 rank 的凸替代？
4. 矩阵函数求梯度时，为什么要整理成 `<G,H>`？
5. 凸函数的一阶条件是什么意思？
6. 强凸比普通凸多了什么？
7. 次梯度和梯度有什么关系？
8. 为什么 `partial I_C(x) = N_C(x)`？
9. soft-thresholding 为什么会产生稀疏性？
10. Fenchel 共轭的几何意义是什么？
11. KKT 条件的四部分分别代表什么？
12. 为什么约束优化需要 constraint qualification？

