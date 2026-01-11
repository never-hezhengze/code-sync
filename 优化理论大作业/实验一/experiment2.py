import numpy as np
import matplotlib.pyplot as plt

# =========================
# 4D Rosenbrock Function
# =========================

def f4(x):
    """
    4维Rosenbrock函数
    f(x) = Σ[(1-x_i)^2 + 100(x_{i+1}-x_i^2)^2] for i=0,1,2
    最小值在x*=(1,1,1,1)处，f(x*)=0
    
    参数:
        x: 长度为4的输入向量
    
    返回:
        函数值（标量）
    """
    return sum((1 - x[i])**2 + 100 * (x[i+1] - x[i]**2)**2 for i in range(3))


def grad_f4(x):
    """
    4维Rosenbrock函数的梯度
    
    参数:
        x: 长度为4的输入向量
    
    返回:
        梯度向量，形状为(4,)
    """
    g = np.zeros(4)
    for i in range(3):
        # 计算第i个分量的梯度贡献
        g[i] += -2 * (1 - x[i]) - 400 * x[i] * (x[i+1] - x[i]**2)
        # 计算第i+1个分量的梯度贡献
        g[i+1] += 200 * (x[i+1] - x[i]**2)
    return g


def hess_f4(x):
    """
    4维Rosenbrock函数的Hessian矩阵（二阶导数矩阵）
    
    参数:
        x: 长度为4的输入向量
    
    返回:
        4x4的Hessian矩阵
    """
    H = np.zeros((4, 4))
    for i in range(3):
        # 对角线元素
        H[i, i] += 2 - 400 * (x[i+1] - 3 * x[i]**2)
        # 非对角线元素（第i,i+1位置）
        H[i, i+1] += -400 * x[i]
        # 非对角线元素（第i+1,i位置，对称）
        H[i+1, i] += -400 * x[i]
        # 对角线元素
        H[i+1, i+1] += 200
    return H


# =========================
# Line Search (Wolfe)
# =========================

def line_search(f, grad, x, d, alpha0=1.0, c1=1e-4, c2=0.9):
    """
    Wolfe线搜索：同时满足Armijo条件和曲率条件
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x: 当前点
        d: 搜索方向
        alpha0: 初始步长
        c1: Armijo条件的参数（充分下降）
        c2: 曲率条件的参数
    
    返回:
        满足Wolfe条件的步长alpha
    """
    alpha = alpha0
    g = grad(x)  # 当前梯度
    fx = f(x)  # 当前函数值

    for _ in range(20):
        # 检查Armijo条件（充分下降）
        if f(x + alpha * d) > fx + c1 * alpha * np.dot(g, d):
            alpha *= 0.5  # 步长过大，缩小
        # 检查曲率条件（强Wolfe）
        elif np.dot(grad(x + alpha * d), d) < c2 * np.dot(g, d):
            alpha *= 1.1  # 步长过小，增大
        else:
            break  # 两个条件都满足
    return alpha


# =========================
# Optimization Algorithms
# =========================

def steepest_descent(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    最速下降法（梯度下降法）
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史)
    """
    x = x0.copy()
    hist = []  # 记录梯度范数

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if hist[-1] < tol:
            break
        
        # 搜索方向为负梯度
        d = -g
        
        # 通过线搜索确定步长
        alpha = line_search(f, grad, x, d)
        
        # 更新点
        x += alpha * d

    return x, hist


def newton(f, grad, hess, x0, tol=1e-6, max_iter=100):
    """
    Newton法（牛顿法）
    使用精确的Hessian矩阵，具有二次收敛性
    
    参数:
        f: 目标函数
        grad: 梯度函数
        hess: Hessian矩阵函数
        x0: 初始点
        tol: 梯度范数收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史)
    """
    x = x0.copy()
    hist = []  # 记录梯度范数

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if hist[-1] < tol:
            break
        
        # 计算Hessian矩阵
        H = hess(x)
        
        # Newton方向：d = -H^{-1}*g
        d = -np.linalg.solve(H, g)
        
        # 更新点（不进行线搜索）
        x += d

    return x, hist


def bfgs(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    BFGS拟牛顿法
    使用秩-2更新公式逐步构造Hessian的近似
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史)
    """
    n = len(x0)
    x = x0.copy()
    H = np.eye(n)  # 初始化Hessian近似为单位矩阵
    hist = []  # 记录梯度范数

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if hist[-1] < tol:
            break

        # 基于近似Hessian计算搜索方向
        d = -H @ g
        
        # 通过线搜索确定步长
        alpha = line_search(f, grad, x, d)
        
        # 计算点的位移
        s = alpha * d
        
        # 更新点
        x_new = x + s
        
        # 计算梯度的变化
        y = grad(x_new) - g

        # 计算BFGS更新中的系数
        rho = 1.0 / np.dot(y, s)
        I = np.eye(n)
        
        # BFGS秩-2更新公式
        H = (I - rho * np.outer(s, y)) @ H @ (I - rho * np.outer(y, s)) + rho * np.outer(s, s)

        x = x_new

    return x, hist


