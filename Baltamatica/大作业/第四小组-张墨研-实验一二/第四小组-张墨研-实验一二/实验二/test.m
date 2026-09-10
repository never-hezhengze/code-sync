%% 数值积分与误差分析实验 - 测试脚本
clear; clc; close all;

%% 测试函数
% 1. 多项式函数
f1 = @(x) x.^4 - 2*x.^3 + x.^2 + 1;
interval1 = [0, 2];
exact1 = 1/5*2^5 - 2/4*2^4 + 1/3*2^3 + 2;

% 2. 三角函数
f2 = @(x) sin(x) + cos(2*x);
interval2 = [0, pi];
exact2 = (-cos(pi)+cos(0)) + (sin(2*pi)/2 - sin(0)/2);

% 3. 指数函数
f3 = @(x) exp(-x.^2);
interval3 = [0, 2];
exact3 = integral(f3, interval3(1), interval3(2));

% 4. 对数函数
f4 = @(x) log(x);
interval4 = [1e-6, 2];
exact4 = 2*log(2) - 2 - (1e-6*log(1e-6) - 1e-6);

% 5. 有理函数
f5 = @(x) 1 ./ (1 + 25*x.^2);
interval5 = [-1, 1];
exact5 = integral(f5, interval5(1), interval5(2));

% 6. 阶梯状函数
f6 = @(x) double(x <= 0.5) + 2*double(x > 0.5);
interval6 = [0, 1];
exact6 = 1*0.5 + 2*0.5;

% 7. 高频振荡函数
f7 = @(x) sin(50*x);
interval7 = [0, 2*pi];
exact7 = 0;

% 8. 高斯型峰值函数
f8 = @(x) exp(-((x-0.5).^2) / 0.01);
interval8 = [0, 1];
exact8 = integral(f8, interval8(1), interval8(2));

% 测试，结构体的最后一项代表是否画图
test_set = {
    f1, interval1, exact1, '多项式函数', false;
    f2, interval2, exact2, '三角函数', false;
    f3, interval3, exact3, '指数函数', false;
    f4, interval4, exact4, '对数函数', false;
    f5, interval5, exact5, '有理函数', false;
    f6, interval6, exact6, '阶梯函数', false;
    f7, interval7, exact7, '高频振荡', false;
    f8, interval8, exact8, '高斯峰值', false
};

segments = 20;
fprintf('\n===== 全部函数批量测试（分段数=%d）=====\n', segments);
for i = 1:size(test_set, 1)
    obj = NumericalIntegrator(test_set{i,1}, test_set{i,2}, segments, test_set{i,3});
    obj = obj.computeAllMethods();
    obj = obj.computeErrors();
    
    fprintf('\n【%s】\n', test_set{i,4});
    fprintf('  中点法误差: %.2e\n', obj.Errors.Midpoint);
    fprintf('  梯形法误差: %.2e\n', obj.Errors.Trapezoidal);
    fprintf('  辛普森误差: %.2e\n', obj.Errors.Simpson);
    if (test_set{i,5})
        obj.plotComparison();
        obj.plotApproximation('midpoint');
        obj.plotApproximation('trapezoidal');
        obj.plotApproximation('simpson');
    end
end