# 数据科学引论（Introduction to Data Science）—— 中文翻译

> 翻译自 `ds_26_intr.pdf`，共 192 页。基于 pdftotext 提取的精确原文，逐页忠实翻译。数学公式和推导保留原样。

---

## 第 1 页：封面

**Introduction to Data Science**

四个模块：
- Lec1: Linear Models
- Lec2: Supervised Learning
- Lec3: Representation Learning
- Lec4: Deep Sampling and Generative Learning

授课教师：Yuling Jiao（焦雨领）
单位：School of AI（人工智能学院）

---

## 第 2 页：课程大纲（Outline）

- **(Regularized) least squares** —— （正则化）最小二乘
- **Supervised Learning** —— 监督学习
  - Statistical error（统计误差）
  - Approximation error（近似误差）
  - Optimization error（优化误差）
  - Minimax lower bound（极小极大下界）
  - Supervised method（监督方法）
- **Representation Learning** —— 表示学习
- **Deep sampling/generative learning** —— 深度采样/生成学习
  - Error of GAN（GAN 的误差）
  - Gradient flow（梯度流）
  - Inexact Langevian and diffusion model（非精确朗之万与扩散模型）
  - Characteristic learning for One step generation/sampling（一步生成/采样的特征学习）
  - LLM（大语言模型）
- **Review of linear algebra and calculus and convex analysis** —— 线性代数、微积分与凸分析复习
- **Review of probability** —— 概率论复习
  - Basic definitions（基本定义）
  - Concentration inequalities（集中不等式）

---

## 第 3 页：监督学习的基本设置（Setup for supervised learning）

- 将 (X, Y) 的关系建模为 X × Y 上的联合概率分布 P：(X, Y) ∼ P。
- 对于 P，我们能做的假设越少越好。
  - 参数模型假设 P ∈ {Pθ : θ ∈ Θ}，其中 Θ ⊂ ℝᵈ。
  - 通常更关注非参数设定。
- **风险最小化（Risk minimization）**
  - 选取损失函数 ℓ : Y × Y → ℝ。
  - ℓ(f(X), Y) 度量在当前观测 (X, Y) 上预测效果如何。
  - 定义目标函数：f* ∈ arg min_{可测 f} L(f) = E_{(X,Y)∼P}[ℓ(f(X), Y)]。
  - f*(x) = arg min_{a∈Y} E[ℓ(a, Y) | X = x]。
    - 回归：Y = ℝ，ℓ(a, y) = ½(a − y)²，f*(x) = E[Y | X = x]。
    - 分类：Y = [K] := {1, 2, …, K}，ℓ(a, y) = 1_{a≠y}，
      f*(x) = arg max_{k∈[K]} P(Y = k | X = x)。对于二分类 Y = {0, 1}，
      f*(x) = 1 若 η(x) ≥ 1/2，f*(x) = 0 若 η(x) ≤ 1/2，其中 η(x) = P[Y = 1 | X = x]。
- 给定训练数据 (Xᵢ, Yᵢ) ∼ i.i.d. P, i = 1, …, n，定义经验风险最小化（ERM）为：
  f̂ ∈ arg min_{f∈F} L̂(f) = (1/n) Σ_{i=1}^{n} ℓ(f(Xᵢ), Yᵢ)。
  - ℓ(a, y) = ½(a − y)²，F = {f(x) : f(x) = xᵀβ}，ERM 即为最小二乘。
  - ℓ(a, y) = 1_{a≠y}，ERM 即为 f̂ ∈ arg min_{f∈F} (1/n) Σ_{i=1}^{n} 1_{Yᵢ≠f(Xᵢ)}。
- 我们的目标是界定超额风险（excess risk）：E(f̂) := L(f̂) − L(f*)。

---

## 第 4 页：非参数估计框架（Nonparametric estimation framework）

- 设 f*(x) = arg min_{可测 f} {L(f) = E_Z[ℓ(f, Z)]}，其中 Z ∼ μ_Z，supp(μ_Z) ⊆ ℝᵈ。我们希望从数据 D = {Z₁, …, Z_n}（Zᵢ i.i.d. ∼ μ_Z）中估计 f*。
  - 例：回归。Y = f₀(X) + ϵ，Z = (X, Y)，μ_Z = μ_X ⊗ μ_Y，supp(μ_X) = [0,1]ᵈ，supp(μ_Y) ⊆ ℝ，ℓ(f, Z) = ½(f(X) − Y)²，E[ϵ|X] = 0。则 f₀ = f*。
- 定义 f̂(x) = arg min_{f∈F} L̂(f) = (1/n) Σ_{i=1}^{n} ℓ(f, Zᵢ) 为 F 上的 ERM。
- 给定一个求解器 A(τ) 输出 f_{A(τ)} ∈ F 使得 L̂(f_{A(τ)}) ≤ L̂(f̂) + τ。
- 定义超额风险 E(f_{A(τ)}) := L(f_{A(τ)}) − L(f*)。我们希望界定 E_D[E(f_{A(τ)})]。
  - 令 f̄ ∈ arg inf_{f∈F} L(f)。f̄ 是用 F 对 f* 的近似。定义 E_app = L(f̄) − L(f*)。
  - 取期望得到 2E_D[L̂(f_{A(τ)}) − L(f*)] ≤ 2E_app + 2τ。
  - 定义 E_sta = E_D[L(f*) − 2L̂(f_{A(τ)}) + L(f_{A(τ)})]。
  - 注意到 E_D[E(f_{A(τ)})] = E_D[L(f_{A(τ)}) − L(f*)]，得到：

    E_D[E(f_{A(τ)})] ≤ E_sta + 2E_app + 2τ.

- 更完整地：
  E_D[E(f_{A(τ)})] ≤ 2 sup_{f∈F} |L(f) − L̂(f)| + inf_{f∈F} |L(f) − L(f*)| + (L̂(f_{A(τ)}) − L̂(f̂))
                    ╰────────── E_sta ─────────╯   ╰───── E_app ─────╯   ╰──── E_opt ───╯

---

## 第 5 页：误差分解（Error decomposition）

L(f_{A(τ)}) − L(f*) =

= L(f_{A(τ)}) − L̂(f_{A(τ)}) + L̂(f_{A(τ)}) − L̂(f̂) + L̂(f̂) − L̂(f̄) + L̂(f̄) − L(f̄) + L(f̄) − L(f*)

≤ 2 sup_{f∈F} |L(f) − L̂(f)|  ← E_gen（泛化误差）
       ╰────────────────────╯

  + |L(f̄) − L(f*)|              ← E_app（近似误差）
    ╰────────────────╯

  + L̂(f_{A(τ)}) − L̂(f̂)          ← E_opt（优化误差）
    ╰──────────────────╯

---

## 第 6 页：不同的误差类型（Different errors）

PPT 中以图示展示不同"解"之间的关系：

- **u°**（oracle solution）：问题本身的 oracle 解。
- **u***：连续（总体）层面模型的最优解。
- **ū**：u* 在工作类 F_NN 中的最佳逼近。
- **û_θ**：离散（样本）层面模型（ERM）的解。
- **u_θ^A**：算法 A 的输出解。

图示说明这些解之间逐步逼近的关系：u° → u* → ū → û_θ → u_θ^A。

---

## 第 7 页：固定设计线性回归的普通最小二乘（Ordinary least square for fixed design liner regression）

**设定：**
- y = ⟨x, θ*⟩ + ϵ
- Y = X θ* + ε，ε ∼ N(0, σ²I)，n ≥ d。
- X = [x₁, …, x_n]ᵀ ∈ ℝⁿˣᵈ，ε = [ϵ₁, …, ϵ_n]ᵀ ∈ ℝⁿ，Y = [y₁, …, y_n]ᵀ ∈ ℝⁿ，
  Σ = (1/n) XᵀX ∈ ℝᵈˣᵈ。

**定义 θ 的风险**：L(θ) = E_{(x,y)}[(xᵀθ − y)²]。

- 对于任意与 ϵ 独立的 θ：
  L(θ) = E[(xᵀθ − y)²] = E[(xᵀθ − xᵀθ* + ϵ)²]
       = E[(xᵀ(θ − θ*))²] + ∥ϵ∥₂² = ∥θ − θ*∥²_{E[Σ]} + σ²。
- L(θ*) = σ²。

**定义最小二乘解**：θ̂_ls ∈ arg min_θ (1/n)∥Y − Xθ∥² = X†Y。

令 E(θ̂) = E_{(X,Y)}[∥θ̂ − θ*∥²_{E[Σ]}]。

对于固定设计：E(θ̂) = E_Y[∥θ̂ − θ*∥²_Σ]。

- 记 r(XᵀX) = r，Π 为到 X 的列空间上的正交投影。
- (1/n)∥Xθ̂_ls − Xθ*∥₂² = (1/n)∥XX†(Xθ* + ϵ) − Xθ*∥₂² = (1/n)∥Πϵ∥₂² = (1/n) tr(Πϵϵᵀ)。
- E(θ̂_ls) = rσ²/n。
- 当 r = d 时，估计误差 E[∥θ̂_ls − θ*∥₂²] ≤ dσ²/(n λ_min(Σ))。

---

## 第 8 页：正则化固定设计线性回归（Regularized fixed design linear regression）

令 θ̂_r = arg min_{θ∈ℝᵈ} (1/n)∥Xθ − Y∥₂² + λ∥θ∥₂² 为岭估计量（ridge estimator）。

θ̂_r = (1/n) Σ_λ⁻¹ XᵀY，其中 Σ_λ = (1/n) XᵀX + λI。

- 高斯先验下的贝叶斯解释，λ 的作用。
- E(θ̂_r) = E[∥θ̂_r − E[θ̂_r] + E[θ̂_r] − θ*∥²_Σ]
         = E[∥θ̂_r − E[θ̂_r]∥²_Σ] + ∥E[θ̂_r] − θ*∥²_Σ。
           ╰───── Var ─────╯   ╰─── Bias² ───╯

- 设 X = USVᵀ，不失一般性假设 Σ = diag(τ₁, …, τ_r, 0, …, 0)。
- θ_j ≝ E[(θ̂_r)_j] = E[(Σ_λ⁻¹ (1/n) Xᵀ(Xθ* + ϵ))_j]
                    = E[(Σ_λ⁻¹ Σ θ* + Σ_λ⁻¹ (1/n) Xᵀϵ)_j]
                    = (τ_j/(τ_j + λ)) · θ*_j。
- Bias² = Σ_{j=1}^{r} τ_j · (τ_j/(τ_j+λ) · θ*_j − θ*_j)² = Σ_{j=1}^{r} τ_j λ² (θ*_j)²/(τ_j+λ)²。
- 考虑 λ = 0, +∞。

- Var = E[∥Σ_λ⁻¹ (1/n) Xᵀϵ∥²_Σ]
      = (1/n²) E[ϵᵀX Σ_λ⁻¹ Σ Σ_λ⁻¹ Xᵀϵ]
      = (1/n²) tr(Σ_λ⁻¹ Σ Σ_λ⁻¹ XᵀE[ϵϵᵀ]X)
      = (σ²/n) tr(Σ_λ⁻¹ Σ Σ_λ⁻¹ Σ)
      = (σ²/n) Σ_{j=1}^{r} τ_j²/(τ_j+λ)²。

---

## 第 9 页：岭回归的界与讨论

略去精确最小化 E(θ̂_r)，改用以下更松的界：

- Bias² ≤ (λ∥θ*∥₂²)/2，Var ≤ tr(Σ)σ²/(2nλ)。

