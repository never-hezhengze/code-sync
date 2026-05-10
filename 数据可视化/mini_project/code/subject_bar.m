clc; clear; close all;

subjects = {
    'Artificial intelligence'
    'Machine learning'
    'Computational intelligence'
    'Educational research'
    'Technological innovation'
    'Knowledge and innovation'
    'Internet of things'
    'Data analysis and big data'
    'Data mining'
    'Cloud computing'
    'Smart infrastructure'
    'Knowledge based systems'
    'Internet of things applications in smart environments'
    'Philosophy of artificial intelligence'
    'Education science'
};

counts = [9384 7921 6170 5403 4963 4685 4346 ...
          4082 4039 3904 3816 3616 3558 3523 3518];

% 为了让数量最多的主题显示在最上方，需要反转顺序
subjects_rev = flip(subjects);
counts_rev = flip(counts);

figure;
barh(counts_rev);

set(gca, 'YTick', 1:length(subjects_rev));
set(gca, 'YTickLabel', subjects_rev);
xlabel('文献数量');
ylabel('主题');
title('Springer中Data Science and Big Data Technology相关主题分布');
grid on;

% 在柱子右侧标注数量
for i = 1:length(counts_rev)
    text(counts_rev(i) + 100, i, num2str(counts_rev(i)), ...
        'VerticalAlignment', 'middle', 'FontSize', 9);
end

set(gca, 'FontSize', 10);
set(gcf, 'Position', [100 100 900 600]);