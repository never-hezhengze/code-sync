import cv2 as cv

img = cv.imread('Photo/picture1.jpg')

# 检测是否读取成功
if img is None:
    print('错误！图片无法读取！')
    exit()

rows, cols = img.shape[:2]
center = (rows // 2, cols // 2)  # 圆心
radius = 50  # 半径

# 复制图像进行处理
output = img.copy()
# 遍历圆内的点并修改颜色
for row in range(rows):
    for col in range(cols):
        if (row - center[0]) ** 2 + (col - center[1]) ** 2 <= radius ** 2:
            output[row, col] = [0, 255, 0]  # 将圆内的点设为绿色

cv.imshow('Circle Points', output)
cv.waitKey(0)
cv.destroyAllWindows()