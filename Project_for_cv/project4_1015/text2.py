import cv2
import numpy as np
import os


def main():
    # 读取图像
    img_path = 'Photo/picture1.jpg'
    image = cv2.imread(img_path)
    if image is None:
        script_dir = os.path.dirname(__file__)
        alt_path = os.path.normpath(os.path.join(script_dir, '..', 'Photo', 'picture1.jpg'))
        image = cv2.imread(alt_path)
        if image is None:
            print(f"无法读取图像，尝试的路径: {img_path} 和 {alt_path}")
            return

    # 灰度并增强对比
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray)

    # 去噪
    denoised = cv2.bilateralFilter(gray_clahe, d=9, sigmaColor=75, sigmaSpace=75)

    # Prewitt 算子核心（水平和垂直）
    px = np.array([[ -1, 0, 1], [ -1, 0, 1], [ -1, 0, 1]], dtype=np.float32)
    py = np.array([[ 1, 1, 1], [ 0, 0, 0], [ -1, -1, -1]], dtype=np.float32)

    # 在每个颜色通道上计算梯度并取最大
    channel_grads = []
    for c in range(3):
        ch = image[:, :, c]
        ch_d = cv2.bilateralFilter(ch, d=9, sigmaColor=75, sigmaSpace=75)
        gx = cv2.filter2D(ch_d.astype(np.float32), -1, px)
        gy = cv2.filter2D(ch_d.astype(np.float32), -1, py)
        grad_c = np.sqrt(gx * gx + gy * gy)
        channel_grads.append(grad_c)

    grad = np.max(np.stack(channel_grads, axis=-1), axis=-1)

    # 归一化
    if grad.max() > 0:
        grad_n = np.clip((grad / grad.max()) * 255, 0, 255).astype(np.uint8)
    else:
        grad_n = np.zeros_like(gray, dtype=np.uint8)

    # 二值化（Otsu）
    _, mask_prew = cv2.threshold(grad_n, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 可选：用 Canny 加强连续性
    median_val = np.median(denoised)
    sigma = 0.33
    lower = int(max(0, (1.0 - sigma) * median_val))
    upper = int(min(255, (1.0 + sigma) * median_val))
    mask_canny = cv2.Canny(denoised, lower, upper)

    mask_combined = cv2.bitwise_or(mask_prew, mask_canny)

    # 开运算去噪
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_clean = cv2.morphologyEx(mask_combined, cv2.MORPH_OPEN, kernel, iterations=1)

    # 骨架化（简单形态学）
    def skeletonize(bin_img: np.ndarray) -> np.ndarray:
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

    try:
        from cv2 import ximgproc as xip
        mask_skel = xip.thinning(mask_clean)
    except Exception:
        mask_skel = skeletonize(mask_clean)

    mask_final = cv2.dilate(mask_skel, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1)), iterations=1)

    # alpha 混合红色叠合
    alpha = 0.75
    red_img = np.zeros_like(image)
    red_img[:, :] = (0, 0, 255)
    blended = cv2.addWeighted(image, 1.0 - alpha, red_img, alpha, 0)
    overlay = image.copy()
    overlay[mask_final == 255] = blended[mask_final == 255]

    # 保存
    script_dir = os.path.dirname(__file__)
    out_dir = os.path.join(script_dir, 'output_picture')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'prewitt_edges_overlay.jpg')
    cv2.imwrite(out_path, overlay)

    # 保存调试图
    cv2.imwrite(os.path.join(out_dir, 'prewitt_debug_grad.jpg'), grad_n)
    cv2.imwrite(os.path.join(out_dir, 'prewitt_debug_mask.jpg'), mask_combined)
    cv2.imwrite(os.path.join(out_dir, 'prewitt_debug_mask_final.jpg'), mask_final)

    print(f"Prewitt 边缘叠合图已保存: {out_path}")


if __name__ == '__main__':
    main()
