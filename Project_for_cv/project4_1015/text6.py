import cv2
import numpy as np
import os


def main():
	# 读取图像（若为彩色则转换为灰度）
	img_path = 'Photo/picture2.jpg'
	img = cv2.imread(img_path)
	if img is None:
		script_dir = os.path.dirname(__file__)
		alt = os.path.normpath(os.path.join(script_dir, '..', 'Photo', 'picture2.jpg'))
		img = cv2.imread(alt)
		if img is None:
			print(f"无法读取图像，尝试路径: {img_path} 和 {alt}")
			return

	if img.ndim == 3:
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	else:
		gray = img.copy()

	# Laplacian 检测
	lap = cv2.Laplacian(gray, ddepth=cv2.CV_32F, ksize=3)
	lap_abs = np.abs(lap)

	# 归一化用于可视化
	if lap_abs.max() > 0:
		lap_viz = np.clip((lap_abs / lap_abs.max()) * 255, 0, 255).astype(np.uint8)
	else:
		lap_viz = np.zeros_like(gray, dtype=np.uint8)

	# 二值化（Otsu）得到边缘图
	_, edge_bw = cv2.threshold(lap_viz, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

	# 保存单独图像
	out_dir = os.path.join(os.path.dirname(__file__), 'output_picture')
	os.makedirs(out_dir, exist_ok=True)
	cv2.imwrite(os.path.join(out_dir, 'text6_gray.jpg'), gray)
	cv2.imwrite(os.path.join(out_dir, 'text6_laplacian_viz.jpg'), lap_viz)
	cv2.imwrite(os.path.join(out_dir, 'text6_laplacian_edge.jpg'), edge_bw)

	# 合并三张图并添加标签
	h, w = gray.shape[:2]
	gap = 10
	spacer = 255 * np.ones((h, gap, 3), dtype=np.uint8)

	gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
	lap_bgr = cv2.cvtColor(lap_viz, cv2.COLOR_GRAY2BGR)
	edge_bgr = cv2.cvtColor(edge_bw, cv2.COLOR_GRAY2BGR)

	combined = np.hstack([gray_bgr, spacer, lap_bgr, spacer, edge_bgr])

	font = cv2.FONT_HERSHEY_SIMPLEX
	font_scale = max(0.5, w / 800)
	thickness = 1
	cv2.putText(combined, 'Original', (10, 25), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)
	cv2.putText(combined, 'Laplacian magnitude', (w + gap + 10, 25), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)
	cv2.putText(combined, 'Edges (binary)', (2 * (w + gap) + 10, 25), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)

	combined_path = os.path.join(out_dir, 'text6_combined.jpg')
	cv2.imwrite(combined_path, combined)

	print(f"已保存: {out_dir}/text6_gray.jpg, text6_laplacian_viz.jpg, text6_laplacian_edge.jpg")
	print(f"合并图已保存: {combined_path}")
if __name__ == '__main__':
	main()


