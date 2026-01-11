import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# =============================
# 1. 目标函数与梯度 (2D Constrained Modified Rosenbrock)
# =============================

def f1(x):
    """
    目标函数：改进的Rosenbrock函数
    f(x1, x2) = (1-x1)^2 + 100(x2-x1^2)^2 + 5*sin(2π*x1)*sin(2π*x2)
    
    Args:
        x: 包含 [x1, x2] 的数组
    
    Returns:
        函数值
    """
    x1, x2 = x
    return (1 - x1)**2 + 100*(x2 - x1**2)**2 + \
           5*np.sin(2*np.pi*x1)*np.sin(2*np.pi*x2)

def grad_f1(x):
    """
    目标函数的梯度向量
    ∇f = [∂f/∂x1, ∂f/∂x2]
    
    Args:
        x: 包含 [x1, x2] 的数组
    
    Returns:
        梯度向量 [df/dx1, df/dx2]
    """
    x1, x2 = x
    # ∂f/∂x1 = -2(1-x1) - 400*x1*(x2-x1^2) + 10π*cos(2π*x1)*sin(2π*x2)
    df_dx1 = -2*(1-x1) - 400*x1*(x2-x1**2) + \
             10*np.pi*np.cos(2*np.pi*x1)*np.sin(2*np.pi*x2)
    # ∂f/∂x2 = 200(x2-x1^2) + 10π*sin(2π*x1)*cos(2π*x2)
    df_dx2 = 200*(x2-x1**2) + \
             10*np.pi*np.sin(2*np.pi*x1)*np.cos(2*np.pi*x2)
    return np.array([df_dx1, df_dx2])

# 等式约束与不等式约束
def ce1(x):   
    """
    等式约束函数：c_eq(x) = x1^2 + x2 - 2 = 0
    
    Args:
        x: [x1, x2]
    
    Returns:
        约束值数组（当等于0时约束满足）
    """
    x1, x2 = x
    return np.array([x1**2 + x2 - 2])

def ci1(x):   
    """
    不等式约束函数：c_ineq(x) = x1 + x2^2 - 3 ≤ 0
    
    Args:
        x: [x1, x2]
    
    Returns:
        约束值数组（当≤0时约束满足）
    """
    x1, x2 = x
    return np.array([x1 + x2**2 - 3])

# 约束的雅可比矩阵（梯度矩阵）
def jac_ce1(x):
    """
    等式约束的雅可比矩阵
    ∇c_eq = [∂c_eq/∂x1, ∂c_eq/∂x2] = [2*x1, 1]
    
    Args:
        x: [x1, x2]
    
    Returns:
        1×2 的雅可比矩阵
    """
    x1, _ = x
    return np.array([[2*x1, 1]])

def jac_ci1(x):
    """
    不等式约束的雅可比矩阵
    ∇c_ineq = [∂c_ineq/∂x1, ∂c_ineq/∂x2] = [1, 2*x2]
    
    Args:
        x: [x1, x2]
    
    Returns:
        1×2 的雅可比矩阵
    """
    _, x2 = x
    return np.array([[1, 2*x2]])

# =============================
# 2. 增广拉格朗日法（ALM - Augmented Lagrangian Method）
# =============================

def ALM(x0, f, grad_f, ce, ci, jac_ce, jac_ci,
        rho=10.0, alpha=1e-3, max_iter=1000):
    """
    增广拉格朗日法求解约束优化问题
    
    增广拉格朗日函数：
    L_aug(x, λ, ρ) = f(x) + λ^T*c_eq(x) + (ρ/2)||c_eq(x)||^2 + (ρ/2)||max(0, c_ineq(x))||^2
    
    Args:
        x0: 初始点
        f: 目标函数
        grad_f: 目标函数梯度
        ce: 等式约束函数
        ci: 不等式约束函数
        jac_ce: 等式约束的雅可比矩阵
        jac_ci: 不等式约束的雅可比矩阵
        rho: 惩罚参数（默认10.0）
        alpha: 步长大小（默认1e-3）
        max_iter: 最大迭代次数（默认1000）
    
    Returns:
        x: 优化后的解
        path: 搜索路径
        history: 收敛历史记录
        k+1: 实际迭代次数
    """
    x = x0.copy()
    # 初始化拉格朗日乘子（等式约束）
    lam = np.zeros(len(ce(x)))
    path = [x.copy()]
    history = []

    for k in range(max_iter):
        # 计算目标函数梯度
        g = grad_f(x)

        # 等式约束项：∇L_eq = J_ce^T * (λ + ρ*c_eq)
        ce_val = ce(x)
        g += jac_ce(x).T @ (lam + rho*ce_val)

        # 不等式约束项：∇L_ineq = ρ * J_ci^T * max(0, c_ineq)
        ci_val = ci(x)
        active = np.maximum(0, ci_val)  # 只考虑活跃约束
        g += rho * jac_ci(x).T @ active

        # 梯度下降更新
        x = x - alpha * g
        # 更新拉格朗日乘子
        lam = lam + rho * ce_val

        # 计算收敛判别准则（KKT条件的衡量）
        crit = np.linalg.norm(grad_f(x)) + \
               np.linalg.norm(ce(x)) + \
               np.linalg.norm(np.maximum(0, ci(x)))

        history.append(crit)
        path.append(x.copy())
        
        # 当收敛准则足够小时退出
        if crit < 1e-6:
            break

    return x, np.array(path), np.array(history), k+1


# =============================
# 3. 序列二次规划法（SQP - Sequential Quadratic Programming）
# =============================

