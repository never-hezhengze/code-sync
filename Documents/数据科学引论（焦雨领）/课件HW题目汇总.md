# 课件 HW（作业）题目汇总

---

## HW 1 — 多元正态的条件分布

**出处**：课件 Minimax lower bound（极小极大下界）部分，约第 10 页

**题目**：

Recall: let $(Y,Z)\sim N(\mu,\Sigma)$ with $\mu=[\mu_y,\mu_z]^T$,

$$\Sigma=\begin{pmatrix}\Sigma_{yy}&\Sigma_{yz}\\\Sigma_{zy}&\Sigma_{zz}\end{pmatrix}\succcurlyeq 0.$$

Then $Z\mid Y\sim N(\mu_{z\mid y},\Sigma_{z\mid y})$ with

$$\mu_{z\mid y}=\mu_z+\Sigma_{zy}\Sigma_{yy}^{-1}(y-\mu_y),\qquad\Sigma_{z\mid y}=\Sigma_{zz}-\Sigma_{zy}\Sigma_{yy}^{-1}\Sigma_{yz}.$$

---

## HW 2 — 近端梯度下降的次线性收敛

**出处**：课件 Proximal gradient descent 部分，约第 39 页

**题目**：

Let $G(x)=x-\operatorname{Prox}_{h/L}(x-\nabla f(x)/L)$. Show that the condition

$$\langle G(x),x-x^*\rangle\geq\gamma\,(F(x)-F(x^*)),\quad\gamma>0$$

also implies $O(1/t)$ convergence for proximal gradient descent.

---

## HW 3 — Logistic 回归的 MLE 推导

**出处**：课件 Plug-in estimator / Logistic model 部分，约第 55 页

**题目**：

For the logistic model $P(Y=1\mid X=x)=\sigma(\theta^T x)$ with $\sigma(t)=1/(1+e^{-t})$, show that the MLE for $\theta$ is given by

$$\hat{\theta}\in\arg\min_{\theta\in\mathbb{R}^d}\frac{1}{n}\sum_{i=1}^n\ell_{\lg}(Y_i,\theta^T x_i),$$

where $\ell_{\lg}(y,t)=-yt+\log(1+e^t)$.

---

## HW 4 — RKHS 的唯一性

**出处**：课件 SVM with kernels / RKHS 部分，约第 62 页

**题目**：

Show that every positive definite kernel $K$ has a unique reproducing kernel Hilbert space (RKHS).

---

## HW 5 — SVM 从 RKHS 正则化框架推导

**出处**：课件 SVM with kernels / Representer theorem 部分，约第 63 页

**题目**：

Show that SVM with kernels can be derived from the regularized RKHS formulation:

$$\min_{f\in\mathcal{H}}\frac{1}{n}\sum_{i=1}^n\ell_{\text{hinge}}(y_i,f(x_i))+\lambda\|f\|_{\mathcal{H}}^2,$$

where $\ell_{\text{hinge}}(y,t)=(1-yt)_+=\max\{0,1-yt\}$ and $\lambda=1/(2nC)$.

---

## HW 6 — SVD 变分刻画：极小-极大和极大-极小公式

**出处**：课件 SVD 部分，约第 99 页

**题目**：

Prove the variational characterizations of singular values:

(1) $\sigma_k=\max_{\substack{S\subseteq\mathbb{R}^n\\\dim(S)=k}}\;\min_{\substack{v\in S\\\|v\|=1}}\|Av\|$.

(2) $\sigma_k=\min_{\substack{S\subseteq\mathbb{R}^n\\\dim(S)=n-k+1}}\;\max_{\substack{v\in S\\\|v\|=1}}\|Av\|$.

---

## HW 7 — 最优线性编码器/解码器

**出处**：课件 SVD application 部分，约第 100 页

**题目**：

Suppose we have data $x_1,\ldots,x_n$ with each $x_i\in\mathbb{R}^d$ and $d$ is huge. We want to compress the data by linear map: find linear encoder $E\in\mathbb{R}^{s\times d}$ and decoder $D\in\mathbb{R}^{d\times s}$ with $s\ll d$ that minimize the reconstruction loss

$$L(E,D)=\sum_{i=1}^n\|x_i-DEx_i\|^2/n.$$

Find the optimal $E$ and $D$. (Answer: $E=V_{1:s}^T$, $D=V_{1:s}$, where $X=U\Sigma V^T$ is the compact SVD of the data matrix.)

---

## HW 8 — 下半连续性与闭性等价

**出处**：课件 Convex functions 部分，约第 106 页

**题目**：

Show that $f$ is lower semi-continuous $\iff$ $C_\alpha=\{x\mid f(x)\leq\alpha\}$ is closed for every $\alpha$ $\iff$ $f$ is closed (i.e., $\operatorname{epi}(f)$ is closed).

---

## HW 9 — 计算常见范数和矩阵范数的次微分

**出处**：课件 Subdifferential 部分，约第 111 页

**题目**：

Compute the subdifferential $\partial f$ for the following functions:

1. $f(x)=\|x\|_1$
2. $f(x)=\|x\|_2$
3. $f(x)=\|x\|_\infty$
4. $f(X)=\|X\|_*$ (nuclear norm of a matrix)

---

## HW 10 — 随机矩阵的谱范数尾界

**出处**：课件 Concentration inequalities 部分末尾，约第 192 页

**题目**：

Let $X\sim\operatorname{subG}_{m\times n}(\sigma^2)$. Show that for any $t>0$, with probability at least $1-2\exp(-t^2)$,

$$\|X\|_2\leq C\sigma(\sqrt{m}+\sqrt{n}+t).$$

---

> 共 10 道 HW 题，涵盖了线性代数（SVD）、凸分析（次微分、近端梯度）、概率论（集中不等式、多元正态）、监督学习（Logistic MLE、SVM/RKHS）等模块。其中 HW 7（最优线性编码器）恰好是期末考试第 1 题，HW 9（次微分计算）与期末考试第 2 题高度相关，HW 5（SVM RKHS 推导）也直接对应课件核心证明。
