% 初始化参数
numSimulations = 100000; % 模拟次数10万
winsA = 0; % A获胜次数
winsB = 0; % B获胜次数
% 进行蒙特卡洛模拟
for i = 1:numSimulations
    scoreA = 2; % A初始胜局数
    scoreB = 1; % B初始胜局数
    while true
        % 随机决定每局的胜者
        if rand() < 0.5
            scoreA = scoreA + 1;
        else
            scoreB = scoreB + 1;
        end
        % 判断是否有赌徒获胜
        if scoreA == 3
            winsA = winsA + 1;
            break;
        elseif scoreB == 3
            winsB = winsB + 1;
            break;
        end
    end
end% 计算并显示获胜概率
probWinA = winsA / numSimulations;
probWinB = winsB / numSimulations;
fprintf('赌徒A获胜的概率: %f\n', probWinA);
fprintf('赌徒B获胜的概率: %f\n', probWinB);


