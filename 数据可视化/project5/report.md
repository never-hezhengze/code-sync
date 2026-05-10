# 一、三维与空间结构类（描述“形状/体量”）
## 1. 曲面图（Surface Plot）
**用途：** 展示多元函数 \( z = f(x, y) \) 的连续变化

**常见领域：**
- 数学（多元函数分析）
- 工程优化（目标函数）
- 机器学习（损失函数）
- 物理（势能面、温度场）

**典型场景：** 最优解搜索与函数形态分析

## 2. 体积图（Volume Plot）
**用途：** 展示三维空间中的整体分布

**常见领域：**
- 医学影像（CT、MRI）
- 流体力学（密度、压力）
- 地球物理（地下结构）

**典型场景：** 观察三维内部结构
## 3. 多边形图（Polygon Plot / Mesh）
**用途：** 表示复杂几何结构或离散空间

**常见领域：**
- 有限元分析（FEA）
- 计算机图形学
- 工程建模

**典型场景：** 空间离散化（网格划分）

# 二、地理与空间分布类
## 4. 地理图（Geographic Map）
**用途：** 将数据与地理位置结合

**常见领域：**
- 地理信息系统（GIS）
- 城市规划
- 区域经济分析

**典型场景：** 空间分布分析（哪里多、哪里少）
## 5. 等高线图（Contour Plot）
**用途：** 用等值线表示相同数值

**常见领域：**
- 地形测绘（等高线）
- 气象（气压、温度）
- 工程（应力分布）

**典型场景：** 二维平面展示三维趋势
# 三、向量场与流动类

## 6. 箭头图（Quiver Plot）
**用途：** 表示向量的方向和大小

**常见领域：**
- 物理（力场、电场）
- 优化（梯度方向）
- 流体力学

**典型场景：** 描述每个点的变化方向

## 7. 流线图（Streamline）
**用途：** 表示连续流动路径

**常见领域：**
- 流体力学
- 空气动力学
- 气象与海洋

**典型场景：** 描述流体运动轨迹

## 8. 羽毛图（Feather Plot）
**用途：** 表示随时间变化的向量

**常见领域：**
- 气象（风速风向）
- 海洋（洋流）
- 时间序列分析

**典型场景：** 动态方向变化

## 9. 罗盘图（Compass Plot）
**用途：** 极坐标下的向量表示

**常见领域：**
- 信号处理（相位）
- 导航系统
- 方向统计

**典型场景：** 方向分布分析

---
# 四、图片复现
## 二维高斯联合概率密度
### 代码
```matlab
% 清理工作区
clear; clc; close all;

% 参数设置
mu = [0, 0];          % 均值向量
sigma = [1, 0.3;      % 协方差矩阵
         0.3, 1];     % 相关系数0.3

% 生成网格数据
x = -3:0.1:3;
y = -3:0.1:3;
[X, Y] = meshgrid(x, y);

% 计算二维高斯联合概率密度
% 公式: p(x,y) = 1/(2π|Σ|^(1/2)) * exp(-1/2 * [x-μ]' * Σ^(-1) * [x-μ])
X_vec = X(:) - mu(1);
Y_vec = Y(:) - mu(2);
Sigma_det = det(sigma);
Sigma_inv = inv(sigma);

% 计算指数部分
for i = 1:length(X_vec)
    Z_vec = [X_vec(i); Y_vec(i)];
    exponent = -0.5 * Z_vec' * Sigma_inv * Z_vec;
    Z(i) = 1/(2*pi*sqrt(Sigma_det)) * exp(exponent);
end

Z = reshape(Z, size(X));

% 绘制曲面图
figure('Position', [100, 100, 800, 600]);
surf(X, Y, Z, 'EdgeColor', 'none', 'FaceAlpha', 0.8);

% 美化图形
colormap('jet');      % 设置颜色映射
colorbar;             % 显示颜色条
xlabel('X', 'FontSize', 12);
ylabel('Y', 'FontSize', 12);
zlabel('Probability Density', 'FontSize', 12);
title('二维高斯联合概率密度函数', 'FontSize', 14);

% 设置视角
view(45, 30);
grid on;

% 可选：添加光照效果
light('Position', [1, 1, 1]);
lighting gouraud;
```
<img src=gauss.jpg with="800">

原图：
<img src=picture1.png with="800">

## 条形磁铁磁场图
### 代码
```matlab
clear; clc; close all;

% 定义网格
x = linspace(-3, 3, 80);
y = linspace(-2, 2, 60);
[X, Y] = meshgrid(x, y);

% 磁铁参数
N = [1, 0];
S = [-1, 0];

% 计算磁场
rN = sqrt((X - N(1)).^2 + (Y - N(2)).^2);
rS = sqrt((X - S(1)).^2 + (Y - S(2)).^2);

rN(rN < 0.2) = 0.2;
rS(rS < 0.2) = 0.2;

Bx = (X - N(1))./rN.^3 - (X - S(1))./rS.^3;
By = (Y - N(2))./rN.^3 - (Y - S(2))./rS.^3;

figure;
hold on;

% 绘制带箭头的流线
h = streamslice(X, Y, Bx, By);
set(h, 'Color', 'b', 'LineWidth', 1.2);

% 绘制条形磁铁
rectangle('Position', [-1, -0.4, 2, 0.8], ...
          'FaceColor', 'r', 'EdgeColor', 'k', 'LineWidth', 2);

% 标注
text(1, 0, 'N', 'FontSize', 14, 'FontWeight', 'bold', ...
    'Color', 'w', 'HorizontalAlignment', 'center');
text(-1, 0, 'S', 'FontSize', 14, 'FontWeight', 'bold', ...
    'Color', 'w', 'HorizontalAlignment', 'center');

% 图形设置
axis equal;
xlim([-3, 3]);
ylim([-2, 2]);
xlabel('x');
ylabel('y');
title('条形磁铁磁场流线（streamslice）');
grid on;
box on;

hold off;
```
<img src=stream_line.jpg with="800">

原图：

<img src=picture2.png with="800">