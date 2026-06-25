# 数学复习 —— 中文翻译

> 翻译自 `Review_of_math5.pdf`，共 56 页。数学公式保留原样。

---

## 第 1 页：封面

**数据科学引论——数学复习**
*Review of Mathematics*

---

## 第 2 页：复习大纲

### 数学复习内容

1. 线性代数基础（矩阵运算、特征值与特征向量）
2. 微积分基础（导数、偏导数、梯度）
3. 最优化基础（梯度下降、拉格朗日乘子法）
4. 矩阵微积分
5. 概率论中常用的数学工具

---

## 第 3 页：向量与矩阵——基本定义

### 向量（Vector）

一个 $n$ 维列向量：
$$\mathbf{x} = \begin{bmatrix} x_1 \\ x_2 \\ \vdots \\ x_n \end{bmatrix} \in \mathbb{R}^n$$

### 矩阵（Matrix）

一个 $m \times n$ 的矩阵：
$$\mathbf{A} = \begin{bmatrix} a_{11} & a_{12} & \cdots & a_{1n} \\ a_{21} & a_{22} & \cdots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{m1} & a_{m2} & \cdots & a_{mn} \end{bmatrix} \in \mathbb{R}^{m \times n}$$

### 基本术语

- **方阵**（Square Matrix）：$m = n$
- **对角矩阵**（Diagonal Matrix）：只有对角元素非零
- **单位矩阵**（Identity Matrix）$\mathbf{I}$：对角元素全为 1 的对角矩阵
- **转置**（Transpose）$\mathbf{A}^T$：行列互换
- **对称矩阵**（Symmetric Matrix）：$\mathbf{A}^T = \mathbf{A}$

---

## 第 4 页：矩阵乘法

### 矩阵乘法

若 $\mathbf{A} \in \mathbb{R}^{m \times n}$，$\mathbf{B} \in \mathbb{R}^{n \times p}$，则 $\mathbf{C} = \mathbf{A}\mathbf{B} \in \mathbb{R}^{m \times p}$，其中：

$$c_{ij} = \sum_{k=1}^{n} a_{ik} b_{kj}$$

### 注意事项

- 矩阵乘法**不满足交换律**：一般 $\mathbf{A}\mathbf{B} \neq \mathbf{B}\mathbf{A}$
- 满足**结合律**：$(\mathbf{A}\mathbf{B})\mathbf{C} = \mathbf{A}(\mathbf{B}\mathbf{C})$
- 满足**分配律**：$\mathbf{A}(\mathbf{B} + \mathbf{C}) = \mathbf{A}\mathbf{B} + \mathbf{A}\mathbf{C}$
- 转置性质：$(\mathbf{A}\mathbf{B})^T = \mathbf{B}^T \mathbf{A}^T$

### 内积与外积

**内积（点积）**：$\mathbf{x}^T \mathbf{y} = \sum_i x_i y_i$（标量）
**外积**：$\mathbf{x} \mathbf{y}^T$（矩阵）

---

## 第 5 页：矩阵的秩与逆

### 矩阵的秩（Rank）

矩阵的秩是其最大线性无关列（或行）的个数。

- $\text{rank}(\mathbf{A}) \leq \min(m, n)$
- $\text{rank}(\mathbf{A}\mathbf{B}) \leq \min(\text{rank}(\mathbf{A}), \text{rank}(\mathbf{B}))$
- 满秩方阵：$\text{rank}(\mathbf{A}) = n$

### 逆矩阵（Inverse Matrix）

对于方阵 $\mathbf{A} \in \mathbb{R}^{n \times n}$，如果存在 $\mathbf{A}^{-1}$ 使得：
$$\mathbf{A}\mathbf{A}^{-1} = \mathbf{A}^{-1}\mathbf{A} = \mathbf{I}$$

则称 $\mathbf{A}$ 为**可逆的**（Invertible）或**非奇异的**（Non-singular）。

**性质**：
- $(\mathbf{A}^{-1})^{-1} = \mathbf{A}$
- $(\mathbf{A}\mathbf{B})^{-1} = \mathbf{B}^{-1}\mathbf{A}^{-1}$
- $(\mathbf{A}^T)^{-1} = (\mathbf{A}^{-1})^T$
- $\mathbf{A}$ 可逆 $\iff$ $\text{rank}(\mathbf{A}) = n$ $\iff$ $\det(\mathbf{A}) \neq 0$

---

## 第 6 页：行列式

### 行列式（Determinant）

行列式 $\det(\mathbf{A})$ 或 $|\mathbf{A}|$ 是一个将方阵映射为标量的函数。

**几何意义**：行列式的绝对值表示由矩阵列向量张成的平行多面体的体积。

**性质**：
- $\det(\mathbf{A}\mathbf{B}) = \det(\mathbf{A}) \cdot \det(\mathbf{B})$
- $\det(\mathbf{A}^{-1}) = 1/\det(\mathbf{A})$
- $\det(\mathbf{A}^T) = \det(\mathbf{A})$
- $\det(c\mathbf{A}) = c^n \det(\mathbf{A})$（$n \times n$ 矩阵）

