% 清理工作区
clear; clc; close all;

% 参数设置
mu = [0, 0];          % 均值向量
sigma = [1, 0.3;      % 协方差矩阵
         0.3, 1];     % 相关系数0.3

% 生成网格数据
x = -3:0.1:3;
y = -3:0.1:3;
[X, Y] = meshgrid(x, y);

% 计算二维高斯联合概率密度
% 公式: p(x,y) = 1/(2π|Σ|^(1/2)) * exp(-1/2 * [x-μ]' * Σ^(-1) * [x-μ])
X_vec = X(:) - mu(1);
Y_vec = Y(:) - mu(2);
Sigma_det = det(sigma);
Sigma_inv = inv(sigma);

% 计算指数部分
for i = 1:length(X_vec)
    Z_vec = [X_vec(i); Y_vec(i)];
    exponent = -0.5 * Z_vec' * Sigma_inv * Z_vec;
    Z(i) = 1/(2*pi*sqrt(Sigma_det)) * exp(exponent);
end

Z = reshape(Z, size(X));

% 绘制曲面图
figure('Position', [100, 100, 800, 600]);
surf(X, Y, Z, 'EdgeColor', 'none', 'FaceAlpha', 0.8);

% 美化图形
colormap('jet');      % 设置颜色映射
colorbar;             % 显示颜色条
xlabel('X', 'FontSize', 12);
ylabel('Y', 'FontSize', 12);
zlabel('Probability Density', 'FontSize', 12);
title('二维高斯联合概率密度函数', 'FontSize', 14);

% 设置视角
view(45, 30);
grid on;

% 可选：添加光照效果
light('Position', [1, 1, 1]);
lighting gouraud;