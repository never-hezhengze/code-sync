%% 生成10个虚拟数据点并绘制散点图
clear; clc; close all;

% 生成10个虚拟数据点
% 方法1：手动指定数据
x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
y = [2.3, 4.1, 5.8, 7.2, 8.5, 9.1, 7.8, 6.5, 4.2, 3.1];

% 绘制散点图
figure('Position', [100, 100, 800, 600]);
scatter(x, y, 80, 'filled', 'b');
xlabel('X轴', 'FontSize', 12);
ylabel('Y轴', 'FontSize', 12);
title('10个虚拟数据点的散点图', 'FontSize', 14);
grid on;