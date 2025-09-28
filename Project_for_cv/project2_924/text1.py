import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取原始图像
image = cv2.imread('Photo/537.png')

# 获取图像尺寸
rows, cols = image.shape[:2]

# 定义平移参数
tx, ty = 100, 50  # 在x方向平移100像素，y方向平移50像素

# 计算扩展后的画布大小，确保能容纳平移后的图像
new_cols = cols + abs(tx) * 2
new_rows = rows + abs(ty) * 2

# 在扩展画布的中心放置原始图像
center_x = (new_cols - cols) // 2
center_y = (new_rows - rows) // 2

# 创建扩展的画布
expanded_image = np.zeros((new_rows, new_cols, 3), dtype=np.uint8)
expanded_image[center_y:center_y+rows, center_x:center_x+cols] = image

# 创建平移矩阵，考虑中心偏移
M = np.float32([[1, 0, tx],
                [0, 1, ty]])

# 进行平移变换
translated = cv2.warpAffine(expanded_image, M, (new_cols, new_rows))

# 创建逆变换矩阵
M_inverse = np.float32([[1, 0, -tx],
                        [0, 1, -ty]])

# 进行逆变换得到A'
restored_full = cv2.warpAffine(translated, M_inverse, (new_cols, new_rows))

# 从扩展画布中提取中心区域（与原始图像大小相同）
restored = restored_full[center_y:center_y+rows, center_x:center_x+cols]

# 计算A与A'的差值图像
difference = cv2.absdiff(image, restored)

# 保存结果
cv2.imwrite('output/A_prime.png', restored)
cv2.imwrite('output/diff_rgb.png', difference)

# 显示结果
plt.figure(figsize=(15, 5))

# 显示原始图像A
plt.subplot(131)
plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.title('original A')
plt.axis('off')

# 显示还原图像A'
plt.subplot(132)
plt.imshow(cv2.cvtColor(restored, cv2.COLOR_BGR2RGB))
plt.title('restored A\'')
plt.axis('off')

# 显示差值图像（彩色）
plt.subplot(133)
plt.imshow(cv2.cvtColor(difference, cv2.COLOR_BGR2RGB))
plt.title('difference')
plt.axis('off')

plt.tight_layout()
plt.show()