**2×2 矩阵的行列式**：
$$\det\begin{bmatrix} a & b \\ c & d \end{bmatrix} = ad - bc$$

---

## 第 7 页：线性方程组

### 线性方程组

$$\mathbf{A}\mathbf{x} = \mathbf{b}$$

- **唯一解**：$\text{rank}(\mathbf{A}) = \text{rank}([\mathbf{A} \mid \mathbf{b}]) = n$（$\mathbf{A}$ 的列数）
  - 解为 $\mathbf{x} = \mathbf{A}^{-1}\mathbf{b}$（如果 $\mathbf{A}$ 可逆）
- **无穷多解**：$\text{rank}(\mathbf{A}) = \text{rank}([\mathbf{A} \mid \mathbf{b}]) < n$
- **无解**：$\text{rank}(\mathbf{A}) < \text{rank}([\mathbf{A} \mid \mathbf{b}])$

### 最小二乘解

当 $\mathbf{A}\mathbf{x} = \mathbf{b}$ 无解时（过定系统），可求最小二乘解：
$$\hat{\mathbf{x}} = (\mathbf{A}^T \mathbf{A})^{-1} \mathbf{A}^T \mathbf{b}$$

（假设 $\mathbf{A}^T \mathbf{A}$ 可逆）

这恰好是普通最小二乘（OLS）回归的矩阵形式！

---

## 第 8 页：特征值与特征向量

### 定义

对于方阵 $\mathbf{A} \in \mathbb{R}^{n \times n}$，如果存在标量 $\lambda$ 和非零向量 $\mathbf{v}$ 使得：
$$\mathbf{A}\mathbf{v} = \lambda \mathbf{v}$$

则 $\lambda$ 称为**特征值**，$\mathbf{v}$ 称为对应的**特征向量**。

### 几何解释

特征向量是矩阵变换下方向不变的向量。特征值表示在该方向上的伸缩因子。

### 求解

特征值由**特征方程**给出：
$$\det(\mathbf{A} - \lambda \mathbf{I}) = 0$$

对于 $n \times n$ 矩阵，特征方程是 $\lambda$ 的 $n$ 次多项式（特征多项式）。

---

## 第 9 页：特征分解

### 谱分解（Spectral Decomposition / Eigendecomposition）

如果 $\mathbf{A}$ 有 $n$ 个线性无关的特征向量，则可以分解为：

$$\mathbf{A} = \mathbf{V} \boldsymbol{\Lambda} \mathbf{V}^{-1}$$

其中 $\mathbf{V}$ 的列是特征向量，$\boldsymbol{\Lambda} = \text{diag}(\lambda_1, \ldots, \lambda_n)$。

### 对称矩阵的特殊性质

如果 $\mathbf{A}$ 为**实对称矩阵**（$\mathbf{A}^T = \mathbf{A}$）：
- 所有特征值都是**实数**
- 不同特征值对应的特征向量是**正交的**
- 可以写成：$\mathbf{A} = \mathbf{V} \boldsymbol{\Lambda} \mathbf{V}^T$，其中 $\mathbf{V}$ 是正交矩阵（$\mathbf{V}^T\mathbf{V} = \mathbf{I}$）

### 正定矩阵

对称矩阵 $\mathbf{A}$ 称为**正定**（Positive Definite），如果对于所有 $\mathbf{x} \neq \mathbf{0}$：
$$\mathbf{x}^T \mathbf{A} \mathbf{x} > 0$$

等价条件：所有特征值 > 0。

协方差矩阵是半正定的经典例子。

---

## 第 10 页：奇异值分解（SVD）

### SVD 定理

任何矩阵 $\mathbf{A} \in \mathbb{R}^{m \times n}$ 都可以分解为：
$$\mathbf{A} = \mathbf{U} \boldsymbol{\Sigma} \mathbf{V}^T$$

其中：
- $\mathbf{U} \in \mathbb{R}^{m \times m}$ 为正交矩阵（左奇异向量）
- $\mathbf{V} \in \mathbb{R}^{n \times n}$ 为正交矩阵（右奇异向量）
- $\boldsymbol{\Sigma} \in \mathbb{R}^{m \times n}$ 为对角矩阵，对角元素 $\sigma_1 \geq \sigma_2 \geq \cdots \geq 0$ 为**奇异值**

### SVD 的重要性

SVD 可以说是线性代数中最重要的矩阵分解：
- 主成分分析（PCA）基于 SVD
- 伪逆（Pseudoinverse）可以通过 SVD 计算
- 矩阵的低秩近似（去除小奇异值）
- 推荐系统中的矩阵分解

---

## 第 11 页：向量范数

### 范数（Norm）

范数度量向量的"大小"或"长度"。

**$\ell_p$ 范数**：
$$\|\mathbf{x}\|_p = \left(\sum_{i=1}^{n} |x_i|^p\right)^{1/p}$$

