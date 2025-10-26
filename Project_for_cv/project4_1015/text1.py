import cv2
import numpy as np
import os


def main():
	# 尝试读取原始图像（优先使用相对路径 Photo/picture1.jpg）
	img_path = 'Photo/picture1.jpg'
	image = cv2.imread(img_path)
	# 如果直接读取失败，尝试基于脚本目录的备选路径
	if image is None:
		script_dir = os.path.dirname(__file__)
		alt_path = os.path.normpath(os.path.join(script_dir, '..', 'Photo', 'picture1.jpg'))
		image = cv2.imread(alt_path)
		if image is None:
			print(f"无法读取图像，尝试的路径: {img_path} 和 {alt_path}")
			return

	# 获取图像尺寸
	rows, cols = image.shape[:2]

	# 转为灰度用于边缘检测
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

	# 改进的处理管线：去噪 -> Roberts 梯度 -> 二值化 -> 细化骨架化
	# 1) 提升局部对比度（CLAHE）并去噪（双边滤波保边缘）
	clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
	gray_clahe = clahe.apply(gray)
	denoised = cv2.bilateralFilter(gray_clahe, d=9, sigmaColor=75, sigmaSpace=75)

	# 2) Roberts 交叉算子 — 在每个颜色通道上计算并取最大值以保留颜色边缘
	kx = np.array([[1, 0], [0, -1]], dtype=np.float32)
	ky = np.array([[0, 1], [-1, 0]], dtype=np.float32)
	channel_grads = []
	for c in range(3):
		ch = image[:, :, c]
		# 在单通道上做去噪以保留通道边缘
		ch_denoised = cv2.bilateralFilter(ch, d=9, sigmaColor=75, sigmaSpace=75)
		gx = cv2.filter2D(ch_denoised.astype(np.float32), -1, kx)
		gy = cv2.filter2D(ch_denoised.astype(np.float32), -1, ky)
		grad_c = np.sqrt(gx * gx + gy * gy)
		channel_grads.append(grad_c)

	# 堆叠并取最大值（保留任一通道的强边缘）
	grad = np.max(np.stack(channel_grads, axis=-1), axis=-1)

	# 归一化
	if grad.max() > 0:
		grad_n = np.clip((grad / grad.max()) * 255, 0, 255).astype(np.uint8)
	else:
		grad_n = np.zeros_like(gray, dtype=np.uint8)

	# 3) 使用 Otsu 得到初步二值图
	_, mask_rob = cv2.threshold(grad_n, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

	# 4) 使用 Canny 作为补充（基于 CLAHE+去噪 的灰度图自适应阈值），融合可抑制噪声并增强连续性
	# Canny 阈值基于中值法
	median_val = np.median(denoised)
	sigma = 0.33
	lower = int(max(0, (1.0 - sigma) * median_val))
	upper = int(min(255, (1.0 + sigma) * median_val))
	mask_canny = cv2.Canny(denoised, lower, upper)

	# 合并 Roberts 和 Canny 结果
	mask_combined = cv2.bitwise_or(mask_rob, mask_canny)

	# 5) 去噪和细化：先做开运算移除小噪点
	kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
	mask_clean = cv2.morphologyEx(mask_combined, cv2.MORPH_OPEN, kernel, iterations=1)

	def skeletonize(bin_img: np.ndarray) -> np.ndarray:
		# Zhang-Suen style skeleton via morphological operations
		img = bin_img.copy()
		img[img != 0] = 255
		skel = np.zeros(img.shape, np.uint8)
		element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
		while True:
			eroded = cv2.erode(img, element)
			dilated = cv2.dilate(eroded, element)
			temp = cv2.subtract(img, dilated)
			skel = cv2.bitwise_or(skel, temp)
			img = eroded.copy()
			if cv2.countNonZero(img) == 0:
				break
		return skel

	# 优先使用 opencv_contrib 的 ximgproc.thinning (如果可用)，否则使用本地 skeletonize 函数
	try:
		from cv2 import ximgproc as xip
		mask_skel = xip.thinning(mask_clean)
	except Exception:
		mask_skel = skeletonize(mask_clean)

	# 6) 最终边缘掩码：可以再次做小范围膨胀以保证可见性
	mask_final = cv2.dilate(mask_skel, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1)), iterations=1)

	# 将边缘以红色叠合回原图，但做 alpha 混合以保留原始细节
	alpha = 0.75  # 红色强度（0-1，越大红色越明显）
	red_img = np.zeros_like(image)
	red_img[:, :] = (0, 0, 255)
	blended = cv2.addWeighted(image, 1.0 - alpha, red_img, alpha, 0)
	overlay = image.copy()
	overlay[mask_final == 255] = blended[mask_final == 255]


	# 保存结果到同目录下的 output_picture，并保存中间调试图像以便进一步调参
	script_dir = os.path.dirname(__file__)
	out_dir = os.path.join(script_dir, 'output_picture')
	os.makedirs(out_dir, exist_ok=True)
	out_path = os.path.join(out_dir, 'edges_overlay.jpg')
	cv2.imwrite(out_path, overlay)

	# 保存调试图像：梯度图、合并掩码与最终掩码
	debug_grad_path = os.path.join(out_dir, 'debug_grad.jpg')
	debug_mask_path = os.path.join(out_dir, 'debug_mask.jpg')
	debug_mask_final = os.path.join(out_dir, 'debug_mask_final.jpg')
	cv2.imwrite(debug_grad_path, grad_n)
	cv2.imwrite(debug_mask_path, mask_combined)
	cv2.imwrite(debug_mask_final, mask_final)

	print(f"边缘叠合图已保存: {out_path}")


if __name__ == '__main__':
	main()

