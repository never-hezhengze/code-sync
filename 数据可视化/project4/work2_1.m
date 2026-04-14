x = 0:pi/100:2*pi;
y = sin(x);

% 由笛卡尔坐标系中的x,y计算出极坐标系下的rho,theta
rho = sqrt(x.^2 + y.^2);
theta = atan2(y, x);

subplot(1,2,1);
plot(x,y);
axis equal;         
grid on;

subplot(1,2,2);
p = polarplot(theta,rho);
p.Color = 'r';