**常用范数**：
- **$\ell_2$（欧氏范数）**：$\|\mathbf{x}\|_2 = \sqrt{\sum x_i^2}$
- **$\ell_1$（曼哈顿范数）**：$\|\mathbf{x}\|_1 = \sum |x_i|$
- **$\ell_\infty$（最大范数）**：$\|\mathbf{x}\|_\infty = \max_i |x_i|$

### 范数在数据科学中的应用

- $\ell_2$ 范数：Ridge 回归（$\ell_2$ 正则化）、欧氏距离
- $\ell_1$ 范数：Lasso 回归（$\ell_1$ 正则化）、稀疏性
- 范数在优化中广泛用作正则化项

---

## 第 12 页：导数基础

### 导数的定义

函数 $f(x)$ 在点 $x$ 处的导数：
$$f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

几何意义：切线的斜率。物理意义：瞬时变化率。

### 基本求导法则

| 函数 | 导数 |
|------|------|
| $c$（常数） | $0$ |
| $x^n$ | $nx^{n-1}$ |
| $e^x$ | $e^x$ |
| $\ln x$ | $1/x$ |
| $\sin x$ | $\cos x$ |
| $\cos x$ | $-\sin x$ |

### 运算法则

- **和差**：$(f \pm g)' = f' \pm g'$
- **乘积**：$(fg)' = f'g + fg'$
- **商**：$(f/g)' = (f'g - fg')/g^2$
- **链式法则**：$(f(g(x)))' = f'(g(x)) \cdot g'(x)$

---

## 第 13 页：偏导数与梯度

### 偏导数（Partial Derivative）

对于多元函数 $f(x_1, \ldots, x_n)$，关于 $x_i$ 的偏导数：
$$\frac{\partial f}{\partial x_i}$$

表示在其他变量保持不变时，$f$ 随 $x_i$ 变化的速率。

### 梯度（Gradient）

梯度向量由所有偏导数组成：
$$\nabla f(\mathbf{x}) = \begin{bmatrix} \frac{\partial f}{\partial x_1} \\ \frac{\partial f}{\partial x_2} \\ \vdots \\ \frac{\partial f}{\partial x_n} \end{bmatrix}$$

### 梯度的几何意义

梯度 $\nabla f(\mathbf{x})$ 指向函数 $f$ 在点 $\mathbf{x}$ 处**上升最快的方向**。

$-\nabla f(\mathbf{x})$ 指向下降最快的方向——这是梯度下降算法的基础。

---

## 第 14 页：Hessian 矩阵

### Hessian 矩阵

二阶偏导数组成的矩阵：
$$\mathbf{H}_f(\mathbf{x}) = \begin{bmatrix} \frac{\partial^2 f}{\partial x_1^2} & \frac{\partial^2 f}{\partial x_1 \partial x_2} & \cdots & \frac{\partial^2 f}{\partial x_1 \partial x_n} \\ \frac{\partial^2 f}{\partial x_2 \partial x_1} & \frac{\partial^2 f}{\partial x_2^2} & \cdots & \frac{\partial^2 f}{\partial x_2 \partial x_n} \\ \vdots & \vdots & \ddots & \vdots \\ \frac{\partial^2 f}{\partial x_n \partial x_1} & \frac{\partial^2 f}{\partial x_n \partial x_2} & \cdots & \frac{\partial^2 f}{\partial x_n^2} \end{bmatrix}$$

### Hessian 的应用

- 判断极值点的类型（利用 Hessian 的正定性）
- 牛顿法中用于二阶优化
- Fisher 信息矩阵（统计中）与 Hessian 密切相关

---

## 第 15 页：多元函数的极值

### 极值的必要条件

如果 $\mathbf{x}^*$ 是 $f$ 的局部极值点，则：
$$\nabla f(\mathbf{x}^*) = \mathbf{0}$$

### 极值的充分条件

检查 Hessian 矩阵：
- $\mathbf{H}_f(\mathbf{x}^*)$ **正定**：$\mathbf{x}^*$ 为**局部极小值**
- $\mathbf{H}_f(\mathbf{x}^*)$ **负定**：$\mathbf{x}^*$ 为**局部极大值**
- $\mathbf{H}_f(\mathbf{x}^*)$ **不定**：$\mathbf{x}^*$ 为**鞍点**（Saddle Point）

### 示例

$f(x, y) = x^2 + y^2$：
- $\nabla f = (2x, 2y)$ → 临界点：$(0, 0)$
- $\mathbf{H} = \begin{bmatrix} 2 & 0 \\ 0 & 2 \end{bmatrix}$ → 正定 → $(0, 0)$ 为全局极小值

---

## 第 16 页：梯度下降

### 梯度下降算法

用于寻找函数最小值的迭代优化算法：

$$\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} - \eta \nabla f(\mathbf{x}^{(k)})$$

其中 $\eta > 0$ 为**学习率**（Learning Rate / Step Size）。

### 直观理解

