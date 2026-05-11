clc; clear; close all;

% 时间范围
t = linspace(0, 10, 200);

% 两条线（可以根据需要调整斜率和截距）
g_f = 0.5*t + 2;   % 上方线 g(f)
g_c = 0.3*t + 1;   % 下方线 g(c)

% 区间 [t_i, t_j]
t_i = 3;
t_j = 7;

% 绘图
figure; hold on;

% 画两条线
plot(t, g_f, 'k', 'LineWidth', 1.5);
plot(t, g_c, 'k', 'LineWidth', 1.5);

% 找到区间内的点
idx = (t >= t_i) & (t <= t_j);

% 填充区域（斜线效果用 hatch 或简单透明代替）
fill([t(idx), fliplr(t(idx))], ...            %fill函数接受X,Y两个向量 依次取两个向量的元素组成坐标点 围成一个封闭图形
     [g_f(idx), fliplr(g_c(idx))], ...
     [0.8 0.8 0.8], 'EdgeColor', 'none', 'FaceAlpha', 0.5);

% 画竖线 ti 和 tj
plot([t_i t_i], [0 g_f(find(t>=t_i,1))], 'k--');
plot([t_j t_j], [0 g_f(find(t>=t_j,1))], 'k--');

% 坐标轴
xlabel('t');
ylabel('F / C');

% 标注
text(8, g_f(end), 'g(f)');
text(8, g_c(end), 'g(c)');
text(t_i, -0.5, 't_i', 'HorizontalAlignment', 'center');
text(t_j, -0.5, 't_j', 'HorizontalAlignment', 'center');

% 轴样式
xlim([0 10]);
ylim([0 8]);
box on;

title('养老保险现金流示意图');

hold off;