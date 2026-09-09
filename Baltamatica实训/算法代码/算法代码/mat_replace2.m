% 实现成对距离计算（欧几里得距离）

load mat_replace.mat

% 初始化距离矩阵，D(i,j)表示第i个点和第j个点之间的距离
n = size(X, 1);    % 获取点的数量
D2 = zeros(n, n);   % 初始化距离矩阵

tic
% 双重循环计算所有点对之间的欧几里得距离
for i = 1:n
    for j = i:n
        % 计算第i个点和第j个点的欧几里得距离
        D2(i,j) = norm(X(i,:) - X(j,:));
    end
end
toc
isequal(triu(D),D2)