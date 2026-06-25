# 课件 HW 题目解答汇总

---

## HW 1 — 多元正态的条件分布

**Original**: Recall: let $(Y,Z)\sim N(\mu,\Sigma)$ with $\mu=[\mu_y,\mu_z]^T$, $\Sigma=\begin{pmatrix}\Sigma_{yy}&\Sigma_{yz}\\\Sigma_{zy}&\Sigma_{zz}\end{pmatrix}\succcurlyeq 0$. Then $Z\mid Y\sim N(\mu_{z\mid y},\Sigma_{z\mid y})$ with $\mu_{z\mid y}=\mu_z+\Sigma_{zy}\Sigma_{yy}^{-1}(y-\mu_y)$, $\Sigma_{z\mid y}=\Sigma_{zz}-\Sigma_{zy}\Sigma_{yy}^{-1}\Sigma_{yz}$.

**中文**：回顾：设 $(Y,Z)\sim N(\mu,\Sigma)$，验证上述条件分布公式。

**解答**：

先假设 $\Sigma\succ 0$ 且 $\Sigma_{yy}$ 可逆；半正定退化情形可用极限或 Moore-Penrose 逆处理。令 $x=(y,z)$，联合密度为

$$f_{Y,Z}(y,z)=(2\pi)^{-(p+q)/2}|\Sigma|^{-1/2}\exp\left[-\frac{1}{2}(x-\mu)^{\top}\Sigma^{-1}(x-\mu)\right].$$

设 Schur 补 $S=\Sigma_{zz}-\Sigma_{zy}\Sigma_{yy}^{-1}\Sigma_{yz}$。分块矩阵求逆给出 $\Omega=\Sigma^{-1}$ 的右下块为 $\Omega_{zz}=S^{-1}$，且二次型可配方为

$$\begin{aligned}
(x-\mu)^{\top}\Sigma^{-1}(x-\mu)
&=(y-\mu_y)^{\top}\Sigma_{yy}^{-1}(y-\mu_y)\\
&\quad +(z-\mu_z-\Sigma_{zy}\Sigma_{yy}^{-1}(y-\mu_y))^{\top}S^{-1}(z-\mu_z-\Sigma_{zy}\Sigma_{yy}^{-1}(y-\mu_y)).
\end{aligned}$$

第一项只含 $y$，因此在条件密度 $f_{Z\mid Y}(z\mid y)=f_{Y,Z}(y,z)/f_Y(y)$ 中会被归一化常数吸收，剩下的 $z$ 的核为正态密度核。所以

$$Z\mid Y=y\sim N\left(\mu_z+\Sigma_{zy}\Sigma_{yy}^{-1}(y-\mu_y),\;\Sigma_{zz}-\Sigma_{zy}\Sigma_{yy}^{-1}\Sigma_{yz}\right).$$

---

## HW 2 — 近端梯度下降的角度条件蕴含 $O(1/t)$ 收敛

**Original**: Let $G(x)=x-\operatorname{Prox}_{h/L}(x-\nabla f(x)/L)$. Show that $\langle G(x),x-x^*\rangle\geq\gamma\,(F(x)-F(x^*))$, $\gamma>0$ also implies $O(1/t)$ convergence for proximal gradient descent.

**中文**：令 $G(x)=x-\operatorname{Prox}_{h/L}(x-\nabla f(x)/L)$。证明条件 $\langle G(x),x-x^*\rangle\geq\gamma\,(F(x)-F(x^*))$（$\gamma>0$）也能推出近端梯度下降的 $O(1/t)$ 收敛。

**解答**：

设 $F=f+h$，其中 $f$ 为凸且 $\nabla f$ 为 $L$-Lipschitz，$h$ 为闭凸函数。近端 GD 迭代为

$$x^{k+1}=\operatorname{Prox}_{h/L}\left(x^k-\frac{1}{L}\nabla f(x^k)\right),\qquad G_k:=G(x^k)=x^k-x^{k+1}.$$

由近端梯度的标准三点不等式，对任意 $z$ 有

$$F(x^{k+1})\leq F(z)+\frac{L}{2}\|x^k-z\|_2^2-\frac{L}{2}\|x^{k+1}-z\|_2^2.$$

取 $z=x^*$ 得到一条 Fejer 型不等式；取 $z=x^k$ 得到下降性

