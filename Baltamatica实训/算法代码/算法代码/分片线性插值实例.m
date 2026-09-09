% 北太天元代码
% 原始数据点
x = [1, 2, 3, 4, 5];
y = [2, 3, 5, 7, 11];

% 需要插值的x坐标点
x_interp = 1.5;

% 调用线性插值函数（这里假设simple_linear_interp是之前定义的函数）
y_interp = simple_linear_interp(x, y, x_interp);

% 绘制原始数据点（用红圈表示）
plot(x, y, 'ro', 'MarkerFaceColor', 'r');
hold on; % 保持图像，以便在上面继续绘制

% 绘制插值点（用叉号表示）
plot(x_interp, y_interp, 'kx', 'MarkerSize', 15, 'LineWidth', 2);

% 绘制连接原始数据点的线段，形成分片线性插值的可视化
for i = 1:length(x)-1
    plot(x(i:i+1), y(i:i+1), 'b-');
end

% 添加图例和轴标签
legend('原始数据点', '插值点', '分片线性插值', 'Location', 'best');
xlabel('x');
ylabel('y');
title('分片线性插值示例');
grid on; % 打开网格线以便观察
hold off; % 释放图像 