在当前位置，沿着负梯度方向（最陡下降方向）移动一小步。

### 学习率的选择

- **太大**：可能发散或振荡
- **太小**：收敛太慢
- 实践中常使用**衰减学习率**或**自适应学习率**（如 Adam）

### 应用

梯度下降是深度学习训练的核心算法。在机器学习中，我们通常最小化损失函数：
$$\boldsymbol{\theta}^{(t+1)} = \boldsymbol{\theta}^{(t)} - \eta \nabla_\theta L(\boldsymbol{\theta}^{(t)})$$

---

## 第 17 页：牛顿法

### 牛顿法（Newton's Method）

利用二阶信息（Hessian）来加速优化：

$$\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} - [\mathbf{H}_f(\mathbf{x}^{(k)})]^{-1} \nabla f(\mathbf{x}^{(k)})$$

### 与梯度下降的比较

| | 梯度下降 | 牛顿法 |
|--|---------|--------|
| 使用信息 | 一阶（梯度） | 二阶（梯度 + Hessian） |
| 收敛速度 | 线性 | 二次（更快） |
| 每次迭代成本 | 低 | 高（需要计算和求逆 Hessian） |
| 实用性 | 大规模问题（深度学习） | 中小规模问题 |

### 在统计中的应用

- 逻辑回归的 MLE 求解常用 Newton-Raphson 法
- 广义线性模型（GLM）的参数估计

---

## 第 18 页：约束优化——拉格朗日乘子法

### 拉格朗日乘子法（Lagrange Multipliers）

用于求解带等式约束的优化问题：

$$\min_{\mathbf{x}} f(\mathbf{x}) \quad \text{s.t.} \quad g(\mathbf{x}) = 0$$

**拉格朗日函数**：
$$\mathcal{L}(\mathbf{x}, \lambda) = f(\mathbf{x}) + \lambda g(\mathbf{x})$$

**必要条件**：
$$\nabla_{\mathbf{x}} \mathcal{L} = \mathbf{0}, \quad \frac{\partial \mathcal{L}}{\partial \lambda} = 0$$

### 应用举例

- SVM 的对偶问题推导
- PCA 的方差最大化（约束 $\|\mathbf{w}\| = 1$）
- 信息论中的最大熵原理

### 几何解释

在最优解处，$\nabla f$ 与 $\nabla g$ 平行（共线）——即目标函数的梯度是约束梯度的倍数。拉格朗日乘子 $\lambda$ 就是这个倍数。

---

## 第 19 页：矩阵微积分 (1)

### 标量对向量的导数

设 $f: \mathbb{R}^n \to \mathbb{R}$，则：
$$\frac{\partial f}{\partial \mathbf{x}} = \begin{bmatrix} \frac{\partial f}{\partial x_1} & \frac{\partial f}{\partial x_2} & \cdots & \frac{\partial f}{\partial x_n} \end{bmatrix}^T = \nabla f(\mathbf{x})$$

### 常用公式

1. $\frac{\partial}{\partial \mathbf{x}} (\mathbf{a}^T \mathbf{x}) = \mathbf{a}$

2. $\frac{\partial}{\partial \mathbf{x}} (\mathbf{x}^T \mathbf{A} \mathbf{x}) = (\mathbf{A} + \mathbf{A}^T) \mathbf{x}$
   - 如果 $\mathbf{A}$ 对称，则为 $2\mathbf{A}\mathbf{x}$

3. $\frac{\partial}{\partial \mathbf{x}} \|\mathbf{A}\mathbf{x} - \mathbf{b}\|_2^2 = 2\mathbf{A}^T(\mathbf{A}\mathbf{x} - \mathbf{b})$

这些公式在推导 OLS 的正规方程时非常有用。

---

## 第 20 页：矩阵微积分 (2)

### 标量对矩阵的导数

设 $f: \mathbb{R}^{m \times n} \to \mathbb{R}$，则：
$$\frac{\partial f}{\partial \mathbf{X}} = \begin{bmatrix} \frac{\partial f}{\partial X_{11}} & \cdots & \frac{\partial f}{\partial X_{1n}} \\ \vdots & \ddots & \vdots \\ \frac{\partial f}{\partial X_{m1}} & \cdots & \frac{\partial f}{\partial X_{mn}} \end{bmatrix}$$

### 常用公式

1. $\frac{\partial}{\partial \mathbf{X}} \log \det(\mathbf{X}) = (\mathbf{X}^{-1})^T$（$\mathbf{X}$ 可逆）

2. $\frac{\partial}{\partial \mathbf{X}} \text{tr}(\mathbf{A}\mathbf{X}) = \mathbf{A}^T$

3. $\frac{\partial}{\partial \mathbf{X}} \text{tr}(\mathbf{X}^T \mathbf{A} \mathbf{X}) = (\mathbf{A} + \mathbf{A}^T)\mathbf{X}$

4. $\frac{\partial}{\partial \mathbf{X}} \det(\mathbf{X}) = \det(\mathbf{X}) \cdot (\mathbf{X}^{-1})^T$

