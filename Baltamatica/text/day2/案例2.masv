clear;clc;close all;

%% 导入数据 附件1
[num,txt,raw] = xlsread(['附件1：污染物浓度数据.xlsx']); 
time = num(:,1:3);
AQI = num(:,4);
质量等级 = string(txt(2:end,5));
污染物指标 = num(:,6:11);
% 导入数据附件2
气象数据 = xlsread(['附件2：气象数据.xlsx']);

% 将 AQI 和 污染物指标 中等于 0 的值替换为 NaN
AQI(AQI == 0) = NaN; % 替换 AQI 中的 0 为 NaN
污染物指标(污染物指标 == 0) = NaN; % 替换 污染物指标 中的 0 为 NaN


%% 绘制箱线图
figure('Position',[20,50,1650,750]);
ydata = [AQI,污染物指标,气象数据(:,5:9)];
boxchart(ydata,'BoxFaceColor','r','MarkerSize',8,'LineWidth',2)
xticks(1:12)
xticklabels({'AQI','PM10','O3','SO2','PM2.5','NO2','CO','降水量','平均气压','平均2分钟风速','平均气温','平均相对湿度'});

%% 缺失值处理
% 将年、月、日向量转换为 datetime 格式
dateVector = datetime(time);
% 将日期向量转换为从起始点开始的连续时间序列值（以天为单位）
timePoints = days(dateVector - dateVector(1));
dataMatrix = [AQI,污染物指标];

% 使用 pchip 进行插值
for i = 1:size(dataMatrix, 2)
    % 找到非 NaN 的索引
    validIdx = ~isnan(dataMatrix(:, i));
    validData = dataMatrix(validIdx, i);
    validTimePoints = timePoints(validIdx);
    
    % 找到 NaN 的索引
    missingIdx = isnan(dataMatrix(:, i));
    missingTimePoints = timePoints(missingIdx);
    
    % 使用 pchip 进行插值
    if any(missingIdx)
        dataMatrix(missingIdx, i) = pchip(validTimePoints, validData, missingTimePoints);
    end
end

AQI = round(dataMatrix(:,1));
污染物指标(:,1:5) = round(dataMatrix(:,2:6));
污染物指标(:,6) = round(dataMatrix(:,7),1);

% % 转换为 cell 数组以便处理
% 质量等级 = cellstr(质量等级);

%% 定义 AQI 范围与质量等级的对应关系
AQI_ranges = [0, 50, 100, 150, 200, 300, 500];
quality_levels = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"];

% 查找空气质量等级为空或无的值
empty_indices = strcmp(质量等级, "") | strcmp(质量等级, "无");

% 根据 AQI 指数补充空气质量等级
for i = 1:length(AQI)
    if empty_indices(i)
        % 找到 AQI 所在的范围
        for j = 1:length(AQI_ranges)-1
            if AQI(i) >= AQI_ranges(j) && AQI(i) < AQI_ranges(j+1)
                质量等级(i) = quality_levels(j);
                break;
            end
        end
    end
end


writematrix([num(:,1:3),AQI], '附件1：处理后的数据.xlsx', "FileType", "spreadsheet");
writematrix(质量等级, '附件1：处理后的数据.xlsx', "FileType", "spreadsheet", "Range", "E1");
writematrix(污染物指标, '附件1：处理后的数据.xlsx', "FileType", "spreadsheet", "Range", "F1");

%% 异常值处理
% 将年、月、日向量转换为 datetime 格式
dateVector = datetime(气象数据(:,2), 气象数据(:,3), 气象数据(:,4));
% 将日期向量转换为从起始点开始的连续时间序列值（以天为单位）
timePoints = days(dateVector - dateVector(1));
dataMatrix = 气象数据(:,5:9);
% 初始化一个逻辑矩阵来存储异常值索引
outlierIndices = false(size(dataMatrix));

% 对每组数据进行异常值检测
for i = 1:size(dataMatrix, 2)
    data = dataMatrix(:, i);
    % 计算均值和标准差
    
    meanData = mean(data);
    stdData = std(data);
    
    % 计算 Z-score
    zScores = (data - meanData) / stdData;
    
    % 找到 Z-score 绝对值大于3的索引
    outlierIndices(:,i) = abs(zScores) > 3;
    
end

% 将异常值替换为NaN
dataMatrix(outlierIndices) = NaN;

% 使用拉格朗日插值法填充缺失值
for i = 1:size(dataMatrix, 2)
    % 找到非 NaN 的索引
    validIdx = ~isnan(dataMatrix(:, i));
    validData = dataMatrix(validIdx, i);
    validTimePoints = timePoints(validIdx);
    
    % 找到 NaN 的索引
    missingIdx = isnan(dataMatrix(:, i));
    missingTimePoints = timePoints(missingIdx);
    
    % 使用拉格朗日插值法填充缺失值
    if any(missingIdx)
        dataMatrix(missingIdx,i) = interp1(validTimePoints, validData, missingTimePoints, 'pchip');
    end
end

气象数据(:,5:9) = dataMatrix;
writematrix(气象数据,'附件2去除异常值后的数据.xlsx')


%% 数据标准化
data_all = [污染物指标,气象数据(:,5:9)];

% 最小-最大标准化
min_values = min(data_all, [], 1); % 每列的最小值
max_values = max(data_all, [], 1); % 每列的最大值
normalized_min_max = (data_all - min_values) ./ (max_values - min_values);

writematrix(normalized_min_max,'最小-最大标准化后的数据.xlsx');

% Z-score 标准化
mean_values = mean(data_all, 1); % 每列的均值
std_values = std(data_all, 0, 1); % 每列的标准差
normalized_z_score = (data_all - mean_values) ./ std_values;

writematrix(normalized_z_score,'Z-score准化后的数据.xlsx');


%% 对标准化后的完整插补数据进行 Kolmogorov-Smirnov 检验(KS 检验)
% 定义最大最小标准化对应的 kstest 检验的p值和统计量
H_mm = zeros(size(data_all,2),1);
p_mm = zeros(size(data_all,2),1);
KSSTAT_mm = zeros(size(data_all,2),1);
% 定义 Z-score 标准化对应的 kstest 检验的p值和统计量
H_Zs = zeros(size(data_all,2),1);
p_Zs = zeros(size(data_all,2),1);
KSSTAT_Zs = zeros(size(data_all,2),1);

for i=1:size(data_all,2)
    
    [H_mm(i),p_mm(i),KSSTAT_mm(i)] = kstest(normalized_min_max(:,i));
    [H_Zs(i),p_Zs(i),KSSTAT_Zs(i)] = kstest(normalized_z_score(:,i));
end

% 创建结果表格
resultTable = table([H_mm,p_mm,KSSTAT_mm],[H_Zs,p_Zs,KSSTAT_Zs],...
    'VariableNames', {'最大最小标准化的KS检验', 'Z-score 标准化的KS检验'}, ...
    'RowNames', {'PM10','O3','SO2','PM2.5','NO2','CO','降水量','平均气压','平均2分钟风速','平均气温','平均相对湿度'});