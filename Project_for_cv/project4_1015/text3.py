import cv2
import numpy as np
import os


def main():
    img_path = 'Photo/picture1.jpg'
    image = cv2.imread(img_path)
    if image is None:
        script_dir = os.path.dirname(__file__)
        alt_path = os.path.normpath(os.path.join(script_dir, '..', 'Photo', 'picture1.jpg'))
        image = cv2.imread(alt_path)
        if image is None:
            print(f"无法读取图像，尝试的路径: {img_path} 和 {alt_path}")
            return

    # 1) 对彩色图像进行双边滤波去噪（保边缘）——降低强度以保留更多细节
    denoised_color = cv2.bilateralFilter(image, d=3, sigmaColor=50, sigmaSpace=50)

    # 2) 转灰度并做 CLAHE
    gray = cv2.cvtColor(denoised_color, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # 3) Laplacian 边缘检测（使用 ksize=3）
    lap = cv2.Laplacian(gray, ddepth=cv2.CV_32F, ksize=3)
    lap_abs = np.abs(lap)

    # 归一化到 0-255
    if lap_abs.max() > 0:
        lap_n = np.clip((lap_abs / lap_abs.max()) * 255, 0, 255).astype(np.uint8)
    else:
        lap_n = np.zeros_like(gray, dtype=np.uint8)

    # 二值化（Otsu），再用 Canny 做补充（基于 denoised gray）
    _, mask_lap = cv2.threshold(lap_n, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    median_val = np.median(gray)
    sigma = 0.33
    lower = int(max(0, (1.0 - sigma) * median_val))
    upper = int(min(255, (1.0 + sigma) * median_val))
    mask_canny = cv2.Canny(gray, lower, upper)

    mask_combined = cv2.bitwise_or(mask_lap, mask_canny)

    # 开运算去噪
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_clean = cv2.morphologyEx(mask_combined, cv2.MORPH_OPEN, kernel, iterations=1)

    # 骨架化
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

    # alpha 混合叠合红色边缘
    alpha = 0.75
    red_img = np.zeros_like(image)
    red_img[:, :] = (0, 0, 255)
    blended = cv2.addWeighted(image, 1.0 - alpha, red_img, alpha, 0)
    overlay = image.copy()
    overlay[mask_final == 255] = blended[mask_final == 255]

    # 保存结果和调试图
    script_dir = os.path.dirname(__file__)
    out_dir = os.path.join(script_dir, 'output_picture')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'laplacian_edges_overlay.jpg')
    cv2.imwrite(out_path, overlay)

    cv2.imwrite(os.path.join(out_dir, 'laplacian_debug_lap.jpg'), lap_n)
    cv2.imwrite(os.path.join(out_dir, 'laplacian_debug_mask.jpg'), mask_combined)
    cv2.imwrite(os.path.join(out_dir, 'laplacian_debug_mask_final.jpg'), mask_final)

    print(f"Laplacian 边缘叠合图已保存: {out_path}")


if __name__ == '__main__':
    main()
