import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取原始图像
image = cv2.imread('Photo/537.png')

# 获取图像尺寸
rows, cols = image.shape[:2]

# 定义仿射变换参数
angle = 30  # 旋转角度
scale_x = 1.2  # x方向缩放
scale_y = 0.8  # y方向缩放
tx, ty = 50, 30  # 平移量

# 计算仿射变换矩阵
center = (cols/2, rows/2)
# 结合旋转和缩放
M = cv2.getRotationMatrix2D(center, angle, 1.0)
M[0,0] *= scale_x  # x方向缩放
M[1,1] *= scale_y  # y方向缩放
# 添加平移
M[0,2] += tx
M[1,2] += ty

# 计算变换后的图像大小
cos_angle = np.abs(M[0,0])
sin_angle = np.abs(M[0,1])
new_width = int(np.ceil((rows * sin_angle + cols * cos_angle)))
new_height = int(np.ceil((rows * cos_angle + cols * sin_angle)))

# 应用仿射变换
transformed_image = cv2.warpAffine(image, M, (new_width, new_height))

# 计算逆变换矩阵
M_inv = cv2.invertAffineTransform(M)

# 应用逆变换
inverse_transformed = cv2.warpAffine(transformed_image, M_inv, (cols, rows))

# 计算差值图像
difference = cv2.absdiff(image, inverse_transformed)

# 显示结果
plt.figure(figsize=(15, 5))

plt.subplot(141)
plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.title('original (A)')
plt.axis('off')

plt.subplot(142)
plt.imshow(cv2.cvtColor(transformed_image, cv2.COLOR_BGR2RGB))
plt.title('transformed image')
plt.axis('off')

plt.subplot(143)
plt.imshow(cv2.cvtColor(inverse_transformed, cv2.COLOR_BGR2RGB))
plt.title('inverse transformed')
plt.axis('off')

plt.subplot(144)
plt.imshow(cv2.cvtColor(difference, cv2.COLOR_BGR2RGB))
plt.title('difference |A - A\'|')
plt.axis('off')

plt.tight_layout()
plt.show()