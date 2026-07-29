%北太天元代码
load_plugin("optimization");
% 目标函数的系数（需要最小化的目标函数，因此系数需要取负）
f = [-2; -1.5; -3];

% 不等式约束 A*x <= b
A = [1, 1, 1]  % 猫粮总量约束
b = [10];

% 变量的下界和上界（在这里都是非负的）
lb = [1 ; 2 ; 1] ;  % x 的下界
ub = [4 ; 5 ; 3] ;  % x 的上界

% 线性规划求解
options = optimoptions('linprog','Algorithm','dual-simplex');
[x, fval, exitflag, output] = linprog(f, A, b, [], [], lb, ub, options);

% 输出结果
if exitflag > 0
    fprintf('最优解:\n');
    disp(x);
    fprintf('最大健康指数和（取负后得到的目标函数值）:\n');
    disp(-fval);
else
    fprintf('问题无解或存在其他问题。\n');
end