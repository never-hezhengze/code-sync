f = @(x,y) sin(x) + cos(y);

subplot(1,2,1);
fcontour(f);
title('2D 等高线');

subplot(1,2,2);
hold on;

k_levels = -2:0.5:2;

for k = k_levels
    % 正分支
    xt = @(t) t;
    yt1 = @(t) acos(k - sin(t));
    zt = @(t) k * ones(size(t));
    
    % 负分支
    yt2 = @(t) -acos(k - sin(t));
    
    % 画两条曲线
    fplot3(xt, yt1, zt, [-pi pi]);
    fplot3(xt, yt2, zt, [-pi pi]);
end

grid on;
%view(3);
xlabel('x'); ylabel('y'); zlabel('z');
title('3D 等高线（fplot3）');

hold off;