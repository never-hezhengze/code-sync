classdef MyROC
    % MyROC 自定义ROC分析类
    %   Labels: 真实类别标签，列向量，元素取值为0或1
    %   Scores: 分类器输出的正类得分，列向量
    %   FPR: 假阳性率向量
    %   TPR: 真阳性率向量
    %   AUC: ROC曲线下面积

    properties (SetAccess = private)
        Labels
        Scores
        FPR
        TPR
        AUC
    end

    methods
        function obj = MyROC(labels, scores)
            % 构造函数：保存标签和得分，并自动计算ROC曲线与AUC
            labels = labels(:);
            scores = scores(:);

            if numel(labels) ~= numel(scores)
                error('labels and scores must have the same number of elements.');
            end
            if any((labels ~= 0) & (labels ~= 1))
                error('labels must contain only 0 and 1.');
            end

            obj.Labels = labels;
            obj.Scores = scores;
            obj = obj.computeROC();
            obj = obj.computeAUC();
        end

        function obj = computeROC(obj)
            % computeROC 根据标签和得分计算不同阈值下的FPR和TPR
            labels = obj.Labels;
            scores = obj.Scores;
            positiveCount = sum(labels == 1);
            negativeCount = sum(labels == 0);

            % 按得分降序排序，在每组相同得分的末尾记录ROC点。
            [sortedScores, sortIndex] = sort(scores, 'descend');
            sortedLabels = labels(sortIndex);
            scoreChangeIndex = [find(diff(sortedScores) ~= 0); numel(sortedScores)];

            cumulativeTP = cumsum(sortedLabels == 1);
            cumulativeFP = cumsum(sortedLabels == 0);
            tpr = [0; cumulativeTP(scoreChangeIndex) / positiveCount; 1];
            fpr = [0; cumulativeFP(scoreChangeIndex) / negativeCount; 1];

            obj.FPR = fpr;
            obj.TPR = tpr;
        end

        function obj = computeAUC(obj)
            % computeAUC 使用梯形法计算ROC曲线下面积
            obj.AUC = trapz(obj.FPR, obj.TPR);
        end

        function plotROC(obj, plotTitle)
            % plotROC 绘制ROC曲线，并在图中标注AUC值
            figure;
            plot(obj.FPR, obj.TPR, 'b-');
            hold on;
            plot([0 1], [0 1], 'r--');
            hold off;

            xlabel('False Positive Rate');
            ylabel('True Positive Rate');
            title(plotTitle);
            legend('ROC Curve', 'Random Classifier');
            text(0.62, 0.12, ['AUC = ' num2str(obj.AUC, '%.4f')]);
            grid on;
            axis([0 1 0 1]);
        end

    end
end
