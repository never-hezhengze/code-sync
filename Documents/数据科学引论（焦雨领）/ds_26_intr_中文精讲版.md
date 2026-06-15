# ds_26_intr 中文精讲版

> 对应原文件：`ds_26_intr.pdf`  
> 定位：这是《数据科学引论》主讲义的中文学习资料。它不是逐页导读，而是按知识模块重写的复习讲义，帮助你理解课程主线、核心概念、公式意义和各章节之间的关系。

## 0. 课程主线

这门课表面上包含很多内容：线性模型、监督学习、表示学习、生成模型、扩散模型、概率论、凸优化、Transformer 等。但它们可以统一成一个问题：

> 给定有限样本，我们如何学习未知的数据规律，并控制误差？

围绕这个问题，课程可以分成四层：

1. **统计层**：总体风险、经验风险、泛化误差、极小极大下界；
2. **优化层**：梯度下降、近端梯度、SGD、KKT；
3. **模型层**：线性模型、SVM、神经网络、表示学习；
4. **生成层**：GAN、扩散模型、Langevin、Follmer flow、Schrodinger Bridge。

学习时不要把每个公式当孤立公式。要问：

- 它是在控制误差吗？
- 它是在证明泛化吗？
- 它是在说明模型表达能力吗？
- 它是在描述分布如何演化吗？

## 1. 监督学习的基本设定

监督学习中有输入 `X` 和输出 `Y`。数据来自未知分布：

```text
(X,Y) ~ P
```

我们有训练样本：

```text
D_n = {(X_i,Y_i)}_{i=1}^n
```

目标是学习一个函数：

```text
f : X -> Y
```

使预测损失尽量小。

总体风险：

```text
L(f) = E[ loss(f(X),Y) ]
```

经验风险：

```text
L_n(f) = 1/n sum_i loss(f(X_i),Y_i)
```

总体风险是真正想最小化的量，但它依赖未知分布，不能直接计算。经验风险是训练时可计算的替代。

经验风险最小化：

```text
f_hat = argmin_{f in F} L_n(f)
```

其中 `F` 是模型类。

## 2. 误差分解

学习理论的核心是误差分解。一个常见形式是：

```text
L(f_hat) - L(f*)
= estimation error
 + approximation error
 + optimization error
```

### 逼近误差

模型类 `F` 不一定包含真实目标函数 `f*`。即使无限数据、完美优化，也只能找到 `F` 里最好的函数。

```text
inf_{f in F} L(f) - L(f*)
```

这叫 approximation error。

模型类越大，逼近误差通常越小。

### 估计误差

我们只能用有限样本训练，所以经验风险与总体风险有偏差。

```text
L(f_hat) - inf_{f in F} L(f)
```

这与样本量、函数类复杂度、噪声有关。

模型类越大，估计误差通常越大。

### 优化误差

实际算法可能没有找到经验风险最小点。例如梯度下降只跑有限步。

```text
L_n(f_algorithm) - inf_{f in F} L_n(f)
```

这与优化算法、步长、光滑性、凸性有关。

学习重点：模型复杂度要平衡逼近误差和估计误差。这就是统计学习的 bias-variance tradeoff。

## 3. 线性回归与最小二乘

固定设计线性回归：

```text
Y = X beta + epsilon
```

普通最小二乘：

```text
beta_hat = argmin_beta ||Y - X beta||_2^2
```

若 `X^T X` 可逆：

```text
beta_hat = (X^T X)^{-1} X^T Y
```

几何理解：`X beta_hat` 是 `Y` 在列空间 `col(X)` 上的正交投影。

误差来源：

- 噪声 `epsilon`；
- 设计矩阵条件数；
- 特征维度与样本量关系。

## 4. 正则化最小二乘

当特征维度高、矩阵病态或样本少时，普通最小二乘不稳定。正则化通过惩罚模型复杂度改善稳定性。

Ridge regression：

```text
min_beta ||Y-X beta||_2^2 + lambda ||beta||_2^2
```

