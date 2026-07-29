% testMyROC 实验一主程序
% 使用data1.mat、data2.mat、data3.mat验证MyROC类的正确性，
% 并进行独立AUC对照验证和重复得分鲁棒性测试。

clear;
clc;

scriptPath = mfilename('fullpath');
if isempty(scriptPath)
    scriptDir = pwd;
else
    scriptDir = fileparts(scriptPath);
end

projectDir = fileparts(scriptDir);
resultDir = fullfile(scriptDir, 'results');
logDir = fullfile(scriptDir, 'run_logs');

if ~exist(resultDir, 'dir')
    mkdir(resultDir);
end

if ~exist(logDir, 'dir')
    mkdir(logDir);
end

dataFiles = {'data1.mat', 'data2.mat', 'data3.mat'};
hasFigure = exist('figure', 'file') == 2 || exist('figure', 'builtin') == 5;
hasPlot = exist('plot', 'file') == 2 || exist('plot', 'builtin') == 5;
hasSaveas = exist('saveas', 'file') == 2 || exist('saveas', 'builtin') == 5;
hasGcf = exist('gcf', 'file') == 2 || exist('gcf', 'builtin') == 5;
canPlot = hasFigure && hasPlot && hasSaveas && hasGcf;

logPath = fullfile(logDir, 'baltamatica_run_output.txt');
logFile = fopen(logPath, 'w');
if logFile ~= -1
    fclose(logFile);
    diary(logPath);
else
    fprintf('无法创建日志文件，将只在命令行输出结果。\n');
end

fprintf('实验一：自定义ROC分析类测试\n');
fprintf('----------------------------------------\n');
if ~canPlot
    fprintf('当前北太天元命令行环境未提供图形函数，跳过ROC图像保存。\n');
end

for i = 1:numel(dataFiles)
    dataPath = fullfile(projectDir, dataFiles{i});
    data = load(dataPath);

    if ~(isfield(data, 'labels') && isfield(data, 'scores'))
        error('数据文件必须包含labels和scores变量。');
    end

    rocObj = MyROC(data.labels, data.scores);
    pairAUC = pairwiseAUC(data.labels, data.scores);

    fprintf('%s: 样本数 = %d, ROC点数 = %d, AUC = %.4f\n', ...
        dataFiles{i}, numel(data.labels), numel(rocObj.FPR), rocObj.AUC);
    fprintf('    Pairwise AUC = %.6f, |MyROC - Pairwise| = %.6g\n', ...
        pairAUC, abs(rocObj.AUC - pairAUC));

    if canPlot
        rocObj.plotROC();
        saveas(gcf, fullfile(resultDir, [dataFiles{i}(1:end-4) '_ROC.png']));
    end
end

% 额外测试：大量样本具有相同预测得分，但分类器仍有区分能力。
tieLabels = [1; 1; 1; 0; 1; 1; 0; 0; 1; 0; 0; 0];
tieScores = [0.9; 0.9; 0.9; 0.9; 0.6; 0.6; 0.6; 0.6; ...
    0.2; 0.2; 0.2; 0.2];
tieROC = MyROC(tieLabels, tieScores);
tiePairAUC = pairwiseAUC(tieLabels, tieScores);

fprintf('tie_test: 样本数 = %d, ROC点数 = %d, AUC = %.4f\n', ...
    numel(tieLabels), numel(tieROC.FPR), tieROC.AUC);
fprintf('    Pairwise AUC = %.6f, |MyROC - Pairwise| = %.6g\n', ...
    tiePairAUC, abs(tieROC.AUC - tiePairAUC));

if canPlot
    tieROC.plotROC();
    saveas(gcf, fullfile(resultDir, 'tie_test_ROC.png'));
end

fprintf('----------------------------------------\n');
if canPlot
    fprintf('测试完成，ROC图像已保存至：%s\n', resultDir);
else
    fprintf('测试完成。当前环境未生成ROC图像，可在支持图形函数的环境中调用plotROC生成图片。\n');
end
diary off;
