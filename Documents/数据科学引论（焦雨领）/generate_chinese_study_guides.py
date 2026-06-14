from pathlib import Path
import re

from pypdf import PdfReader


PDFS = [
    "Review_of_probability2.pdf",
    "Review_of_probability4.pdf",
    "Review_of_math5.pdf",
    "ds_26_intr.pdf",
]


def clean(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def lines_for_page(page) -> list[str]:
    text = page.extract_text() or ""
    return [clean(line) for line in text.splitlines() if clean(line)]


def title_for(lines: list[str], page_no: int) -> str:
    if not lines:
        return "Untitled"
    first = lines[0]
    if page_no == 1:
        return first
    skip = {
        "▶",
        "Theorem",
        "Proof",
    }
    for line in lines[:5]:
        if line and not any(line.startswith(s) for s in skip):
            return line
    return first


def cn_title(title: str) -> str:
    mapping = [
        ("Introduction to Data Science", "数据科学引论"),
        ("Review — Probability", "概率复习"),
        ("Review — Some Supplementary Proofs", "补充证明复习"),
        ("Contents", "目录"),
        ("Outline", "大纲"),
        ("Best low rank approximation", "最佳低秩近似"),
        ("best linear encoder and decoder", "最佳线性编码器与解码器"),
        ("Setup for supervised learning", "监督学习设定"),
        ("Nonparametric estimation framework", "非参数估计框架"),
        ("Error decomposition", "误差分解"),
        ("Different errors", "不同类型的误差"),
        ("Ordinary least square", "普通最小二乘"),
        ("Regularized", "正则化"),
        ("Least squares", "最小二乘"),
        ("Rademacher processes", "Rademacher 过程"),
        ("Dudley", "Dudley 熵积分"),
        ("Lower bound", "下界"),
        ("Domain adaptation", "领域自适应"),
        ("Image restoration", "图像复原"),
        ("Image generation", "图像生成"),
        ("Gradient flow", "梯度流"),
        ("Score matching", "分数匹配"),
        ("Follmer", "Follmer 流"),
        ("F¨ollmer", "Follmer 流"),
        ("Conditional Independence", "条件独立"),
        ("Borel-Cantelli", "Borel-Cantelli 引理"),
        ("Jensen", "Jensen 不等式"),
        ("Tail Probability", "用尾概率表示期望"),
        ("Conditional Expectation", "条件期望"),
        ("Measurability", "可测性"),
        ("Measurable", "可测映射"),
        ("Martingales", "鞅"),
        ("Brownian Motion", "布朗运动"),
        ("Variation", "变差"),
        ("Quadratic Variation", "二次变差"),
        ("Stochastic Differential", "随机微分方程"),
        ("Ito", "Ito 积分 / Ito 公式"),
        ("Itˆ", "Ito 积分 / Ito 公式"),
        ("Itô", "Ito 积分 / Ito 公式"),
        ("Generative", "生成式建模"),
        ("Fokker", "Fokker-Planck 方程"),
        ("Langevin", "Langevin 动力学"),
        ("SVD", "奇异值分解"),
        ("Singular", "奇异值"),
        ("Condition number", "条件数"),
        ("Nuclear norm", "核范数"),
        ("Derivative", "导数"),
        ("Convex", "凸性"),
        ("Subdifferential", "次微分"),
        ("Bregman", "Bregman 距离"),
        ("Fenchel", "Fenchel 共轭"),
        ("KKT", "KKT 条件"),
        ("Linear programming", "线性规划"),
        ("Random Variables", "随机变量"),
        ("Probability", "概率"),
        ("Supervised", "监督学习"),
        ("Rademacher", "Rademacher 复杂度"),
        ("Approximation", "逼近误差"),
        ("Gradient descent", "梯度下降"),
        ("SGD", "随机梯度下降"),
        ("SVM", "支持向量机"),
        ("Representation", "表示学习"),
        ("Diffusion", "扩散模型"),
        ("Transformers", "Transformer"),
        ("Norm", "范数"),
    ]
    for key, value in mapping:
        if key.lower() in title.lower():
            return value
    return "中文导读"


def bullets_for(title: str, text: str, filename: str) -> list[str]:
    lower = (title + " " + text).lower()
    bullets: list[str] = []

    if "introduction to data science" in lower:
        bullets += [
            "这是课程总标题页。整门课会把统计学习、优化、表示学习和生成式学习串成一条主线。",
            "读主讲义时不要把每个公式孤立看，要问它服务于哪类学习问题：预测、表示、生成，还是误差分析。",
        ]
    elif title.lower() == "outline" or title.lower() == "contents":
        bullets += [
            "这是目录页，用来定位本文件的结构。",
            "建议把后续页面先按章节分组，再逐页看细节；这样不容易被公式淹没。",
        ]
    elif "setup for supervised learning" in lower:
        bullets += [
            "监督学习设定通常包含输入 `X`、标签 `Y`、样本分布、损失函数和目标风险。",
            "要区分总体风险和经验风险：前者是理论目标，后者是训练时能计算的替代量。",
        ]
    elif "nonparametric estimation" in lower:
        bullets += [
            "非参数估计不预设低维参数形式，而是在较大的函数类中学习目标函数。",
            "分析通常分解为逼近误差和估计误差：模型能不能表达，以及有限样本能不能学准。",
        ]
    elif "error decomposition" in lower or "different errors" in lower:
        bullets += [
            "误差分解是统计学习理论的主线：把总误差拆成可分别控制的几部分。",
            "常见部分包括 approximation error（逼近误差）、estimation error（估计误差）和 optimization error（优化误差）。",
        ]
    elif "ordinary least square" in lower or "least square" in lower:
        bullets += [
            "最小二乘通过最小化平方损失拟合线性模型，是线性回归和许多非参数方法的基础。",
            "固定设计情形下，重点关注矩阵形式、投影解释和噪声如何影响估计误差。",
        ]
    elif "conditional independence" in lower or "collider" in lower:
        bullets += [
            "这一页提醒你：普通独立和条件独立不是同一件事。给定一个共同结果变量时，本来独立的原因变量可能变得相关。",
            "看到 `X -> Z <- Y` 时要想到 collider：条件化在 `Z` 上会打开一条依赖路径。",
            "复习时重点会解释为什么 `X` 与 `Y` 独立，不代表 `X` 与 `Y` 在给定 `Z` 后仍独立。",
        ]
    elif "borel" in lower or "lim sup" in lower or "lim inf" in lower:
        bullets += [
            "`lim sup An` 表示事件 `An` 无穷多次发生，`lim inf An` 表示从某个时刻起最终一直发生。",
            "Borel-Cantelli 第一引理用概率总和收敛推出“无穷多次发生”的概率为 0。",
            "第二引理还需要相互独立：概率总和发散时，无穷多次发生的概率为 1。",
        ]
    elif "jensen" in lower or "lp" in lower and "lq" in lower:
        bullets += [
            "本页用 Jensen 不等式比较不同的 `Lp` 范数：在概率空间上，若 `p <= q`，则 `||X||_Lp <= ||X||_Lq`。",
            "直观上，`q` 越大越强调尾部，因此 `Lq` 可积性通常比 `Lp` 更强。",
        ]
    elif "tail probability" in lower or "p(x>t)" in lower:
        bullets += [
            "尾概率公式把期望写成尾部分布的积分，是证明矩有限和尾界的重要工具。",
            "核心记忆：非负 `X` 满足 `E[X] = integral_0^infty P(X > t) dt`。",
            "推广到高阶矩时，`E[X^p]` 与 `t^(p-1) P(X>t)` 的积分有关。",
        ]
    elif "conditional expectation" in lower or "radon" in lower:
        bullets += [
            "条件期望严格来说是相对于一个子 sigma 代数 `G` 的随机变量。",
            "它有两个定义条件：必须 `G`-可测；并且在任意 `A in G` 上与原变量积分相同。",
            "直观上，`E[X|G]` 是在较少信息下对 `X` 的平均化，也可看成 `L2` 投影。",
        ]
    elif "measurable" in lower or "sigma" in lower or "filtration" in lower:
        bullets += [
            "可测性描述“某个函数能否用当前 sigma 代数中的信息观察到”。",
            "实值函数可测通常只需检查 `{f <= t}` 是否属于 sigma 代数。",
            "在随机过程中，filtration 表示随时间增长的信息流，`Xt` 关于 `Ft` 可测表示时刻 `t` 不能预知未来。",
        ]
    elif "martingale" in lower:
        bullets += [
            "鞅刻画“公平游戏”：未来在当前信息下的条件期望等于现在。",
            "核心形式是 `E[Xt | Fs] = Xs`，其中 `s < t`。",
            "它是理解布朗运动、随机积分和随机微分方程的基础语言。",
        ]
    elif "brownian" in lower or "wiener" in lower:
        bullets += [
            "布朗运动是连续时间随机过程的基本模型，具有独立增量、正态增量和连续路径。",
            "它本身是鞅，但路径非常粗糙：一阶变差发散，二次变差等于时间长度。",
            "这解释了为什么普通 Riemann 积分不能直接处理 `dWt`。",
        ]
    elif "variation" in lower:
        bullets += [
            "变差衡量路径在一个区间内的总波动量。",
            "布朗运动的一阶变差和二次变差是随机分析的关键分界：路径不光滑，但二次变差稳定。",
        ]
    elif "stochastic differential" in lower or "sde" in lower:
        bullets += [
            "随机微分方程把确定性漂移项 `dt` 和随机扰动项 `dWt` 结合起来。",
            "读 SDE 时先分清 drift（漂移）和 diffusion（扩散）两部分。",
            "它是扩散模型、Langevin 动力学和连续时间生成模型的共同语言。",
        ]
    elif re.search(r"\bito\b", lower) or "itˆ" in lower or "itô" in lower or "isometry" in lower or "dwt" in lower:
        bullets += [
            "Ito 积分使用左端点信息，保证积分过程不使用未来信息。",
            "Ito isometry 把随机积分的二阶矩转化为被积函数平方的时间积分，是最常用的估计工具。",
            "`(dWt)^2 = dt` 是记忆 Ito 公式时的计算口诀，不是普通微积分等式。",
        ]
    elif "fokker" in lower:
        bullets += [
            "Fokker-Planck 方程描述 SDE 解的概率密度如何随时间演化。",
            "SDE 是样本路径层面的运动，FPE 是分布层面的运动。",
            "不变分布就是让 FPE 的时间导数为 0 时得到的稳定分布。",
        ]
    elif "langevin" in lower:
        bullets += [
            "Langevin 动力学通过梯度和噪声共同驱动样本移动，常用于采样和生成模型。",
            "当势能函数取 `-log p_data` 时，目标分布会成为对应动力学的不变分布。",
        ]
    elif "generative" in lower or "diffusion" in lower or "gan" in lower:
        bullets += [
            "生成式学习的目标是从样本中学习一个分布，并能产生新的样本。",
            "扩散模型常把数据逐渐加噪到简单分布，再学习反向过程把噪声还原为数据。",
            "注意区分三层对象：样本、分布、把一个分布推到另一个分布的映射或随机过程。",
        ]
    elif "condition number" in lower:
        bullets += [
            "条件数衡量线性系统对扰动的敏感程度，通常越大越病态。",
            "它依赖所选范数，但在有限维空间里不同范数具有等价性。",
        ]
    elif "svd" in lower or "singular" in lower or "low rank" in lower:
        bullets += [
            "SVD 把矩阵分解为正交方向和奇异值，是低秩近似、PCA、压缩和条件数分析的基础。",
            "最佳低秩近似定理说明：保留最大的若干奇异值，就是谱范数或 Frobenius 范数下的最优低秩近似。",
        ]
    elif "nuclear" in lower or "schatten" in lower:
        bullets += [
            "Schatten 范数是把矩阵奇异值当向量后取向量范数。",
            "核范数是奇异值的 `l1` 和，常作为矩阵秩的凸替代。",
        ]
    elif "derivative" in lower or "frechet" in lower or "det" in lower:
        bullets += [
            "矩阵函数的导数最好通过内积表示一阶变化：`df(X)[H] = <G, H>`。",
            "Frechet 导数强调对任意扰动方向的线性近似，是矩阵优化里最稳的语言。",
        ]
    elif "convex" in lower or "cone" in lower or "elliptical" in lower:
        bullets += [
            "凸集的核心是线段封闭；凸函数的核心是函数图像下方的线性插值不超过函数值。",
            "强凸性比普通凸性更强，会带来唯一解和更好的收敛性质。",
        ]
    elif "subdifferential" in lower or "subgradient" in lower or "normal cone" in lower:
        bullets += [
            "次梯度把不可微凸函数的一阶最优性条件推广到非光滑情形。",
            "Fermat 法则：凸优化问题的最优点满足 `0 in partial f(x*)`。",
            "约束问题可以通过指示函数和 normal cone 转化为次微分条件。",
        ]
    elif "bregman" in lower:
        bullets += [
            "Bregman 距离不是普通距离，而是由凸函数的一阶线性化误差定义。",
            "它常用于镜像下降、广义投影和 KL 距离相关算法。",
        ]
    elif "fenchel" in lower or "legendre" in lower or "conjugate" in lower:
        bullets += [
            "Fenchel 共轭把函数表示为所有仿射下界的上确界，是凸分析和对偶理论的核心工具。",
            "闭凸函数满足双共轭等于自身，这是很多对偶证明的基础。",
        ]
    elif "kkt" in lower or "lagrange" in lower or "linear programming" in lower:
        bullets += [
            "KKT 条件把可行性、驻点条件、对偶可行性和互补松弛统一起来。",
            "对凸优化，在适当约束资格条件下，KKT 通常也是最优性的充要条件。",
        ]
    elif "rademacher" in lower or "symmetrization" in lower or "dudley" in lower:
        bullets += [
            "Rademacher 复杂度衡量函数类对随机符号噪声的拟合能力，用来控制泛化误差。",
            "symmetrization 用 ghost sample 把经验过程转化为更容易处理的随机符号过程。",
            "Dudley 熵积分把复杂度和覆盖数联系起来。",
        ]
    elif "approximation" in lower or "holder" in lower or "relu" in lower:
        bullets += [
            "逼近误差衡量模型类本身能否表达目标函数，是统计误差之外的另一部分误差。",
            "对 Holder 光滑函数，常用 Taylor 展开和 ReLU 网络构造来得到逼近率。",
        ]
    elif "gradient descent" in lower:
        bullets += [
            "梯度下降分析通常依赖光滑性下降引理：步长合适时目标函数会下降。",
            "凸性、强凸性和非凸性会对应不同的收敛结论。",
        ]
    elif "proximal" in lower:
        bullets += [
            "近端梯度下降用于 `f+h` 形式，其中 `f` 光滑、`h` 可非光滑但近端算子可解。",
            "它把梯度步和对非光滑项的近端映射组合起来。",
        ]
    elif "stochastic gradient" in lower or "sgd" in lower:
        bullets += [
            "SGD 用随机梯度替代全梯度，分析重点是无偏性、方差和步长。",
            "方差缩减方法通过控制变量降低随机梯度噪声。",
        ]
    elif "supervised" in lower or "classification" in lower or "risk" in lower:
        bullets += [
            "监督学习的核心是用训练样本最小化经验风险，并希望泛化到总体风险。",
            "分类问题常把不可优化的 0-1 损失替换为凸 surrogate loss。",
        ]
    elif "svm" in lower or "kernel" in lower or "rkhs" in lower:
        bullets += [
            "SVM 可以看成带正则的 hinge loss 经验风险最小化。",
            "核技巧把内积替换为核函数，相当于在高维特征空间中做线性分类。",
            "支持向量来自 KKT 条件中非零对偶变量对应的样本。",
        ]
    elif "representation" in lower or "ssl" in lower or "contrastive" in lower:
        bullets += [
            "表示学习关注如何把原始数据变成更适合下游任务的特征。",
            "自监督学习利用未标注数据构造训练信号；对比学习通过拉近正样本、推远负样本学习表示。",
        ]
    elif "transformer" in lower or "llm" in lower or "pretraining" in lower or "icl" in lower:
        bullets += [
            "Transformer 是现代深度学习和大语言模型的核心架构。",
            "预训练可以被理解为从大量序列中学习隐含概念和上下文规律。",
            "ICL 关注模型如何在上下文样例中推断隐藏任务。",
        ]
    elif "probability" in lower or "random variable" in lower or "sub-gaussian" in lower:
        bullets += [
            "概率论部分从样本空间、事件、sigma 代数、概率测度和随机变量开始。",
            "浓缩不等式关注随机变量偏离均值的概率，sub-Gaussian 和 sub-exponential 是常见尾部条件。",
        ]
    elif "norm" in lower or "inner product" in lower:
        bullets += [
            "范数衡量大小，内积衡量角度和投影；很多优化结论都依赖范数与对偶范数。",
            "有限维空间中范数等价，但具体常数会影响算法和误差界。",
        ]
    else:
        bullets += [
            "本页主要是在引入或连接一个课程概念。阅读时先识别对象是什么、假设是什么、结论是什么。",
            "如果有公式，建议把它拆成三部分：左边表示要研究的量，右边表示可计算或可估计的量，条件说明公式何时成立。",
        ]

    if "proof" in lower or "derivation" in lower:
        bullets.append("这类证明页建议抓住证明路线，不必一开始背每一步：先看用到的工具，再看关键不等式或等式变形。")
    if "example" in lower:
        bullets.append("例子页的价值在于把抽象定义落地；复习时可以自己换一组简单数字检验结论。")
    return bullets[:4]


def guide_intro(filename: str, pages: int) -> str:
    if filename.startswith("ds_26"):
        scope = "这份主讲义覆盖线性模型、监督学习、表示学习、生成式学习以及课程前置数学与概率工具。"
    elif "math" in filename:
        scope = "这份 review 主要补充线性代数、矩阵分析、凸优化、次微分、对偶和 KKT 等证明材料。"
    else:
        scope = "这份 review 主要补充测度论概率、条件期望、鞅、布朗运动、SDE、Ito 公式和生成模型中的随机过程语言。"
    return (
        f"# {Path(filename).stem} 中文学习版\n\n"
        f"> 来源：`{filename}`  \n"
        f"> 页数：{pages}  \n"
        "> 说明：这是按页整理的中文导读/学习笔记，不覆盖原 PDF。公式和英文术语尽量保留，中文部分负责解释它们在课程中的作用。\n\n"
        f"{scope}\n\n"
        "建议读法：先看每页的“本页导读”，再回到原 PDF 看公式和图；遇到证明页，优先抓证明思路和用到的工具。\n\n"
    )


def build_markdown(filename: str) -> str:
    reader = PdfReader(filename)
    chunks = [guide_intro(filename, len(reader.pages))]
    glossary = set()

    for i, page in enumerate(reader.pages, 1):
        lines = lines_for_page(page)
        title = title_for(lines, i)
        text = clean(" ".join(lines[:18]))
        translated = cn_title(title)
        bullets = bullets_for(title, text, filename)
        if translated != "中文导读":
            glossary.add(translated)

        chunks.append(f"## 第 {i} 页：{translated}\n\n")
        chunks.append(f"原始标题：`{title}`\n\n")
        chunks.append("本页导读：\n\n")
        for bullet in bullets:
            chunks.append(f"- {bullet}\n")
        if len(lines) > 1:
            key_terms = extract_terms(" ".join(lines))
            if key_terms:
                chunks.append("\n关键词：")
                chunks.append("、".join(f"`{term}`" for term in key_terms[:8]))
                chunks.append("\n")
        chunks.append("\n")

    if glossary:
        chunks.append("## 快速术语表\n\n")
        for term in sorted(glossary):
            chunks.append(f"- {term}\n")
    return "".join(chunks)


TERM_PATTERNS = [
    r"\bconditional expectation\b",
    r"\bconditional independence\b",
    r"\bBorel-?Cantelli\b",
    r"\bJensen\b",
    r"\bpush-forward\b",
    r"\bRadon-?Nikodym\b",
    r"\bmartingale\b",
    r"\bBrownian motion\b",
    r"\bIto\b",
    r"\bFokker-Planck\b",
    r"\bLangevin\b",
    r"\bSVD\b",
    r"\bcondition number\b",
    r"\bnuclear norm\b",
    r"\bsubdifferential\b",
    r"\bBregman\b",
    r"\bFenchel\b",
    r"\bKKT\b",
    r"\bRademacher\b",
    r"\bSGD\b",
    r"\bSVM\b",
    r"\bRKHS\b",
    r"\bGAN\b",
    r"\bdiffusion model\b",
    r"\bTransformer\b",
]


def extract_terms(text: str) -> list[str]:
    found = []
    for pattern in TERM_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            found.append(m.group(0))
    return found


def main() -> None:
    for pdf in PDFS:
        out = Path(pdf).with_suffix("")
        md = out.with_name(out.name + "_中文学习版.md")
        md.write_text(build_markdown(pdf), encoding="utf-8")
        print(md)


if __name__ == "__main__":
    main()