解为：

```text
beta_hat_lambda = (X^T X + lambda I)^{-1} X^T Y
```

`lambda` 的作用：

- 增大矩阵最小特征值；
- 降低方差；
- 引入偏差。

这体现了 bias-variance tradeoff：

- `lambda` 太小：方差大，过拟合；
- `lambda` 太大：偏差大，欠拟合。

Lasso：

```text
min_beta ||Y-X beta||_2^2 + lambda ||beta||_1
```

`l1` 正则会产生稀疏解，适合高维变量选择。

## 5. 泛化误差与经验过程

泛化分析通常要控制：

```text
sup_{f in F} | L(f) - L_n(f) |
```

这叫 uniform deviation。

如果这个量小，那么经验风险小的函数总体风险也不会太差。

挑战在于：`F` 可能非常大，不能只对单个函数使用大数定律。

## 6. Rademacher 复杂度

Rademacher 变量：

```text
epsilon_i = +1 or -1 with probability 1/2
```

Rademacher 复杂度衡量函数类拟合随机噪声的能力：

```text
R_n(F) = E sup_{f in F} 1/n sum_i epsilon_i f(X_i)
```

直观理解：

- 如果函数类能很好拟合随机符号，说明它太灵活，容易过拟合；
- 如果拟合不了随机噪声，复杂度较低，泛化更好。

泛化界通常形如：

```text
sup_{f in F} |L(f)-L_n(f)| <= complexity(F,n)
```

Rademacher 复杂度就是这个 complexity 的一种表达。

## 7. Symmetrization

symmetrization 用 ghost sample 把总体-经验差转化成两个经验样本之间的差。

思路：

```text
P f - P_n f
```

不好处理，因为 `P` 是未知总体。引入独立样本 `X'_i` 后：

```text
P f ≈ P'_n f
```

于是：

```text
P f - P_n f
≈ P'_n f - P_n f
```

再引入 Rademacher 符号，把差值随机对称化。

这一步是经验过程理论里非常核心的技巧。

## 8. Dudley 熵积分

函数类复杂度也可以通过覆盖数衡量。

覆盖数：

```text
N(F, d, epsilon)
```

表示用半径 `epsilon` 的球覆盖函数类 `F` 至少需要多少个球。

Dudley entropy integral 把 Rademacher 复杂度与覆盖数联系起来：

```text
R_n(F) roughly <= integral sqrt(log N(F,epsilon)) d epsilon
```

直观理解：

- 覆盖数越大，函数类越复杂；
- 熵积分越大，泛化越难。

## 9. 近似误差与神经网络表达能力

在非参数回归中，目标函数 `f*` 可能属于 Holder 类：

```text
H^zeta
```

`zeta` 表示光滑度。

神经网络逼近理论研究：

> 给定光滑度和维度，ReLU 网络需要多宽、多深，才能把目标函数逼近到某个精度？

常见证明思路：

1. 用 Taylor 展开局部近似光滑函数；
2. 用分片线性函数逼近多项式或局部结构；
3. 用 ReLU 网络实现这些分片结构；
4. 合并得到全局误差界。

逼近误差越小，说明模型类表达能力越强。

## 10. 梯度下降

对光滑函数 `f`，梯度下降：

```text
x_{k+1} = x_k - alpha grad f(x_k)
```

如果 `grad f` 是 `L`-Lipschitz，常用步长：

```text
alpha <= 1/L
```

下降引理：

```text
f(x_{k+1}) <= f(x_k) - c ||grad f(x_k)||^2
```

不同假设下结论不同：

- 非凸：通常保证梯度范数变小；
- 凸：函数值次线性收敛；
- 强凸：函数值线性收敛。

## 11. 近端梯度下降

当目标函数：

```text
F(x) = f(x) + h(x)
```

其中 `f` 光滑，`h` 非光滑但凸时，使用 proximal gradient：

```text
x_{k+1}
= prox_{alpha h}( x_k - alpha grad f(x_k) )
```

近端算子：

