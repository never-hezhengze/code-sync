% 批量张量矩阵乘法（矩阵化实现）
load('for_replace.mat')
x = reshape(x, 1, 20, 1);   % 将x重塑为1x20x1，便于与T按维度广播相乘
y = reshape(y, 1, 1, 30);   % 将y重塑为1x1x30，便于与T按维度广播相乘

tic
% 逐元素相乘后，先对第3维(k)求和，再对第2维(j)求和，最终得到100x1的结果
r2 = sum(sum(T .* x .* y, 3), 2);  % 按 j, k 维度求和，保留 i
toc

isequal(r, r2)  % 验证结果是否一致