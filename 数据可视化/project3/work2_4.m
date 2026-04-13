% 数据
categories = {'心', '肝', '脾', '肺', '肾', '脑'};
percentages = [7, 52, 1, 6, 27, 7]; 

% 颜色
colors = [0.85 0.45 0.45;  
          0.60 0.75 0.45;  
          0.90 0.70 0.40;  
          0.95 0.85 0.65;  
          0.50 0.40 0.35;  
          0.75 0.55 0.45];

figure('Position', [100, 100, 900, 700]);

% 饼图
p = piechart(percentages, categories);

% 颜色
p.ColorOrder = colors;

% 设置标题
p.Title = '分布量对比图';

% 在侧边显示类别
p.LegendVisible = 'on';

% 背景
set(gcf, 'Color', 'white');