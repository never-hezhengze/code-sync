import cv2
import numpy as np
import matplotlib.pyplot as plt

# ========== 1. 读取图像 ==========
img = cv2.imread('/Users/hezhengze/Code/数据可视化/project2/scatter.png')

if img is None:
    raise ValueError("图片读取失败，请检查路径！")

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# ========== 2. 边缘检测 ==========
edges = cv2.Canny(gray, 50, 150)

# ========== 3. 霍夫直线检测坐标轴 ==========
lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                        threshold=100,
                        minLineLength=200,
                        maxLineGap=10)

h, w = gray.shape
x_lines = []
y_lines = []

if lines is not None:
    for line in lines:
        x1, y1, x2, y2 = line[0]
        
        # 水平线（x轴）
        if abs(y1 - y2) < 5:
            y_lines.append((y1 + y2) // 2)
        
        # 垂直线（y轴）
        if abs(x1 - x2) < 5:
            x_lines.append((x1 + x2) // 2)

# ========== 4. 确定绘图区 ROI ==========
if len(x_lines) == 0 or len(y_lines) == 0:
    raise ValueError("未检测到坐标轴，请检查图像质量！")

# 🔥 不再裁剪边界（保留坐标轴上的点）
x_left = min(x_lines)
x_right = max(x_lines)
y_top = min(y_lines)
y_bottom = max(y_lines)

roi = gray[y_top:y_bottom, x_left:x_right]

# ========== 5. 二值化 ==========
_, binary = cv2.threshold(
    roi, 0, 255,
    cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
)

# ========== 6. 去噪 ==========
kernel = np.ones((3, 3), np.uint8)
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

# ========== 7. 连通域检测 ==========
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)

points = []

for i in range(1, num_labels):  # 跳过背景
    area = stats[i, cv2.CC_STAT_AREA]
    w_box = stats[i, cv2.CC_STAT_WIDTH]
    h_box = stats[i, cv2.CC_STAT_HEIGHT]
    
    ratio = w_box / h_box if h_box != 0 else 0

    # 🔥 改进筛选（去掉轴线，保留点）
    if 30 < area < 300 and 0.5 < ratio < 2:
        
        # ❗ 去掉“长条结构”（坐标轴）
        if w_box > 50 or h_box > 50:
            continue

        cx, cy = centroids[i]
        
        # 转换回原图坐标
        cx += x_left
        cy += y_top
        
        points.append((cx, cy))

# ========== 8. 可视化检测结果 ==========
img_show = img.copy()

for (x, y) in points:
    cv2.circle(img_show, (int(x), int(y)), 6, (0, 0, 255), -1)

plt.figure(figsize=(6,6))
plt.imshow(cv2.cvtColor(img_show, cv2.COLOR_BGR2RGB))
plt.title(f"Detected {len(points)} points")
plt.axis('off')
plt.show()

# ========== 9. 像素坐标 → 数据坐标 ==========
# ⚠️ 根据你的 MATLAB 设置修改
x_min, x_max = 0, 10
y_min, y_max = 0, 10

data_points = []

for (px, py) in points:
    x = x_min + (px - x_left) / (x_right - x_left) * (x_max - x_min)
    y = y_max - (py - y_top) / (y_bottom - y_top) * (y_max - y_min)
    
    data_points.append((x, y))

# 排序（方便查看）
data_points = sorted(data_points, key=lambda p: (p[0], p[1]))

# ========== 10. 输出结果 ==========
print("\n恢复的数据点：")
for p in data_points:
    print(f"({p[0]:.3f}, {p[1]:.3f})")