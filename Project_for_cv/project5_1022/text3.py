import cv2
import numpy as np
from matplotlib import pyplot as plt

# -------------------- (1) 读取原始图像A --------------------
imgA = cv2.imread('Photo/picture2.jpg', cv2.IMREAD_COLOR)
if imgA is None:
    print("错误：无法读取图像文件，请检查路径！")
    exit()

# 将图像转换为灰度
grayA = cv2.cvtColor(imgA, cv2.COLOR_BGR2GRAY)

# -------------------- (2) 几何变换生成A' --------------------
# 使用透射（投影）变换：通过四点对应构造单应矩阵 H
rows, cols = grayA.shape

# 定义原图像中的四个点（顺序为左上、右上、右下、左下）
pad = 30  # 用以在目标点上制造透视效果的偏移量
src_pts = np.float32([[0, 0], [cols - 1, 0], [cols - 1, rows - 1], [0, rows - 1]])

dst_pts = np.float32([
    [0 + pad, 0 + pad],
    [cols - 1 - pad * 0.2, 0 + pad * 0.5],
    [cols - 1 - pad * 0.6, rows - 1 - pad * 0.2],
    [0 + pad * 0.4, rows - 1 - pad * 0.6]
])

# 计算单应矩阵并进行透视变换
H = cv2.getPerspectiveTransform(src_pts, dst_pts)
imgA_ = cv2.warpPerspective(imgA, H, (cols, rows), flags=cv2.INTER_LINEAR)
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