def SQP(x0, f, grad_f, ce, ci):
    """
    使用scipy的SLSQP求解器实现序列二次规划法
    SLSQP: Sequential Least Squares Programming
    
    每次迭代求解一个二次子问题并沿着解方向进行搜索，
    是处理约束非线性规划问题的高效方法。
    
    Args:
        x0: 初始点
        f: 目标函数
        grad_f: 目标函数梯度
        ce: 等式约束函数
        ci: 不等式约束函数
    
    Returns:
        res.x: 优化后的解
        hist: 收敛历史记录
        res.nit: 实际迭代次数
    """
    # 构建约束列表
    cons = []

    # 添加等式约束：c_eq(x) = 0
    for i in range(len(ce(x0))):
        cons.append({'type': 'eq',
                     'fun': lambda x, i=i: ce(x)[i]})

    # 添加不等式约束：c_ineq(x) ≤ 0 → -c_ineq(x) ≥ 0
    for i in range(len(ci(x0))):
        cons.append({'type': 'ineq',
                     'fun': lambda x, i=i: -ci(x)[i]})

    # 收敛历史记录列表
    hist = []

    def callback(xk):
        """每次迭代后的回调函数，记录收敛准则"""
        crit = np.linalg.norm(grad_f(xk)) + \
               np.linalg.norm(ce(xk)) + \
               np.linalg.norm(np.maximum(0, ci(xk)))
        hist.append(crit)

    # 调用scipy的minimize函数，使用SLSQP方法
    res = minimize(f, x0,
                   jac=grad_f,
                   method='SLSQP',
                   constraints=cons,
                   callback=callback,
                   options={'ftol': 1e-9, 'maxiter': 1000})

    return res.x, np.array(hist), res.nit


# =============================
# 4. 可视化函数
# =============================

def plot_contour_and_path(path):
    """
    绘制目标函数的等高线图和优化搜索路径
    
    Args:
        path: 搜索路径，形状为 (迭代数+1, 2)
    """
    # 生成网格点用于绘制等高线
    x = np.linspace(-1.5, 2, 400)
    y = np.linspace(-0.5, 3, 400)
    X, Y = np.meshgrid(x, y)
    Z = f1([X, Y])  # 目标函数值

    plt.figure(figsize=(8, 6))
    # 绘制目标函数的等高线（40条级别）
    plt.contour(X, Y, Z, levels=40, cmap='viridis')

    # 绘制等式约束边界：x1^2 + x2 - 2 = 0（红色）
    plt.contour(X, Y, X**2 + Y - 2, levels=[0], colors='r')
    # 绘制不等式约束边界：x1 + x2^2 - 3 = 0（蓝色）
    plt.contour(X, Y, X + Y**2 - 3, levels=[0], colors='b')

    # 绘制搜索路径（黑色圆点连接）
    path = np.array(path)
    plt.plot(path[:,0], path[:,1], 'ko-', label='ALM Path')

    plt.xlabel('x1')
    plt.ylabel('x2')
    plt.legend()
    plt.title('2D Constrained Rosenbrock Optimization Path')
    plt.show()

def plot_convergence(hist_alm, hist_sqp):
    """
    绘制两种方法的收敛曲线对比
    使用对数标度查看收敛速度
    
    Args:
        hist_alm: ALM方法的收敛历史
        hist_sqp: SQP方法的收敛历史
    """
    plt.figure()
    #plt.semilogy(hist_alm, label='ALM')
    plt.semilogy(hist_sqp, label='SQP')
    plt.xlabel('Iteration')
    plt.ylabel(r'$\log(||\nabla f|| + ||c||)$')
    plt.legend()
    plt.title('Convergence Comparison')
    plt.show()

# =============================
# 5. 主程序
# =============================

if __name__ == "__main__":
    # 定义初始点
    x0 = np.array([0.0, 0.0])

    print("="*60)
    print("运行ALM（增广拉格朗日法）...")
    # 运行ALM算法
    x_alm, path_alm, hist_alm, iter_alm = ALM(
        x0, f1, grad_f1, ce1, ci1, jac_ce1, jac_ci1
    )

    # 输出ALM结果
    print("ALM 优化结果:")
    print("  迭代次数        :", iter_alm)
    print("  最优解 x        :", x_alm)
    print("  f(x)            :", f1(x_alm))
    print("  ||grad f||      :", np.linalg.norm(grad_f1(x_alm)))
    print("  ||c_eq||        :", np.linalg.norm(ce1(x_alm)))
    print("  max(0, c_ineq)  :", np.max(np.maximum(0, ci1(x_alm))))

    print("="*60)
    print("运行SQP（序列二次规划法）...")
    # 运行SQP算法
    x_sqp, hist_sqp, iter_sqp = SQP(
        x0, f1, grad_f1, ce1, ci1
    )

    # 输出SQP结果
    print("SQP 优化结果:")
    print("  迭代次数        :", iter_sqp)
    print("  最优解 x        :", x_sqp)
    print("  f(x)            :", f1(x_sqp))
    print("  ||grad f||      :", np.linalg.norm(grad_f1(x_sqp)))
    print("  ||c_eq||        :", np.linalg.norm(ce1(x_sqp)))
    print("  max(0, c_ineq)  :", np.max(np.maximum(0, ci1(x_sqp))))

    # 绘制优化路径
    plot_contour_and_path(path_alm)
    # 绘制收敛对比
    plot_convergence(hist_alm, hist_sqp)

