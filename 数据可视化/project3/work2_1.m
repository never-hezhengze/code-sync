clc; clear; close all;

% 年份
years = {'1953', '1973', '1982', '1990', '2000'};

% 数据（每行一个年龄组）
data = [
    33.08, 26.27, 18.16, 18.20, 12.20;   % 0~14岁
    65.01, 67.79, 74.40, 72.42, 76.30;   % 15~64岁
    1.97,  5.94,  7.40,  9.38, 11.50     % 65岁以上
];

% 绘图
figure;
bar(data);
colororder("reef")
% 横轴标签（3组）
set(gca, 'XTickLabel', {'0~14岁', '15~64岁', '65岁以上'});

xlabel('年龄组');
ylabel('百分比 (%)');

% 图例（5个年份）
legend(years, 'Location', 'northwest');

grid on;
ylim([0 80]);

title('上海市相应年份人口年龄结构');