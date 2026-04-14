theta = linspace(0,2*pi,25);
rho = 2*theta;

x = rho .* cos(theta);
y = rho .* sin(theta);

subplot(1,2,1);
polarplot(theta,rho);

subplot(1,2,2);
p = plot(x,y);
p.Color = 'r';
axis equal;         
grid on;