```text
prox_{alpha h}(z)
= argmin_x 1/(2 alpha)||x-z||^2 + h(x)
```

它把梯度步和非光滑正则项处理分开。

例子：`h(x)=lambda ||x||_1` 时，prox 是 soft-thresholding。

## 12. SGD 与方差缩减

SGD 使用随机梯度：

```text
x_{k+1} = x_k - alpha_k g(x_k,xi_k)
```

要求通常是：

```text
E[g(x,xi)] = grad f(x)
```

即无偏。

SGD 的难点是方差：

```text
E||g - grad f||^2
```

方差越大，收敛越抖。方差缩减方法如 SVRG/SAGA 的思想是：用控制变量减少随机梯度噪声。

## 13. 极小极大下界

上界告诉我们某个算法能做到多好；下界告诉我们任何算法都不可能突破什么限制。

极小极大风险：

```text
inf_estimator sup_{P in class} risk(estimator, P)
```

含义：

- 先考虑最好的估计器；
- 再考虑最坏的数据分布；
- 得到问题本身的难度。

常用证明工具包括：

- KL divergence；
- testing reduction；
- Fano / Le Cam；
- packing number。

学习重点：下界不是分析某个算法，而是证明所有算法都不能比某个速率更快。

## 14. 二分类与风险

二分类中：

```text
Y in {0,1} or {-1,+1}
```

Bayes classifier：

```text
f*(x) = 1_{eta(x) >= 1/2}
```

其中：

```text
eta(x) = P(Y=1 | X=x)
```

0-1 loss 不可凸、不易优化，因此实际训练常用 surrogate loss。

常见 surrogate：

- hinge loss；
- logistic loss；
- exponential loss；
- square loss。

关键问题：优化 surrogate loss 是否能带来分类风险下降？

## 15. Plug-in estimator

plug-in 方法先估计：

```text
eta(x) = P(Y=1|X=x)
```

再代入 Bayes rule：

```text
f_hat(x) = 1_{eta_hat(x) >= 1/2}
```

优点：思路清楚。

缺点：如果 `eta(x)` 在 `1/2` 附近很难估计，分类边界会不稳定。

## 16. SVM

线性可分数据中，SVM 寻找最大间隔超平面：

```text
y_i (w^T x_i + b) >= 1
```

最大间隔等价于最小化：

```text
1/2 ||w||^2
```

软间隔 SVM：

```text
min 1/2 ||w||^2 + C sum xi_i
s.t. y_i(w^T x_i+b) >= 1 - xi_i
     xi_i >= 0
```

等价于带正则的 hinge loss：

```text
sum max(0, 1 - y_i f(x_i)) + regularization
```

支持向量来自 KKT 条件：只有间隔边界上或违反间隔的样本对应非零对偶变量。

## 17. Kernel 与 RKHS

核方法把内积：

```text
<phi(x), phi(x')>
```

写成核函数：

```text
k(x,x')
```

这样无需显式构造高维特征映射。

RKHS 是带 reproducing property 的 Hilbert 函数空间：

```text
f(x) = <f, k(x,.)>_H
```

在 RKHS 中训练 SVM/正则化最小二乘，可以使用 representer theorem：最优解可写成训练样本核函数的线性组合。

## 18. 表示学习

传统浅层模型依赖人工特征。表示学习希望自动学习：

```text
z = encoder(x)
```

使 `z` 更适合下游任务。

好的表示应当：

- 保留任务相关信息；
- 去掉无关变化；
- 降低维度或组织数据结构；
- 改善泛化和样本效率。

## 19. 监督表示学习与充分降维

监督表示学习可以从 sufficient dimension reduction 角度理解：

希望找到低维表示 `Z = phi(X)`，使得：

```text
Y independent of X given Z
```

也就是说，`Z` 已经包含预测 `Y` 所需的全部信息。

这比单纯降维更强：降维不能丢掉和标签有关的信息。

## 20. 自监督学习与对比学习