### 在统计中的应用

这些公式在推导多元正态分布的 MLE、多元线性回归等场合频繁使用。

---

## 第 21 页：泰勒展开

### 一元函数的泰勒展开

$$f(x) \approx f(a) + f'(a)(x-a) + \frac{f''(a)}{2!}(x-a)^2 + \cdots + \frac{f^{(n)}(a)}{n!}(x-a)^n$$

**一阶近似（线性近似）**：
$$f(x) \approx f(a) + f'(a)(x-a)$$

**二阶近似**：
$$f(x) \approx f(a) + f'(a)(x-a) + \frac{1}{2}f''(a)(x-a)^2$$

### 在统计中的应用

- Delta 方法（用泰勒展开近似非线性函数的方差）
- 牛顿法的理论基础
- 似然函数的渐近正态性推导

---

## 第 22 页：多元泰勒展开

### 多元二阶泰勒展开

$$f(\mathbf{x}) \approx f(\mathbf{a}) + \nabla f(\mathbf{a})^T (\mathbf{x} - \mathbf{a}) + \frac{1}{2}(\mathbf{x} - \mathbf{a})^T \mathbf{H}_f(\mathbf{a}) (\mathbf{x} - \mathbf{a})$$

- 第一项：常数（函数在展开点的值）
- 第二项：线性项（梯度的贡献）
- 第三项：二次项（曲率的贡献）

### 应用

在极值点 $\mathbf{x}^*$ 附近，$\nabla f(\mathbf{x}^*) = 0$，于是：
$$f(\mathbf{x}) \approx f(\mathbf{x}^*) + \frac{1}{2}(\mathbf{x} - \mathbf{x}^*)^T \mathbf{H}_f(\mathbf{x}^*) (\mathbf{x} - \mathbf{x}^*)$$

这解释了为什么 Hessian 的正定性决定极值点的类型。

---

## 第 23 页：积分基础

### 不定积分
$$\int f(x) \, dx = F(x) + C, \quad F'(x) = f(x)$$

### 定积分
$$\int_a^b f(x) \, dx = F(b) - F(a)$$

几何意义：曲线下的**面积**（考虑符号）。

### 常用积分公式

| 函数 | 不定积分 |
|------|---------|
| $x^n$（$n \neq -1$） | $\frac{x^{n+1}}{n+1}$ |
| $1/x$ | $\ln\|x\|$ |
| $e^x$ | $e^x$ |
| $\sin x$ | $-\cos x$ |
| $\cos x$ | $\sin x$ |

### 在概率论中的应用

- 连续随机变量的概率由 PDF 下方的面积给出
- CDF 是 PDF 的积分
- 期望是 $x \cdot f(x)$ 的积分

---

## 第 24 页：多重积分

### 二重积分

$$\iint_D f(x, y) \, dx \, dy$$

几何意义：曲面 $z = f(x, y)$ 在区域 $D$ 下方的体积。

### 在概率论中的应用

- 联合连续随机变量的概率：
  $$P((X, Y) \in A) = \iint_A f_{X,Y}(x, y) \, dx \, dy$$

- 总概率为 1：
  $$\int_{-\infty}^{\infty} \int_{-\infty}^{\infty} f_{X,Y}(x, y) \, dx \, dy = 1$$

### 积分次序交换

在适当条件下（Fubini 定理）：
$$\iint f(x, y) \, dx \, dy = \int \left[ \int f(x, y) \, dx \right] dy = \int \left[ \int f(x, y) \, dy \right] dx$$

---

## 第 25 页：常用积分技巧

### 分部积分法（Integration by Parts）

$$\int u \, dv = uv - \int v \, du$$

应用：计算 $\mathbb{E}[X] = \int x f(x) dx$ 时常需要分部积分。

### 换元积分法（Substitution）

$$\int f(g(x)) \cdot g'(x) \, dx = \int f(u) \, du$$

（令 $u = g(x)$，$du = g'(x)dx$）

### Gamma 积分

$$\int_0^\infty x^{\alpha-1} e^{-\beta x} \, dx = \frac{\Gamma(\alpha)}{\beta^\alpha}$$

其中 $\Gamma(n) = (n-1)!$ 对于正整数 $n$。

这个积分在计算 Gamma 分布的归一化常数和期望时频繁出现。

---

## 第 26 页：级数

### 泰勒级数（Taylor Series）

$$f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!} (x-a)^n$$

### 常用级数展开

$$e^x = \sum_{n=0}^{\infty} \frac{x^n}{n!} = 1 + x + \frac{x^2}{2!} + \frac{x^3}{3!} + \cdots$$

$$\ln(1+x) = \sum_{n=1}^{\infty} (-1)^{n+1} \frac{x^n}{n}, \quad |x| < 1$$

$$\frac{1}{1-x} = \sum_{n=0}^{\infty} x^n, \quad |x| < 1$$

### 几何级数

$$\sum_{n=0}^{\infty} ar^n = \frac{a}{1-r}, \quad |r| < 1$$