$$F(x^{k+1})\leq F(x^k)-\frac{L}{2}\|G_k\|_2^2.$$

记 $\epsilon_k=F(x^k)-F(x^*)$。由下降性，

$$\|G_k\|_2^2\leq\frac{2}{L}(\epsilon_k-\epsilon_{k+1}).$$

再利用题设角度条件 $\langle G_k,x^k-x^*\rangle\geq \gamma\epsilon_k$，有

$$\|x^k-x^*\|_2^2-\|x^{k+1}-x^*\|_2^2=2\langle G(x^k),x^k-x^*\rangle-\|G(x^k)\|_2^2\geq 2\gamma\epsilon_k-\tfrac{2}{L}(\epsilon_k-\epsilon_{k+1}).$$

对 $k=0,\ldots,t-1$ 求和：

$$\|x^0-x^*\|_2^2\geq 2\gamma\sum_{k=0}^{t-1}\epsilon_k-\frac{2}{L}(\epsilon_0-\epsilon_t)\geq 2\gamma t\,\epsilon_t-\frac{2}{L}\epsilon_0,$$

其中最后一步用到了 $\epsilon_k$ 非增。因此

$$\epsilon_t\leq \frac{\|x^0-x^*\|_2^2+\frac{2}{L}\epsilon_0}{2\gamma t}=O(1/t).$$

注意这里不需要额外假设 $\epsilon_0\leq \frac{L}{2}\|x^0-x^*\|^2$；这个不等式对一般复合目标 $f+h$ 并不总成立。

---

## HW 3 — Logistic 回归的 MLE 推导

**Original**: For the logistic model $P(Y=1\mid X=x)=\sigma(\theta^T x)$ with $\sigma(t)=1/(1+e^{-t})$, show that the MLE for $\theta$ is $\hat{\theta}\in\arg\min_{\theta\in\mathbb{R}^d}\frac{1}{n}\sum_{i=1}^n\ell_{\lg}(Y_i,\theta^T x_i)$, where $\ell_{\lg}(y,t)=-yt+\log(1+e^t)$.

**中文**：对 Logistic 模型 $P(Y=1\mid X=x)=\sigma(\theta^T x)$（$\sigma(t)=1/(1+e^{-t})$），证明 $\theta$ 的 MLE 为 $\hat{\theta}\in\arg\min_{\theta}\frac{1}{n}\sum_{i=1}^n\ell_{\lg}(Y_i,\theta^T x_i)$，其中 $\ell_{\lg}(y,t)=-yt+\log(1+e^t)$。

**解答**：

给定 i.i.d. 数据 $(x_i,Y_i)$，$Y_i\in\{0,1\}$。记 $p_i(\theta)=P(Y_i=1\mid x_i)=\sigma(\theta^T x_i)$。似然函数：$L(\theta)=\prod_{i=1}^n p_i(\theta)^{Y_i}(1-p_i(\theta))^{1-Y_i}$。负对数似然：

$$-\log L(\theta)=-\sum_{i=1}^n\bigl[Y_i\log p_i(\theta)+(1-Y_i)\log(1-p_i(\theta))\bigr].$$

注意到 $\log\sigma(t)=-\log(1+e^{-t})$，$\log(1-\sigma(t))=\log\frac{e^{-t}}{1+e^{-t}}=-t-\log(1+e^{-t})$。代入：

$$\begin{aligned}-Y_i\log\sigma(t_i)-(1-Y_i)\log(1-\sigma(t_i))&=Y_i\log(1+e^{-t_i})+(1-Y_i)(t_i+\log(1+e^{-t_i}))\\&=(1-Y_i)t_i+\log(1+e^{-t_i})\\&=(1-Y_i)t_i+\log\frac{1+e^{t_i}}{e^{t_i}}=(1-Y_i)t_i+\log(1+e^{t_i})-t_i\\&=-Y_i t_i+\log(1+e^{t_i})=\ell_{\lg}(Y_i,t_i),\end{aligned}$$

其中 $t_i=\theta^T x_i$。MLE 最大化 $L(\theta)$，等价于最小化 $-\frac{1}{n}\log L(\theta)=\frac{1}{n}\sum_{i=1}^n\ell_{\lg}(Y_i,\theta^T x_i)$。证毕。

