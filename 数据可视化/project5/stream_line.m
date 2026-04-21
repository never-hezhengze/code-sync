clear; clc; close all;

% 定义网格
x = linspace(-3, 3, 80);
y = linspace(-2, 2, 60);
[X, Y] = meshgrid(x, y);

% 磁铁参数
N = [1, 0];
S = [-1, 0];

% 计算磁场
rN = sqrt((X - N(1)).^2 + (Y - N(2)).^2);
rS = sqrt((X - S(1)).^2 + (Y - S(2)).^2);

rN(rN < 0.2) = 0.2;
rS(rS < 0.2) = 0.2;

Bx = (X - N(1))./rN.^3 - (X - S(1))./rS.^3;
By = (Y - N(2))./rN.^3 - (Y - S(2))./rS.^3;

figure;
hold on;

% 绘制带箭头的流线
h = streamslice(X, Y, Bx, By);
set(h, 'Color', 'b', 'LineWidth', 1.2);

% 绘制条形磁铁
rectangle('Position', [-1, -0.4, 2, 0.8], ...
          'FaceColor', 'r', 'EdgeColor', 'k', 'LineWidth', 2);

% 标注
text(1, 0, 'N', 'FontSize', 14, 'FontWeight', 'bold', ...
    'Color', 'w', 'HorizontalAlignment', 'center');
text(-1, 0, 'S', 'FontSize', 14, 'FontWeight', 'bold', ...
    'Color', 'w', 'HorizontalAlignment', 'center');

% 图形设置
axis equal;
xlim([-3, 3]);
ylim([-2, 2]);
xlabel('x');
ylabel('y');
title('条形磁铁磁场流线（streamslice）');
grid on;
box on;

hold off;