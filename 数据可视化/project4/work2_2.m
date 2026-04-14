r = 2;
xc = 4;
yc = 3;

theta1 = linspace(0,2*pi);
x = r*cos(theta1) + xc;
y = r*sin(theta1) + yc;

% 由笛卡尔坐标系中的x,y计算出极坐标系下的rho,theta
rho = sqrt(x.^2 + y.^2);
theta = atan2(y, x);

% 第一张图（笛卡尔坐标系）
subplot(1,2,1);
plot(x,y)
axis equal
grid on

%第二张图（极坐标系）
subplot(1,2,2);
p = polarplot(theta,rho);
p.Color = 'r';