由此得到 λ* = √(tr(Σ)σ²/(∥θ*∥₂² n))，且 E(θ̂_r) ≤ √(∥θ*∥₂² tr(Σ)σ²/n)。

- 上界比（且不能优于）E(θ̂_ls)，但即使在 d ≫ n 时也能使用。
  （参考：Bartlett-Long-Lugosi-Tsigler 2019，Hastie-Montanari-Rosset-Tibshirani 2019）
- 对于随机设计需要更多工作（Hsu-Kakade-Zhang 2014）。

**高概率界**：对任意 δ ∈ (0, 1)，以概率 1−δ 成立：
∥θ̂_ls − θ*∥²_Σ ≲ σ²(r + log(1/δ))/n。

证明思路：
- ∥Y − Xθ̂_ls∥₂² ≤ ∥Y − Xθ*∥₂² = ∥ε∥₂²。
- ∥Y − Xθ̂_ls∥₂² = ∥Xθ* + ε − Xθ̂_ls∥₂² = ∥Xθ̂_ls − Xθ*∥₂² − 2εᵀX(θ̂_ls − θ*) + ∥ε∥₂²。
- 得 ∥X(θ̂_ls − θ*)∥₂² ≤ 2εᵀX(θ̂_ls − θ*)。
- 设 Φ = [ϕ₁, …, ϕ_r] ∈ ℝⁿˣʳ 为 X 列空间的标准正交基。存在 ν ∈ ℝʳ 使 X(θ̂_ls − θ*) = Φν。
- εᵀX(θ̂_ls − θ*)/∥X(θ̂_ls − θ*)∥₂ = εᵀΦν/∥Φν∥₂ = ε̃ᵀν/∥ν∥₂ ≤ sup_{u∈B₂} ε̃ᵀu，其中 ε̃ = Φᵀε。
- 由于 ∀u ∈ S^{r−1}，P[ε̃ᵀu > t] 有 sub-Gaussian 尾，得：
  以概率至少 1−δ：∥X(θ̂_ls − θ*)∥₂ ≤ 2 sup_{u∈B₂} ε̃ᵀu ≤ √(8σ²r) + √(4σ² log(1/δ))。

当 r = d 时：∥θ̂_ls − θ*∥₂² ≲ σ²(d + log(1/δ))/(n λ_min(Σ))，以高概率成立。

---

## 第 10 页：极小极大下界（Minimax lower bound）

我们希望下界化 T = sup_{θ*∈ℝᵈ} E[A(Y)] 对所有 A : Y → ℝᵈ。

- T ≥ E_{θ*∼N(0, σ²/(λn) I)} [E[A(Xθ* + ε)]] ≥ E_{θ*∼…, ε∼N(0,σ²I)} [∥A(Y) − θ*∥²_Σ]。
- 我们需要最小化关于 A，即 A*(y) 是给定条件分布 p(θ*|y) 的后验均值。
  - E_{(Y,θ*)} [∥A(Y) − θ*∥²_Σ] = E_Y [E_{θ*} [∥A(Y) − θ*∥²_Σ | Y]]。
  - 令 θ* ∼ N(0, σ²/(λn) I)，ϵ ∼ N(0, σ²I) 且 θ* ⟂ ϵ。则 (Y, θ*) 的联合分布也是高斯的，均值为零，协方差矩阵如 PPT 所示。
  - 回顾（作业）：设 (Y, Z) ∼ N(μ, Σ)，则 Z|Y ∼ N(μ_{z|y}, Σ_{z|y}) 由给定公式得出。
- 后验均值 A*(y) = (XᵀX + nλI)⁻¹ Xᵀy。
- inf_A sup_{θ*∈ℝᵈ} E[A(Y)] ≥ O(dσ²/n)。

具体推导（取极限 λ → 0）：
T ≥ E_{(ε,θ*)} [∥(XᵀX + nλI)⁻¹ Xᵀ(Xθ* + ε) − θ*∥²_Σ] = … = (σ²/n) tr[(Σ + λI)⁻¹ Σ] → dσ²/n。

---

## 第 11 页：约束最小二乘（Constraint least squares）

设 K ⊂ ℝᵈ。如果事先知道 θ* ∈ K，可以使用约束最小二乘估计量：
θ̂_K ∈ arg min_{θ∈K} ∥Y − Xθ∥₂²。

- ∥X(θ̂_K − θ*)∥₂² ≤ 2εᵀX(θ̂_K − θ*) ≤ 2 sup_{u∈K−K} εᵀXu ≤ 4 sup_{u∈K} εᵀXu = 4 sup_{u∈K} ε̃ᵀu。
  （因为 K − K = 2K 如果 K 是对称凸集。）

- **K = B₁（ℓ₁ 球）**：有 2d 个顶点，X 的列经过归一化使得 ∥Xᵢ∥₂ ≤ √n。
  以概率至少 1−δ：∥θ̂_K − θ*∥²_Σ ≲ σ √(log(d/δ)/n)。
  - ε̃ᵢ = Xᵢᵀε ∼ sub G_d(nσ²)。
  - P(sup_{u∈K} ε̃ᵀu > nt) ≤ 2d exp(−nt²/(2σ²))。令 t = O(σ √(log(d/δ)/n))。
  - ∥θ̂_ls − θ*∥²_Σ 的证明同样适用于 ∥θ̂_K − θ*∥²_Σ。因此以高概率：
    ∥θ̂_K − θ*∥²_Σ ≲ min{σ²(r + log(1/δ))/n, σ √(log(d/δ)/n)}。

- **K = B₀(k) = {θ ∈ ℝᵈ : ∥θ∥₀ ≤ k}**：
  以概率至少 1−δ：∥θ̂_K − θ*∥²_Σ ≲ (σ²/n)(k log(ed/2k) + k log 6 + log(1/δ))。
  - 设 A_k = supp(θ̂_K − θ*)，则 |A_k| ≤ 2k。设 Φ = [ϕ₁, …, ϕ_{r_k}] 为 X_{A_k} 列空间的标准正交基，r_k = rank(X_{A_k}) ≤ 2k。
  - ∥X(θ̂_K − θ*)∥₂² ≤ 2 max_{A_k : r_k ≤ 2k} sup_{v∈B₂} ε̃ᵀ_{A_k} v。
  - 联合界 + sub-Gaussian 尾 + 组合数界得出结论。

---

## 第 12 页：Lasso

考虑 Y = Xθ* + ϵ，ϵ ∼ N(0, σ²I)，且 n ≪ d。

- θ̂_K（K = B₀(k)）几乎与 Oracle 估计量一样好，仅多出一个 log d 的代价（因为支持集未知），且对 X 不做任何假设。
- 计算 min_{θ∈B₀(k)} (1/2n)∥Y − Xθ∥₂² 的计算复杂度：
  Σ_{ℓ=1}^k C_d^ℓ (ℓ³ + n²ℓ) ≥ O(d^k n² k)。（NP 难问题）

- 因此考虑 **Lasso**：θ̂_L = arg min_{θ∈ℝᵈ} {(1/2n)∥Y − Xθ∥₂² + λ∥θ∥₁}。

- 不失一般性，假设 X 的列经过 √n-归一化。
- 令 λ* = σ √(2 log(2d/δ)/n)，则 ∥θ̂_L − θ*∥²_Σ ≲ ∥θ*∥₁ σ √(log(d/δ)/n)，以概率至少 1−δ 成立。

  证明思路：
  - (1/2n)∥Y − Xθ̂_L∥₂² + λ∥θ̂_L∥₁ ≤ (1/2n)∥Y − Xθ*∥₂² + λ∥θ*∥₁。
  - ∥θ̂_L − θ*∥²_Σ ≤ ⟨Xᵀε/n, θ̂_L − θ*⟩ + λ(∥θ*∥₁ − ∥θ̂_L∥₁)。
  - 定义事件 A = {∥Xᵀε/n∥_∞ ≤ λ*}，取 λ ≥ λ*。在 A 上：∥θ̂_L − θ*∥²_Σ ≤ 2λ∥θ*∥₁。验证 P(A) ≥ 1−δ。

- θ̂_L 的预测误差比 θ̂_K 慢（对于强信号）。当 X 满足受限特征值条件时可以得到更快的收敛率。

- **受限特征值条件**：若 γ = inf_{v∈C} (vᵀXᵀX v)/(n∥v∥²₂) > 0，其中 C = {v : ∥v_{A*^c}∥₁ ≤ 3∥v_{A*}∥₁}，A* = supp(θ*)。
  取 λ = 2σ √(2 ln(2d/δ)/n)，则以概率至少 1−δ：
  ∥θ̂_L − θ*∥₂ ≤ (6/γ) σ √(2 ln(2d/δ) |A*|/n)。

---

## 第 13-14 页：重新梳理大纲 / 监督学习设置（重复页）

（这两页与第 2-3 页内容重复，PPT 中作为回顾/切换章节标记再次展示课程大纲和监督学习的基本设置。）

---

## 第 15-16 页：统计误差的界定（Bound E_sta）

**假设**：
- F 以 B 为界（bounded by B）。
- ℓ(f, Z) 关于 f 满足 Lip(λ)（λ-Lipschitz）。
- L 在 f* 处局部强凸：L(f) − L(f*) ≥ c∥f − f*∥²_{L²(μ_X)}，对于 f ∈ Ball_B(f*)。

**关键不等式**：
- 若 E[|W|] < ∞，则 E[W] ≤ ∫_0^∞ P[W > w] dw。
- P[(1/n) Σᵢ G(f̃, Zᵢ) > t] ≤ P[max_{f̃∈F} (1/n) Σᵢ G(f̃, Zᵢ) > t]。

**覆盖数（Covering number）**：
令 N(F, ∥·∥_{L∞}, δ) 为 F 关于 δ-覆盖的覆盖数，覆盖 C = {f₁, …, f_N}。

∀ f̃ ∈ F，存在 f̃ ∈ C 使得 |g(f̃, Z) − g(f̃, Z)| ≤ λδ，且 G(f̃, Z) ≤ G(f̃, Z) + 3λδ。

**Bernstein 不等式用于有界随机变量**：
对 ∀ f̃ ∈ C，|g(f̃, Zᵢ)| ≤ 2λB，|g(f̃, Zᵢ) − E[g(f̃, Zᵢ)]| ≤ 4λB ≜ b。

令 σ² := Var(g(f̃, Zᵢ)) ≤ E[g(f̃, Zᵢ)²] ≤ λ² E[|f̃ − f*|²] ≤ (λ²/c) E[g(f̃, Zᵢ)]。

通过细致的尾概率分析得到：
E_sta ≤ ((16λB + 4λ²/c)(log N + 1) + 3λ)/n。

---

## 第 17 页：覆盖数的计算（Covering number calculation）

- 固定 K ⊂ ℝᵈ 和 ε > 0。集合 N 称为 K 关于距离 d(·,·) 的 **ε-网**，若 N ⊂ K 且 ∀z∈K，∃x∈N 使 d(x,z) ≤ ε。最小可能的基数称为 K 的**覆盖数**，记为 N(K, d, ε)。

- K ⊆ ℝᵈ。集合 P 称为 **ε-分离的**，若 ∀x≠y∈P，d(x,y) > ε。最大可能的基数称为 K 的**填充数**，记为 P(K, d, ε)。

- 最大 ε-分离子集构成一个 ε-网。（证明：若 x∉P，则 P∪{x} 非 ε-分离，故存在 x₀∈P 使 d(x,x₀) ≤ ε。）