---

## HW 4 — RKHS 的唯一性

**Original**: Show that every positive definite kernel $K$ has a unique reproducing kernel Hilbert space (RKHS).

**中文**：证明每个正定核 $K$ 有唯一的再生核 Hilbert 空间。

**解答**：

**存在性**：先取形式线性空间

$$H_0=\operatorname{span}\{K(\cdot,x):x\in\mathcal{X}\}.$$

在 $H_0$ 上定义半内积

$$\left\langle\sum_i a_iK(\cdot,x_i),\sum_j b_jK(\cdot,y_j)\right\rangle_0=\sum_{i,j}a_i b_jK(x_i,y_j).$$

正定性保证 $\langle f,f\rangle_0\geq0$。若存在零范数元素，则先对零范数子空间取商；取商后得到内积空间，再完备化得到 Hilbert 空间 $H$。对 $f=\sum_i a_iK(\cdot,x_i)\in H_0$，

$$\langle f,K(\cdot,x)\rangle_H=\sum_i a_iK(x_i,x)=f(x).$$

且 $|f(x)|\leq\|f\|_H\sqrt{K(x,x)}$，因此赋值泛函连续，再生性可由稠密性延拓到整个 $H$。

**唯一性**：设 $H_1,H_2$ 均为 $K$ 的 RKHS。则 $\forall x$，$K(\cdot,x)\in H_1\cap H_2$，且 $\operatorname{span}\{K(\cdot,x)\}$ 在 $H_1,H_2$ 中均稠密（若 $f\perp\operatorname{span}\{K(\cdot,x)\}$，则 $\forall x$，$f(x)=\langle f,K(\cdot,x)\rangle=0$，故 $f=0$）。在稠密子空间上，内积均由 $K$ 的双线性扩张唯一确定：$\langle\sum a_i K(\cdot,x_i),\sum b_j K(\cdot,y_j)\rangle=\sum a_i b_j K(x_i,y_j)$。完备化在等距同构意义下唯一，故 $H_1\cong H_2$。

---

## HW 5 — SVM 的 RKHS 正则化推导

**Original**: Show that SVM with kernels can be derived from the regularized RKHS formulation: $\min_{f\in\mathcal{H}}\frac{1}{n}\sum_{i=1}^n\ell_{\text{hinge}}(y_i,f(x_i))+\lambda\|f\|_{\mathcal{H}}^2$, where $\ell_{\text{hinge}}(y,t)=(1-yt)_+=\max\{0,1-yt\}$ and $\lambda=1/(2nC)$.

**中文**：证明带核的 SVM 可以从 RKHS 正则化框架 $\min_{f\in\mathcal{H}}\frac{1}{n}\sum_{i=1}^n\ell_{\text{hinge}}(y_i,f(x_i))+\lambda\|f\|_{\mathcal{H}}^2$ 推导出来，其中 $\ell_{\text{hinge}}(y,t)=(1-yt)_+$，$\lambda=1/(2nC)$。

**解答**：

由表示定理（Representer Theorem），目标函数 $\frac{1}{n}\sum_{i=1}^n\ell_{\text{hinge}}(y_i,f(x_i))+\lambda\|f\|_{\mathcal{H}}^2$ 的最优解具有形式 $f^*(x)=\sum_{i=1}^n\alpha_i K(x_i,x)$。代入：$\|f^*\|_{\mathcal{H}}^2=\sum_{i,j}\alpha_i\alpha_j K(x_i,x_j)$，$f^*(x_i)=\sum_j\alpha_j K(x_i,x_j)$。引入松弛变量 $\xi_i\geq 0$ 满足 $\xi_i\geq 1-y_i f^*(x_i)$，则 $\ell_{\text{hinge}}(y_i,f^*(x_i))=\xi_i$。原问题等价于：

$$\min_{\alpha,\xi}\;\frac{1}{n}\sum_{i=1}^n\xi_i+\lambda\sum_{i,j}\alpha_i\alpha_j K(x_i,x_j),\quad\text{s.t.}\;y_i\sum_j\alpha_j K(x_i,x_j)\geq 1-\xi_i,\;\xi_i\geq 0.$$

