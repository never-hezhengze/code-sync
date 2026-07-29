% 导入附件 1 数据
data_GKD = readmatrix('附件1.csv',"OutputType","string");  % 导入数据附件1
data_GKD = data_GKD(2:end,:); % 删除标题行
data_GKD_z = str2double(data_GKD(:,1:6)); % 获取数值数据"两尘四气"
data_GKD_time = datetime(data_GKD(:,7),'Format','yyyy/MM/dd HH:mm'); % 获取检测时间点数据（年月日时）
data_GKD_Str = data_GKD(:,7); %保存时间字符串
disp(sprintf('导入国控点原始数据的行数为：%d',size(data_GKD_z,1)));

%% 导入附件 2 数据
data_ZJD = readmatrix('附件2.csv',"OutputType","string");  % 导入数据附件2
data_ZJD = data_ZJD(2:end,:);  % 删除标题行
data_ZJD_z = str2double(data_ZJD(:,1:11));% 获取数值数据"两尘四气"及风速、压强、降水量、温度、湿度
data_ZJD_time = datetime(data_ZJD(:,12),'Format','yyyy/MM/dd HH:mm'); % % 获取检测时间点数据（年月日时分）
data_ZJD_Str = data_ZJD(:,12); %保存时间字符串
disp(sprintf('导入自建点原始数据的行数为：%d',size(data_ZJD_z,1)));

%% 缺失值和异常值分析
% 将两尘四气绘制为时间的函数
标题 = string({"PM2.5";"PM10";"CO";"NO2";"SO2";"O3";"风速";"压强";"降水量";"温度";"湿度"});
figure(1)
for i=1:6
    subplot(2,3,i);
    plot(data_GKD_z(1001:2000,i),'ro','MarkerSize',4)
    title(标题(i))
end

figure(2)
for i=1:11
    subplot(4,3,i);
    plot(data_ZJD_z(1:1000,i),'ro','MarkerSize',4)
    title(标题(i))
end

if any(isnan(data_GKD_z),'all') || any(ismissing(data_GKD_Str))
    disp("国控点数据含有缺失值，需进一步处理");
else
    disp("国控点数据不含缺失值。");
end
if any(isnan(data_ZJD_z),'all') || any(ismissing(data_ZJD_Str))
    disp("自建点数据含有缺失值，需进一步处理");
else
    disp("自建点数据不含缺失值。");
end

%% 重复值分析
% 自建点相同时间点取平均值
[uniqueTimePoints, ~, idx] = unique(data_ZJD_Str);  % 返回唯一值和唯一值对应的索引值
counts = accumarray(idx, 1);  % 统计每个唯一值出现的次数
repeatedTimePoints = uniqueTimePoints(counts > 1); % 将大于1次的视为重复值

for i=1:size(repeatedTimePoints,1)   % 开始遍历重复值
    wz = find(data_ZJD_Str == repeatedTimePoints(i),1000,'last');  % 查找重复值的索引
    data_ZJD_Str(wz(2:end)) = []; % 删除重复的时间点
    data_ZJD_z(wz(1),:) = mean(data_ZJD_z(wz,:),1); % 将重复的检测值取平均值
    data_ZJD_z(wz(2:end),:) = [];% 删除其余数据
end
disp(sprintf('处理重复自建点数据后的行数为：%d',size(data_ZJD_z,1)));



%%

% 初始化一个逻辑矩阵来存储异常值索引
outlierIndices = false(size(data_ZJD_z));

% 对每组数据进行异常值检测
for i = 1:size(data_ZJD_z, 2)
    % 计算均值和标准差
    meanData = mean(data_ZJD_z(:, i));
    stdData = std(data_ZJD_z(:, i));
    
    % 计算 Z-score
    zScores = (data_ZJD_z(:, i) - meanData) / stdData;
    
    % 找到 Z-score 绝对值大于3的索引
    outlierIndices(:,i) = abs(zScores) > 3;
end

% 找到包含异常值的行索引
outlierColumns = any(outlierIndices, 2);

% 删除包含异常值的整行
data_ZJD_z = data_ZJD_z(~outlierColumns,:);
data_ZJD_Str = data_ZJD_Str(~outlierColumns);
disp(sprintf('处理异常值自建点数据后的行数为：%d',size(data_ZJD_z,1)));
% 保存结果
writematrix([data_ZJD_z,data_ZJD_Str],'处理后的数据.csv')

%%
% 初始化一个逻辑矩阵来存储异常值索引
outlierIndices = false(size(data_GKD_z));

% 对每组数据进行异常值检测
for i = 1:size(data_GKD_z, 2)
    % 计算均值和标准差
    meanData = mean(data_GKD_z(:, i));
    stdData = std(data_GKD_z(:, i));
    
    % 计算 Z-score
    zScores = (data_GKD_z(:, i) - meanData) / stdData;
    
    % 找到 Z-score 绝对值大于3的索引
    outlierIndices(:,i) = abs(zScores) > 3;
end

% 找到包含异常值的行索引
outlierColumns = any(outlierIndices, 2);

% 删除包含异常值的整行
data_GKD_z = data_GKD_z(~outlierColumns,:);
data_GKD_Str = data_GKD_Str(~outlierColumns);
disp(sprintf('处理异常值国控点点数据后的行数为：%d',size(data_GKD_z,1)));
% 保存结果
writematrix([data_GKD_z,data_GKD_Str],'处理后的国控点数据.csv')

%% 保存可用数据为mat文件
% save('清洗完全部数据.mat','data_*')
save('清洗完全部数据.mat','data_ZJD_z','data_ZJD_Str','data_GKD_z','data_GKD_Str')

clear;clc;
% 后面的建模过程中可以直接拿来使用
load('清洗完全部数据.mat')