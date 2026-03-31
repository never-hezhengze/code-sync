clc; clear; close all;

words = ["景色优美","交通方便","人很多","价格偏高", ...
         "服务很好","环境干净","排队时间长","适合拍照", ...
         "设施完善","天气炎热"];

counts = [80,60,50,40,70,65,45,75,55,35];

figure
wc = wordcloud(words, counts);

wc.FontName = 'SimHei';
title('旅游评价词云')