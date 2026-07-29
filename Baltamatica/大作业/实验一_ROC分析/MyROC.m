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
            if nargin == 0
                obj.Labels = [];
                obj.Scores = [];
                obj.FPR = [];
                obj.TPR = [];
                obj.AUC = [];
                return;
            end

            if nargin ~= 2
                error('构造函数必须同时输入labels和scores。');
            end
            if ~(isnumeric(labels) && isnumeric(scores))
                error('labels和scores必须为数值向量。');
            end
            if ~(isvector(labels) && isvector(scores))
                error('labels和scores必须为向量。');
            end
            if isempty(labels) || isempty(scores)
                error('labels和scores不能为空。');
            end
            if numel(labels) ~= numel(scores)
                error('labels和scores长度必须一致。');
            end

            labels = labels(:);
            scores = scores(:);

            if ~all(labels == 0 | labels == 1)
                error('labels只能包含0和1。');
            end
            if ~all(isfinite(scores))
                error('scores不能包含NaN或Inf。');
            end
            if ~(any(labels == 1) && any(labels == 0))
                error('labels必须同时包含正类1和负类0，否则ROC曲线和AUC无定义。');
            end

            obj.Labels = labels;
            obj.Scores = scores;
            obj = obj.computeROC();
            obj = obj.computeAUC();
        end

        function obj = computeROC(obj)
            % computeROC 根据标签和得分计算不同阈值下的FPR和TPR
            if isempty(obj.Labels) || isempty(obj.Scores)
                error('请先提供Labels和Scores。');
            end

            labels = obj.Labels(:);
            scores = obj.Scores(:);
            positiveCount = sum(labels == 1);
            negativeCount = sum(labels == 0);

            if ~(positiveCount > 0 && negativeCount > 0)
                error('labels必须同时包含正类1和负类0，否则ROC曲线和AUC无定义。');
            end

            % 按得分降序排序后按同分组累计，避免逐阈值重复扫描全样本。
            [sortedScores, sortIndex] = sort(scores, 'descend');
            sortedLabels = labels(sortIndex);
            scoreChangeIndex = [find(diff(sortedScores) ~= 0); numel(sortedScores)];

            fpr = zeros(numel(scoreChangeIndex) + 2, 1);
            tpr = zeros(numel(scoreChangeIndex) + 2, 1);
            truePositive = 0;
            falsePositive = 0;
            previousIndex = 1;

            for i = 1:numel(scoreChangeIndex)
                currentIndex = scoreChangeIndex(i);
                groupLabels = sortedLabels(previousIndex:currentIndex);

                truePositive = truePositive + sum(groupLabels == 1);
                falsePositive = falsePositive + sum(groupLabels == 0);

                tpr(i + 1) = truePositive / positiveCount;
                fpr(i + 1) = falsePositive / negativeCount;
                previousIndex = currentIndex + 1;
            end

            % 最后一项对应阈值 -Inf；它与最后一个唯一得分后的端点一致，
            % 保留该点是为了明确覆盖“全判为正类”的极端情况。
            fpr(end) = 1;
            tpr(end) = 1;

            obj.FPR = fpr;
            obj.TPR = tpr;
        end

        function obj = computeAUC(obj)
            % computeAUC 使用梯形法计算ROC曲线下面积
            if isempty(obj.FPR) || isempty(obj.TPR)
                error('请先调用computeROC计算FPR和TPR。');
            end
            if numel(obj.FPR) ~= numel(obj.TPR)
                error('FPR和TPR长度必须一致。');
            end

            sortedFPR = obj.FPR(:);
            sortedTPR = obj.TPR(:);
            if ~all(diff(sortedFPR) >= -eps)
                error('FPR必须按升序排列，请先重新调用computeROC。');
            end

            obj.AUC = trapz(sortedFPR, sortedTPR);
        end

        function plotROC(obj)
            % plotROC 绘制ROC曲线，并在图中标注AUC值
            if isempty(obj.FPR) || isempty(obj.TPR) || isempty(obj.AUC)
                error('请先完成ROC和AUC计算。');
            end

            figure('Color', 'w');
            if numel(obj.FPR) <= 200
                plot(obj.FPR, obj.TPR, 'b-o', 'LineWidth', 2, 'MarkerSize', 4);
            else
                plot(obj.FPR, obj.TPR, 'b-', 'LineWidth', 2);
            end
            hold on;
            plot([0 1], [0 1], 'r--', 'LineWidth', 1.5);
            hold off;

            xlabel('False Positive Rate', 'FontSize', 12);
            ylabel('True Positive Rate', 'FontSize', 12);
            title('Receiver Operating Characteristic (ROC) Curve', 'FontSize', 12);
            legend('ROC Curve', 'Random Classifier', 'Location', 'SouthEast');
            text(0.62, 0.12, ['AUC = ' num2str(obj.AUC, '%.4f')], ...
                'FontSize', 12, 'BackgroundColor', 'w', 'EdgeColor', [0.7 0.7 0.7]);
            grid on;
            axis([0 1 0 1]);
            set(gca, 'FontSize', 12);
        end
    end
end