令 $w=\sum_i\alpha_i\phi(x_i)$（其中 $K(x_i,x_j)=\langle\phi(x_i),\phi(x_j)\rangle_{\mathcal{H}}$），则 $\sum_{i,j}\alpha_i\alpha_j K(x_i,x_j)=\|w\|_{\mathcal{H}}^2$，$f^*(x_i)=\langle w,\phi(x_i)\rangle_{\mathcal{H}}$。代入 $\lambda=1/(2nC)$ 并乘以 $n$：

$$\min_{w,\xi}\;\frac{1}{2C}\|w\|_{\mathcal{H}}^2+\sum_{i=1}^n\xi_i,\quad\text{s.t.}\;y_i\langle w,\phi(x_i)\rangle_{\mathcal{H}}\geq 1-\xi_i,\;\xi_i\geq 0.$$

乘以正数 $C$ 不改变最优解，即得无偏置版本的软间隔核 SVM 原问题

$$\min_{w,\xi}\frac{1}{2}\|w\|_{\mathcal{H}}^2+C\sum_{i=1}^n\xi_i,\quad\text{s.t.}\;y_i\langle w,\phi(x_i)\rangle_{\mathcal{H}}\geq1-\xi_i,\;\xi_i\geq0.$$

若标准写法包含偏置 $b$，可把判别函数写成 $f(x)=\langle w,\phi(x)\rangle+b$，通常不惩罚 $b$，或等价地在特征中加入常数坐标并单独处理偏置正则化。因此 RKHS 正则化形式正是核 SVM 的原始问题形式。

---

## HW 6 — SVD 的变分刻画

**Original**: Prove the variational characterizations of singular values: (1) $\sigma_k=\max_{\substack{S\subseteq\mathbb{R}^n\\\dim(S)=k}}\;\min_{\substack{v\in S\\\|v\|=1}}\|Av\|$; (2) $\sigma_k=\min_{\substack{S\subseteq\mathbb{R}^n\\\dim(S)=n-k+1}}\;\max_{\substack{v\in S\\\|v\|=1}}\|Av\|$.

**中文**：证明奇异值的变分刻画公式 (1) 和 (2)。

**解答**：

设 $A=U\Sigma V^{\top}$ 为 SVD，右奇异向量 $v_1,\ldots,v_n$ 构成 $\mathbb{R}^n$ 的标准正交基，对应奇异值 $\sigma_1\geq\cdots\geq\sigma_n\geq 0$（补零后）。

**(1) 证明 $\sigma_k=\max_{\dim(S)=k}\min_{v\in S,\|v\|=1}\|Av\|$**。

取 $S_k=\operatorname{span}\{v_1,\ldots,v_k\}$。对任意 $v=\sum_{i=1}^k c_i v_i\in S_k$ 且 $\|v\|_2=1$，有 $\|Av\|_2^2=\sum_{i=1}^k\sigma_i^2 c_i^2\geq\sigma_k^2\sum_{i=1}^k c_i^2=\sigma_k^2$，故 $\min_{v\in S_k,\|v\|=1}\|Av\|\geq\sigma_k$，右端 $\max$ 至少为 $\sigma_k$。

反之，任取 $k$ 维子空间 $S$。$\dim(S)=k$，$\dim(\operatorname{span}\{v_k,\ldots,v_n\})=n-k+1$，两子空间维数之和 $k+(n-k+1)=n+1>n$，故存在单位向量 $v\in S\cap\operatorname{span}\{v_k,\ldots,v_n\}$。写 $v=\sum_{i=k}^n c_i v_i$，$\sum c_i^2=1$，则 $\|Av\|_2^2=\sum_{i=k}^n\sigma_i^2 c_i^2\leq\sigma_k^2\sum_{i=k}^n c_i^2=\sigma_k^2$。于是 $\min_{v\in S,\|v\|=1}\|Av\|\leq\|Av\|\leq\sigma_k$。对任意 $S$ 成立，故 $\max_S\min_v\leq\sigma_k$。综上等号成立。

**(2) 证明 $\sigma_k=\min_{\dim(S)=n-k+1}\max_{v\in S,\|v\|=1}\|Av\|$**。

取 $S_k=\operatorname{span}\{v_k,\ldots,v_n\}$，其维数为 $n-k+1$。对任意单位向量 $v=\sum_{i=k}^n c_i v_i\in S_k$，

