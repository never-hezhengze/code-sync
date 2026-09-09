function y_interp = simple_linear_interp(x, y, x_interp)
% simple_linear_interp - 简单的线性插值函数
% 输入：
%   x - 已知数据点的x坐标向量
%   y - 已知数据点的y坐标向量，与x对应
%   x_interp - 需要插值的x坐标点
% 输出：
%   y_interp - 插值得到的y坐标值

    % 检查输入向量的长度是否匹配
    if length(x) ~= length(y)
        error('x and y vectors must have the same length.');
    end

    % 查找x_interp在x向量中的位置（如果不在范围内，则使用边界点进行插值）
    idx = find(x <= x_interp, 1, 'last');

    % 处理边界情况
    if isempty(idx)
        idx = 1; % x_interp小于x中的所有值，使用第一个点进行插值（外插）
    elseif idx == length(x)
        idx = idx - 1; % x_interp大于x中的所有值，使用最后一个点进行插值（外插）
    else
        % 如果x_interp位于两个数据点之间，则使用这两个点进行插值（内插）
        if x(idx) == x_interp
            y_interp = y(idx); % 如果x_interp恰好等于某个数据点，则直接返回对应的y值
            return;
        end
    end

    % 进行线性插值计算
    x1 = x(idx);
    y1 = y(idx);
    x2 = x(idx + 1);
    y2 = y(idx + 1);

    % 插值公式：y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
    y_interp = y1 + (x_interp - x1) * (y2 - y1) / (x2 - x1);
end