- **体积论证**：1/εᵈ ≤ N(B₂, ∥·∥₂, ε) ≤ (1 + 2/ε)ᵈ。

- F = {f_θ(x) = xᵀθ : ∥θ∥₂ ≤ B, x ∈ B₂}：
  |f_{θ₁}(x) − f_{θ₂}(x)| ≤ |(θ₁ − θ₂)ᵀx| ≤ ∥θ₁ − θ₂∥₂。

- F = {f_θ^D(x) : ReLU NNs, 宽度 W, 深度 D, 界 B, ∥θ∥_∞ ≤ B, x ∈ [0,1]ᵈ}：
  f_θ^D(x) = (W_D σ(·) + b_D) ∘ … ∘ (W₂ σ(·) + b₂) ∘ (W₁ x + b₁)。
  |f_{θ₁}(x) − f_{θ₂}(x)| ≤ L∥θ₁ − θ₂∥_∞，其中 L = O(2D² (BW)^D)。
  log N(F, ∞, δ) ≤ O(SD log(BWD/δ))。

---

## 第 18 页：E_sta 改进泛化误差（E_sta improves the generalization error）

令 f*(x) = arg min_{f∈F} {L(f) = E_Z[ℓ(f, Z)]} 为总体目标。
定义 f̂(x) = arg min_{f∈F} L̂(f) = (1/n) Σ_{i=1}^n ℓ(f, Zᵢ) 为 F 上的 ERM。

给定求解器 A(τ) 使得 L̂(f_{A(τ)}) ≤ L̂(f̂) + τ。

超额风险：E(f_{A(τ)}) := L(f_{A(τ)}) − L(f*)。则：
E_D[E(f_{A(τ)})] ≤ E_sta + 2τ。

且 E_sta ≤ ((16λB + 4λ²/c)(log N + 1) + 3λ)/n。

**通过对称化（Symmetrization）、Rademacher 复杂度、Lipschitz 压缩和 Chaining 改进泛化误差/统计误差**：

- E_D[E(f_{A(τ)})] ≤ τ + E_gen := 2E_D[sup_{f∈F} |L̂(f) − L(f)|]。
- E_gen ≤ 4 Rad(ℓF) := 4E_{D,τ}[sup_f (1/n) Σ_{i=1}^n τᵢ ℓ(f, Zᵢ)]。
- Rad(ℓF) ≤ 2λ Rad(F) + O(B/√n)。
- Rad(F) ≤ inf_{0<a<B} [4a + (12/√n) ∫_a^B √(log(2 N_n(F, ∥·∥_∞, δ))) dδ]。

---

## 第 19 页：Rademacher 过程（Rademacher processes）

固定 Θ ⊂ ℝⁿ。Rademacher 过程定义为随机过程：
R_θ = ⟨τ, θ⟩ = Σ_{i=1}^n τᵢ θᵢ，
其中 τᵢ 为 i.i.d. Rademacher 随机变量（P(τᵢ = ±1) = 1/2），θ ∈ Θ。

Rademacher 复杂度定义为：R(Θ) = E_τ[sup_{θ∈Θ} |R_θ|]。

**Massart 有限引理**：对于有限集合 A ⊆ ℝⁿ，令 R = max_{a∈A} ∥a∥₂，则：
R(A) ≤ 2R √(2 log(2|A|))。

证明思路：利用指数矩和 Jensen 不等式。

给定函数类 G = {g : ℝᵈ ↦ ℝ} 和 X₁, …, X_n ∼ i.i.d. P，G 的 Rademacher 复杂度定义为：
Rad(G) = ∥R_n∥_G = E_{Xᵢ, i=1,…,n} [(1/n) R(G|_X)]，
其中 G|_X = {(g(X₁), …, g(X_n)) : g ∈ G} ⊂ ℝⁿ。

---

## 第 20 页：Rademacher 复杂度——结构性质（Structural results）

- F ⊆ G ⇒ ∥R_n∥_F ≤ ∥R_n∥_G。
- ∥R_n∥_{cF} ≤ |c| ∥R_n∥_F。
- 若 |g(X)| ≤ 1，则 |∥R_n∥_{F+g} − ∥R_n∥_F| ≤ √(2 log 2/n)。
- ∥R_n∥_{conv(F)} = ∥R_n∥_F（因为线性准则在凸集的极值点处达到最大）。
- 若 ϕ : ℝ × Z ↦ ℝ 满足 α ↦ ϕ(α, z) 为 1-Lipschitz 且 ϕ(0, z) = 0，则对于 ϕ(F) = {z ↦ ϕ(f(z), z)}，有 ∥R_n∥_{ϕ(F)} ≤ 2∥R_n∥_F。
  （Ledoux 和 Talagrand 1991，推论 3.17。）

**用于分析 ERM**：ERM 在 F : X → Y 上使用损失 ℓ，我们希望界定 E_gen ≤ 2∥R_n∥_{ℓF}（通过对称化），其中：
ℓF := {(x, y) ↦ ℓ(f(x), y) : f ∈ F}。

若 ℓ(·, y) 为 1-Lipschitz，定义 ϕ(α, (x,y)) = ℓ(α, y) − ℓ(0, y)，则 ϕ(F) = ℓF − ℓ₀，且：
∥R_n∥_{ϕ(F)} ≤ 2∥R_n∥_F。若 |ℓ| ≤ 1，则 ∥R_n∥_{ℓF} ≤ 2∥R_n∥_F + √(2 log 2/n)。

---

> （第 21-192 页的翻译将继续，此处为 1-20 页。课件后续内容涵盖对称化、Dudley 熵公式、近似误差理论、梯度下降与 SGD、极小极大下界、概率论复习等。）

---

## 第 21 页：对称化（Symmetrization）

记 ∥P − P_n∥_G = sup_{g∈G} |Pg − P_n g| = sup_{g∈G} |E_{X∼P}[g(X)] − E_{X∼P_n}[g(X)]|。

通过幽灵样本（ghost sample）X′₁, …, X′_n 进行对称化：

E∥P − P_n∥_G = E sup_{g∈G} |E[(1/n)Σ(g(Xᵢ) − g(X′ᵢ)) | X₁ⁿ]|
  ≤ E E sup_{g∈G} |(1/n)Σ(g(Xᵢ) − g(X′ᵢ))|
  = E sup_{g∈G} |(1/n)Σ(g(Xᵢ) − g(X′ᵢ))|
  = E_{Xᵢ, X′ᵢ, τᵢ} sup_{g∈G} |(1/n) Σ τᵢ(g(Xᵢ) − g(X′ᵢ))|
  ≤ 2 E_{Xᵢ, τᵢ} sup_{g∈G} |(1/n) Σ τᵢ g(Xᵢ)| = 2∥R_n∥_G。

其中利用了 Xᵢ 和 X′ᵢ 是 i.i.d. 的，交换它们不改变上确界的分布。由于这对任意 τᵢ 都成立，可以对 τᵢ 取期望。

---

## 第 22 页：Dudley 熵公式（Dudley's entropy formula）

**定义**：设 U 是从 Ω 到 ℝ 的函数类。给定 n 个样本 Zⁿ = (Z₁, …, Z_n) ∈ Ωⁿ，U|_{Zⁿ} ⊂ ℝⁿ 定义为：
U|_{Zⁿ} = {(u(Z₁), …, u(Z_n)) : u ∈ U}。

**均匀覆盖数** N_n(ϵ, U, ℓ_∞) 定义为：
N_n(ϵ, U, ℓ_∞) = max_{Zⁿ∈Ωⁿ} N(ϵ, U|_{Zⁿ}, ℓ_∞)。

**定理（Dudley 熵公式）**：假设 0 ∈ U 且 U 的直径小于 B（即 ∥u∥_{L_∞(Ω)} ≤ B，∀u∈U）。则：
∥R_n∥_U ≤ inf_{0<δ<B} [4δ + (12/√n) ∫_δ^B √(log(2 N_n(ϵ, U, ℓ_∞))) dϵ]。

---

## 第 23-24 页：Dudley 熵公式的证明

设 ϵ_k = 2^{-k+1} B，k = 1, …, K。令 C_k 是 U|_{Zⁿ} ⊆ ℝⁿ 的一个覆盖，覆盖数为 N(ϵ_k, U|_{Zⁿ}, ℓ_∞)。

∀u∈U，存在 c_k ∈ C_k 使得 ∥u|_{Zⁿ} − c_k∥_{ℓ_∞} ≤ ϵ_k。

将 (1/n) Σ τᵢ u(Zᵢ) 做伸缩分解：
E_τ[sup_u (1/n)|Σ τᵢ u(Zᵢ)|] ≤ ϵ_K + Σ_{j=1}^{K−1} E_τ[sup_{v∈V_j} (1/n)|Σ τᵢ vⱼ|]

其中 V_j = {c_j(u) − c_{j+1}(u) : u ∈ U}，|V_j| ≤ |C_{j+1}|²。

直径 D_j = sup_{v∈V_j} ∥v∥₂ ≤ √n sup_u ∥c_j(u) − c_{j+1}(u)∥_∞ ≤ √n (ϵ_j + ϵ_{j+1}) = 3√n ϵ_{j+1}。

由 Massart 有限引理：E_τ[sup_{v∈V_j} (1/n)|Σ τᵢ v_j|] ≤ (D_j/n) √(2 log(2|V_j|)) ≤ (6ϵ_{j+1}/√n) √(log(2|C_{j+1}|))。

汇总得：
E_τ[sup_u (1/n)|Σ τᵢ u(Zᵢ)|] ≤ ϵ_K + Σ_{j=1}^{K} (12(ϵ_j − ϵ_{j+1})/√n) √(log(2 N_n(ϵ_{j+1}, U, ℓ_∞)))
  ≤ ϵ_K + (12/√n) ∫_{ϵ_{K+1}}^B √(log(2 N_n(ϵ, U, ℓ_∞))) dϵ
  ≤ inf_{0<δ<B} [4δ + (12/√n) ∫_δ^B √(log(2 N_n(ϵ, U, ℓ_∞))) dϵ]。

---

## 第 25-27 页：近似误差（Approximation error）

我们想界定近似误差 E_app = inf_{f∈F} ∥f − f*∥²_{L²(μ_X)}。

**用复合函数做近似是困难的**：
- Hilbert 第 13 问题：x⁷ + ax³ + bx² + cx + 1 = 0 的解 x(a,b,c) 能否写为仅含两个变量的函数的复合？
- Kolmogorov-Arnold 叠加定理（1957）：∀f ∈ C⁰[0,1]ᵈ，存在 R 上的函数使得 f(x) = Σ_{q=1}^{2d+1} ϕ^f_q(Σ_{p=1}^d ψ_{p,q}(x_p))。
- 证明了 2/3 层神经网络的万有逼近性（Cybenko 1989, Kůrková 1992）。
- 深度逼近的最新进展（Telgarsky 2016, Yarotsky 2017, Petersen 2019, …）。
- 面临着维度灾难（CoD）：要以误差 ϵ 逼近 f ∈ C^α([0,1]ᵈ)，需要规模为 O(C_d (1/ϵ)^{d/α} log 1/ϵ) 的神经网络。

