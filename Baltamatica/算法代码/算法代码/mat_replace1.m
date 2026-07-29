% 实现成对距离计算（欧几里得距离）
rng default
% 生成100个3维随机点，每行为一个点
X = randi(100, 100, 3);  % 100个3维点

% 初始化距离矩阵，D(i,j)表示第i个点和第j个点之间的距离
n = size(X, 1);    % 获取点的数量
D = zeros(n, n);   % 初始化距离矩阵

tic
% 双重循环计算所有点对之间的欧几里得距离
for i = 1:n
    for j = 1:n
        % 计算第i个点和第j个点的欧几里得距离
        D(i,j) = norm(X(i,:) - X(j,:));
    end
end
toc

save('mat_replace.mat','X','D')