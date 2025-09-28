import cv2 as cv

gray_img = cv.imread('Photo/picture2.jpg', cv.IMREAD_GRAYSCALE)

# 检测是否读取成功
if gray_img is None:
    print('错误！图片无法读取！')
    exit()

rows, cols = gray_img.shape[:2]
center = (rows // 2, cols // 2)  # 圆心
radius = 50  # 半径

alpha = 0.5  # 透明度

# 将灰度图像转换为BGR彩色图像
color_img = cv.cvtColor(gray_img, cv.COLOR_GRAY2BGR)
output = color_img.copy()

# 保存原始彩色图像（用于相减）
original_color = color_img.copy()

# 遍历圆内的点并修改颜色
for row in range(rows):
    for col in range(cols):
        if (row - center[0]) ** 2 + (col - center[1]) ** 2 <= radius ** 2:
            # 获取原始BGR值
            original_b, original_g, original_r = output[row, col]
            
            # 混合绿色：B=0, G=255, R=0
            blended_b = int(original_b * (1 - alpha) + 0 * alpha)
            blended_g = int(original_g * (1 - alpha) + 255 * alpha)
            blended_r = int(original_r * (1 - alpha) + 0 * alpha)
            
            output[row, col] = [blended_b, blended_g, blended_r]
            
# 使用绝对值差计算差异
abs_difference = cv.absdiff(output, original_color)

cv.imshow('1. Original Image', original_color)
cv.imshow('2. With Semi-transparent Circle', output)
cv.imshow('3. Absolute Difference', abs_difference)

cv.waitKey(0)
cv.destroyAllWindows()