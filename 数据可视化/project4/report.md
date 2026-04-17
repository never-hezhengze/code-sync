# 任务一（极坐标图转换成笛卡尔坐标图）
### 代码实现：
```matlab
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
```
```matlab
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
```
关键代码：
利用`x = rho .* cos(theta);
y = rho .* sin(theta);`将极坐标系里的$\rho、 \theta$转换成笛卡尔坐标系里的$x、y$

### 运行结果
<img src=picture\picture1_1.jpg with="800">
<img src=picture\picture1_2.jpg with="800">


# 任务二（笛卡尔坐标图转换成极坐标图）
### 代码实现：
```matlab
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
```
```matlab
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
```
关键代码：
利用`rho = sqrt(x.^2 + y.^2);
theta = atan2(y, x);`将笛卡尔坐标系里的$x、y$转换成极坐标系里的$\rho、 \theta$
### 运行结果：
<img src=picture\picture2_1.jpg with="800">
<img src=picture\picture2_2.jpg with="800">

# 任务三
fcontour(f) 绘制 z = f(x,y) 函数的等高线。它与fplot3绘图函数有何异同？能否根据相同的 z = f(x,y)用fplot3绘图。
### 函数分析
`fcontour(f)` 用于绘制： **二维等高线图（等值线）**

数学含义是：
\[
f(x,y) = c
\]
也就是把三维曲面\(z = f(x,y)\)“切片”，投影到 (xy) 平面上。

特点：
* 输出是 **2D 图**
* 显示的是“高度相同的曲线”
* 本质是 **隐式曲线集合**


`fplot3` 用于绘制： **三维参数曲线**

形式是：
\[
x = x(t),\quad y = y(t),\quad z = z(t)
\]

特点：

* 输出是 **3D 曲线（不是曲面）**
* 只能画“一条线”，不能画整个面

对于同一个\(z = f(x,y)\)，为了通过fplot3来绘制fcontour函数的效果，可以绘制多条fplot3空间曲线来模拟fcontour

### 代码实现：
```matlab
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
    zt = @(t) k + 0*t;   % 保证维度一致
    
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
```
### 运行结果：
<img src=picture\picture3.jpg with="800">

通过给定$z$的值，让$fplot3$绘制一个$z=k$平面上的曲线，再多次改变$k$的值达到等高线的效果