# Review_of_probability2 中文学习版

> 来源：`Review_of_probability2.pdf`  
> 页数：41  
> 说明：这是按页整理的中文导读/学习笔记，不覆盖原 PDF。公式和英文术语尽量保留，中文部分负责解释它们在课程中的作用。

这份 review 主要补充测度论概率、条件期望、鞅、布朗运动、SDE、Ito 公式和生成模型中的随机过程语言。

建议读法：先看每页的“本页导读”，再回到原 PDF 看公式和图；遇到证明页，优先抓证明思路和用到的工具。

## 第 1 页：概率复习

原始标题：`Review — Probability`

本页导读：

- 概率论部分从样本空间、事件、sigma 代数、概率测度和随机变量开始。
- 浓缩不等式关注随机变量偏离均值的概率，sub-Gaussian 和 sub-exponential 是常见尾部条件。

## 第 2 页：目录

原始标题：`Contents`

本页导读：

- 这是目录页，用来定位本文件的结构。
- 建议把后续页面先按章节分组，再逐页看细节；这样不容易被公式淹没。

## 第 3 页：条件独立

原始标题：`Conditional Independence — In View of Random Variables`

本页导读：

- 这一页提醒你：普通独立和条件独立不是同一件事。给定一个共同结果变量时，本来独立的原因变量可能变得相关。
- 看到 `X -> Z <- Y` 时要想到 collider：条件化在 `Z` 上会打开一条依赖路径。
- 复习时重点会解释为什么 `X` 与 `Y` 独立，不代表 `X` 与 `Y` 在给定 `Z` 后仍独立。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

关键词：`Conditional Independence`

## 第 4 页：Borel-Cantelli 引理

原始标题：`Limit of Sets and Borel-Cantelli Lemma`

本页导读：

- `lim sup An` 表示事件 `An` 无穷多次发生，`lim inf An` 表示从某个时刻起最终一直发生。
- Borel-Cantelli 第一引理用概率总和收敛推出“无穷多次发生”的概率为 0。
- 第二引理还需要相互独立：概率总和发散时，无穷多次发生的概率为 1。

关键词：`Borel-Cantelli`

## 第 5 页：中文导读

原始标题：`Recall.If P∞`

本页导读：

- `lim sup An` 表示事件 `An` 无穷多次发生，`lim inf An` 表示从某个时刻起最终一直发生。
- Borel-Cantelli 第一引理用概率总和收敛推出“无穷多次发生”的概率为 0。
- 第二引理还需要相互独立：概率总和发散时，无穷多次发生的概率为 1。
- 这类证明页建议抓住证明路线，不必一开始背每一步：先看用到的工具，再看关键不等式或等式变形。

关键词：`Borel-Cantelli`

## 第 6 页：中文导读

原始标题：`Recall.If moreover,{A n}∞`

本页导读：

- `lim sup An` 表示事件 `An` 无穷多次发生，`lim inf An` 表示从某个时刻起最终一直发生。
- Borel-Cantelli 第一引理用概率总和收敛推出“无穷多次发生”的概率为 0。
- 第二引理还需要相互独立：概率总和发散时，无穷多次发生的概率为 1。
- 这类证明页建议抓住证明路线，不必一开始背每一步：先看用到的工具，再看关键不等式或等式变形。

关键词：`Borel-Cantelli`

## 第 7 页：Jensen 不等式

原始标题：`Jensen’s Inequality Application`

本页导读：

- 本页用 Jensen 不等式比较不同的 `Lp` 范数：在概率空间上，若 `p <= q`，则 `||X||_Lp <= ||X||_Lq`。
- 直观上，`q` 越大越强调尾部，因此 `Lq` 可积性通常比 `Lp` 更强。

关键词：`Jensen`

## 第 8 页：中文导读

原始标题：`Some Notations`

本页导读：

- 概率论部分从样本空间、事件、sigma 代数、概率测度和随机变量开始。
- 浓缩不等式关注随机变量偏离均值的概率，sub-Gaussian 和 sub-exponential 是常见尾部条件。

关键词：`push-forward`

## 第 9 页：用尾概率表示期望

原始标题：`Represent Expectation by Tail Probability`

本页导读：

- 尾概率公式把期望写成尾部分布的积分，是证明矩有限和尾界的重要工具。
- 核心记忆：非负 `X` 满足 `E[X] = integral_0^infty P(X > t) dt`。
- 推广到高阶矩时，`E[X^p]` 与 `t^(p-1) P(X>t)` 的积分有关。

## 第 10 页：用尾概率表示期望

原始标题：`Represent Expectation by Tail Probability`

本页导读：

- 尾概率公式把期望写成尾部分布的积分，是证明矩有限和尾界的重要工具。
- 核心记忆：非负 `X` 满足 `E[X] = integral_0^infty P(X > t) dt`。
- 推广到高阶矩时，`E[X^p]` 与 `t^(p-1) P(X>t)` 的积分有关。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

## 第 11 页：条件期望

