import numpy as np
import matplotlib.pyplot as plt

# ======================================================
# 1. 测试函数
# ======================================================

def f2(x):
    """
    修改的Rosenbrock函数，包含额外的三角函数项
    f(x) = (1-x0)^2 + 100(x1-x0^2)^2 + 5*sin(2π*x0)*sin(2π*x1)
    
    参数:
        x: 输入向量，长度为2
    
    返回:
        函数值（标量）
    """
    return (1 - x[0])**2 + 100*(x[1] - x[0]**2)**2 + \
           5*np.sin(2*np.pi*x[0]) * np.sin(2*np.pi*x[1])

def grad_f2(x):
    """
    计算f2函数的梯度
    
    参数:
        x: 输入向量
    
    返回:
        梯度向量，形状为(2,)
    """
    # 第一个分量的梯度
    df_dx1 = -2*(1-x[0]) - 400*x[0]*(x[1]-x[0]**2) + \
             10*np.pi*np.cos(2*np.pi*x[0]) * np.sin(2*np.pi*x[1])
    
    # 第二个分量的梯度
    df_dx2 = 200*(x[1]-x[0]**2) + \
             10*np.pi*np.sin(2*np.pi*x[0]) * np.cos(2*np.pi*x[1])
    
    return np.array([df_dx1, df_dx2])


# ======================================================
# 2. 稳定版 Armijo + 强 Wolfe 线搜索
# ======================================================
def line_search(f, grad, x, d, max_ls=20):
    """
    Armijo + 强Wolfe条件的线搜索
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x: 当前点
        d: 搜索方向
        max_ls: 最大线搜索迭代次数
    
    返回:
        步长alpha
    """
    alpha = 1.0  # 初始步长
    c1, c2 = 1e-4, 0.9  # Wolfe条件的常数参数
    fx = f(x)  # 当前函数值
    g = grad(x)  # 当前梯度

    for _ in range(max_ls):
        new_x = x + alpha * d
        # 检查Armijo条件（充分下降）
        if f(new_x) > fx + c1 * alpha * np.dot(g, d):
            alpha *= 0.5
        # 检查强Wolfe条件（曲率条件）
        elif abs(np.dot(grad(new_x), d)) > c2 * abs(np.dot(g, d)):
            alpha *= 0.5
        else:
            return alpha

    return alpha  # 超过最大次数直接返回当前步长


# ======================================================
# 3. 各算法
# ======================================================

def steepest_descent(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    最速下降法（梯度下降法）
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数的收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史, 迭代路径)
    """
    x = x0.copy()
    hist, path = [], [x.copy()]

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if np.linalg.norm(g) < tol:
            break
        
        # 搜索方向为负梯度方向
        d = -g
        
        # 通过线搜索确定步长
        alpha = line_search(f, grad, x, d)
        
        # 更新点
        x = x + alpha*d
        path.append(x.copy())

    return x, hist, np.array(path)


def hessian_numeric(grad, x, eps=1e-5):
    """
    通过有限差分数值方法计算Hessian矩阵
    H[i,j] = (grad_i(x+eps*e_j) - grad_i(x)) / eps
    
    参数:
        grad: 梯度函数
        x: 计算点
        eps: 有限差分步长
    
    返回:
        Hessian矩阵的近似
    """
    n = len(x)
    H = np.zeros((n, n))
    g0 = grad(x)  # 基点梯度
    
    # 对每个坐标方向进行扰动
    for i in range(n):
        x_eps = x.copy()
        x_eps[i] += eps
        # 计算梯度差除以步长
        H[:, i] = (grad(x_eps) - g0) / eps
    
    return H


def newton(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    Newton法（牛顿法）
    使用二阶导数信息加速收敛
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数的收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史, 迭代路径)
    """
    x = x0.copy()
    hist, path = [], [x.copy()]

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if np.linalg.norm(g) < tol:
            break
        
        # 计算Hessian矩阵
        H = hessian_numeric(grad, x)
        
        # Newton方向：d = -H^{-1}*g
        d = np.linalg.solve(H, -g)
        
        # 不进行线搜索，直接使用Newton步（假设足够接近最优点）
        x = x + d
        path.append(x.copy())

    return x, hist, np.array(path)


