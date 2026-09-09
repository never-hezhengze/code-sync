clear;
x = [0.1,0.2,0.15,0,-0.2,0.3];
y = [0.95,0.84,0.86,1.06,1.50,0.72];
xi = -0.2:0.01:0.3;
yi = lagrange(x,y,xi);
plot(x,y,'or',xi,yi,'g');
title('lagrange 插值');