def cg_prp(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    共轭梯度法（CG）- Polak-Ribierung-Polyak（PRP）公式
    适用于大规模问题
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史)
    """
    x = x0.copy()
    g = grad(x)  # 初始梯度
    d = -g  # 初始搜索方向为负梯度
    hist = [np.linalg.norm(g)]  # 初始化历史记录

    for _ in range(max_iter):
        # 检查收敛条件
        if hist[-1] < tol:
            break

        # 通过线搜索确定步长
        alpha = line_search(f, grad, x, d)
        
        # 更新点
        x_new = x + alpha * d
        
        # 计算新梯度
        g_new = grad(x_new)

        # PRP共轭系数公式
        beta = np.dot(g_new, g_new - g) / max(np.dot(g, g), 1e-12)
        beta = max(beta, 0.0)  # 防止负值（自动重启）

        # 更新搜索方向（保持共轭性）
        d = -g_new + beta * d
        
        # 更新点和梯度
        x, g = x_new, g_new
        hist.append(np.linalg.norm(g))  # 记录梯度范数

    return x, hist


def trust_region(f, grad, hess, x0, tol=1e-6, max_iter=1000):
    """
    信任域方法
    使用Cauchy点作为子问题的解，动态调整信任域半径
    
    参数:
        f: 目标函数
        grad: 梯度函数
        hess: Hessian矩阵函数
        x0: 初始点
        tol: 梯度范数收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史)
    """
    x = x0.copy()
    delta = 1.0          # 初始信任域半径
    delta_max = 10.0     # 最大信任域半径
    eta = 0.1            # 步长接受阈值

    hist = []  # 记录梯度范数

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if hist[-1] < tol:
            break

        # 获取Hessian矩阵
        B = hess(x)

        # ---- 计算Cauchy点（沿负梯度方向） ----
        gBg = g @ B @ g  # 梯度在Hessian作用下的二次项
        if gBg <= 0:
            tau = 1.0  # Hessian非正定，使用单位步
        else:
            # 计算最优的梯度下降步长与信任域的交点
            tau = min(np.linalg.norm(g)**3 / (delta * gBg), 1.0)

        # 信任域内的候选步
        p = -tau * delta * g / np.linalg.norm(g)

        # ---- 计算实际下降量与预测下降量的比值rho ----
        actual_red = f(x) - f(x + p)  # 实际函数值下降
        predicted_red = -g @ p - 0.5 * p @ B @ p  # 二次模型预测的下降

        if predicted_red <= 0:
            rho = 0  # 预测不是下降方向
        else:
            rho = actual_red / predicted_red  # 下降比例

        # ---- 根据比值rho更新信任域半径 ----
        if rho < 0.25:
            delta *= 0.25  # 实际下降远小于预期，缩小信任域
        elif rho > 0.75 and np.linalg.norm(p) >= delta:
            delta = min(2 * delta, delta_max)  # 实际下降接近预期且步达边界，扩大信任域

        # ---- 接受或拒绝该步 ----
        if rho > eta:  # eta通常为0.1
            x = x + p  # 接受该步

    return x, hist


# =========================
# Main Experiment (Part 2)
# =========================

if __name__ == "__main__":
    # 初始点
    x0 = np.array([-1.2, 1.0, -0.8, 0.6])

    # 运行所有优化算法
    results = {
        "Steepest": steepest_descent(f4, grad_f4, x0),  # 最速下降法
        "Newton": newton(f4, grad_f4, hess_f4, x0),  # Newton法
        "BFGS": bfgs(f4, grad_f4, x0),  # BFGS拟牛顿法
        "CG-PRP": cg_prp(f4, grad_f4, x0),  # 共轭梯度法
        "TrustRegion": trust_region(f4, grad_f4, hess_f4, x0),  # 信任域方法
    }

    # 输出各算法的优化结果
    for name, (xopt, hist) in results.items():
        print(f"{name}: iter={len(hist)}, ||grad||={hist[-1]:.2e}")

    # =========================
    # Convergence Plot
    # =========================

    # 绘制收敛曲线：梯度范数随迭代次数的变化（对数尺度）
    plt.figure()
    for name, (_, hist) in results.items():
        # 跳过收敛过慢的算法（提高图的可读性）
        if name == "TrustRegion" or name == "Steepest":
            continue
        plt.plot(np.log10(hist), label=name)

    plt.xlabel("Iteration")
    plt.ylabel("log ||∇f(x)||")
    plt.title("Convergence Curves (4D Rosenbrock)")
    plt.legend()
    plt.grid(True)
    plt.show()