$$\|Av\|_2^2=\sum_{i=k}^n\sigma_i^2c_i^2\leq\sigma_k^2\sum_{i=k}^n c_i^2=\sigma_k^2.$$

并且取 $v=v_k$ 时达到 $\sigma_k$，故 $\max_{v\in S_k,\|v\|=1}\|Av\|=\sigma_k$。所以 $\min_S\max_v\leq\sigma_k$。

反之，任取 $n-k+1$ 维子空间 $S$。$\dim(S)=n-k+1$，$\dim(\operatorname{span}\{v_1,\ldots,v_k\})=k$，两子空间维数之和 $(n-k+1)+k=n+1>n$，故存在 $v\in S\cap\operatorname{span}\{v_1,\ldots,v_k\}$。$\|Av\|_2^2=\sum_{i=1}^k\sigma_i^2 c_i^2\geq\sigma_k^2$，故 $\max_{v\in S}\|Av\|\geq\sigma_k$。对任意 $S$ 成立，$\min_S\max_v\geq\sigma_k$。等号成立。

---

## HW 7 — 最优线性编码器/解码器

**Original**: Suppose we have data $x_1,\ldots,x_n$ with each $x_i\in\mathbb{R}^d$ and $d$ is huge. Find linear encoder $E\in\mathbb{R}^{s\times d}$ and decoder $D\in\mathbb{R}^{d\times s}$ with $s\ll d$ that minimize $L(E,D)=\sum_{i=1}^n\|x_i-DEx_i\|^2/n$. Find the optimal $E$ and $D$.

**中文**：（即期末考试第 1 题，解答见下）

**解答**：

令 $X=[x_1,\ldots,x_n]^{\top}\in\mathbb{R}^{n\times d}$，则

$$L(E,D)=\frac{1}{n}\|X-XE^{\top}D^{\top}\|_F^2.$$

任意 $XE^{\top}D^{\top}$ 的秩不超过 $s$，因此

$$\min_{E,D}L(E,D)\geq \min_{\operatorname{rank}(X_s)\leq s}\frac{1}{n}\|X-X_s\|_F^2.$$

由 Eckart-Young-Mirsky 定理，右侧最优解为 $X$ 的最佳秩 $s$ 截断。设 $X=U\Sigma V^{\top}$ 为紧凑 SVD，$\sigma_1\geq\cdots\geq\sigma_r>0$，令 $V_s=[v_1,\ldots,v_s]$，则

$$X_s=U_s\Sigma_sV_s^{\top}=XV_sV_s^{\top}.$$

取

$$E=V_s^{\top}\in\mathbb{R}^{s\times d},\qquad D=V_s\in\mathbb{R}^{d\times s},$$

则 $XE^{\top}D^{\top}=XV_sV_s^{\top}=X_s$，达到下界，故为一组最优线性编码器/解码器。最优重构损失为

$$L^*=\frac{1}{n}\sum_{i=s+1}^r\sigma_i^2.$$

最优解不唯一：若 $R\in\mathbb{R}^{s\times s}$ 可逆，则 $\tilde E=RV_s^{\top}$、$\tilde D=V_sR^{-1}$ 给出相同的重构投影。

---

## HW 8 — 下半连续性与闭性等价

**Original**: Show that $f$ is lower semi-continuous $\iff$ $C_\alpha=\{x\mid f(x)\leq\alpha\}$ is closed for every $\alpha$ $\iff$ $f$ is closed (i.e., $\operatorname{epi}(f)$ is closed).

**中文**：证明 $f$ 下半连续 $\iff$ 对任意 $\alpha$，$C_\alpha=\{x\mid f(x)\leq\alpha\}$ 为闭集 $\iff$ $f$ 是闭的（即 $\operatorname{epi}(f)$ 为闭集）。

**解答**：

**(a) $f$ 下半连续 $\Rightarrow$ $C_\alpha$ 闭**：设 $x_n\in C_\alpha$，$x_n\to x$。由下半连续性 $f(x)\leq\liminf_{n\to\infty}f(x_n)\leq\alpha$，故 $x\in C_\alpha$。

