import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# 读取原始图像
image = cv2.imread('Photo/537.png')

# 获取图像尺寸
rows, cols = image.shape[:2]


def rotate_forward_and_mark_holes(img, angle_deg=30.0, save_path='output_picture/Figure_rotated_holes.png'):
	"""
	使用前向映射将图像绕中心旋转 angle_deg 度。
	对目标坐标取整(round)，统计目标图像中没有被映射到的像素点（空洞），
	并在输出图像中用白点标注这些空洞。返回 (dest_marked, holes_count, total_pixels)
	"""
	rows, cols = img.shape[:2]
	cx, cy = (cols - 1) / 2.0, (rows - 1) / 2.0

	theta = np.deg2rad(angle_deg)
	cos_t = np.cos(theta)
	sin_t = np.sin(theta)

	# 先计算旋转后四个角的坐标以确定新的画布大小与偏移
	corners = np.array([
		[0 - cx, 0 - cy],
		[cols - 1 - cx, 0 - cy],
		[0 - cx, rows - 1 - cy],
		[cols - 1 - cx, rows - 1 - cy],
	], dtype=float)

	rot_corners = np.empty_like(corners)
	for i, (dx, dy) in enumerate(corners):
		rx = cos_t * dx - sin_t * dy
		ry = sin_t * dx + cos_t * dy
		rot_corners[i, 0] = rx + cx
		rot_corners[i, 1] = ry + cy

	min_x = rot_corners[:, 0].min()
	max_x = rot_corners[:, 0].max()
	min_y = rot_corners[:, 1].min()
	max_y = rot_corners[:, 1].max()

	new_cols = int(np.ceil(max_x - min_x + 1))
	new_rows = int(np.ceil(max_y - min_y + 1))

	# 偏移量：将原始坐标系平移到新画布中
	offset_x = -min_x
	offset_y = -min_y

	# 目标图像（初始化为黑色）和映射标记（使用更大的画布）
	if img.ndim == 2:
		dest = np.zeros((new_rows, new_cols), dtype=img.dtype)
	else:
		dest = np.zeros((new_rows, new_cols, img.shape[2]), dtype=img.dtype)
	mapped = np.zeros((new_rows, new_cols), dtype=bool)

	# 前向映射：遍历源像素 -> 计算目标位置（包含偏移） -> 取整 -> 赋值
	for y in range(rows):
		for x in range(cols):
			dx = x - cx
			dy = y - cy
			x_rot = cos_t * dx - sin_t * dy
			y_rot = sin_t * dx + cos_t * dy

			x_new = x_rot + cx + offset_x
			y_new = y_rot + cy + offset_y

			xi = int(round(x_new))
			yi = int(round(y_new))

			if 0 <= xi < new_cols and 0 <= yi < new_rows:
				dest[yi, xi] = img[y, x]
				mapped[yi, xi] = True

	total_pixels = rows * cols
	holes_count = int(np.count_nonzero(~mapped))

	# 将空洞位置设为白点以便可视化
	dest_marked = dest.copy()
	# 对于单通道或三通道都适用的赋值方式
	if dest_marked.ndim == 2:
		dest_marked[~mapped] = 255
	else:
		dest_marked[~mapped] = [255, 255, 255]

	# 确保输出目录存在
	out_dir = os.path.dirname(save_path)
	if out_dir and not os.path.exists(out_dir):
		os.makedirs(out_dir, exist_ok=True)

	cv2.imwrite(save_path, dest_marked)

	return dest_marked, holes_count, total_pixels


if __name__ == '__main__':
	import sys, os

	if image is None:
		print("无法读取图像 'Photo/537.png'，请检查路径。")
		sys.exit(1)

	# 允许从命令行传入角度（度）
	angle = 30.0
	if len(sys.argv) > 1:
		try:
			angle = float(sys.argv[1])
		except ValueError:
			print('传入的角度无效，使用默认 30 度。')

	out_img, holes, total = rotate_forward_and_mark_holes(image, angle_deg=angle)
	print(f"角度 {angle}° -> 空洞数量: {holes} / {total} ({holes/total:.2%})")

	# 显示原图与结果
	fig, axes = plt.subplots(1, 2, figsize=(12, 6))
	axes[0].set_title('Original')
	axes[0].axis('off')
	# Matplotlib expects RGB
	axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

	axes[1].set_title(f'Forward mapping rotation {angle}° (holes white)')
	axes[1].axis('off')
	axes[1].imshow(cv2.cvtColor(out_img, cv2.COLOR_BGR2RGB))

	plt.tight_layout()
	# 同步保存一份可视化大图
	vis_path = 'output_picture/Figure_rotated_holes_vis.png'
	fig.savefig(vis_path)
	print(f'已保存结果: output_picture/Figure_rotated_holes.png 和 {vis_path}')
	plt.show()
