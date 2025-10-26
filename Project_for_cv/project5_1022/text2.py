import cv2
import numpy as np
from matplotlib import pyplot as plt

# -------------------- (1) 读取原始图像A --------------------
imgA = cv2.imread('Photo/picture1.jpg', cv2.IMREAD_COLOR)
if imgA is None:
    print("错误：无法读取图像文件，请检查路径！")
    exit()

# 将图像转换为灰度
grayA = cv2.cvtColor(imgA, cv2.COLOR_BGR2GRAY)

# -------------------- (2) 几何变换生成A' --------------------
# 仿射变换：先旋转再做水平错切（shear），同时保留缩放
rows, cols = grayA.shape
angle = 30  # 旋转角度（度）
scale = 0.8  # 缩放因子
shear = 0.3  # 水平错切系数（正值会使图像在 x 方向按 y 线性偏移）

# 1) 以图像中心为原点的旋转+缩放矩阵（3x3 齐次）
cx, cy = cols / 2.0, rows / 2.0
theta = np.deg2rad(angle)
cos_t = np.cos(theta) * scale
sin_t = np.sin(theta) * scale
R = np.array([[cos_t, -sin_t, 0.0],
              [sin_t,  cos_t, 0.0],
              [0.0,    0.0,   1.0]])

# 2) 水平错切矩阵（shear）在 y 轴方向对 x 产生偏移：
# [1  shear 0]
# [0   1    0]
# [0   0    1]
S = np.array([[1.0, shear, 0.0],
              [0.0, 1.0,   0.0],
              [0.0, 0.0,   1.0]])

# 3) 合并变换：先旋转再错切 -> T = S * R
T = S.dot(R)

# 4) 围绕图像中心进行变换，需要平移到原点并在变换后平移回来：
T_trans = np.array([[1.0, 0.0, cx],
                    [0.0, 1.0, cy],
                    [0.0, 0.0, 1.0]])
T_invtrans = np.array([[1.0, 0.0, -cx],
                       [0.0, 1.0, -cy],
                       [0.0, 0.0, 1.0]])

# 最终齐次矩阵： M_hom = T_trans * T * T_invtrans
M_hom = T_trans.dot(T).dot(T_invtrans)

# cv2.warpAffine 需要 2x3 仿射矩阵
M = M_hom[0:2, :]

imgA_ = cv2.warpAffine(imgA, M, (cols, rows), flags=cv2.INTER_LINEAR)
grayA_ = cv2.cvtColor(imgA_, cv2.COLOR_BGR2GRAY)

# -------------------- (3) 特征点检测与描述 --------------------
# 使用 ORB（Oriented FAST and Rotated BRIEF）算法
orb = cv2.ORB_create()

# 检测关键点并计算描述子
kpA, desA = orb.detectAndCompute(grayA, None)
kpA_, desA_ = orb.detectAndCompute(grayA_, None)

print(f"图像A的特征点数: {len(kpA)}")
print(f"图像A'的特征点数: {len(kpA_)}")

# -------------------- (4) 特征点匹配 --------------------
# 使用汉明距离的暴力匹配器（适合ORB）
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

# 匹配描述子
matches = bf.match(desA, desA_)

# 按距离排序（越小越相似）
matches = sorted(matches, key=lambda x: x.distance)

# -------------------- (5) 绘制匹配结果 --------------------
# 仅绘制前50个匹配点
img_match = cv2.drawMatches(imgA, kpA, imgA_, kpA_, matches[:50], None, flags=2)

# 显示结果
plt.figure(figsize=(14, 6))
plt.title("ORB matching results")
plt.imshow(cv2.cvtColor(img_match, cv2.COLOR_BGR2RGB))
plt.axis('off')
plt.show()
