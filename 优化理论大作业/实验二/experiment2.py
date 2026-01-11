import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# =====================================================
# 1. Constrained 4D Rosenbrock
# =====================================================

def f(x):
    val = 0.0
    for k in range(3):
        val += (1 - x[k])**2 + 100 * (x[k+1] - x[k]**2)**2
    return val

def grad_f(x):
    g = np.zeros(4)

    g[0] = -2*(1-x[0]) - 400*x[0]*(x[1]-x[0]**2)
    g[1] = 200*(x[1]-x[0]**2) - 2*(1-x[1]) - 400*x[1]*(x[2]-x[1]**2)
    g[2] = 200*(x[2]-x[1]**2) - 2*(1-x[2]) - 400*x[2]*(x[3]-x[2]**2)
    g[3] = 200*(x[3]-x[2]**2)

    return g

# =====================================================
# 2. 约束
# =====================================================

def ce(x):
    return np.array([x[0] + x[1] + x[2] + x[3] - 2])

def ci(x):
    return np.array([
        -(x[0] - x[1] + 1),
        2*x[2] - x[3] - 3,
        x[0]**2 + x[3]**2 - 4
    ])

# =====================================================
# 3. 雅可比
# =====================================================

def jac_ce(x):
    return np.array([[1, 1, 1, 1]])

def jac_ci(x):
    return np.array([
        [-1, 1, 0, 0],
        [0, 0, 2, -1],
        [2*x[0], 0, 0, 2*x[3]]
    ])

# =====================================================
# 4. 收敛指标
# =====================================================

def convergence_metric(x):
    return (
        np.linalg.norm(grad_f(x)) +
        np.linalg.norm(ce(x)) +
        np.linalg.norm(np.maximum(0, ci(x)))
    )

# =====================================================
# 5. ALM（记录收敛历史）
# =====================================================

def ALM(x0, rho=10.0, alpha=1e-4, max_iter=1000):
    x = x0.copy()
    lam = np.zeros(len(ce(x)))
    history = []

    for k in range(max_iter):
        g = grad_f(x)
        g += jac_ce(x).T @ (lam + rho * ce(x))
        g += rho * jac_ci(x).T @ np.maximum(0, ci(x))

        x = x - alpha * g
        lam = lam + rho * ce(x)

        crit = convergence_metric(x)
        history.append(crit)

        if crit < 1e-6:
            return x, history, k + 1

    return x, history, max_iter

# =====================================================
# 6. SQP（记录收敛历史）
# =====================================================

def SQP(x0):
    history = []

    def callback(xk):
        history.append(convergence_metric(xk))

    cons = [
        {'type': 'eq',   'fun': lambda x: ce(x)[0]},
        {'type': 'ineq', 'fun': lambda x: x[0] - x[1] + 1},
        {'type': 'ineq', 'fun': lambda x: -(2*x[2] - x[3] - 3)},
        {'type': 'ineq', 'fun': lambda x: -(x[0]**2 + x[3]**2 - 4)}
    ]

    res = minimize(
        f, x0,
        jac=grad_f,
        method='SLSQP',
        constraints=cons,
        callback=callback,
        options={'ftol': 1e-9, 'maxiter': 1000}
    )

    return res.x, history, res.nit

# =====================================================
# 7. 主程序 + 收敛曲线绘制
# =====================================================

if __name__ == "__main__":

    x0 = np.zeros(4)

    print("="*60)
    print("Running ALM...")
    x_alm, hist_alm, it_alm = ALM(x0)

    print("ALM results:")
    print("  Iterations        :", it_alm)
    print("  Solution x        :", x_alm)
    print("  f(x)              :", f(x_alm))
    print("  ||grad f||        :", np.linalg.norm(grad_f(x_alm)))
    print("  ||c_eq||          :", np.linalg.norm(ce(x_alm)))
    print("  max(0, c_ineq)    :", np.max(np.maximum(0, ci(x_alm))))

    print("="*60)
    print("Running SQP...")
    x_sqp, hist_sqp, it_sqp = SQP(x0)

    print("SQP results:")
    print("  Iterations        :", it_sqp)
    print("  Solution x        :", x_sqp)
    print("  f(x)              :", f(x_sqp))
    print("  ||grad f||        :", np.linalg.norm(grad_f(x_sqp)))
    print("  ||c_eq||          :", np.linalg.norm(ce(x_sqp)))
    print("  max(0, c_ineq)    :", np.max(np.maximum(0, ci(x_sqp))))

    # ================= 收敛曲线 =================
    plt.figure(figsize=(8, 5))
    #plt.semilogy(hist_alm, label='ALM')
    plt.semilogy(hist_sqp, label='SQP')
    plt.xlabel('Iteration')
    plt.ylabel(r'$\|\nabla f\| + \|c_{eq}\| + \|\max(0,c_{ineq})\|$')
    plt.title('Convergence Curves (4D Constrained Rosenbrock)')
    plt.legend()
    plt.grid(True)
    plt.show()
