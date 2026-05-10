clc; clear; close all;

% 设置中文字体
set(0,'defaultAxesFontName','SimSun');
set(0,'defaultTextFontName','SimSun');

% 横轴：查全率 Recall
x = linspace(0,1,500);

% 构造三条 P-R 曲线的控制点
xA = [0 0.2 0.4 0.6 0.75 0.82 0.9 1.0];
yA = [1 0.99 0.96 0.91 0.86 0.80 0.62 0];

xB = [0 0.2 0.4 0.6 0.72 0.80 0.9 1.0];
yB = [1 0.94 0.87 0.83 0.78 0.72 0.65 0];

xC = [0 0.2 0.4 0.55 0.65 0.75 0.88 1.0];
yC = [1 0.91 0.80 0.70 0.65 0.55 0.38 0];

% 使用 pchip 插值得到平滑曲线
YA = interp1(xA, yA, x, 'pchip');
YB = interp1(xB, yB, x, 'pchip');
YC = interp1(xC, yC, x, 'pchip');

YA = max(min(YA,1),0);
YB = max(min(YB,1),0);
YC = max(min(YC,1),0);

% -------------------------------------------------
% 求平衡点：即 P-R 曲线与 y = x 的交点
% -------------------------------------------------
fA = @(t) interp1(xA, yA, t, 'pchip') - t;
fB = @(t) interp1(xB, yB, t, 'pchip') - t;
fC = @(t) interp1(xC, yC, t, 'pchip') - t;

pxA = fzero(fA, [0 1]);
pxB = fzero(fB, [0 1]);
pxC = fzero(fC, [0 1]);

pA = [pxA, pxA];
pB = [pxB, pxB];
pC = [pxC, pxC];

points = [pA; pB; pC];

% -------------------------------------------------
% 绘图
% -------------------------------------------------
figure;
hold on;
box on;

% 绘制 P-R 曲线
plot(x, YA, 'Color', [0.85 0.35 0.35], 'LineWidth', 2.2);
plot(x, YB, 'k', 'LineWidth', 1.8);
plot(x, YC, 'k', 'LineWidth', 1.8);

% 绘制平衡线 y = x
plot([0 1], [0 1], '--', ...
    'Color', [0.85 0.35 0.35], ...
    'LineWidth', 1.2);

% 绘制真实平衡点和辅助虚线
for i = 1:size(points,1)
    px = points(i,1);
    py = points(i,2);

    plot(px, py, 'o', ...
        'MarkerSize', 8, ...
        'MarkerFaceColor', [0.85 0.35 0.35], ...
        'MarkerEdgeColor', [0.85 0.35 0.35]);

    plot([px px], [0 py], '--', ...
        'Color', [0.85 0.35 0.35], ...
        'LineWidth', 1.0);

    plot([0 px], [py py], '--', ...
        'Color', [0.85 0.35 0.35], ...
        'LineWidth', 1.0);
end

% 添加箭头，指向真实平衡点
quiver(0.72, 0.97, pA(1)-0.72, pA(2)-0.97, 0, ...
    'Color', [0.85 0.35 0.35], ...
    'LineWidth', 1.2, ...
    'MaxHeadSize', 0.45);

quiver(0.69, 0.94, pB(1)-0.69, pB(2)-0.94, 0, ...
    'Color', [0.85 0.35 0.35], ...
    'LineWidth', 1.2, ...
    'MaxHeadSize', 0.45);

quiver(0.66, 0.91, pC(1)-0.66, pC(2)-0.91, 0, ...
    'Color', [0.85 0.35 0.35], ...
    'LineWidth', 1.2, ...
    'MaxHeadSize', 0.45);

% 标注文字
text(0.36, 0.97, 'A', 'FontSize', 14);
text(0.97, 0.52, 'B', 'FontSize', 14);
text(0.43, 0.72, 'C', 'FontSize', 14);

text(0.62, 0.98, '平衡点', ...
    'FontSize', 13, ...
    'Color', [0.45 0.25 0.25]);

% 坐标轴设置
xlabel('查全率', 'FontSize', 14);
ylabel('查准率', 'FontSize', 14);

xlim([0 1]);
ylim([0 1]);

xticks(0:0.2:1);
yticks(0:0.2:1);

axis square;
set(gca, 'FontSize', 12, 'LineWidth', 1.2);

title('P-R曲线与平衡点示意图', 'FontSize', 14);

hold off;