% problem2_1_min_vehicle 的 fullness_score
data1 = [
0.422177
0.422783
0.422783
0.422765
0.422765
0.423085
0.575366
0.652636
0.656504
0.422422
0.422957
0.448267
0.464020
];

% problem2_2_min_cost 的 fullness_score
data2 = [
0.464601
0.464601
0.431072
0.431072
0.432061
0.464903
0.575366
0.652636
0.656504
0.464980
0.476132
0.464996
0.464660
];

% 合并数据
data = [data1; data2];

% 分组标签
group = [
    ones(length(data1),1);
    2*ones(length(data2),1)
];

% 绘制箱线图
figure;
boxplot(data, group, 'Labels', {'Min Vehicle', 'Min Cost'});

ylabel('Fullness Score');
title('Comparison of Fullness Score');

grid on;