自监督学习不依赖人工标签，而是从数据本身构造训练信号。

对比学习基本思想：

- 正样本对：应该靠近；
- 负样本对：应该远离。

SimCLR、MoCo 等方法都属于这类。

对比学习的核心是让 encoder 学到语义上稳定的表示，而不是记住像素细节。

## 21. 生成式学习

生成式学习的目标是学习数据分布：

```text
X_1,...,X_n ~ nu
```

并生成新样本：

```text
X_new ~ nu_hat approx nu
```

判别式学习关注 `Y|X`，生成式学习关注 `X` 的分布本身。

主要路线：

- VAE；
- GAN；
- flow-based model；
- diffusion model；
- score-based model；
- Schrodinger Bridge；
- Follmer flow。

## 22. GAN

GAN 包含 generator 和 discriminator。

Generator：

```text
Z ~ mu
g(Z) ~ generated distribution
```

Discriminator 尝图区分真实样本和生成样本。

理论上，GAN 可以被理解为最小化某种分布距离。课件中提到 IPM：

```text
d_F(P,Q) = sup_{f in F} | E_P f - E_Q f |
```

其中 `F` 是判别器函数类。

GAN 的难点：

- 训练不稳定；
- mode collapse；
- 理论距离和实际神经网络训练之间有差距。

## 23. Diffusion / Score-based model

扩散模型的思想：

1. 正向过程逐步加噪，把数据分布变成简单分布；
2. 学习反向去噪过程；
3. 从噪声出发生成样本。

连续时间写法常用 SDE：

```text
dXt = f(Xt,t)dt + g(t)dWt
```

反向 SDE 会出现 score：

```text
grad_x log p_t(x)
```

score matching 的目标是学习：

```text
s_theta(x,t) approx grad_x log p_t(x)
```

一旦 score 学得好，就可以模拟反向过程生成数据。

## 24. Langevin 与 score matching

如果知道目标密度 `p(x)` 的 score：

```text
grad log p(x)
```

可以用 Langevin 采样：

```text
X_{k+1} = X_k + gamma grad log p(X_k) + sqrt(2 gamma) xi_k
```

实际中 `p` 未知，所以学习 score。

Stein lemma 和 score matching 提供了不用知道归一化常数也能学习 score 的方法。

## 25. Schrodinger Bridge

Schrodinger Bridge 可以理解为在给定初始分布和终端分布之间，寻找最可能的随机路径。

它和最优传输、扩散模型都有联系。

在图像复原中，给定退化图像和目标清晰图像分布，可以通过 bridge 学习从退化状态到清晰状态的随机变换。

## 26. Follmer flow

Follmer flow 通过构造一个从简单分布到目标分布的连续流来实现采样。

直观上：

```text
Z ~ Gaussian
X_t = transform_t(Z)
X_1 ~ target distribution
```

课程中把它用于 generative learning，尤其是讨论 one-step sampling 和 latent-space extension。

学习重点：它和 diffusion 都是在构造从简单分布到复杂分布的路径，只是技术路线不同。

## 27. 分布匹配与不确定性量化

分布匹配的目标是让生成分布接近真实分布。

不确定性量化则更关注条件分布：

```text
nu(. | X=x)
```

也就是给定输入后，输出不是一个点估计，而是一个分布。

这在预测任务中很重要，因为真实世界存在噪声和多解性。

## 28. Transformer 与 LLM 误差分析

Transformer 是现代深度学习的核心结构。主讲义后半部分讨论 LLM 的逼近、非参数回归、预训练和 in-context learning。

可以用统计学习语言理解：

- 预训练：从大规模序列中学习潜在结构；
- 下游任务：利用表示或上下文完成预测；
- ICL：模型从上下文样例中推断隐藏任务或 latent concept。

误差分析仍然遵循老问题：

```text
approximation error
estimation error
optimization / algorithmic error
```

只是模型类变成了 Transformer，数据结构变成了序列和上下文。

## 29. 前置数学：范数、SVD、凸优化