def bfgs(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    BFGS拟牛顿法
    使用秩-2更新公式逐步逼近Hessian矩阵
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数的收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史, 迭代路径)
    """
    n = len(x0)
    H = np.eye(n)  # 初始化Hessian近似为单位矩阵
    x = x0.copy()
    hist, path = [], [x.copy()]

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if np.linalg.norm(g) < tol:
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

        # 如果满足曲率条件，更新Hessian近似
        if y @ s > 1e-10:
            rho = 1.0 / (y @ s)
            I = np.eye(n)
            # BFGS更新公式
            H = (I - rho*np.outer(s, y)) @ H @ (I - rho*np.outer(y, s)) + rho*np.outer(s, s)

        x = x_new
        path.append(x.copy())

    return x, hist, np.array(path)


def cg_prp(f, grad, x0, tol=1e-6, max_iter=1000):
    """
    共轭梯度法（CG）- Polak-Ribiere-Polyak（PRP）公式
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        tol: 梯度范数的收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史, 迭代路径)
    """
    x = x0.copy()
    g = grad(x)  # 初始梯度
    d = -g  # 初始搜索方向为负梯度
    hist, path = [], [x.copy()]

    for _ in range(max_iter):
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if np.linalg.norm(g) < tol:
            break

        # 非下降方向处理：如果方向与梯度呈钝角则重启
        if np.dot(d, g) >= 0:
            d = -g

        # 通过线搜索确定步长
        alpha = line_search(f, grad, x, d)
        
        # 更新点
        x_new = x + alpha * d
        
        # 计算新梯度
        g_new = grad(x_new)

        # PRP公式计算共轭系数
        beta = max(0, (g_new @ (g_new - g)) / (g @ g))
        
        # 更新搜索方向（保持共轭性）
        d = -g_new + beta * d

        x, g = x_new, g_new
        path.append(x.copy())

    return x, hist, np.array(path)


def trust_region(f, grad, x0, delta=1.0, tol=1e-6, max_iter=1000):
    """
    信赖域方法（简化版）
    限制每步的步长不超过delta
    
    参数:
        f: 目标函数
        grad: 梯度函数
        x0: 初始点
        delta: 信赖域半径
        tol: 梯度范数的收敛容差
        max_iter: 最大迭代次数
    
    返回:
        (最优点, 梯度范数历史, 迭代路径)
    """
    x = x0.copy()
    hist, path = [], [x.copy()]

    for _ in range(max_iter):
        g = grad(x)  # 计算梯度
        hist.append(np.linalg.norm(g))  # 记录梯度范数
        
        # 检查收敛条件
        if np.linalg.norm(g) < tol:
            break

        # 搜索方向为负梯度
        d = -g
        
        # 限制步长在信任域范围内
        if np.linalg.norm(d) > delta:
            d = delta * d / np.linalg.norm(d)

        # 更新点（不进行线搜索）
        x = x + d
        path.append(x.copy())

    return x, hist, np.array(path)


# ======================================================
# 4. 主程序
# ======================================================
if __name__ == "__main__":

    # 初始点
    x0 = np.array([-1.2, 1.0])

    # 运行所有优化算法
    results = {
        "Steepest": steepest_descent(f2, grad_f2, x0),
        "Newton": newton(f2, grad_f2, x0),
        "BFGS": bfgs(f2, grad_f2, x0),
        "CG-PRP": cg_prp(f2, grad_f2, x0),
        "TrustRegion": trust_region(f2, grad_f2, x0)
    }

    # 绘制收敛曲线：梯度范数随迭代次数的变化
    plt.figure()
    # ======================================================
    #for name, (_, hist, _) in results.items():
    #    plt.plot(np.log10(hist), label=name)
    
    for name, (_, hist, _) in results.items():
        if name == "TrustRegion":
           continue
        plt.plot(np.log10(hist), label=name)
    # ======================================================       
    plt.legend()
    plt.xlabel("Iteration")
    plt.ylabel("log ||∇f(x)||")
    plt.title("Convergence Curves")
    plt.show()

    # 生成等高线图数据
    x1 = np.linspace(-1.5, 2, 400)
    x2 = np.linspace(-0.5, 3, 400)
    X1, X2 = np.meshgrid(x1, x2)
    Z = (1-X1)**2 + 100*(X2-X1**2)**2 + 5*np.sin(2*np.pi*X1)*np.sin(2*np.pi*X2)

    # 绘制优化路径：在等高线图上显示各算法的搜索轨迹
    plt.figure()
    plt.contour(X1, X2, Z, 40)
    # ======================================================
    #for name, (_, _, path) in results.items():
    #    plt.plot(path[:,0], path[:,1], label=name)

    for name, (_, _, path) in results.items():
        if name == "TrustRegion":
            continue
        plt.plot(path[:,0], path[:,1], label=name)
    # ======================================================
    plt.legend()
    plt.title("Optimization Paths")
    plt.show()

    # 输出各算法的优化结果
    for name, (xopt, hist, _) in results.items():
        print(f"{name}: iter={len(hist)}, x*={xopt}, ||grad||={hist[-1]:.2e}")
