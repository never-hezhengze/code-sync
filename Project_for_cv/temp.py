import cv2
import numpy as np
import math

def rigid_transform_expand_canvas(image, angle=30, tx=0, ty=0, scale=1.0):
    """
    使用扩大画布的方法进行刚性变换，确保图像不被裁剪
    """
    h, w = image.shape[:2]
    
    # 将角度转换为弧度
    angle_rad = math.radians(angle)
    
    # 计算旋转后的四个角点
    corners = np.array([
        [0, 0],
        [w, 0],
        [w, h],
        [0, h]
    ], dtype=np.float32)
    
    # 将角点转换为齐次坐标
    corners_homogeneous = np.column_stack([corners, np.ones(4)])
    
    # 构建变换矩阵
    center_x, center_y = w / 2, h / 2
    
    # 平移图像到原点
    T1 = np.array([[1, 0, -center_x],
                   [0, 1, -center_y],
                   [0, 0, 1]])
    
    # 旋转
    R = np.array([[math.cos(angle_rad), -math.sin(angle_rad), 0],
                  [math.sin(angle_rad), math.cos(angle_rad), 0],
                  [0, 0, 1]])
    
    # 缩放
    S = np.array([[scale, 0, 0],
                  [0, scale, 0],
                  [0, 0, 1]])
    
    # 平移回原位置并添加额外平移
    T2 = np.array([[1, 0, center_x + tx],
                   [0, 1, center_y + ty],
                   [0, 0, 1]])
    
    # 组合变换矩阵
    M = T2 @ S @ R @ T1
    
    # 变换角点
    transformed_corners = (M @ corners_homogeneous.T).T
    
    # 计算新图像的边界
    x_coords = transformed_corners[:, 0]
    y_coords = transformed_corners[:, 1]
    
    min_x, max_x = math.floor(min(x_coords)), math.ceil(max(x_coords))
    min_y, max_y = math.floor(min(y_coords)), math.ceil(max(y_coords))
    
    # 计算新图像尺寸（添加一些边距）
    margin = 10
    new_w = int(max_x - min_x) + 2 * margin
    new_h = int(max_y - min_y) + 2 * margin
    
    # 调整变换矩阵以适应新画布
    adjust_matrix = np.array([[1, 0, -min_x + margin],
                              [0, 1, -min_y + margin],
                              [0, 0, 1]])
    
    M_adjusted = adjust_matrix @ M
    
    # 提取2x3变换矩阵用于warpAffine
    M_2x3 = M_adjusted[:2, :]
    
    # 应用变换
    transformed = cv2.warpAffine(image, M_2x3, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    
    # 计算逆变换矩阵
    M_inv = np.linalg.inv(M_adjusted)
    inverse_matrix = M_inv[:2, :]
    
    # 记录原始图像在新画布中的位置
    original_center_transformed = M_adjusted @ np.array([center_x, center_y, 1])
    original_position = (int(original_center_transformed[0] - w/2), 
                         int(original_center_transformed[1] - h/2), w, h)
    
    return transformed, M_2x3, inverse_matrix, original_position, (new_w, new_h)

def inverse_transform_expand(image, inverse_matrix, original_position, target_size=None):
    """
    应用逆变换恢复图像
    """
    h, w = image.shape[:2]
    
    if target_size is None:
        orig_x, orig_y, orig_w, orig_h = original_position
        target_size = (orig_w, orig_h)
    
    # 应用逆变换到整个画布
    restored_full = cv2.warpAffine(image, inverse_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    
    # 裁剪到原始图像区域
    orig_x, orig_y, orig_w, orig_h = original_position
    
    # 确保裁剪区域在图像范围内
    orig_x = max(0, min(orig_x, w - orig_w))
    orig_y = max(0, min(orig_y, h - orig_h))
    
    # 调整尺寸以确保不越界
    actual_w = min(orig_w, w - orig_x)
    actual_h = min(orig_h, h - orig_y)
    
    restored = restored_full[orig_y:orig_y+actual_h, orig_x:orig_x+actual_w]
    
    # 如果裁剪后的尺寸不匹配，进行调整
    if restored.shape[:2] != (orig_h, orig_w):
        restored = cv2.resize(restored, (orig_w, orig_h))
    
    return restored

def calculate_difference(original, restored):
    # 确保尺寸一致
    if original.shape != restored.shape:
        min_h = min(original.shape[0], restored.shape[0])
        min_w = min(original.shape[1], restored.shape[1])
        original = original[:min_h, :min_w]
        restored = restored[:min_h, :min_w]
    
    original = original.astype(np.float32)
    restored = restored.astype(np.float32)
    difference = cv2.absdiff(original, restored)
    mse = np.mean((original - restored) ** 2)
    return difference, mse

def display_results(original, transformed, restored, difference):
    """
    显示结果图像
    """
    # 调整显示大小
    def resize_for_display(img, max_width=400):
        h, w = img.shape[:2]
        if w > max_width:
            scale = max_width / w
            new_w = max_width
            new_h = int(h * scale)
            return cv2.resize(img, (new_w, new_h))
        return img
    
    orig_disp = resize_for_display(original)
    trans_disp = resize_for_display(transformed)
    rest_disp = resize_for_display(restored)
    
    # 归一化差异图像
    diff_normalized = cv2.normalize(difference, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    diff_disp = resize_for_display(diff_normalized)
    
    # 对差异图像应用颜色映射
    if len(diff_disp.shape) == 2 or diff_disp.shape[2] == 1:
        diff_colored = cv2.applyColorMap(diff_disp, cv2.COLORMAP_HOT)
    else:
        diff_colored = diff_disp
    
    # 显示单个图像
    cv2.imshow('1. Original Image A', orig_disp)
    cv2.imshow('2. Transformed Image B (Full)', trans_disp)
    cv2.imshow('3. Restored Image A\'', rest_disp)
    cv2.imshow('4. Difference (A - A\')', diff_colored)
    
    print("查看所有窗口，按任意键继续...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def main():
    # 读取图像
    image = cv2.imread('Photo/picture1.jpg')
    if image is None:
        # 如果无法读取图像，创建测试图像
        print("无法读取图像，创建测试图像...")
        image = np.zeros((300, 400, 3), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (350, 250), (255, 255, 255), -1)
        cv2.circle(image, (200, 150), 80, (0, 0, 255), -1)
        cv2.putText(image, 'TEST IMAGE', (120, 160), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    
    print(f"原始图像尺寸: {image.shape}")
    
    # 进行变换 - 使用较大的变换参数测试
    print("进行刚性变换...")
    transformed_B, transform_matrix, inverse_matrix, original_position, canvas_size = rigid_transform_expand_canvas(
        image, angle=45, tx=50, ty=30, scale=0.8
    )
    
    print(f"变换后图像尺寸: {canvas_size}")
    print(f"原始位置信息: {original_position}")
    
    # 进行逆变换
    print("进行逆变换...")
    restored_A = inverse_transform_expand(transformed_B, inverse_matrix, original_position)
    
    print(f"恢复后图像尺寸: {restored_A.shape}")
    
    # 计算差异
    difference, mse = calculate_difference(image, restored_A)
    print(f"均方误差 (MSE): {mse:.4f}")
    
    # 显示结果
    display_results(image, transformed_B, restored_A, difference)
    
    # 保存结果
    cv2.imwrite('original_A.jpg', image)
    cv2.imwrite('transformed_B_full.jpg', transformed_B)
    cv2.imwrite('restored_A_prime.jpg', restored_A)
    
    # 保存差异图像
    diff_normalized = cv2.normalize(difference, None, 0, 255, cv2.NORM_MINMAX)
    cv2.imwrite('difference.jpg', diff_normalized.astype(np.uint8))
    
    print("处理完成！")

if __name__ == "__main__":
    main()