主讲义最后还回顾了许多数学工具。

### 范数

范数衡量向量大小：

```text
||x||_q = (sum |x_i|^q)^{1/q}
```

常见：

- `l1`：稀疏；
- `l2`：欧氏距离；
- `l_infinity`：最大坐标。

### SVD

```text
A = U Sigma V^T
```

用于低秩近似、PCA、图像压缩、线性系统稳定性分析。

### 凸优化

凸优化的优势是局部最优就是全局最优。

核心工具：

- 一阶条件；
- 次梯度；
- Fenchel 共轭；
- KKT；
- 对偶理论。

## 30. 前置概率：从事件到浓缩不等式

概率论部分从：

```text
(Omega, F, P)
```

开始。

随机变量是可测函数：

```text
X : Omega -> R
```

基础量：

```text
E[X]
Var(X)
M_X(t)=E[e^{tX}]
```

学习理论中非常重要的是尾界。

sub-Gaussian 随机变量具有类似高斯的尾部：

```text
P(|X-EX| > t) <= exp(-c t^2)
```

sub-exponential 随机变量尾部更重：

```text
P(|X-EX| > t) <= exp(-c min(t^2,t))
```

Hoeffding、Bernstein、McDiarmid 等浓缩不等式用于控制经验均值偏离总体均值。

## 31. 如何复习这门课

建议按下面顺序复习：

1. 先掌握监督学习设定：总体风险、经验风险、ERM；
2. 理解误差分解：逼近、估计、优化；
3. 学泛化工具：Rademacher、covering number、Dudley；
4. 学优化算法：GD、prox-GD、SGD；
5. 学分类模型：Bayes classifier、surrogate loss、SVM；
6. 学表示学习：encoder、SSL、contrastive learning；
7. 学生成模型：GAN、diffusion、score、Langevin；
8. 回头补数学：SVD、凸优化、概率不等式。

## 32. 关键公式速查

```text
L(f) = E loss(f(X),Y)
L_n(f) = 1/n sum loss(f(X_i),Y_i)
```

```text
f_hat = argmin_{f in F} L_n(f)
```

```text
generalization gap = sup_{f in F} |L(f)-L_n(f)|
```

```text
R_n(F) = E sup_{f in F} 1/n sum epsilon_i f(X_i)
```

```text
beta_hat = (X^T X)^{-1} X^T Y
```

```text
ridge: beta_hat = (X^T X + lambda I)^{-1} X^T Y
```

```text
GD: x_{k+1} = x_k - alpha grad f(x_k)
```

```text
prox: prox_h(z)=argmin_x 1/2||x-z||^2+h(x)
```

```text
SVM: min 1/2||w||^2 + C sum xi_i
```

```text
IPM: d_F(P,Q)=sup_{f in F}|E_P f - E_Q f|
```

```text
Langevin: X_{k+1}=X_k+gamma grad log p(X_k)+sqrt(2gamma)xi_k
```

## 33. 自测题

1. 总体风险和经验风险的区别是什么？
2. 为什么需要 uniform convergence，而不是只对单个函数用大数定律？
3. 逼近误差和估计误差为什么存在 tradeoff？
4. Ridge regression 中 `lambda` 增大分别如何影响 bias 和 variance？
5. Rademacher 复杂度为什么能衡量过拟合能力？
6. Dudley 熵积分中的覆盖数代表什么？
7. 非参数回归中的 Holder 光滑度影响什么？
8. 梯度下降在非凸、凸、强凸情形下分别能保证什么？
9. 近端梯度为什么适合 `f+h` 且 `h` 非光滑的问题？
10. SVM 的支持向量为什么由 KKT 条件决定？
11. 表示学习和普通特征工程有什么区别？
12. 对比学习为什么需要正样本和负样本？
13. GAN 中 discriminator 对应什么分布距离思想？
14. 扩散模型为什么需要学习 score？
15. Langevin 动力学为什么可以用于采样？
16. LLM 误差分析和传统监督学习误差分析有什么共同结构？