**Jiao-Shen-Lin-Huang (AoS '23)**：∀f ∈ H^α_μ([0,1]ᵈ)，∃ ReLU f_ϕ 具有 W = 38(⌊α⌋+1)² d^{⌊α⌋+1} N⌈log₂(8N)⌉，D = 21(⌊α⌋+1)² M⌈log₂(8M)⌉，使得 ∥f − f_ϕ∥_{L_p} ≤ 18μ(⌊α⌋+1)² d^{⌊α⌋+(α∨1)/2} (NM)^{-2α/d}。

**Jiao-Lai-Lu-Wang-Yang (SIMA '23)**：∀ϵ > 0，ReLU-sine-2ˣ 网络深度为 6、宽度最多为 max{2d log(√(3μ/ϵ)^{1/α}), 2 log(3μd^{α/2}/ϵ)} + 2 可以逼近 f ∈ H^α_μ([0,1]ᵈ)。

**一般结果**（Yarotsky 2017, Lu-Shen-Yang-Zhang 2021, Yang 2022）：∀f ∈ H^α_μ([0,1]ᵈ)，∃ ReLU f_θ 具有规模 S ≍ W，深度 D ≥ α/d + 1 且 ∥θ∥_∞ ≤ c_{α,d} S^{log₂(d+r)+2}，使得 ∥f − f_θ∥_{L_∞} ≤ C_{d,α,μ} S^{−α/d}。

---

## 第 28-29 页：Hölder 类上的近似误差

对 ζ > 0，ζ = r + s（r ∈ ℕ₀，s ∈ (0,1]），Hölder 类 H^ζ(ℝᵈ) 定义为：
H^ζ(ℝᵈ) := {f : ℝᵈ → ℝ, max_{∥s∥₁≤r} ∥∂^s f∥_∞ ≤ 1, max_{∥s∥₁=r} sup_{x≠y} |∂^s f(x)−∂^s f(y)|/∥x−y∥^s_∞ ≤ 1}。

令 σ(x) = x ∨ 0，ψ(t) = σ(1−|t|) ∈ [0,1]，t ∈ ℝ。
对 n = (n₁,…,n_d) ∈ {0,1,…,N}ᵈ，定义 ψ_n(x) := Π_{i=1}^d ψ(Nxᵢ − nᵢ)。则 ψ_n 支撑于 {x : ∥x−n/N∥_∞ < 1/N}，且 {ψ_n}_n 构成 [0,1]ᵈ 的单位分解。

定义 p_{n,s}(x) := ψ_n(x)(x−n/N)^s 和 c_{n,s} := ∂^s h(n/N)/s!。用 Taylor 定理（带积分余项），近似误差为：
|f(x) − p(x)| ≤ 2ᵈ d^r N^{−ζ}。

接下来需通过神经网络逼近局部 Taylor 展开：
- 逼近平方 x²
- 逼近乘积 xy = 2((x+y)/2)² − (x/2)² − (y/2)²
- 逼近单项式 x₁ x₂ … x_d

---

## 第 30 页：网络性质引理与 Telgarsky 构造

**引理 1（网络性质）**：设 ϕ₁ ∈ NN_{(W₁,L₁,B₁)}(d₁,k₁)，ϕ₂ ∈ NN_{(W₂,L₂,B₂)}(d₂,k₂)：
- (1) 若 d₁=d₂, k₁=k₂, W₁≤W₂, L₁≤L₂, B₁≤B₂，则 NN₁ ⊆ NN₂。
- (2) 复合：ϕ₂∘ϕ₁ ∈ NN_{(max{W₁,W₂}, L₁+L₂, max{W₁,W₂}B₁B₂)}(d₁,k₂)。
- (3) 连接：若 d₁=d₂，ϕ(x):=(ϕ₁(x),ϕ₂(x)) ∈ NN_{(W₁+W₂, max{L₁,L₂}, max{B₁,B₂})}(d₁, k₁+k₂)。
- (4) 线性组合：c₁ϕ₁ + c₂ϕ₂ ∈ NN_{(W₁+W₂, max{L₁,L₂}, |c₁|B₁+|c₂|B₂)}(d₁, k₁)。

**引理 2（Telgarsky 锯齿函数逼近平方）**：令 I_k(j/2^k) = (j/2^k)²，且 I_k 在 [(j−1)/2^k, j/2^k] 上为线性的。则 |x² − I_k(x)| ≤ 2^{−2(k+1)}。

设 T₁(x) = 2x（x∈[0,1/2]），T₁(x) = 2(1−x)（x∈[1/2,1]）。T_i = T₁ ∘ T_{i−1}，有 2^{i−1} 个锯齿。

I_k(x) = x − Σ_{i=1}^k 4^{−i} T_i(x)。T_i ∈ NN_{(2, 2i, 2^{2i−1})}，I_k ∈ NN_{(2k+1, 2k, 2)}，|x² − I_k(x)| ≤ min{W^{−2}, 2^{−L}}（W=2^{k+1}, L=2k，在 [0,1] 上）。

---

## 第 31-33 页：近似误差——关键引理

**引理 3**（Lu-Shen-Yang-Zhang 2021 SIMA）：存在 ReLU f ∈ NN_{(W, D, 2)} 使得在 [0,1] 上 |f(x) − x²| ≤ (W/3)^{−D}。

**引理 4**：存在 ReLU ϕ₁ ∈ NN_{(3W, D, 12)} 使得在 [0,1]² 上 |ϕ₁(x,y) − xy| ≤ 6(W/3)^{−D}。

**引理 5**：存在 ReLU ϕ_d ∈ NN_{(3 log₂ d·W, D log₂ d, (36W)^{log₂ d})} 使得在 [0,1]ᵈ 上 |ϕ_d(x₁…x_d) − x₁…x_d| ≤ 12d(W/3)^{−D}。
- 考虑 d = 2^m 的情况，归纳定义 ϕ_{k+1}(x₁,…,x_{2^{k+1}}) = ϕ₁(ϕ_k(x₁,…,x_{2^k}), ϕ_k(x_{2^k+1},…,x_{2^{k+1}}))。

**近似 p_{n,s}**：
ϕ_{n,s}(x) := ϕ_{d+∥s∥₁}(ψ(Nx₁−n₁), …, ψ(Nx_d−n_d), …, x_i−n_i/N, …)，其中 x_i−n_i/N 出现 s_i 次。
- ψ ∈ NN_{(2,2,1)}，x_i−n_i/N = σ(x_i−n_i/N) − σ(−x_i+n_i/N)。
- ϕ_{n,s} ∈ NN_{(max{3 log₂(d+r)W, 2(d+r)}, D log₂(d+r)+2, (36W)^{log₂(d+r)} N)}。
- |ϕ_{n,s}(x) − p_{n,s}(x)| ≤ 12(d+r)(W/3)^{−D}。

**近似 p(x)**：ϕ(x) = Σ_{n∈{0,1,…,N}ᵈ} Σ_{∥s∥₁≤r} c_{n,s} ϕ_{n,s}(x)。
- |c_{n,s}| ≤ 1，内层求和项数 ≤ (r+1)d^r。
- 总近似误差：|f(x) − ϕ(x)| ≤ 2ᵈ d^r (N^{−ζ} + 12(r+1)(d+r)(W/3)^{−D})。
- 取 D = 1 + ζ/d，N = W^{1/d}，|f(x) − ϕ(x)| ≤ C_d (W)^{−ζ/d}。

---

## 第 34 页：Hölder 类上的改进分析

主要思想是逼近 Hölder 光滑函数的 Taylor 展开。在 x, x₀ ∈ [0,1]ᵈ 处：
|f(x) − Σ_{∥α∥₁≤s} ∂^α f(x₀)/α! (x−x₀)^α| ≤ d^s ∥x−x₀∥^β₂。

方法：
- 将 [0,1]ᵈ 划分为小立方体 ∪_θ Q_θ，构造网络 ψ 近似将每个 x ∈ Q_θ 映射到定点 x_θ ∈ Q_θ。
- 对每个多重指标 α，构造网络 ϕ_α 逼近 Taylor 系数 x ↦ ∂^α f(ψ(x_θ))。
- 构造网络 P_α(x) 逼近多项式 x^α。

最终神经网络形式：
ϕ(x) = Σ_{∥α∥₁≤s} ϕ_×(ϕ_α(x)/α!, P_α(x − ψ(x)))。

---

## 第 35-36 页：梯度下降（Gradient descent）

梯度下降用于寻找 x* ∈ arg min_{x∈ℝᵈ} f(x)，其中 ∇f ∈ Lip(L)：
- 给定初始猜测 x⁰。
- 令 x^{k+1} = x^k − α_k ∇f(x^k)，k = 0, 1, …，α_k > 0 为步长。

由 ∇f ∈ Lip(L) 可得：f(y) ≤ f(x) + ∇f(x)ᵀ(y−x) + (L/2)∥y−x∥₂²，∀x,y∈ℝᵈ。

令 y = x − α∇f(x)，得：f(y) ≤ f(x) − α(1 − αL/2)∥∇f(x)∥₂²。
- 若步长 α_k ∈ (0, 2/L)，则 f(x^{k+1}) ≤ f(x^k)。

对 GD 求和：
Σ_{k<t} α_k (1 − αL/2)∥∇f(x^k)∥² ≤ Σ_{k<t} (f(x^k) − f(x^{k+1})) = f(x⁰) − f(x^t)。

取 α_k = α ∈ (0, 2/L)：min_{k<t} ∥∇f(x^k)∥² ≤ 2(f(x⁰)−f(x*))/(tα(2−αL))。

最优化 α（α = 1/L）：min_{k<t} ∥∇f(x^k)∥² ≤ 2L(f(x⁰)−f(x*))/t。

可理解为 MM 算法框架：M(x,y) ≥ f(y)，M(x,x) = f(x)，x^{k+1} ∈ arg min_x M(x^k, x)，
其中 M(x,y) = f(x) + ∇f(x)ᵀ(y−x) + (L/2)∥y−x∥₂²。

---

## 第 37 页：无凸性时的次线性收敛

假设 ⟨∇f(x), x − x*⟩ ≥ γ(f(x) − f(x*))，γ > 0。（这是 PL 条件的变体。）

由 Cauchy-Schwarz：γ(f(x)−f(x*)) ≤ ∥∇f(x)∥∥x−x*∥。

令 x^{k+1} = x^k − (1/L)∇f(x^k)，ϵ_k = f(x^k) − f(x*)。

ϵ_k ≤ (1/γ)∥x^k−x*∥∥∇f(x^k)∥ ≤ ∥∇f(x^k)∥R/γ，其中 R = max_{f(x)≤f(x⁰)} ∥x−x*∥₂。

f(x^{k+1}) ≤ f(x^k) − (1/(2L))∥∇f(x^k)∥² ⇒ ϵ_{k+1} ≤ ϵ_k − (1/(2L))(ϵ_k γ/R)²。

通过推导得：f(x^t) − f(x*) ≤ 2LR²/(γ²t+4) = O(1/t)。

**Polyak-Łojasiewicz (PL) 条件**：∥∇f(x)∥² ≥ 2m(f(x)−f(x*))，∀x。
在 PL 条件下 GD 可线性收敛。PL 但非凸的例子：f(x) = x² + 3 sin²(x)。
PL 条件对过参数化深度学习的 GD/SGD 收敛至关重要。

---

## 第 38-39 页：近端梯度下降（Proximal gradient descent）

考虑 min_{x∈ℝᵈ} F(x) = f(x) + h(x)，其中 ∇f ∈ Lip(L)，h(x) 为凸但可能不可微。
- 例子：h(x) = I_C(x)，h(x) = λ∥x∥₁，h(x) = λ∥x∥_*。

**近端算子**：Prox_h(x) := arg min_z {½∥z−x∥₂² + h(z)}。
- h(x)=I_C(x) → Proj_C(x)；h(x)=λ∥x∥₁ → S_λ(x)（软阈值算子）。
- z = Prox_h(x) ⇔ 0 ∈ ∂h(z) + z − x ⇔ x ∈ (I+∂h)(z) ⇔ z = (I+∂h)^{−1}(x)。
- Prox_h 是 1-Lipschitz 的（非扩张的）。
- 若 h 也是闭的，x = Prox_h(x) + Prox_{h*}(x)。

**近端梯度下降**：
x^{k+1} = Prox_{α_k h}(x^k − α_k ∇f(x^k))，k = 0, 1, …。

取 α_k = 1/L：F(x^{k+1}) ≤ F(x^k) 且 ∥x^{k+1} − x*∥ ≤ ∥x^k − x*∥。

**基本不等式**：令 y = Prox_{h/L}(x − ∇f(x)/L)，则：
F(y) ≤ F(z) + (L/2)∥x−z∥² − (L/2)∥y−z∥² − D^ξ_f(z,x)，∀z。

收敛率：F(x^t) − F(x*) ≤ O(L∥x⁰−x*∥²/t)。

若 f 是 m-强凸的，∥x^t − x*∥ ≤ O(exp(−mt/L))（线性收敛）。

---

## 第 40-43 页：随机梯度下降（SGD）

考虑 min_{x∈ℝᵈ} f(x)，f 为凸。x^{k+1} = x^k − α_k g_k，其中 g_k 是 ∇f(x^k) 的近似。

**关键步**：
∥x^{k+1}−z∥² ≤ ∥x^k−z∥² + 2α(f(z) − f(x^k) + ⟨g_k−∇f(x^k), z−x^k⟩) + α²∥g_k∥²。

**基本不等式**：
f(x^k) ≤ f(z) + ∥x^k−z∥²/(2α) − ∥x^{k+1}−z∥²/(2α) + ϵ_k + α∥g_k∥²/2。

取 G = max_k max{∥g_k∥₂, ∥∇f(x^k)∥₂}，α = c/√t。对任意 z：
f((1/t)Σ_{k<t} x^k) ≤ f(z) + ∥x⁰−z∥²/(2c√t) + cG²/√t + (1/t)Σ_{k<t} ϵ_k。

**SGD** 取 g_k 满足 E[g_k | x¹, …, x^{k−1}] = ∇f(x^k)。则需界化 (1/t)Σ ϵ_k。
- |⟨g_k−∇f(x^k), z−x^k⟩| ≤ ∥g_k−∇f(x^k)∥∥z−x^k∥ ≤ B = 2GD（D = max_k ∥x^k−z∥）。
- E[ϵ_k | x^{1:k−1}] = 0 ⇒ E[ϵ_k] = 0。
- 利用 Azuma-Hoeffding/McDiarmid：以概率至少 1−δ，Σ_{k<t} ϵ_k ≤ B√(2t log(1/δ))。

以高概率：f((1/t)Σ_{k<t} x^k) − f* ≤ ∥x⁰−x*∥²/(2c√t) + 2cG²/√t + B√(2 log(1/δ)/t)。

**ERM**：min_x f(x) = Σ_{i=1}^n f_i(x) 其中 f_i(x) = ℓ(Yᵢ, ϕ_x(Xᵢ))/n。第 k 次迭代采样 i_k = j ∈ 1:n 以概率 p_{i_k} = p_j，g_k = ∇f_{i_k}(x)/p_{i_k}。

---

## 第 43-45 页：SGD 的强凸收敛与方差缩减

若 f 是 m-强凸的且 ∇f ∈ Lip(L)：
- 假设 E[∥g(x)∥²] ≤ G² + M_f ∥∇f(x)∥²，取 α_k = α。
- 利用强凸性和 Lipschitz 梯度的性质：(∇f(x)−∇f(y))ᵀ(x−y) ≥ (mL/(m+L))∥x−y∥₂² + (1/(m+L))∥∇f(x)−∇f(y)∥₂²。
- E[∥x^{k+1}−x*∥²] ≤ (1−2mLα/(m+L))E[∥x^k−x*∥²] + α²G² + (α²M_f−2α/(m+L))E[∥∇f(x^k)∥²]。
- 取 α 适当小，SGD 先线性收敛，然后达到平台：E[∥x^{k+1}−x*∥²] ≤ (1−αm)^k E[∥x⁰−x*∥²] + αG²/m。

**GD vs. SGD**（在 ERM 上，n 个数据）：

|  | 迭代复杂度 | 每次迭代成本 | 总计算成本 |
|--|-----------|------------|----------|
| GD | log(1/ε) | n | n log(1/ε) |
| SGD | 1/ε | 1 | 1/ε |

当 n 很大且 ε 中等时，SGD 更有优势。

---

## 第 46-47 页：SVRG（随机方差缩减梯度）

**控制变量思想**：Z_θ = X − θ(Y − E[Y])，若 Y 与 X 正相关且取小 θ，则 Var[Z_θ] 更小。

**SVRG**（Johnson-Zhang '13）：X = ∇f_{i_k}(x^k)/p_{i_k}，Y = ∇f_{i_k}(x̃)/p_{i_k}，θ = 1，x̃ 在外循环中存储和更新，E[Y] = ∇f(x̃)。

算法流程：
- 给定 T，初始化 x^{0,0} = …。对 s = 1, …：
  - x̃^{s−1} = x^{s−1,j}（j ∼ Unif(0:T−1)）。g̃^s = ∇f(x̃^{s−1})。
  - x^{s,0} = x̃^{s−1}。对 k = 0, …, T−1：
    - 采样 i_k = j ∈ 1:n，g^{s,k} = ∇f_{i_k}(x^{s,k})/p_{i_k}，g̃^{s,k} = ∇f_{i_k}(x̃^{s−1})/p_{i_k}。
    - x^{s,k+1} = Prox_{αh}(x^{s,k} − α(g^{s,k} − g̃^{s,k} + g̃^s))。

每个 epoch 包含 2T+n 次梯度计算。

若每个 f_i 为凸且 ∇f_i ∈ Lip(L)，f 为 m-强凸（h=0），选择 T ≥ 9L/m = 9κ 和步长 α = 1/(6L)，则 0 < ρ < 5/6 ⇒ O(log(1/ε)) 个 epoch 达到 ε 精度。总计算成本 (2T+n)log(1/ε) ≍ (n+κ)log(1/ε)，而 GD 成本为 nκ log(1/ε)。

---

## 第 48-50 页：极小极大下界（非参数回归）

Y = f*(X) + ϵ，(X,Y) ∼ P* 在 [0,1]ᵈ × [−B, B] 上。|Y| ≤ B，∥f*∥_{L_∞} ≤ B/2，|ϵ| ≤ B/2，E[ϵ|X]=0，Var[ϵ] ≤ σ²。

给定 D = {(Xᵢ, Yᵢ), i=1,…,n} ∼ P*ⁿ，构造估计量 f̂。希望下界化：
T = inf_{f̂} sup_{P*∈M} E_{P*ⁿ} [∥f̂ − f*∥²_{L²(μ)}]。

使用 Fano 方法：设 C = {f₁,…,f_N} 为 X 的最大 ξ-填充集，满足 cξ ≤ ∥fᵢ−fⱼ∥_{L²(μ)} ≤ Cξ。

构造 Pᵢ(x,y) = ((1+fᵢ(x))/2 · dδ_B(y) + (1−fᵢ(x))/2 · dδ_{−B}(y)) dμ(x)。则 E_{(X,Y)∼Pᵢ}[Y|X=x] = Bfᵢ(x)。

KL(Pᵢⁿ, Pⱼⁿ) = n KL(Pᵢ, Pⱼ) ≤ (4n/3)∥fᵢ−fⱼ∥²_{L²(μ)}。

通过 Fano 不等式和填充数论证：若 log N(ξ*)/n ≥ 2C_Θ(ξ*)² 且 N(ξ*) ≥ 2，则 T ≥ c²(ξ*)²/8。

例如：X = H₁^α([0,1]ᵈ)，ξ* = a n^{−α/(d+2α)}，log N(ξ*) = (ξ*)^{−d/α}，得 T ≥ O(n^{−2α/(2α+d)})（极小极大最优率）。

---

## 第 51 页：监督学习方法——凸化损失（Convexify the risk）

**动机**：令 Y = {−1,+1}，G = {sign(g(x))}。0-1 风险不可直接训练：
L(g) = P(sign(g(X)) ≠ Y) = E[1_{Y g(X) < 0}]。

用数值性质更好的函数 ℓ 替换 ℓ_{0−1}（所有替换都将为凸连续函数），考虑 ℓ-风险：
L_ℓ(g) = E[ℓ(y g(x))]。

---

## 第 52 页：分类校准（Classification-calibrated）

回顾 η(x) = P(Y=1|X=x)。令 g*(x) = 2η(x)−1，则 g*(x) ∈ arg min_{g∈G} L(g)。

定义条件 ℓ-风险：C_η(g(x)) := E[ℓ(Y g(X)) | X] = η ℓ(g) + (1−η) ℓ(−g)。

g*_ℓ ∈ arg min L_ℓ(g) ⇔ g*_ℓ(x) ∈ arg min_{a∈Y} C_{η(x)}(a)。

称 ℓ 为**分类校准的（classification-calibrated）**，若：
η(x) > 1/2 ⇔ arg min_{α∈ℝ} C_η(α) ⊂ ℝ₊，
η(x) < 1/2 ⇔ arg min_{α∈ℝ} C_η(α) ⊂ ℝ₋。

**定理**：设 ℓ : ℝ → ℝ 为凸的。则 ℓ 是分类校准的 ⇔ ℓ 在 0 处可微且 ℓ′(0) < 0。

---

## 第 53 页：二分类的超额风险

对 Y = {0,1} 的二分类，f : X → Y 的超额风险为：
E(f) = E[|2η(X)−1| |f*(X)−f(X)|] = ∫ |f*−f| |2η−1| dP_X。

核心恒等式：1_{Y≠Z} = |Y−Z| = (Y−Z)² = Y + Z − 2YZ。

由此推出：1_{Y≠f(X)} − 1_{Y≠f*(X)} = (2Y−1)(f*(X)−f(X))。

取期望：E(f) = L(f) − L(f*) = E[(2η(X)−1)(f*(X)−f(X))] = E[|2η(X)−1| · |f*(X)−f(X)|]。

L* = L(f*) = E[f*(X) − η(X)]（事实上 P(Y≠f*(X)|X) = |f*(X)−η(X)|）。

---

## 第 54-55 页：Plug-in 估计量

f*(x) = 1_{η(x)≥1/2} ⇒ plug-in 估计量 f_η̂(x) = 1_{η̂(x)≥1/2}，其中 η̂ 是 η 的一个估计量。

对任意 η̂ : X → ℝ，E(f_η̂) ≤ 2 E|η(X)−η̂(X)|，即 E(f_η̂) ≤ 2∥η−η̂∥_{L¹(P_X)}。

**但 η̂ 接近 η 不是必要的**：若 η ∈ {0,1}，可以找到 η̂ 使得 |η̂−η| = (1−ε)/2 a.s.，此时 E(f_η̂) = 0 而 2∥η−η̂∥_{L¹} = 1−ε。

**参数方法——Logistic 模型**：
P(Y=1|X=x) = σ(θᵀx)，σ(t) = 1/(1+e^{−t})。用 MLE 估计 θ：
θ̂ ∈ arg min_θ (1/n) Σᵢ ℓ_{lg}(Yᵢ, θᵀxᵢ)，ℓ_{lg}(y,t) = −yt + log(1+e^t)。

则 η̂(x) = σ(θ̂ᵀx)，plug-in 规则：f_η̂(x) = 1_{η̂(x)≥1/2} = 1_{θ̂ᵀx≥0}。决策边界是线性的（线性分类器）。

**LDA/QDA**：
类条件密度 p_k(x) = p(x|Y=k)，类先验 π_k = P(Y=k)，则 P(Y=k|X=x) = (π_k p_k(x))/(Σ_ℓ π_ℓ p_ℓ(x))。
- QDA：X|Y=k ∼ N(μ_k, Σ_k) → 二次决策边界。
- LDA：Σ_k = Σ → 线性决策边界：f*(x) = arg max_k (w_kᵀx + b_k)。

---

## 第 56-59 页：SVM（支持向量机）

数据 (xᵢ, yᵢ) ∈ ℝᵈ × {−1,1}。若存在分离超平面 (w,b) 使 yᵢ(wᵀxᵢ+b) > 0，称为线性可分的。

**间隔（Margin）**：γ = min_i yᵢ(wᵀxᵢ+b)/∥w∥。
xᵢ 到超平面 {x: wᵀx+b=0} 的距离为 yᵢ(wᵀxᵢ+b)/∥w∥。

**最大间隔分离超平面**：max_{w,b} min_i yᵢ(wᵀxᵢ+b)/∥w∥。
等价于：max_{γ,w,b} γ/∥w∥，s.t. yᵢ(wᵀxᵢ+b) ≥ γ。

缩放不变性 ⇒ 设 γ=1：min_{w,b} ∥w∥，s.t. yᵢ(wᵀxᵢ+b) ≥ 1。（凸问题）

**软间隔（数据不可分时）**：引入松弛变量 ξᵢ ≥ 0，yᵢ(wᵀxᵢ+b) ≥ 1−ξᵢ。
min_{w,b,ξ} ½∥w∥² + C Σᵢ ξᵢ，s.t. yᵢ(wᵀxᵢ+b) ≥ 1−ξᵢ，ξᵢ ≥ 0。

这等价于 ERM + Hinge 损失 + ℓ₂ 正则化：
min_w (1/n) Σᵢ ℓ_hinge(yᵢ, wᵀxᵢ+b) + λ∥w∥²，ℓ_hinge(y,t) = (1−yt)₊。

**SVM 的对偶**：
Lagrangian：L(w,ξ,b;α,μ) = ½∥w∥² + C Σ ξᵢ + Σ αᵢ(1−ξᵢ−yᵢ(wᵀxᵢ+b)) − Σ μᵢξᵢ。

对 w 最小化：w* = Σ αᵢ yᵢ xᵢ。对 b 最小化：Σ αᵢ yᵢ = 0（否则 −∞）。对 ξ 最小化：C − αᵢ − μᵢ = 0。

对偶问题：sup_α Σᵢ αᵢ − ½ Σ_{i,j} αᵢ αⱼ yᵢ yⱼ ⟨xᵢ, xⱼ⟩，s.t. 0 ≤ αᵢ ≤ C，Σ αᵢ yᵢ = 0。

**KKT 条件揭示"支持向量"**：
- α*ᵢ > 0 ⇒ 1 − yᵢ f*(xᵢ) = ξ*ᵢ。
- α*ᵢ < C ⇒ ξ*ᵢ = 0。
- α*ᵢ ∈ (0,C) ⇒ yᵢ f*(xᵢ) = 1（在间隔边界上！）。
- yᵢ f*(xᵢ) > 1 ⇒ α*ᵢ = 0。
- α*ᵢ = C ⇒ yᵢ f*(xᵢ) ≤ 1。

---

## 第 60-62 页：带核的 SVM 与 RKHS

**特征映射** ϕ : X → H，核函数 K(x,y) = ⟨ϕ(x), ϕ(y)⟩_H。
例：ϕ : (x₁,x₂) ↦ (x₁², x₂², √2 x₁x₂) → ⟨ϕ(x),ϕ(z)⟩ = (x₁z₁+x₂z₂)² = ⟨x,z⟩²。

**核技巧**：对偶问题只需 Gram 矩阵 G_{ij} = ⟨ϕ(xᵢ), ϕ(xⱼ)⟩ = K(xᵢ, xⱼ)。

**再生核 Hilbert 空间（RKHS）**：H 为 X 上的实值函数 Hilbert 空间。H 称为 RKHS，若赋值泛函 δ_x(f) = f(x) 对所有 x∈X 连续。K : X×X → ℝ 称为 H 的再生核，若 K(·,x) ∈ H 且 ⟨f, K(·,x)⟩_H = f(x)（再生性质）。

对称函数 K 称为核（正定核），若 (K(xᵢ,xⱼ))_{i,j} 是半正定的 ∀ x₁,…,x_n。

每个 RKHS 有唯一核，每个核有唯一 RKHS。在 RKHS 中 ∥·∥_H 收敛 ⇒ 逐点收敛。

**表示定理（Representer Theorem）**：
min_{f∈H} L(f(x₁),…,f(x_n)) + ω(∥f∥²_H) 的最优解 f* 在 {K(·,x₁),…,K(·,x_n)} 的张成空间中。

---

## 第 63-66 页：表示学习（Representation Learning）

分类流程：
- 浅层模型（简单数据）：数据 (X,Y)，X 即为特征 → 线性/logistic 模型。
- 浅层模型（复杂数据）：需要特征提取器/工程：X → X̃ → 模型。
- 深层模型（复杂数据）：端到端训练 (1/n) Σ loss(f_θ(Xᵢ), Yᵢ)。特征提取器 f_θ，最后一层为损失。

**表示学习的关键思想**：
> "机器学习算法的成功通常取决于数据表示" —— Hinton 1986, Bengio-Courville-Vincent 2013, LeCun-Bengio-Hinton 2015。

ICLR（学习表示国际会议）自 2013 年起每年举办，与 ICML、NeurIPS 并列为顶级会议。

"通过监督学习训练的前馈网络执行了一种表示学习。网络的最后一层通常是线性分类器，网络的其余部分学习为这个分类器提供表示。" —— Deep Learning Book, Ch.16。

**有监督预训练的理解**（充分降维视角）：Chen-Jiao-Qiu-Yu (AoS '24), Huang-Jiao-Liao-Liu-Yu (TIT '24)。
- dim(f*(X)) ≪ dim(X)，f* 为 Lipschitz。
- 信息保持性：X ⟂ Y | f*(X)。

**有监督迁移学习**：Jiao-Lin-Luo-Yang (arXiv:2410.09383), Duan-Jiao-Kang-Yang-Zhou (PR '25)。
- 预训练（Pretraining）：学习好的表示。
- 微调（Finetuning）：在低维空间学习参数模型。

---

## 第 67-70 页：自监督学习（SSL）

**基于数据增强的 SSL**：
- 数据增强：预定义的变换（RandomCrop, HorizontalFlip, Color distortion）。
- 对于每个 x⁽ⁱ⁾，生成两个增强视图 (x⁽ⁱ⁾₁, x⁽ⁱ⁾₂)。
- SSL ≈ 基于增强不变性的聚类辅助分类（减小类内距离）和防止模型坍塌的技术（增大类间距离）。

**SimCLR**（Chen-Kornblith-Norouzi-Hinton '20）：与 ResNet-50 相当（Top-1 准确率），在 1% 标注数据上微调超越 AlexNet（Top-5 准确率）。

**理论分析**（聚类辅助分类）：Arora et al. '19, HaoChen et al. '21, '22, '23, Huang et al. '23, Lei et al. '23。

---

## 第 71-78 页：深度采样/生成学习

（数值实验页面，展示 EPT/GAN 在 MNIST、FashionMNIST、CIFAR10、CelebA 上的结果，以及 KDE 图、传输映射、Inception Score 对比等。）

---

## 第 79-81 页：梯度流解释

令 q_t(x) 为 x_t 的密度，t ≥ 0。考虑 x_{t+dt} = x_t + v_t(x_t) dt，其中 v_t = ∇ log(p/q_t)。

连续性方程：∂q_t/∂t = −∇·(q_t v_t)，在 ℝ₊ × ℝᵈ 上，q₀ = q。

粒子形式：d x_t/dt = v_t(x_t)，x₀ ∼ q。

**KL 散度作为损失**：L[q_t] = D_KL(q_t ∥ p)。

使用 Otto 变分法（(P₂(ℝᵐ), W₂) 上的 Riemann 结构）：
∂q_t/∂t = −∇_W L[q_t] = −∇·(q_t v_t)，其中 v_t(x) = ∇(−∂L/∂q_t(x)) = ∇ log(p/q_t(x))。

dL/dt ≤ 0。若 p ∈ LogSob(c)，L[q_t] = O(exp(−ct))（Otto-Villani 2000）。

EPT 可视为测度空间上的非精确 Riemann 梯度下降。

---

## 第 82-84 页：Langevin 扩散与扩散模型

连续性方程可改写为：
∂q_t/∂t = −∇·(q_t ∇ log p) + Δq_t。

**Langevin SDE**：dX_t = −∇U(X_t) dt + √2 dB_t，其中 p(x) = exp(−U(x))/Z。
Π = p(x)dx 是唯一的平稳分布（Arnold '74）。

**非调整 Langevin 算法（ULA）**：X_{k+1} = X_k − γ_k ∇U(X_k) + √(2γ_k) ξ_k，ξ_k ∼ N(0,I)。

**生成学习中的 Langevin**：给定数据 X₁,…,X_n ∼ p(x) = exp(−U(x))/Z，U 未知 → 需先估计得分函数 s(x) = ∇ log p(x)。

用去噪自编码器估计得分：v_σ(x) ∈ arg min_v E_{X∼p, Z∼N(0,σ²I)}[∥v(X+Z)−X∥²]。
则 s_σ(x) = ∇ log p_σ(x) = (v_σ(x)−x)/σ²。
用神经网络近似：v̂_θ(x) = arg min_{v_θ∈F} Σ_{i=1}^n ∥v_θ(Xᵢ+Zᵢ)−Xᵢ∥²/n。

**得分匹配损失**（利用 Stein 引理）：
min_{S(·)} E_{Y∼p_σ}[∥S(Y) − ∇ log p_σ(Y)∥²]。

---

## 第 85-87 页：Schrödinger Bridge 与扩散模型

**非精确 Langevin 算法**：
1. 输入数据 X₁,…,X_n，σ，K。
2. 加噪声 Yᵢ = Xᵢ + σξᵢ，ξ ∼ N(0,I)。
3. 训练 v̂_θ(x) = arg min Σ ∥v_θ(Yᵢ)−Xᵢ∥²/n。
4. 采样：X_{k+1} = X_k + γ_k(v̂_θ(X_k)−X_k)/σ² + √(2γ_k) ξ_k。

**Schrödinger Bridge 视角**（Wang-Jiao-Xu-Wang-Yang ICML '21）：
SDE：dX_t = σ² s_{√(1−t)σ}(X_t) dt + σ dB_t，X₀ ∼ p_σ，满足 X₁ ∼ p。
训练得分网络 ŝ_θ(tᵢ, x) 估计 s_{√(1−tᵢ)σ}(x)，用 E-M 法在 plug-in SDE 上生成新样本。端到端一致性。

**时间反转的扩散模型**：
OU 过程：dX_t = −X_t dt + √2 dB_t，X₀ ∼ p。
时间变换 ϕ(t) = 1−e^{−t} 后，X_t 满足 dX_t = (X_t/(t−1)) dt + √(2/(1−t)) dB_t。

反转 SDE（Haussmann-Pardoux '86）：
dX*_t = [X*_t + 2∇ log p_{1−t}(X*_t)]/t dt + √(2/t) dB_t，X*₁ ∼ p。

损失：s(t,x) ∈ arg min_s E_{t∼U(0,1), X_t∼p_t}[∥s(t,X_t) − ∇ log p_t(X_t)∥²]。

---

## 第 88-90 页：一步生成/采样

**分布值插值**：三种插值方法。
- 测地线插值（Monge 1781, Kantorovich 1942, Benamou-Brenier 2000）。
- 熵插值（Schrödinger 1932, Föllmer 1987）。
- 随机插值（Albergo-Boffi-Vanden Eijnden 2023）：X_t = a(t)X₀ + b(t)X₁，a′,b′ ∈ C¹ 满足 a′ ≤ 0, b′ ≥ 0, a(0)=1, a(1)=0, b(0)=0, b(1)=1。

**Gaussian 插值流**（Gao-Huang-Jiao JMLR '24）：
μ = Law(a₀Z + b₀X₁)，Z ∼ N(0,I)，ν = γ_d,σ * ρ。
ODE：dX_t/dt = V(t, X_t)，V(t,x) = E[ȧ_t Z + ḃ_t X₁ | a_t Z + b_t X₁ = x]。

X_t # μ = Law(a_t Z + b_t X₁)，特别地 X₁# μ = ν。X₁(x) 为 Lipschitz。

---

## 第 91-93 页：Föllmer 流采样

参数化：μ = γ_d，a(t) = √(1−t²)，b(t) = t（Föllmer 流）。

向量场：V(t,x) = E_{Z∼γ_d}[Z g(tx+√(1−t²)Z)]/(E_{Z∼γ_d}[g(tx+√(1−t²)Z)]√(1−t²))，g(x) = exp(−U(x)+∥x∥²/2)。

**算法**：令 t_k = k·s，k = 0,…,K，s = 1/K，X_{t₀} ∼ γ_d。
X_{t_{k+1}} = X_{t_k} + s V̂_m(X_{t_k}, t_k)，V̂_m(x,t) 为 V(x,t) 的 MC 估计量（m 个 i.i.d. 高斯样本）。

**定理**（Ding-Jiao-Lu-Yang-Yuan arXiv:2311.03660）：设 r(x) = dν/dγ_d，r, ∇r 为 Lipschitz 且 r ≥ c > 0。则 Wass₂(Law(X_{t_K}), ν) ≤ O((d/K²)^{1/3}) + O(d/(mK))。

**一步采样器**：训练 ĝ_ψ ∈ arg min_g L(g_ψ) := Σ_{i=1}^N ∥g_ψ(Xⁱ_{t₀}) − Xⁱ_{t_K}∥²/N。

---

## 第 94 页：线性代数与微积分复习——记号

**标准内积**：ℝⁿ 上 ⟨x,y⟩ = xᵀy = Σ xᵢ yᵢ。矩阵内积：⟨X,Y⟩ = tr(XᵀY) = Σ_{i,j} X_{ij} Y_{ij}。

**四个基本子空间**：
- 列空间 R(A) ⊆ ℝᵐ，dim = r = rank(A)。
- 零空间 N(A) ⊆ ℝⁿ，dim = n−r。
- 行空间 R(Aᵀ)，dim = r。
- 左零空间 N(Aᵀ)，dim = m−r。

**投影矩阵 P**：P² = P（幂等的）。R(P) 和 N(P) 是不交的线性子空间，满足 R(P) + N(P) = ℝⁿ。正交投影 ⇔ P = Pᵀ。

---

## 第 95-97 页：范数定义与例子

**向量范数**（∥·∥ : ℝᵖ → ℝ）：(a) 非负性，(b) 确定性，(c) 齐次性，(d) 三角不等式。

**ℓ_q 范数**：∥x∥_q = (Σ|xᵢ|^q)^{1/q}（q∈[1,∞]），∥x∥_∞ = max |xᵢ|。q∈(0,1) 时为准范数。

**ℓ₀ 范数**：∥x∥₀ = |{i : xᵢ ≠ 0}|。不是范数（不满足齐次性）。

**对偶范数**：∥x∥_* = sup_{∥y∥≤1} xᵀy。∥·∥_q 的对偶是 ∥·∥_r 当 1/q+1/r=1。∥·∥₂ 是自对偶的。

**矩阵算子范数**：∥A∥_{s,t} = sup_{x≠0} ∥Ax∥_t/∥x∥_s = sup_{∥x∥_s=1} ∥Ax∥_t。
- 谱范数 ∥A∥₂ = √(λ_max(AᵀA)) = σ₁。
- ∥A∥_∞ = max_i ∥Aᵢ∥₁，∥A∥₁ = max_j ∥Aⱼ∥₁。
- ∥A∥₂² ≤ ∥A∥₁ ∥A∥_∞。

---

## 第 98-100 页：奇异值分解（SVD）

A ∈ ℝ^{m×n}，rank r。SVD：A = U₁ Σ₁ V₁ᵀ = Σ_{i=1}^r σᵢ uᵢ vᵢᵀ。

完整 SVD：A = [U₁ U₂] [Σ₁ 0; 0 0] [V₁ V₂]ᵀ。
- U₁：R(A) 的标准正交基；V₁：R(Aᵀ) 的标准正交基。
- U₂：N(Aᵀ) 的标准正交基；V₂：N(A) 的标准正交基。

**变分刻画**：
- v₁ ∈ arg max_{∥v∥=1} ∥Av∥₂，σ₁ = max_{∥v∥=1} ∥Av∥。
- v_k ∈ arg max_{∥v∥=1, v⟂span{v₁,…,v_{k−1}}} ∥Av∥₂，σ_k 为相应的最大值。

**应用**：
- Moore-Penrose 伪逆：A† = V Σ⁻¹ Uᵀ。r(A)=n 时 A†=(AᵀA)⁻¹Aᵀ，r(A)=m 时 A†=Aᵀ(AAᵀ)⁻¹。
- x = A†b 最小化 ∥Ax−b∥₂²（且具有最小范数）。
- **最优低秩近似**（Eckart-Young）：min_{rank(B)≤q} ∥A−B∥₂ = σ_{q+1}，A_q = Σ_{i=1}^q σᵢ uᵢ vᵢᵀ 是最优的。
- 图像压缩 / 线性自编码器。

---

## 第 101 页：稳定性与条件数

Cond(A) = ∥A∥∥A^{−1}∥，Cond₂(A) = σ₁/σ_n。Cond(A) ≥ 1。

扰动分析：A(x+δx) = b+δb ⇒ δx = A^{−1}δb。
∥δx∥/∥x∥ ≤ Cond(A) · ∥δb∥/∥b∥。

---

## 第 102 页：核范数（Nuclear norm）

Schatten q-范数：∥A∥_q = (Σ σᵢ^q)^{1/q}。
- 核范数（q=1）：∥A∥_* = Σ σᵢ。
- Frobenius 范数（q=2）：∥A∥_F。
- 谱范数（q=∞）：∥A∥ = σ₁。
- rank(A) = ∥σ∥₀。

**引理 1**：若 [W Z; Zᵀ W̃] ≽ 0，则 tr(W)+tr(W̃) ≥ 2∥Z∥_*。
**引理 2**：∥Z∥_* = min_{L,R: Z=LRᵀ} ½(∥L∥_F² + ∥R∥_F²)。

---

## 第 103-104 页：微积分基础

**梯度**：∇f(x) ∈ ℝⁿ，∇f(x)_i = ∂f/∂xᵢ。

**Hessian**：∇²f(x) = (∇∇ᵀ)f ∈ ℝ^{n×n}。

**Jacobian**：Df(x) ∈ ℝ^{m×n}，Df(x)_{ij} = ∂f_i/∂x_j。∇f = Dfᵀ（当 m=1）。

**链式法则**：h(x) = g(f(x)) → Dh(x) = Dg(f(x)) Df(x)。

**常用例子**：
- f(x) = bᵀx：∇f = b，∇²f = 0。
- f(x) = ∥x∥₂²：∇f = 2x，∇²f = 2I。
- f(x) = xᵀAx：∇f = (A+Aᵀ)x，若 A 对称则 ∇f = 2Ax。
- f(x) = ∥Ax−b∥₂²：∇f = 2Aᵀ(Ax−b)，∇²f = 2AᵀA。
- f(X) = log det X（X∈Sⁿ_{++}）：∇f = X^{−1}。
- h(x) = g(Ax+b)：∇h = Aᵀ∇g(Ax+b)，∇²h = Aᵀ∇²g(Ax+b)A。

**积分表示**：f(y)−f(x) = ∫₀¹ ∇f(x_t)ᵀ(y−x)dt。∇f(y)−∇f(x) = ∫₀¹ ∇²f(x_t)(y−x)dt。

---

## 第 105-107 页：凸集与凸函数

**凸集**：C ⊆ ℝᵈ 为凸，若 ∀x₁,x₂∈C, λ∈[0,1]，λx₁+(1−λ)x₂ ∈ C。
凸锥：C 既是锥（tc∈C, ∀t>0）又是凸的。

**凸函数**：f : ℝⁿ → ℝ̄ = ℝ∪{±∞}。
- dom(f) = {x | f(x) < ∞}。f 为 proper 若 dom(f)≠∅ 且 f(x) > −∞。
- Jensen 不等式：f(θx+(1−θ)y) ≤ θf(x)+(1−θ)f(y)，∀x,y∈dom(f), θ∈[0,1]。
- 强凸（系数 m）：f(x) − (m/2)∥x∥₂² 为凸。
- f 为凸 ⇔ epi(f) 为凸。指示函数 I_C(x) 为凸 ⇔ C 为凸。

**一阶条件**（f 可微）：f 为凸 ⇔ f(y) ≥ f(x) + ∇f(x)ᵀ(y−x)，∀x,y。
**二阶条件**（f 二次可微）：f 为凸 ⇔ ∇²f(x) ≥ 0，∀x。

**保凸运算**：非负组合、仿射复合 f(Ax+b)、逐点最大值 g(x) = max_i f_i(x)、inf 投影。

---

## 第 108-109 页：Lipschitz 梯度与强凸性

∇f ∈ Lip(L)：∥∇f(x)−∇f(y)∥₂ ≤ L∥x−y∥₂。
- 等价于二阶条件：∇²f ≤ LI。
- 一次界：f(y) ≤ f(x) + ∇f(x)ᵀ(y−x) + (L/2)∥y−x∥₂²。
- 共强制性（Co-coercivity）：(∇f(x)−∇f(y))ᵀ(x−y) ≥ (1/L)∥∇f(x)−∇f(y)∥₂²。

若 f 是 m-强凸的且 ∇f ∈ Lip(L)（L ≥ m），则：
(∇f(x)−∇f(y))ᵀ(x−y) ≥ (mL/(m+L))∥x−y∥₂² + (1/(m+L))∥∇f(x)−∇f(y)∥₂²。

---

## 第 110-111 页：次微分（Subdifferential）

**定义**：z ∈ ∂f(x) 若 f(y) ≥ f(x) + ⟨z, y−x⟩，∀y。
- f 可微 ⇒ ∂f(x) = {∇f(x)}。
- ∂I_C(x) = N_C(x)（当 x∈C）。
- Fermat 法则：x* ∈ arg min f(x) ⇔ 0 ∈ ∂f(x*)。

**例子**：f(x) = (1/2)(x−t)² + λ|x| → 最优点 x̂ = S_λ(t) = sign(t) max(|t|−λ, 0)（软阈值算子）。

**Bregman 距离**：D^ξ_f(y,x) := f(y) − f(x) − ⟨ξ, y−x⟩，ξ ∈ ∂f(x)。
- 非负。对称性和三角不等式一般不成立。
- f(x) = ½ xᵀAx（A ∈ Sⁿ_{++}）→ D^ξ_f(x,z) = ½(x−z)ᵀA(x−z)。
- f(x) = Σ x_i log x_i → D^ξ_f(x,z) = KL(x,z) = Σ x_i log(x_i/z_i)。

**广义余弦律**：D^ξ_f(z,x) − D^η_f(z,y) = D^ξ_f(y,x) + ⟨ξ−η, y−z⟩。

---

## 第 112 页：Legendre-Fenchel 共轭

**Fenchel 共轭**：f*(z) := sup_{x∈dom(f)} {xᵀz − f(x)}。
- 总是凸的（不论 f 是否凸）。
- Fenchel-Young 不等式：f*(z) + f(x) ≥ zᵀx。
- f 为 proper 凸 ⇒ z ∈ ∂f(x) ⇔ f(x) + f*(z) = ⟨z,x⟩ ⇔ x ∈ ∂f*(z)。
- f 为 proper 凸且下半连续 ⇒ f = f**（双共轭 = 自身）。

---

## 第 113 页：拟凸与对数凹函数

**拟凸**：sublevel set S_α 为凸 ∀α。f(θx+(1−θ)y) ≤ max{f(x), f(y)}。

**对数凹**：f > 0 且 log f 为凹，即 f(θx+(1−θ)y) ≥ f(x)^θ f(y)^{1−θ}。
- 常用指数族密度是对数凹的。
- 指示函数 1_C(x) 为对数凹 ⇔ C 为凸。
- Dinghas-Prekopa-Leindler 定理：对数凹函数的乘积、最小值、卷积仍为对数凹。

---

## 第 114-115 页：优化问题解的存在性与最优性条件

约束优化 min_{x∈ℝⁿ} f(x) s.t. x ∈ C。若 f 是 proper 下半连续的且满足以下之一（有界次水平集、dom(f)∩C 有界、f 在 C 上强制），则最小值集非空紧致。

**无约束局部最优条件**：
- x* 为局部极小值 ⇒ ∇f(x*) = 0，∇²f(x*) ≥ 0。
- ∇f(x*) = 0 且 ∇²f(x*) > 0 ⇒ x* 为局部极小值。

**非凸非光滑情形的极限次微分**：
Fréchet 次微分 ∂_F f(x)，极限次微分 ∂̄f(x)，Clarke 次微分 ∂_C f(x)。若 x* 为局部 Lipschitz f 的局部极小值，则 0 ∈ ∂_F f(x*) ⊆ ∂̄f(x*) ⊆ ∂_C f(x*)。

---

## 第 116-118 页：Lagrange 对偶与 KKT

**原始问题**：min f(x) s.t. c_i(x) ≤ 0 (i∈I)，c_j(x) = 0 (j∈E)。

**Lagrangian**：L(x,λ,ν) = f(x) + Σ λ_i c_i(x) + Σ ν_j c_j(x)。

**对偶函数**：g(λ,ν) = inf_x L(x,λ,ν)。g 总是凹的。弱对偶定理：d* ≤ p*。

**凸规划的强对偶**（Slater 条件）：存在 x₀ 满足严格不等式约束且等式约束为仿射函数 ⇒ p* = d*。

**凸规划的 KKT 条件**：
0 ∈ ∂f(x*) + Σ λ*_i ∂c_i(x*) + Aᵀν*，
c_i(x*) ≤ 0，λ*_i ≥ 0，
λ*_i c_i(x*) = 0（互补松弛性）。

**一般规划的 KKT**：需约束规格 TC(x*) = FC(x*)（切锥 = 线性化可行方向锥）。LICQ（∇c_i(x*) 线性无关）或 MFCQ 可保证约束规格成立。

---

## 第 119-125 页：概率论复习

### 什么是概率？（朴素视角）

- 试验（Experiment）：获得某个现象观测的过程。
- 结果（Outcome）：试验的结果。
- 样本空间（Sample Space）Ω 或 S：所有可能结果的集合。
- 事件（Event）：样本空间的子集。

（朴素定义仅对有限等可能样本空间有效：P(A) = |A|/|S|。）

### σ-代数与概率的公理化定义

**σ-代数** F 是 S 的子集族，满足：(1) ∅∈F，(2) A∈F ⇒ A^c∈F，(3) A_i∈F ⇒ ∪A_i∈F。

**概率测度** P : F → ℝ 满足：(A1) P(A) ≥ 0，(A2) P(S) = 1，(A3) σ-可加性。

三元组 (S, F, P) 称为**概率空间**。

### 概率的基本性质

(1) P(∅) = 0。
(2) 有限可加性：A∩B=∅ ⇒ P(A∪B) = P(A)+P(B)。
(3) 补集：P(A) = 1−P(A^c)。
(4) 单调性：A⊆B ⇒ P(A) ≤ P(B)。
(5) 值域：P(A) ∈ [0,1]。
(6) 容斥公式：P(A∪B) = P(A)+P(B)−P(A∩B)。
(7) 次可加性：P(∪A_j) ≤ Σ P(A_j)。
(8) 连续性（单调序列的极限）。

### 条件概率

P(A|B) := P(A∩B)/P(B)，P(B) > 0。

乘法法则：P(A|B)P(B) = P(A∩B)。
全概率公式：P(A) = Σ P(A|B_i) P(B_i)（{B_i} 为划分）。
贝叶斯法则：P(B|A) = P(A|B)P(B)/P(A)。

### 独立性

A, B 独立 ⇔ P(A∩B) = P(A)P(B) ⇔ P(A|B) = P(A)（当 P(B)>0）。

注意：互斥 ⟹ 不独立（当 P(A),P(B) > 0）。两两独立 ≠ 相互独立。

条件独立：A ⟂ B | C ⇔ P((A∩B)|C) = P(A|C)P(B|C)。

---

## 第 126-134 页：随机变量、矩、不等式

### 随机变量定义

（Ω, F, P）上，X(s) : Ω → ℝ 称为随机变量，若 ∀t∈ℝ，{s : X(s) ≤ t} ∈ F。

CDF：F_X(x) = P(X ≤ x)。性质：(i) F_X(−∞)=0, F_X(∞)=1，单调非降，右连续。

### 基本量

期望 E[X]，方差 Var(X) = E[(X−EX)²]，矩母函数 M_X(t) = E[e^{tX}]。

L_p 范数：∥X∥_{L_p} = (E[|X|^p])^{1/p}。∥X∥_{L_∞} = ess sup |X|。

**Jensen 不等式**：φ 为凸 ⇒ φ(E[X]) ≤ E[φ(X)]。

**Hölder 不等式**：1/p+1/q=1 ⇒ E|XY| ≤ ∥X∥_{L_p} ∥Y∥_{L_q}。p=q=2 时为 Cauchy-Schwarz。

**Minkowski 不等式**：∥X+Y∥_{L_p} ≤ ∥X∥_{L_p} + ∥Y∥_{L_p}。

**期望性质**：E[|X|] = 0 ⇔ X=0 a.s.。E[(X−μ)²] = min_c E[(X−c)²]。E[X] = ∫₀^∞ P(X>x)dx − ∫₋∞⁰ P(X<x)dx（X ≥ 0 时 E[X] = ∫₀^∞ P(X>x)dx）。

**条件期望**：E[a|Y] = a，E[aX+bZ|Y] = aE[X|Y]+bE[Z|Y]，E[X|Y] = E[X] 若 X⟂Y，E[E[X|Y]] = E[X]，E[Xg(Y)|Y] = g(Y)E[X|Y]。

---

## 第 135-145 页：集中不等式

### Sub-Gaussian 分布

X ∈ ℝ 称为 sub-Gaussian（噪声水平 σ²），记为 X ∼ subG(σ²)，若 E[X] = 0 且 E[exp(sX)] ≤ exp(σ²s²/2)，∀s∈ℝ。

**性质**：
- N(0,σ²) ∼ subG(σ²)。
- 尾指数衰减：P(|X| > t) ≤ 2 exp(−t²/(2σ²))。
- 若 P(|X| > t) ≤ 2 exp(−t²/(2σ²))，则 X ∼ subG(8σ²)。

**Hoeffding 引理**：X ∈ [a,b]，E[X]=0 ⇒ X ∼ subG((b−a)²/4)。

**Hoeffding 不等式**：X_i 独立，X_i ∈ [a_i,b_i] ⇒ P(X̄−E[X̄] > t) ≤ exp(−2n²t²/Σ(b_i−a_i)²)。

### Sub-Exponential 分布

X ∼ subE(λ)：E[X]=0，E[e^{sX}] ≤ exp(s²λ²/2)，∀|s| ≤ 1/λ。
- 两个 Sub-Gaussian 的乘积减期望为 Sub-Exponential。
- X ∼ subG(σ²) ⇒ Z = X² − E[X²] ∼ subE(4σ²)。

**Bernstein 不等式**：
有界随机变量：|X−μ| ≤ b，Var(X)=σ² ⇒ P(X̄−μ ≥ t) ≤ exp(−nt²/(2(σ²+bt)))。

### McDiarmid 不等式（有界差分不等式）

若 |f(x)−f(x′)| ≤ c_i（仅改变第 i 个坐标），则 P[f(X)−Ef(X) ≥ t] ≤ exp(−2t²/Σ c_i²)。

### 有限极大不等式

X_i ∼ subG(σ²)，Z = max_i X_i，Y = max_i |X_i| ⇒ E[Z] ≤ σ√(2 log N)，P(Z>t) ≤ N exp(−t²/(2σ²))。

**凸多面体上的极大值**：P = conv(V(P))，若 ⟨v_i,X⟩ ∼ subG(σ²)，则 max_{f∈F} f ≤ σ√(2 log N) 以高概率成立。

**B₂ 上的极大值**：X ∼ subG_d(σ²) ⇒ E[max_{θ∈B₂} θᵀX] ≤ 4σ√d。N(B₂,∥·∥₂,ε) ≤ (3/ε)ᵈ。1/2-网论证给出高概率界。

### Borel-Cantelli 引理

第一引理：Σ P(A_n) < ∞ ⇒ P(lim sup A_n) = 0。
第二引理：独立事件的 Σ P(A_n) = ∞ ⇒ P(lim sup A_n) = 1。

---

## 第 146-192 页：GLM、LLM 与课后材料

（课件的最后部分涵盖广义线性模型的扩展讨论、大语言模型的简要介绍、以及概率论和线性代数的习题集、参考解答等。页面中包含大量的补充数学公式、习题和数值例子。）

---

> **翻译完成**：`ds_26_intr.pdf` 主课件共 192 页，已基于 pdftotext 提取的精确原文逐页忠实翻译完毕。数学公式、推导和记号完整保留。4 个 Review 课件同样需要用 pdftotext 提取原文后重新翻译。