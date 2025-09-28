import cv2
import numpy as np
import matplotlib.pyplot as plt

def arnold_transform(img, num_iterations):
    rows, cols = img.shape[:2]
    transformed = np.zeros_like(img)
    
    # 确保图像是正方形
    n = min(rows, cols)
    for k in range(num_iterations):
        for y in range(n):
            for x in range(n):
                # Arnold变换公式
                xx = (x + y) % n
                yy = (x + 2*y) % n
                transformed[yy, xx] = img[y, x]
        img = transformed.copy()
    return transformed

def arnold_inverse_transform(img, num_iterations):
    rows, cols = img.shape[:2]
    transformed = np.zeros_like(img)
    
    # 确保图像是正方形
    n = min(rows, cols)
    for k in range(num_iterations):
        for y in range(n):
            for x in range(n):
                # Arnold反变换公式
                xx = (2*x - y) % n
                yy = (-x + y) % n
                transformed[yy, xx] = img[y, x]
        img = transformed.copy()
    return transformed

# 读取原始图像
image = cv2.imread('Photo/537.png')
if image is None:
    raise ValueError("无法读取图像")

# 获取图像尺寸并确保为正方形
rows, cols = image.shape[:2]
size = min(rows, cols)
image = image[:size, :size]

# 进行Arnold变换（加密）
iterations = 1  # 迭代次数
encrypted = arnold_transform(image, iterations)

# 进行Arnold反变换（解密）
decrypted = arnold_inverse_transform(encrypted, iterations)

# 计算原图与恢复图的差值
difference = cv2.absdiff(image, decrypted)

# 显示结果
plt.figure(figsize=(15, 5))

plt.subplot(141)
plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.title('original image A')
plt.axis('off')

plt.subplot(142)
plt.imshow(cv2.cvtColor(encrypted, cv2.COLOR_BGR2RGB))
plt.title('Arnold A-->B')
plt.axis('off')

plt.subplot(143)
plt.imshow(cv2.cvtColor(decrypted, cv2.COLOR_BGR2RGB))
plt.title('Arnold B-->A\'')
plt.axis('off')

plt.subplot(144)
plt.imshow(cv2.cvtColor(difference, cv2.COLOR_BGR2RGB))
plt.title('difference |A-A\'|')
plt.axis('off')

plt.tight_layout()
plt.show()