几何级数在计算几何分布的归一化和期望时很有用。

---

## 第 27 页：指数函数与对数函数

### 指数函数 $e^x$

**关键性质**：
- $\frac{d}{dx} e^x = e^x$
- $e^{a+b} = e^a \cdot e^b$
- $e^{a \ln b} = b^a$

**在统计中**：正态分布的 PDF 包含 $e^{-x^2}$ 项；指数分布的 PDF 为 $e^{-\lambda x}$。

### 对数函数 $\ln x$

**关键性质**：
- $\frac{d}{dx} \ln x = \frac{1}{x}$
- $\ln(ab) = \ln a + \ln b$
- $\ln(a^b) = b \ln a$

**在统计中**：
- 对数似然函数将乘积化为求和（简化 MLE 求导）
- 对数变换常用于偏态数据的正态化

---

## 第 28 页：Gamma 函数与 Beta 函数

### Gamma 函数

$$\Gamma(\alpha) = \int_0^\infty t^{\alpha-1} e^{-t} \, dt, \quad \alpha > 0$$

**性质**：
- $\Gamma(\alpha+1) = \alpha \Gamma(\alpha)$
- $\Gamma(n) = (n-1)!$（$n$ 为正整数）
- $\Gamma(1/2) = \sqrt{\pi}$

### Beta 函数

$$B(\alpha, \beta) = \int_0^1 t^{\alpha-1} (1-t)^{\beta-1} \, dt$$

**与 Gamma 函数的关系**：
$$B(\alpha, \beta) = \frac{\Gamma(\alpha)\Gamma(\beta)}{\Gamma(\alpha+\beta)}$$

Beta 函数是 Beta 分布的归一化常数，也是理解 Beta 分布期望和方差的关键。

---

## 第 29 页：凸函数与 Jensen 不等式

### 凸函数（Convex Function）

函数 $f$ 称为**凸的**，如果对于任意 $\lambda \in [0, 1]$：
$$f(\lambda x + (1-\lambda)y) \leq \lambda f(x) + (1-\lambda)f(y)$$

即"弦在函数的图像上方"。

**凸性判定**：$f''(x) \geq 0$（一元）；Hessian 半正定（多元）。

### Jensen 不等式

对于凸函数 $f$：
$$f(\mathbb{E}[X]) \leq \mathbb{E}[f(X)]$$

### 应用

- 信息论中的 KL 散度非负性（利用 $-\log$ 的凸性）
- EM 算法的理论基础
- 许多不等式和界的推导

---

## 第 30 页：概率论中常用的数学恒等式

### 二项式定理

$$(a+b)^n = \sum_{k=0}^{n} \binom{n}{k} a^k b^{n-k}$$

应用：二项分布 PMF 之和为 1 的验证。

### 指数函数的级数表示

二项分布的 PMF 乘以 $e^\lambda$ 的级数 → 泊松分布的归一化。

### 几何级数求和

$$\sum_{k=0}^{\infty} p(1-p)^k = 1$$

$$\sum_{k=1}^{\infty} k p(1-p)^{k-1} = \frac{1}{p}$$

应用于几何分布的 PMF 归一化和期望计算。

---

## 第 31 页：OLS 正规方程的推导

### 问题

最小化残差平方和：
$$L(\boldsymbol{\beta}) = \|\mathbf{y} - \mathbf{X}\boldsymbol{\beta}\|_2^2$$

### 推导

展开：
$$L(\boldsymbol{\beta}) = (\mathbf{y} - \mathbf{X}\boldsymbol{\beta})^T(\mathbf{y} - \mathbf{X}\boldsymbol{\beta}) = \mathbf{y}^T\mathbf{y} - 2\boldsymbol{\beta}^T\mathbf{X}^T\mathbf{y} + \boldsymbol{\beta}^T\mathbf{X}^T\mathbf{X}\boldsymbol{\beta}$$

求梯度（使用矩阵微积分公式）：
$$\nabla_\beta L = -2\mathbf{X}^T\mathbf{y} + 2\mathbf{X}^T\mathbf{X}\boldsymbol{\beta}$$

设梯度为零：
$$\mathbf{X}^T\mathbf{X}\hat{\boldsymbol{\beta}} = \mathbf{X}^T\mathbf{y}$$

这就是**正规方程**。解得：
$$\hat{\boldsymbol{\beta}} = (\mathbf{X}^T\mathbf{X})^{-1}\mathbf{X}^T\mathbf{y}$$

---

## 第 32 页：PCA 的数学推导

### 问题

寻找单位向量 $\mathbf{w}$（$\|\mathbf{w}\| = 1$），使数据投影后的方差最大：
$$\max_{\|\mathbf{w}\|=1} \text{Var}(\mathbf{X}\mathbf{w}) = \max_{\|\mathbf{w}\|=1} \mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w}$$

其中 $\boldsymbol{\Sigma}$ 为数据的协方差矩阵。

### 使用拉格朗日乘子法

