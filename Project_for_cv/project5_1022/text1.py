import cv2
import numpy as np
from matplotlib import pyplot as plt

# -------------------- (1) 读取原始图像A --------------------
imgA = cv2.imread('Photo/537.png', cv2.IMREAD_COLOR)
if imgA is None:
    print("错误：无法读取图像文件，请检查路径！")
    exit()

# 将图像转换为灰度
grayA = cv2.cvtColor(imgA, cv2.COLOR_BGR2GRAY)

# -------------------- (2) 几何变换生成A' --------------------
# 例如：仿射变换（旋转 + 平移）
rows, cols = grayA.shape
M = cv2.getRotationMatrix2D((cols / 2, rows / 2), 30, 0.8)  # 旋转30°，缩放0.8
imgA_ = cv2.warpAffine(imgA, M, (cols, rows))
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
