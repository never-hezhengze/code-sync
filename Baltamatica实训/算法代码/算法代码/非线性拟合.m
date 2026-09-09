% 原始数据
xdata = [0.9 1.5 13.8 19.8 24.1 28.2 35.2 60.3 74.6 81.3];
ydata = [455.2 428.6 124.1 67.3 43.2 28.1 13.1 -0.4 -1.3 -1.5];

% 创建简单的指数衰减模型。
fun = @(x,xdata) x(1)*exp(x(2)*xdata);
x0 = [100,-1]; %设置初始点
x = lsqcurvefit(fun,x0,xdata,ydata)

% 绘制数据和拟合曲线
times = linspace(xdata(1),xdata(end));
plot(xdata,ydata,'ko',times,fun(x,times),'b-')
legend('数据','拟合指数模型')
title('数据与拟合曲线')
