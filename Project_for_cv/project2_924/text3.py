import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取原始图像
image = cv2.imread('Photo/537.png')

# 获取图像尺寸
rows, cols = image.shape[:2]

# 定义变换参数
angle = 30  # 旋转角度
tx, ty = 50, 30  # 平移距离
scale = 1.2  # 缩放比例

# 计算变换后图像的新尺寸
# 获取图像四个角点的坐标
corners = np.array([
    [0, 0],
    [cols, 0],
    [cols, rows],
    [0, rows]
], dtype=np.float32)

# 构建仿射变换矩阵
rotation_matrix = cv2.getRotationMatrix2D((cols/2, rows/2), angle, scale)
rotation_matrix[0, 2] += tx
rotation_matrix[1, 2] += ty

# 变换角点坐标
transformed_corners = cv2.transform(corners.reshape(1, -1, 2), rotation_matrix).reshape(-1, 2)

# 计算新的图像尺寸
x_min, y_min = np.min(transformed_corners, axis=0)
x_max, y_max = np.max(transformed_corners, axis=0)
new_width = int(np.ceil(x_max - x_min))
new_height = int(np.ceil(y_max - y_min))

# 调整变换矩阵以确保整个图像可见
final_matrix = rotation_matrix.copy()
final_matrix[0, 2] -= x_min  # 调整 x 方向的平移
final_matrix[1, 2] -= y_min  # 调整 y 方向的平移

# 应用正向变换
transformed_image = cv2.warpAffine(image, final_matrix, (new_width, new_height))

# 计算逆变换矩阵
inverse_matrix = cv2.invertAffineTransform(final_matrix)

# 应用逆变换
restored_image = cv2.warpAffine(transformed_image, inverse_matrix, (cols, rows))

# 计算原始图像和恢复图像的差值
diff = cv2.absdiff(image, restored_image)

# 显示结果
plt.figure(figsize=(15, 5))

plt.subplot(141)
plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.title('Original Image')
plt.axis('off')

plt.subplot(142)
plt.imshow(cv2.cvtColor(transformed_image, cv2.COLOR_BGR2RGB))
plt.title('Transformed Image')
plt.axis('off')

plt.subplot(143)
plt.imshow(cv2.cvtColor(restored_image, cv2.COLOR_BGR2RGB))
plt.title('Inverse Transformed Image')
plt.axis('off')

plt.subplot(144)
plt.imshow(cv2.cvtColor(diff, cv2.COLOR_BGR2RGB))
plt.title('Difference |A - A\'|')
plt.axis('off')

plt.tight_layout()
plt.show()
