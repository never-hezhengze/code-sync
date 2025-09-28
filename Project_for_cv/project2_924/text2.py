import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取原始图像
image = cv2.imread('Photo/537.png')

# 获取图像尺寸
rows, cols = image.shape[:2]

# 定义平移参数、旋转角度
tx, ty = 50, 25  # 在x方向平移50像素，y方向平移25像素
angle = 30  # 旋转角度

# 计算新画布尺寸（考虑旋转和平移）
angle_rad = np.abs(angle * np.pi / 180.0)
width_rot = int(np.ceil(rows * np.abs(np.sin(angle_rad)) + cols * np.abs(np.cos(angle_rad))))
height_rot = int(np.ceil(rows * np.abs(np.cos(angle_rad)) + cols * np.abs(np.sin(angle_rad))))

# 确保新尺寸能容纳平移后的图像
new_width = width_rot + abs(tx) * 2  # 在两边都留出平移空间
new_height = height_rot + abs(ty) * 2

# 计算新的中心点
center_x = new_width // 2
center_y = new_height // 2

# 首先将图像放置在新画布中心
M_center = np.float32([
    [1, 0, center_x - cols//2],
    [0, 1, center_y - rows//2]
])
centered = cv2.warpAffine(image, M_center, (new_width, new_height))

# 创建旋转矩阵（围绕新画布的中心点）
M_rotation = cv2.getRotationMatrix2D((center_x, center_y), angle, 1.0)
rotated = cv2.warpAffine(centered, M_rotation, (new_width, new_height))

# 创建平移矩阵
M_translation = np.float32([
    [1, 0, tx],
    [0, 1, ty]
])

# 进行平移变换
transformed = cv2.warpAffine(rotated, M_translation, (new_width, new_height))

# 计算逆变换矩阵
# 先逆平移
M_translation_inv = np.float32([
    [1, 0, -tx],
    [0, 1, -ty]
])
inverse_translated = cv2.warpAffine(transformed, M_translation_inv, (new_width, new_height))

# 再逆旋转
M_rotation_inv = cv2.getRotationMatrix2D((center_x, center_y), -angle, 1.0)
inverse_rotated = cv2.warpAffine(inverse_translated, M_rotation_inv, (new_width, new_height))

# 提取与原图相同大小的区域（从中心位置）
y_start = center_y - rows//2
y_end = y_start + rows
x_start = center_x - cols//2
x_end = x_start + cols
inverse_transformed_cropped = inverse_rotated[y_start:y_end, x_start:x_end]

# 计算原图与逆变换图像的差值
diff = cv2.absdiff(image, inverse_transformed_cropped)

# 转换BGR到RGB（因为OpenCV使用BGR，而Matplotlib使用RGB）
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
transformed_rgb = cv2.cvtColor(transformed, cv2.COLOR_BGR2RGB)
inverse_transformed_rgb = cv2.cvtColor(inverse_transformed_cropped, cv2.COLOR_BGR2RGB)
diff_rgb = cv2.cvtColor(diff, cv2.COLOR_BGR2RGB)

# 创建matplotlib图表
plt.figure(figsize=(12, 8))

# 添加子图
plt.subplot(221)
plt.imshow(image_rgb)
plt.title('Original Image')
plt.axis('off')

plt.subplot(222)
plt.imshow(transformed_rgb)
plt.title('Transformed Image')
plt.axis('off')

plt.subplot(223)
plt.imshow(inverse_transformed_rgb)
plt.title('Inverse Transformed Image')
plt.axis('off')

plt.subplot(224)
plt.imshow(diff_rgb)
plt.title('Difference')
plt.axis('off')

# 调整子图之间的间距
plt.tight_layout()

# 显示图像
plt.show()