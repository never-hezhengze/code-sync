%% Matlab实验：对标实现两类科学可视化图形
% 图形类别：
% 1) 曲面图（Surface Plot）
% 2) 等高线 + 箭头图 + 流线图（Contour + Quiver + Streamline）
% 说明：
% 本脚本使用虚拟数据进行复现，目标是参考公开资料中的图形结构与表达方式，
% 在 Matlab 中完成同类型图形实现。

clear; clc; close all;

outdir = 'matlab_output_figures';
if ~exist(outdir, 'dir')
    mkdir(outdir);
end

%% Part A. 曲面图：仿照官方 MATLAB 文档中的 surface plot 风格
% 数据采用 peaks 函数，它是 Matlab 常用的示例曲面。
[X, Y, Z] = peaks(121);

fig1 = figure('Color','w','Position',[100 100 900 640]);
surf(X, Y, Z, 'EdgeColor', [0.2 0.2 0.2], 'LineWidth', 0.25);
colormap(parula);
shading interp;
colorbar;
xlabel('X');
ylabel('Y');
zlabel('Z');
title('Surface Plot Based on Virtual Data (peaks)');
view(-35, 28);
grid on;
box on;

exportgraphics(fig1, fullfile(outdir, 'surface_plot_output.png'), 'Resolution', 300);

%% Part B. 等高线图 + 箭头图 + 流线图：对标教学讲义中的向量场图
% 虚拟标量场：f(x,y) = sin(xy)
% 再通过 gradient 计算其梯度场，并绘制 contour、quiver、streamline。
s = linspace(0, 2*pi, 120);
[X2, Y2] = meshgrid(s, s);
F = sin(X2 .* Y2);
[Fx, Fy] = gradient(F, s(2)-s(1), s(2)-s(1));

fig2 = figure('Color','w','Position',[120 120 920 700]);
contour(X2, Y2, F, -1:0.25:1, 'LineWidth', 0.8);
hold on;

step = 6;
quiver(X2(1:step:end,1:step:end), ...
       Y2(1:step:end,1:step:end), ...
       Fx(1:step:end,1:step:end), ...
       Fy(1:step:end,1:step:end), ...
       1.0, 'Color', [0 0.2 0.9]);

startY = linspace(1.5, 2.5, 7);
startX = 2 * ones(size(startY));
streamline(X2, Y2, Fx, Fy, startX, startY);

xlabel('x');
ylabel('y');
title('Contour + Quiver + Streamline Plot Based on Virtual Data');
axis equal;
axis([0 2*pi 0 2*pi]);
grid on;
box on;

exportgraphics(fig2, fullfile(outdir, 'vectorfield_plot_output.png'), 'Resolution', 300);

%% Part C. 可选：分别输出独立版本，便于论文排版
fig3 = figure('Color','w','Position',[140 140 850 650]);
contour(X2, Y2, F, -1:0.25:1, 'LineWidth', 1.0);
colorbar;
xlabel('x'); ylabel('y');
title('Contour Plot of f(x,y)=sin(xy)');
axis equal;
axis([0 2*pi 0 2*pi]);
grid on;
exportgraphics(fig3, fullfile(outdir, 'contour_only_output.png'), 'Resolution', 300);

fig4 = figure('Color','w','Position',[160 160 850 650]);
quiver(X2(1:step:end,1:step:end), ...
       Y2(1:step:end,1:step:end), ...
       Fx(1:step:end,1:step:end), ...
       Fy(1:step:end,1:step:end), ...
       1.0, 'Color', [0 0.2 0.9]);
xlabel('x'); ylabel('y');
title('Quiver Plot of Gradient Field');
axis equal;
axis([0 2*pi 0 2*pi]);
grid on;
exportgraphics(fig4, fullfile(outdir, 'quiver_only_output.png'), 'Resolution', 300);

fig5 = figure('Color','w','Position',[180 180 850 650]);
streamline(X2, Y2, Fx, Fy, startX, startY);
xlabel('x'); ylabel('y');
title('Streamline Plot of Gradient Field');
axis equal;
axis([0 2*pi 0 2*pi]);
grid on;
exportgraphics(fig5, fullfile(outdir, 'streamline_only_output.png'), 'Resolution', 300);

disp('实验完成，图片已输出到 matlab_output_figures 文件夹。');