**(b) $C_\alpha$ 闭 $\forall\alpha$ $\Rightarrow$ $f$ 下半连续**：设 $x_n\to x$，令 $L=\liminf f(x_n)$。任取子列 $x_{n_k}$ 使 $f(x_{n_k})\to L$。$\forall\varepsilon>0$，当 $k$ 充分大时 $f(x_{n_k})\leq L+\varepsilon$，即 $x_{n_k}\in C_{L+\varepsilon}$。$C_{L+\varepsilon}$ 闭，故 $x\in C_{L+\varepsilon}$，即 $f(x)\leq L+\varepsilon$。由 $\varepsilon$ 任意性，$f(x)\leq L=\liminf f(x_n)$。

**(c) $\operatorname{epi}(f)$ 闭 $\iff$ $f$ 下半连续**：先设 $f$ 下半连续。若 $(x_n,t_n)\in\operatorname{epi}(f)$ 且 $(x_n,t_n)\to(x,t)$，则 $f(x_n)\leq t_n$。由下半连续性，

$$f(x)\leq\liminf_{n\to\infty}f(x_n)\leq\lim_{n\to\infty}t_n=t,$$

所以 $(x,t)\in\operatorname{epi}(f)$，即 $\operatorname{epi}(f)$ 闭。反过来，设 $\operatorname{epi}(f)$ 闭。任取 $x_n\to x$，令 $L=\liminf f(x_n)$，并取子列 $x_{n_k}$ 使 $f(x_{n_k})\to L$。因为 $(x_{n_k},f(x_{n_k}))\in\operatorname{epi}(f)$ 且收敛到 $(x,L)$，由闭性得 $(x,L)\in\operatorname{epi}(f)$，即 $f(x)\leq L=\liminf f(x_n)$。故 $f$ 下半连续。

---

## HW 9 — 常见函数的次微分计算

**Original**: Compute the subdifferential $\partial f$ for: 1. $f(x)=\|x\|_1$; 2. $f(x)=\|x\|_2$; 3. $f(x)=\|x\|_\infty$; 4. $f(X)=\|X\|_*$ (nuclear norm).

**中文**：计算 $\partial f$：1. $f(x)=\|x\|_1$；2. $f(x)=\|x\|_2$；3. $f(x)=\|x\|_\infty$；4. $f(X)=\|X\|_*$。

**解答**：

**1. $f(x)=\|x\|_1=\sum_{i=1}^n|x_i|$**。各分量独立，$\partial f(x)=\partial|x_1|\times\cdots\times\partial|x_n|$。对每个分量：$x_i>0$ 时 $\partial|x_i|=\{1\}$；$x_i<0$ 时 $\partial|x_i|=\{-1\}$；$x_i=0$ 时 $\partial|x_i|=[-1,1]$。故 $\partial\|x\|_1=\{g:g_i=\operatorname{sign}(x_i)\text{ if }x_i\neq0,\;g_i\in[-1,1]\text{ if }x_i=0\}$。

**2. $f(x)=\|x\|_2$**。$x\neq0$ 时可微：$\partial\|x\|_2=\{\nabla\|x\|_2\}=\{x/\|x\|_2\}$。$x=0$ 时，由次梯度定义 $g\in\partial\|0\|_2\iff\|y\|_2\geq\langle g,y\rangle,\forall y\iff\|g\|_2\leq 1$。故 $\partial\|0\|_2=\{g:\|g\|_2\leq1\}=B_2$。

**3. $f(x)=\|x\|_\infty=\max_{1\leq i\leq n}|x_i|$**。令 $I=\{i:|x_i|=\|x\|_\infty\}$ 为活动集。$x\neq0$ 时：$\partial\|x\|_\infty=\operatorname{conv}\{\operatorname{sign}(x_i)e_i:i\in I\}=\{g:\operatorname{supp}(g)\subseteq I,\;g_i\operatorname{sign}(x_i)\geq0,\;\sum_{i\in I}|g_i|=1\}$，即活动分量符号一致、绝对值之和为 1。$x=0$ 时，活动集为全部 $2n$ 个函数 $\pm e_i$，$\partial\|0\|_\infty=\operatorname{conv}\{\pm e_i:i=1,\ldots,n\}=\{g:\|g\|_1\leq1\}=B_1$。

**4. $f(X)=\|X\|_*=\sum_i\sigma_i(X)$**。设 $X\in\mathbb{R}^{m\times n}$，紧凑 SVD 为 $X=U_r\Sigma_rV_r^{\top}$，其中 $r=\operatorname{rank}(X)$。核范数在 $X$ 处的次微分为

