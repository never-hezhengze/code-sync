clc; clear; close all;

%% ===== 表格数据 =====
x = [60 70 80 90 100 110 120];   % 圆柱半径（nm）

random = [510 555 570 620 656 690 720];  % 随机（nm）
extinction = [480 510 540 570 600 636 670]; % 消光（nm）

%% ===== 绘制散点图 =====
figure;

% 第一组（蓝色圆点）
scatter(x, random, 60, 'b', 'filled'); 
hold on;

% 第二组（橙色三角）
scatter(x, extinction, 70, '^', 'MarkerEdgeColor',[0.85 0.33 0.1], ...
    'MarkerFaceColor',[0.85 0.33 0.1]);

%% ===== 坐标与标签 =====
xlabel('圆柱半径 (nm)');
ylabel('波长 (nm)');

xlim([50 130]);
ylim([450 750]);

%% ===== 图例 =====
legend('随机', '消光', 'Location', 'northwest');

%% ===== 网格与美化 =====
grid on;
box on;

title('(b)');