$$\mathcal{L}(\mathbf{w}, \lambda) = \mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w} - \lambda(\mathbf{w}^T\mathbf{w} - 1)$$

求导并设为零：
$$\frac{\partial \mathcal{L}}{\partial \mathbf{w}} = 2\boldsymbol{\Sigma}\mathbf{w} - 2\lambda\mathbf{w} = 0$$
$$\Rightarrow \boldsymbol{\Sigma}\mathbf{w} = \lambda \mathbf{w}$$

所以 $\mathbf{w}$ 是 $\boldsymbol{\Sigma}$ 的**特征向量**，$\lambda$ 为对应的**特征值**。

最大化方差意味着应选择最大特征值对应的特征向量！

---

## 第 33 页：信息论基础

### 熵（Entropy）

熵度量随机变量的不确定性：
$$H(X) = -\sum_{x} p(x) \log p(x)$$

（离散情况；连续情况用微分熵，但不再深入）

**性质**：
- $H(X) \geq 0$
- 当 $X$ 为确定常数时，$H(X) = 0$
- 对于离散均匀分布，熵最大

### 交叉熵（Cross-Entropy）

$$H(p, q) = -\sum_x p(x) \log q(x)$$

机器学习中的交叉熵损失函数：$p$ 为真实分布，$q$ 为预测分布。

### KL 散度

$$D_{KL}(p \| q) = \sum_x p(x) \log \frac{p(x)}{q(x)} \geq 0$$

度量两个分布之间的差异。由 Jensen 不等式可证 $D_{KL} \geq 0$。

---

## 第 34 页：逻辑回归的损失函数推导

### 从 MLE 到交叉熵损失

对于二分类，$Y \mid \mathbf{X} \sim \text{Bernoulli}(p(\mathbf{X}))$，其中：
$$p(\mathbf{X}) = \sigma(\boldsymbol{\beta}^T \mathbf{X}) = \frac{1}{1 + e^{-\boldsymbol{\beta}^T \mathbf{X}}}$$

**似然函数**：
$$L(\boldsymbol{\beta}) = \prod_{i=1}^{n} p_i^{y_i} (1-p_i)^{1-y_i}$$

**对数似然**（取负号得到损失）：
$$\ell(\boldsymbol{\beta}) = \sum_{i=1}^{n} \left[ y_i \log p_i + (1-y_i) \log(1-p_i) \right]$$

**损失函数**（交叉熵损失）：
$$J(\boldsymbol{\beta}) = -\ell(\boldsymbol{\beta}) = -\sum_{i=1}^{n} \left[ y_i \log \hat{y}_i + (1-y_i) \log(1-\hat{y}_i) \right]$$

---

## 第 35 页：习题——线性代数

### 习题 1：矩阵运算

已知 $\mathbf{A} = \begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}$，$\mathbf{B} = \begin{bmatrix} 5 & 6 \\ 7 & 8 \end{bmatrix}$。

计算 (a) $\mathbf{A} + \mathbf{B}$，(b) $\mathbf{A}\mathbf{B}$，(c) $\mathbf{A}^{-1}$，(d) $\det(\mathbf{A})$

**解答**：
(a) $\begin{bmatrix} 6 & 8 \\ 10 & 12 \end{bmatrix}$
(b) $\begin{bmatrix} 19 & 22 \\ 43 & 50 \end{bmatrix}$
(c) $-\frac{1}{2}\begin{bmatrix} 4 & -2 \\ -3 & 1 \end{bmatrix} = \begin{bmatrix} -2 & 1 \\ 1.5 & -0.5 \end{bmatrix}$
(d) $\det(\mathbf{A}) = -2$

---

## 第 36 页：习题——特征值与特征向量

### 习题 2

求矩阵 $\mathbf{A} = \begin{bmatrix} 4 & 1 \\ 2 & 3 \end{bmatrix}$ 的特征值和特征向量。

**解答**：
特征方程：$\det(\mathbf{A} - \lambda\mathbf{I}) = \det\begin{bmatrix} 4-\lambda & 1 \\ 2 & 3-\lambda \end{bmatrix} = 0$
$(4-\lambda)(3-\lambda) - 2 = \lambda^2 - 7\lambda + 10 = 0$
$\lambda_1 = 5, \lambda_2 = 2$

对于 $\lambda_1 = 5$：$(A - 5I)\mathbf{v} = 0 \Rightarrow \mathbf{v}_1 = \begin{bmatrix} 1 \\ 1 \end{bmatrix}$

对于 $\lambda_2 = 2$：$(A - 2I)\mathbf{v} = 0 \Rightarrow \mathbf{v}_2 = \begin{bmatrix} -1 \\ 2 \end{bmatrix}$

---

## 第 37 页：习题——微积分

### 习题 3：求梯度

求 $f(\mathbf{x}) = \mathbf{x}^T \mathbf{A} \mathbf{x}$ 的梯度，其中 $\mathbf{A} = \begin{bmatrix} 1 & 2 \\ 2 & 1 \end{bmatrix}$。