$$\partial\|X\|_*=\{U_rV_r^{\top}+W:\;U_r^{\top}W=0,\;WV_r=0,\;\|W\|_2\leq1\}.$$

若把 $U_r,V_r$ 扩充成正交基，也可写成 $U_rV_r^{\top}+U_\perp ZV_\perp^{\top}$，其中 $\|Z\|_2\leq1$。等价刻画为

$$G\in\partial\|X\|_*\iff \|G\|_2\leq1\quad\text{且}\quad \langle G,X\rangle=\|X\|_*.$$

特别地，若 $r=\min(m,n)$，则没有剩余的 $W$ 项，$\partial\|X\|_*=\{U_rV_r^{\top}\}$；若 $X=0$，则 $\partial\|0\|_*=\{G:\|G\|_2\leq1\}$。

---

## HW 10 — 随机矩阵的谱范数尾界

**Original**: Let $X\sim\operatorname{subG}_{m\times n}(\sigma^2)$. Show that $\forall t>0$, with probability at least $1-2\exp(-t^2)$, $\|X\|_2\leq C\sigma(\sqrt{m}+\sqrt{n}+t)$.

**中文**：设 $X\sim\operatorname{subG}_{m\times n}(\sigma^2)$（即 $\forall u\in S^{m-1},v\in S^{n-1}$，$u^{\top}Xv\sim\operatorname{subG}(\sigma^2)$）。证明以概率至少 $1-2\exp(-t^2)$ 有 $\|X\|_2\leq C\sigma(\sqrt{m}+\sqrt{n}+t)$。

**解答**：

**步骤 1（$\varepsilon$-网）**：取 $S^{n-1}$ 的 $1/4$-网 $\mathcal{N}$，$|\mathcal{N}|\leq9^n$；取 $S^{m-1}$ 的 $1/4$-网 $\mathcal{M}$，$|\mathcal{M}|\leq9^m$。

**步骤 2（网逼近）**：谱范数可写成

$$\|X\|_2=\sup_{\|u\|_2=1,\|v\|_2=1}|v^{\top}Xu|.$$

对任意单位向量 $u,v$，取 $u_0\in\mathcal{N}$、$v_0\in\mathcal{M}$ 使 $\|u-u_0\|_2,\|v-v_0\|_2\leq1/4$。则

$$\begin{aligned}
|v^{\top}Xu|
&\leq |v_0^{\top}Xu_0|+|(v-v_0)^{\top}Xu_0|+|v^{\top}X(u-u_0)|\\
&\leq \max_{a\in\mathcal{M},b\in\mathcal{N}}|a^{\top}Xb|+\frac{1}{4}\|X\|_2+\frac{1}{4}\|X\|_2.
\end{aligned}$$

取上确界得到

$$\|X\|_2\leq2\max_{a\in\mathcal{M},b\in\mathcal{N}}|a^{\top}Xb|.$$

**步骤 3（联合界 + sub-Gaussian 尾）**：对固定 $a,b$，$a^{\top}Xb$ 是参数至多为 $\sigma^2$ 的 sub-Gaussian 随机变量，因此存在绝对常数 $c>0$，使

$$\mathbb{P}(|a^{\top}Xb|>s)\leq2\exp\left(-c\frac{s^2}{\sigma^2}\right).$$

由联合界，

$$\mathbb{P}(\|X\|_2>2s)\leq2\cdot9^{m+n}\exp\left(-c\frac{s^2}{\sigma^2}\right).$$

取

$$s=C_0\sigma(\sqrt{m}+\sqrt{n}+t),$$

其中 $C_0$ 足够大。由于 $(\sqrt{m}+\sqrt{n}+t)^2$ 可同时支配 $m+n$ 与 $t^2$，可令

$$c\frac{s^2}{\sigma^2}\geq (m+n)\log 9+t^2,$$

从而

$$\mathbb{P}(\|X\|_2>2C_0\sigma(\sqrt{m}+\sqrt{n}+t))\leq2e^{-t^2}.$$

把 $2C_0$ 记为新的绝对常数 $C$，即得以概率至少 $1-2e^{-t^2}$，

$$\|X\|_2\leq C\sigma(\sqrt{m}+\sqrt{n}+t).$$
