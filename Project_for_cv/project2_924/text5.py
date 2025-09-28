import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取原始图像
image = cv2.imread('Photo/537.png')

# 获取图像尺寸
rows, cols = image.shape[:2]

# 定义四个角点坐标（原图）
pts1 = np.float32([[50, 50], [cols-50, 50], [50, rows-50], [cols-50, rows-50]])
# 定义变换后的四个角点坐标
pts2 = np.float32([[100, 150], [cols-150, 100], [80, rows-80], [cols-80, rows-100]])

# 计算投影变换矩阵
matrix = cv2.getPerspectiveTransform(pts1, pts2)
# 计算逆变换矩阵
matrix_inv = np.linalg.inv(matrix)

# 计算变换后和逆变换可能需要的最大尺寸
pts_test = np.float32([[0,0], [cols-1,0], [0,rows-1], [cols-1,rows-1]])
# 计算正向变换的边界
dst_pts = cv2.perspectiveTransform(pts_test.reshape(1,4,2), matrix).reshape(4,2)
min_x, min_y = np.int32(np.min(dst_pts, axis=0))
max_x, max_y = np.int32(np.max(dst_pts, axis=0))

# 计算更大的输出尺寸，确保包含所有可能的变换结果
max_dim = max(max_x - min_x, max_y - min_y, cols, rows)
output_size = (max_dim, max_dim)

# 计算中心对齐的偏移量
offset_x = (max_dim - (max_x - min_x)) // 2
offset_y = (max_dim - (max_y - min_y)) // 2

# 调整正向变换矩阵，包含中心对齐
transform_matrix = np.copy(matrix)
transform_matrix[0:2,2] += [-min_x + offset_x, -min_y + offset_y]

# 调整逆变换矩阵
inverse_transform_matrix = np.linalg.inv(transform_matrix)

# 进行正向投影变换
warped = cv2.warpPerspective(image, transform_matrix, output_size)

# 计算逆变换的输出尺寸（与原图相同）
unwarped = cv2.warpPerspective(warped, inverse_transform_matrix, (cols, rows))

# 计算差异（确保对齐后再相减）
diff = cv2.absdiff(image, unwarped)

# 创建足够大的画布显示结果
plt.figure(figsize=(20, 5))

# 显示原始图像
plt.subplot(141)
plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.title('original image')
plt.axis('off')

# 显示投影变换后的图像
plt.subplot(142)
plt.imshow(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
plt.title('warped image')
plt.axis('off')

# 显示逆变换后的图像
plt.subplot(143)
plt.imshow(cv2.cvtColor(unwarped, cv2.COLOR_BGR2RGB))
plt.title('unwarped image')
plt.axis('off')

# 显示差异
plt.subplot(144)
plt.imshow(cv2.cvtColor(diff, cv2.COLOR_BGR2RGB))
plt.title('difference image')
plt.axis('off')

plt.tight_layout()
plt.show()
