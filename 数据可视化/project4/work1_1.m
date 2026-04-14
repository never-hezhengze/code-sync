theta = 0:0.01:2*pi;
rho = sin(2*theta).*cos(2*theta);

x = rho .* cos(theta);
y = rho .* sin(theta);

subplot(1,2,1);
polarplot(theta,rho);

subplot(1,2,2);
p = plot(x,y);
p.Color = 'r';
axis equal;         
grid on;