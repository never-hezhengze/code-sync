import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt

# 读取图片
img = cv.imread('Photo/picture1.jpg')
if img is None:
    print('错误！图片无法读取！')
    exit()

# 转换为灰度图，方便展示
gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

# --- 添加椒盐噪声函数 ---
def salt_pepper_noise(image, prob=0.02):
    noisy = image.copy()
    h, w = image.shape
    # 生成随机矩阵
    rnd = np.random.rand(h, w)
    noisy[rnd < prob/2] = 0       # 椒（黑点）
    noisy[rnd > 1 - prob/2] = 255 # 盐（白点）
    return noisy

# 给灰度图添加椒盐噪声
noisy_img = salt_pepper_noise(gray, prob=0.05)

# --- 各种滤波 ---
# 均值滤波
mean_blur = cv.blur(noisy_img, (3, 3))

# 高斯滤波
gaussian_blur = cv.GaussianBlur(noisy_img, (3, 3), 0)

# 中值滤波
median_blur = cv.medianBlur(noisy_img, 3)

# 双边滤波
bilateral_blur = cv.bilateralFilter(noisy_img, 9, 75, 75)

# --- 显示对比 ---
titles = ['Original', 'Noisy Image', 'Blurred', 'GaussianBlur', 'MedianBlur', 'BilateralFilter']
images = [gray, noisy_img, mean_blur, gaussian_blur, median_blur, bilateral_blur]

plt.figure(figsize=(12, 8))
for i in range(6):
    plt.subplot(2, 3, i+1)
    plt.imshow(images[i], cmap='gray')
    plt.title(titles[i])
    plt.axis('off')
plt.tight_layout()
plt.show()
