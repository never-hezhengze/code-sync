function [coeff, score, latent] = my_pca(X)
    % X: 输入数据矩阵，每行是一个样本，每列是一个特征
    % coeff: 主成分系数（特征向量）
    % score: 主成分得分（转换后的数据）
    % latent: 特征值

    % 标准化数据（减去均值）
    [m, n] = size(X);
    X_mean = mean(X);
    X_centered = X - repmat(X_mean, m, 1);

    % 计算协方差矩阵
    CovMatrix = cov(X_centered);

    % 计算协方差矩阵的特征值和特征向量
    [V, D] = eig(CovMatrix);

    % 将特征值和特征向量按降序排列
    [latent, order] = sort(diag(D), 'descend');
    V = V(:, order);

    % 计算主成分得分（转换后的数据）
    score = X_centered * V;

    % 返回主成分系数（特征向量）和得分
    coeff = V;
end