% 批量张量矩阵乘法
rng default
T = randi(100, 100, 20, 30);   % 生成一个100x20x30的三维张量
x = randi(100, 20, 1);         % 生成20维列向量
y = randi(100, 30, 1);         % 生成30维列向量
r = zeros(100, 1);       % 初始化结果向量

tic
% 三重循环实现批量张量与向量的乘法
for i = 1:100           % 遍历第1维（样本数）
    for j = 1:20        % 遍历第2维
        for k = 1:30    % 遍历第3维
            % 对每个样本，累加T(i,j,k) * x(j) * y(k)
            r(i) = r(i) + T(i,j,k) * x(j) * y(k);
        end
    end
end
toc

save('for_replace.mat','T','x','y','r')