原始标题：`Conditional Expectation`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`Conditional Expectation`

## 第 12 页：条件期望

原始标题：`Conditional Expectation`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`Conditional Expectation`

## 第 13 页：目录

原始标题：`Contents`

本页导读：

- 这是目录页，用来定位本文件的结构。
- 建议把后续页面先按章节分组，再逐页看细节；这样不容易被公式淹没。

## 第 14 页：中文导读

原始标题：`Some Basic Concepts`

本页导读：

- 可测性描述“某个函数能否用当前 sigma 代数中的信息观察到”。
- 实值函数可测通常只需检查 `{f <= t}` 是否属于 sigma 代数。
- 在随机过程中，filtration 表示随时间增长的信息流，`Xt` 关于 `Ft` 可测表示时刻 `t` 不能预知未来。

## 第 15 页：可测性

原始标题：`Verification of Measurability`

本页导读：

- 可测性描述“某个函数能否用当前 sigma 代数中的信息观察到”。
- 实值函数可测通常只需检查 `{f <= t}` 是否属于 sigma 代数。
- 在随机过程中，filtration 表示随时间增长的信息流，`Xt` 关于 `Ft` 可测表示时刻 `t` 不能预知未来。

## 第 16 页：可测映射

原始标题：`Relationship between Measurable Function andσ-Algebra`

本页导读：

- 可测性描述“某个函数能否用当前 sigma 代数中的信息观察到”。
- 实值函数可测通常只需检查 `{f <= t}` 是否属于 sigma 代数。
- 在随机过程中，filtration 表示随时间增长的信息流，`Xt` 关于 `Ft` 可测表示时刻 `t` 不能预知未来。

## 第 17 页：可测映射

原始标题：`Relationship between Measurable Function andσ-Algebra`

本页导读：

- 可测性描述“某个函数能否用当前 sigma 代数中的信息观察到”。
- 实值函数可测通常只需检查 `{f <= t}` 是否属于 sigma 代数。
- 在随机过程中，filtration 表示随时间增长的信息流，`Xt` 关于 `Ft` 可测表示时刻 `t` 不能预知未来。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

## 第 18 页：条件期望

原始标题：`Conditional Expectation`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`Conditional Expectation`、`Radon-Nikodym`

## 第 19 页：条件期望

原始标题：`Conditional Expectation`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`Conditional Expectation`

## 第 20 页：中文导读

原始标题：`Connection to the Naive Definition`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`conditional expectation`

## 第 21 页：条件期望

原始标题：`Two Ways of Understanding Conditional Expectation`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`Conditional Expectation`

## 第 22 页：中文导读

原始标题：`First Understanding —E[X|G]as the Average`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

## 第 23 页：中文导读

原始标题：`First Understanding —E[X|G]as the Average`

本页导读：

- 本页主要是在引入或连接一个课程概念。阅读时先识别对象是什么、假设是什么、结论是什么。
- 如果有公式，建议把它拆成三部分：左边表示要研究的量，右边表示可计算或可估计的量，条件说明公式何时成立。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

## 第 24 页：中文导读

原始标题：`First Understanding —E[X|G]as the Average`

本页导读：

- 鞅刻画“公平游戏”：未来在当前信息下的条件期望等于现在。
- 核心形式是 `E[Xt | Fs] = Xs`，其中 `s < t`。
- 它是理解布朗运动、随机积分和随机微分方程的基础语言。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

关键词：`martingale`

## 第 25 页：条件期望

原始标题：`Corollaries — Properties of Conditional Expectation`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。

关键词：`Conditional Expectation`

## 第 26 页：中文导读

原始标题：`Second Understanding —E[X|G]as An Orthogonal Projection`

本页导读：

- 本页用 Jensen 不等式比较不同的 `Lp` 范数：在概率空间上，若 `p <= q`，则 `||X||_Lp <= ||X||_Lq`。
- 直观上，`q` 越大越强调尾部，因此 `Lq` 可积性通常比 `Lp` 更强。

关键词：`Jensen`

## 第 27 页：鞅

原始标题：`Martingales`

本页导读：

- 可测性描述“某个函数能否用当前 sigma 代数中的信息观察到”。
- 实值函数可测通常只需检查 `{f <= t}` 是否属于 sigma 代数。
- 在随机过程中，filtration 表示随时间增长的信息流，`Xt` 关于 `Ft` 可测表示时刻 `t` 不能预知未来。

关键词：`martingale`

## 第 28 页：鞅

原始标题：`Understanding Martingales`

本页导读：

- 条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。
- 它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。
- 直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。
- 例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。

关键词：`conditional expectation`、`martingale`

## 第 29 页：布朗运动

原始标题：`Brownian Motion as A Martingale`

本页导读：

- 鞅刻画“公平游戏”：未来在当前信息下的条件期望等于现在。
- 核心形式是 `E[Xt | Fs] = Xs`，其中 `s < t`。
- 它是理解布朗运动、随机积分和随机微分方程的基础语言。

关键词：`Martingale`、`Brownian Motion`

