classdef NumericalIntegrator
/*
本类是用三种经典的面积近似方法来近似计算数值积分
可以绘制柱状对比图和三种方法的示意图
*/

    properties
        Function       
        Interval     
        Segments
        ExactValue
        
        % 三种近似方法对应的误差，结果
        Errors
        Results       
        Nodes = []     
        f_Nodes = []   
    end

    methods
        %% 构造函数
        function obj = NumericalIntegrator(f, interval, segments, exact)
            obj.Function = f;
            obj.Interval = interval;
            obj.Segments = segments;
            obj.ExactValue = exact;
            % 初始化结果与误差结构体
            obj.Results = struct(...
                'Midpoint', [], ...
                'Trapezoidal', [], ...
                'Simpson', []);
            obj.Errors = struct(...
                'Midpoint', [], ...
                'Trapezoidal', [], ...
                'Simpson', []);
        end

        %% 中点矩形法
        function [result, nodes, f_nodes] = rectangularMid(obj)
            a = obj.Interval(1);
            b = obj.Interval(2);
            n = obj.Segments;
            h = (b - a) / n;

            % 生成各分段中点
            nodes = a + h/2 + (0:n-1)*h;
            f_nodes = obj.Function(nodes);
            result = h * sum(f_nodes);
            
            obj.Nodes = nodes;
            obj.f_Nodes = f_nodes;
        end

        %% 梯形法
        function [result, nodes, f_nodes] = trapezoidal(obj)
            a = obj.Interval(1);
            b = obj.Interval(2);
            n = obj.Segments;
            h = (b - a) / n;

            % 生成分段端点
            nodes = linspace(a, b, n+1);
            f_nodes = obj.Function(nodes);
            result = h/2 * (f_nodes(1) + 2*sum(f_nodes(2:end-1)) + f_nodes(end));
            
            obj.Nodes = nodes;
            obj.f_Nodes = f_nodes;
        end

        %% 辛普森法
        function [result, nodes, f_nodes] = simpson(obj)
            a = obj.Interval(1);
            b = obj.Interval(2);
            n = obj.Segments;

            if mod(n, 2) ~= 0
                error('辛普森法要求分段数 Segments 为偶数');
            end

            h = (b - a) / n;
            nodes = linspace(a, b, n+1);
            f_nodes = obj.Function(nodes);

            % 复合辛普森公式
            result = h/3 * (f_nodes(1) + f_nodes(end) ...
                + 4*sum(f_nodes(2:2:end-1)) ...
                + 2*sum(f_nodes(3:2:end-2)));

            % 更新类属性
            obj.Nodes = nodes;
            obj.f_Nodes = f_nodes;
        end

        %% 计算所有方法的积分值
        function obj = computeAllMethods(obj)
            [res_mid, ~, ~] = obj.rectangularMid();
            [res_trap, ~, ~] = obj.trapezoidal();
            [res_simp, ~, ~] = obj.simpson();

            obj.Results.Midpoint = res_mid;
            obj.Results.Trapezoidal = res_trap;
            obj.Results.Simpson = res_simp;
        end

        %% 计算各方法的绝对误差
        function obj = computeErrors(obj)
            obj.Errors.Midpoint = abs(obj.Results.Midpoint - obj.ExactValue);
            obj.Errors.Trapezoidal = abs(obj.Results.Trapezoidal - obj.ExactValue);
            obj.Errors.Simpson = abs(obj.Results.Simpson - obj.ExactValue);
        end

        %% 绘制各方法结果与精确值的对比柱状图
        function plotComparison(obj)
            method_names = {'中点矩形法', '梯形法', '辛普森法'};
            values = [obj.Results.Midpoint, obj.Results.Trapezoidal, obj.Results.Simpson];

            figure;
            bar(values, 'FaceColor', [0.6 0.75 0.9]);
            set(gca, 'XTickLabel', method_names, 'FontSize', 10);
            ylabel('积分近似值');
            title('不同数值积分方法结果对比');
            hold on;
            
            yline(obj.ExactValue, 'r--', 'LineWidth', 1.5, 'DisplayName', '精确值');
            legend('数值积分结果', '精确值', 'Location', 'best');
            grid on;
            hold off;
        end

        %% 绘制函数曲线与积分近似示意图
        function plotApproximation(obj, method)
            a = obj.Interval(1);
            b = obj.Interval(2);
            f = obj.Function;

            % 生成精细曲线用于绘制原函数
            x_fine = linspace(a, b, 1000);
            y_fine = f(x_fine);

            figure;
            plot(x_fine, y_fine, 'b-', 'LineWidth', 1.5, 'DisplayName', '原函数 f(x)');
            hold on;

            switch lower(method)
                case 'midpoint'
                    [~, nodes, f_nodes] = obj.rectangularMid();
                    h = (b - a) / obj.Segments;
                    % 逐个绘制矩形
                    for i = 1:obj.Segments
                        x_left = nodes(i) - h/2;
                        x_right = nodes(i) + h/2;
                        fill([x_left, x_right, x_right, x_left], ...
                            [0, 0, f_nodes(i), f_nodes(i)], ...
                            'cyan', 'FaceAlpha', 0.3, 'EdgeColor', 'blue');
                    end
                    plot(nodes, f_nodes, 'ro', 'MarkerFaceColor', 'r', 'DisplayName', '中点节点');
                    title('中点矩形法积分近似示意');

                case 'trapezoidal'
                    [~, nodes, f_nodes] = obj.trapezoidal();
                    % 逐个绘制梯形
                    for i = 1:length(nodes)-1
                        fill([nodes(i), nodes(i+1), nodes(i+1), nodes(i)], ...
                            [0, 0, f_nodes(i+1), f_nodes(i)], ...
                            'magenta', 'FaceAlpha', 0.3, 'EdgeColor', 'red');
                    end
                    plot(nodes, f_nodes, 'ro', 'MarkerFaceColor', 'r', 'DisplayName', '等分节点');
                    title('梯形法积分近似示意');

                case 'simpson'
                    [~, nodes, f_nodes] = obj.simpson();
                    % 每两个子区间拟合一条抛物线并填充
                    for i = 1:2:length(nodes)-2
                        x_seg = nodes(i:i+2);
                        y_seg = f_nodes(i:i+2);
                        p = polyfit(x_seg, y_seg, 2);
                        x_plot = linspace(x_seg(1), x_seg(3), 100);
                        y_plot = polyval(p, x_plot);
                        fill([x_seg(1), x_plot, x_seg(3)], [0, y_plot, 0], ...
                            'green', 'FaceAlpha', 0.3, 'EdgeColor', 'green');
                    end
                    plot(nodes, f_nodes, 'ro', 'MarkerFaceColor', 'r', 'DisplayName', '等分节点');
                    title('辛普森法积分近似示意');

                otherwise
                    error('方法参数必须为 ''midpoint'' / ''trapezoidal'' / ''simpson''');
            end

            xlabel('x');
            ylabel('f(x)');
            legend('Location', 'best');
            grid on;
            hold off;
        end
    end
end