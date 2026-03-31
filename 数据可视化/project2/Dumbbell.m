clc; clear; close all;

%% ========== 1. 构造数据（哑铃分布） ==========
n = 500;
data = [randn(n,1)*1.5 - 8; randn(n,1)*1.5 + 8];

%% ========== 2. 三图对比 ==========
figure('Position',[100 100 1200 400])

%% ---------- (1) 小提琴图 ----------
subplot(1,3,1)

violinplot(data);

title('Violin Plot')
ylabel('Value')

%% ---------- (2) 直方图 ----------
subplot(1,3,2)

histogram(data,30)
title('Histogram')

%% ---------- (3) 箱线图 ----------
subplot(1,3,3)

boxplot(data)
title('Boxplot')