## 第 30 页：布朗运动

原始标题：`Brownian Motion Illustration`

本页导读：

- 布朗运动是连续时间随机过程的基本模型，具有独立增量、正态增量和连续路径。
- 它本身是鞅，但路径非常粗糙：一阶变差发散，二次变差等于时间长度。
- 这解释了为什么普通 Riemann 积分不能直接处理 `dWt`。

## 第 31 页：布朗运动

原始标题：`Properties of Brownian Motion`

本页导读：

- 布朗运动是连续时间随机过程的基本模型，具有独立增量、正态增量和连续路径。
- 它本身是鞅，但路径非常粗糙：一阶变差发散，二次变差等于时间长度。
- 这解释了为什么普通 Riemann 积分不能直接处理 `dWt`。

关键词：`Brownian Motion`

## 第 32 页：变差

原始标题：`Variations of Functions`

本页导读：

- 变差衡量路径在一个区间内的总波动量。
- 布朗运动的一阶变差和二次变差是随机分析的关键分界：路径不光滑，但二次变差稳定。

关键词：`Brownian motion`

## 第 33 页：布朗运动

原始标题：`First Order Variation of Brownian Motion`

本页导读：

- 布朗运动是连续时间随机过程的基本模型，具有独立增量、正态增量和连续路径。
- 它本身是鞅，但路径非常粗糙：一阶变差发散，二次变差等于时间长度。
- 这解释了为什么普通 Riemann 积分不能直接处理 `dWt`。

关键词：`Brownian Motion`

## 第 34 页：布朗运动

原始标题：`Quadratic Variation of Brownian Motion`

本页导读：

- 布朗运动是连续时间随机过程的基本模型，具有独立增量、正态增量和连续路径。
- 它本身是鞅，但路径非常粗糙：一阶变差发散，二次变差等于时间长度。
- 这解释了为什么普通 Riemann 积分不能直接处理 `dWt`。

关键词：`Brownian Motion`

## 第 35 页：随机微分方程

原始标题：`Stochastic Differential Equations (SDE)`

本页导读：

- 随机微分方程把确定性漂移项 `dt` 和随机扰动项 `dWt` 结合起来。
- 读 SDE 时先分清 drift（漂移）和 diffusion（扩散）两部分。
- 它是扩散模型、Langevin 动力学和连续时间生成模型的共同语言。

## 第 36 页：中文导读

原始标题：`How to Define the Stochastic Integral?`

本页导读：

- 本页主要是在引入或连接一个课程概念。阅读时先识别对象是什么、假设是什么、结论是什么。
- 如果有公式，建议把它拆成三部分：左边表示要研究的量，右边表示可计算或可估计的量，条件说明公式何时成立。

关键词：`Brownian motion`

## 第 37 页：Ito 积分 / Ito 公式

原始标题：`Itˆ o Integral`

本页导读：

- Ito 积分使用左端点信息，保证积分过程不使用未来信息。
- Ito isometry 把随机积分的二阶矩转化为被积函数平方的时间积分，是最常用的估计工具。
- `(dWt)^2 = dt` 是记忆 Ito 公式时的计算口诀，不是普通微积分等式。

## 第 38 页：生成式建模

原始标题：`The Idea of Generative Modeling`

本页导读：

- 布朗运动是连续时间随机过程的基本模型，具有独立增量、正态增量和连续路径。
- 它本身是鞅，但路径非常粗糙：一阶变差发散，二次变差等于时间长度。
- 这解释了为什么普通 Riemann 积分不能直接处理 `dWt`。

关键词：`Brownian motion`

## 第 39 页：生成式建模

原始标题：`Generative Modeling Illustration`

本页导读：

- 随机微分方程把确定性漂移项 `dt` 和随机扰动项 `dWt` 结合起来。
- 读 SDE 时先分清 drift（漂移）和 diffusion（扩散）两部分。
- 它是扩散模型、Langevin 动力学和连续时间生成模型的共同语言。

## 第 40 页：生成式建模

原始标题：`Generative Modeling Illustration`

本页导读：

- 生成式学习的目标是从样本中学习一个分布，并能产生新的样本。
- 扩散模型常把数据逐渐加噪到简单分布，再学习反向过程把噪声还原为数据。
- 注意区分三层对象：样本、分布、把一个分布推到另一个分布的映射或随机过程。

## 第 41 页：中文导读

原始标题：`Thank you!`

本页导读：

- 本页主要是在引入或连接一个课程概念。阅读时先识别对象是什么、假设是什么、结论是什么。
- 如果有公式，建议把它拆成三部分：左边表示要研究的量，右边表示可计算或可估计的量，条件说明公式何时成立。

## 快速术语表

- Borel-Cantelli 引理
- Ito 积分 / Ito 公式
- Jensen 不等式
- 变差
- 可测性
- 可测映射
- 布朗运动
- 条件期望
- 条件独立
- 概率复习
- 生成式建模
- 用尾概率表示期望
- 目录
- 随机微分方程
- 鞅
