function auc = pairwiseAUC(labels, scores)
    % pairwiseAUC 使用Wilcoxon-Mann-Whitney定义独立验证AUC
    % labels: 真实类别标签，元素取值为0或1
    % scores: 分类器输出的正类得分
    % auc: 正负样本两两比较得到的AUC

    labels = labels(:);
    scores = scores(:);

    if numel(labels) ~= numel(scores)
        error('labels和scores长度必须一致。');
    end
    if ~all(labels == 0 | labels == 1)
        error('labels只能包含0和1。');
    end
    if ~(any(labels == 1) && any(labels == 0))
        error('labels必须同时包含正类1和负类0。');
    end

    positiveScores = scores(labels == 1);
    negativeScores = scores(labels == 0);
    pairCount = numel(positiveScores) * numel(negativeScores);
    winCount = 0;

    for i = 1:numel(positiveScores)
        winCount = winCount + sum(positiveScores(i) > negativeScores);
        winCount = winCount + 0.5 * sum(positiveScores(i) == negativeScores);
    end

    auc = winCount / pairCount;
end