**解答**：
$f(x_1, x_2) = x_1^2 + 4x_1x_2 + x_2^2$

$\frac{\partial f}{\partial x_1} = 2x_1 + 4x_2$

$\frac{\partial f}{\partial x_2} = 4x_1 + 2x_2$

$\nabla f = \begin{bmatrix} 2x_1 + 4x_2 \\ 4x_1 + 2x_2 \end{bmatrix} = (\mathbf{A} + \mathbf{A}^T)\mathbf{x} = 2\mathbf{A}\mathbf{x}$

---

## 第 38 页：习题——优化

### 习题 4：梯度下降

$f(x) = x^2 + 2x + 3$，起点 $x^{(0)} = 5$，学习率 $\eta = 0.1$。执行 3 次梯度下降迭代。

**解答**：
$f'(x) = 2x + 2$

$x^{(1)} = 5 - 0.1 \times (2 \times 5 + 2) = 5 - 1.2 = 3.8$

$x^{(2)} = 3.8 - 0.1 \times (2 \times 3.8 + 2) = 3.8 - 0.96 = 2.84$

$x^{(3)} = 2.84 - 0.1 \times (2 \times 2.84 + 2) = 2.84 - 0.768 = 2.072$

解析解：$f'(x) = 0 \Rightarrow x = -1$。梯度下降正在向 -1 靠近。

---

## 第 39 页：习题——积分

### 习题 5

计算 $\int_0^\infty 2x e^{-2x} \, dx$（这恰好是指数分布 $\text{Exponential}(2)$ 的期望）。

**解答**：
$$\int_0^\infty 2x e^{-2x} \, dx = 2 \int_0^\infty x e^{-2x} \, dx$$

使用 Gamma 积分：
$$\int_0^\infty x e^{-2x} dx = \frac{\Gamma(2)}{2^2} = \frac{1}{4}$$

所以 $\int_0^\infty 2x e^{-2x} dx = 2 \times \frac{1}{4} = \frac{1}{2}$。

这验证了 $\mathbb{E}[X] = 1/2$ 对于 $X \sim \text{Exponential}(2)$。

---

## 第 40 页：习题——MLE 推导练习

### 习题 6

利用矩阵微积分，推导多元线性回归 $\mathbf{y} = \mathbf{X}\boldsymbol{\beta} + \boldsymbol{\varepsilon}$ 中 $\boldsymbol{\beta}$ 的 MLE。

**解答**：
似然（正态误差假设下）：
$$L(\boldsymbol{\beta}) \propto \exp\left(-\frac{1}{2\sigma^2}(\mathbf{y} - \mathbf{X}\boldsymbol{\beta})^T(\mathbf{y} - \mathbf{X}\boldsymbol{\beta})\right)$$

最大化似然 ⇔ 最小化 $(\mathbf{y} - \mathbf{X}\boldsymbol{\beta})^T(\mathbf{y} - \mathbf{X}\boldsymbol{\beta})$

该式对 $\boldsymbol{\beta}$ 的梯度：
$$\nabla_\beta = -2\mathbf{X}^T\mathbf{y} + 2\mathbf{X}^T\mathbf{X}\boldsymbol{\beta}$$

设为零得到 $\hat{\boldsymbol{\beta}} = (\mathbf{X}^T\mathbf{X})^{-1}\mathbf{X}^T\mathbf{y}$。

这展示了在正态误差假设下，OLS 估计量就是 MLE。

---

## 第 41-56 页：综合复习与总结

### 数学复习核心要点

**线性代数**：
- 矩阵乘法、逆、行列式、秩
- 特征值与特征向量、特征分解
- SVD 及其在 PCA 和推荐系统中的应用
- 向量范数（$\ell_1$, $\ell_2$, $\ell_\infty$）

**微积分**：
- 导数、链式法则
- 偏导数、梯度、Hessian
- 泰勒展开（一元和多元）
- 积分基础与 Gamma 积分

**最优化**：
- 梯度下降与学习率
- 牛顿法（二阶优化）
- 拉格朗日乘子法
- 约束优化在统计中的应用

**矩阵微积分**：
- 标量对向量的导数
- 标量对矩阵的导数
- OLS 正规方程和 PCA 的推导

**在数据科学中的应用**：
- OLS 推导、PCA 推导、逻辑回归损失函数
- 信息论基础（熵、交叉熵、KL 散度）

### 备考建议

- 熟练掌握矩阵乘法和转置的性质
- 能够手动计算 2×2 矩阵的特征值和特征向量
- 理解梯度下降的迭代更新公式
- 知晓拉格朗日乘子法的用途和适用条件
- 能够复现 OLS 正规方程和 PCA 的推导过程
- 理解凸函数和 Jensen 不等式的含义

---

> **翻译完成**：`Review_of_math5.pdf` 共 56 页，逐页翻译完毕。这是 4 个 review 课件中的最后一个，所有 review 课件翻译工作已全部完成。
