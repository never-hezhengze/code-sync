%北太天元用Monte Carlo(蒙特卡洛)方法计算 int_0^1 x^2 dx
n = 1000;
x = rand(n,1);
y = rand(n,1);    
和 = sum(double(x.^2>y));
sprintf("x^2 从0积到1的积分值是 %3.4f\n", 和/n)
ind1 = find(y <= x.^2);
sh1 = scatter(x(ind1), y(ind1), 'filled');
set(sh1, 'SizeData', 50);
hold on  
ind2 = find(y > x.^2 );
sh2 = scatter(x(ind2), y(ind2), 'filled');
set(sh2, 'SizeData', 50);
legend('y=x^2曲线下方的点', 'y=x^2曲线上方的点','FontSize',12)
title("蒙特卡罗方法计算 x^2 的积分")
hold off 
