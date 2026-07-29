% 假设我们有一个20行4列的数据集
rng default;
X = rand(20, 4);

% 标准化数据
X_mean = mean(X);
X_std = std(X);
X_scaled = (X - X_mean) ./ X_std;

% 应用PCA
[coeff, score, latent] = my_pca(X_scaled);

% 选择前两个主成分
coeff_2d = coeff(:, 1:2);
score_2d = score(:, 1:2);

% 现在score_2d包含了降维到2维的数据
disp(['原数据大小: ', num2str(size(X))]);
disp(['转换后数据大小: ', num2str(size(score_2d))]);

% 可以选择打印出解释方差比，以了解所选主成分能够解释原始数据方差的百分比
explained_variance_ratio = latent(1:2) / sum(latent);
disp(['解释方差比: ', num2str(explained_variance_ratio')]);

close all
figure(1)

scatter(score_2d(:,1), score_2d(:,2),'filled')
for i=1:size(score_2d,1)
    text(score_2d(i,1),score_2d(i,2), num2str(i));
end
xlabel("第一主成分")
ylabel("第二主成分")
title("北太天元: 画成降维后的两个主成分上的得分")

figure(2)
hold on
for i=1:size(coeff_2d,1)
    text(coeff_2d(i,1), coeff_2d(i,2), ['第', num2str(i), 'feature']);
    quiver( 0, 0 , coeff_2d(i,1), coeff_2d(i,2),0);
end
xlabel("第一主成分")
ylabel("第二主成分")
title("北太天元: 各个feature对主成分的贡献")
hold off