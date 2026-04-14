clc; clear; close all;

% ===== 模拟数据 =====
rng(1);

% group0：双峰分布
n0 = 200;       % group0 总样本数
p = 0.5;        % 两个峰比例
sigma = 0.12;   % 控制峰的分离程度（关键参数）

idx = rand(n0,1) < p;

group0 = zeros(n0,1);
group0(idx)  = 4.8 + sigma * randn(sum(idx),1);
group0(~idx) = 5.3 + sigma * randn(sum(~idx),1);

% group1
group1 = [5.0 + 0.1*randn(50,1); 5.15 + 0.1*randn(100,1)];

% 合并数据 
y = [group0; group1];

% 分类变量
group = categorical([zeros(n0,1); ones(150,1)], [0 1], {'0.0','1.0'});

% 画小提琴图
figure;
v = violinplot(y, GroupByColor=group);

v(1).FaceColor = [0.4 0.6 0.8]; % group0
v(2).FaceColor = [0.9 0.5 0.3]; % group1

xlabel('分类标签');
ylabel('红细胞');
title('不同患病情况下的红细胞情况');

grid on;