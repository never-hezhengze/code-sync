% 使用北太天元的polyfit函数来拟合一条直线，返回线性系数a和b
% 示例数据点
x = [1, 2, 3, 4, 5];
y = [2.2, 2.8, 3.6, 4.5, 5.1];

p = polyfit(x, y, 1); % 1表示线性拟合

% 提取系数
a = p(1);
b = p(2);

% 显示结果
fprintf('拟合的直线方程为: y = %.2fx + %.2f\n', a, b);

% 绘制原始数据点和拟合的直线
scatter(x, y, 'filled');
hold on;
plot(x, a*x + b, 'r', 'LineWidth', 2);
xlabel('x');ylabel('y');
title('线性回归拟合');
legend('数据点', '拟合直线');
grid on;
hold off; 