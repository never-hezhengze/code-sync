function piva = piMonteCarlo(n)
    % piMonteCarlo(n) 用随机投点法拟周率 pi 作出模拟图，n 为投点次数，
    % 可以是非负整数标量或向量。
    %
    % piva = piMonteCarlo(n) 用随机投点法模拟圆周率 pi，返回模拟值 piva。
    % 若 n 为标量（向量），则 piva 也为标量（向量）。
    
    x = 0;y = 0;d = 0;
    m = length(n);  % 求变量 n 的长度；
    pivalue = zeros(m,1);  % 为变量 pivalue 赋初值
    % 通过循环用投点法模拟圆周率 pi
    for i = 1:m
        x = 2 *rand(n(i),1) - 1;
        y = 2 *rand(n(i),1) - 1;
        d = x.^2 + y.^2;
        pivalue(i) = 4*sum(d<=1)/n(i);    % 圆周率模拟值
    end
    
    if nargout == 0
        % 不输出圆周率的模拟值，返回模拟图
        if m > 1
            % 如果 n 为向量，则返回圆周率的模拟值与投点个数的散点图
            figure;
            plot(n,pivalue,'k.')
            h = refline(0,pi);
            set(h,'linewidth',1.5,'color','k');
            text(1.05*n(end),pi,'π','fontsize',15);
            xlabel('投点个数');ylabel('π 的模拟值');
        else
            % 如果 n 为标量，则返回绘制投点法模拟圆周率的示意图
            figure;
            plot(x,y,'k.');
            hold on;
            t = linspace(0,2*pi,100);
            plot(cos(t),sin(t),'k','LineWidth',2);
            xlabel('X');ylabel('Y');
            title(['π 的模拟值：',num2str(pivalue)]);
            axis([-1.1 1.1 -1.1 1.1]);
            % axis equal;
        end
    else
            piva = pivalue;
    end
   
   
   