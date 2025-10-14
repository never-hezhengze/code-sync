import cv2
import numpy as np
import matplotlib.pyplot as plt
import os


def make_scale(sx, sy, cx, cy):
    T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], dtype=float)
    S = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=float)
    T2 = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]], dtype=float)
    return T2 @ S @ T1


def make_rotate(angle_deg, cx, cy):
    theta = np.deg2rad(angle_deg)
    c = np.cos(theta)
    s = np.sin(theta)
    T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], dtype=float)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)
    T2 = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]], dtype=float)
    return T2 @ R @ T1


def make_translate(tx, ty):
    T = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=float)
    return T


def apply_transform(img, M3):
    rows, cols = img.shape[:2]
    M2 = M3[:2, :]
    # output size keep same as original
    dst = cv2.warpAffine(img, M2, (cols, rows), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
    return dst


def compare_images(a, b):
    # ensure same shape
    if a.shape != b.shape:
        raise ValueError('shape mismatch')
    diff = cv2.absdiff(a, b)
    if diff.ndim == 3:
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    else:
        gray = diff
    nonzero = int(np.count_nonzero(gray))
    mse = float(np.mean((gray.astype(np.float32)) ** 2))
    return nonzero, mse, diff


def main():
    src_path = 'Photo/537.png'
    img = cv2.imread(src_path)
    if img is None:
        print(f"Cannot read {src_path}")
        return

    rows, cols = img.shape[:2]
    cx, cy = (cols - 1) / 2.0, (rows - 1) / 2.0

    # parameters
    sx, sy = 0.8, 0.8
    angle = 30.0
    tx, ty = 40, -20

    S = make_scale(sx, sy, cx, cy)
    R = make_rotate(angle, cx, cy)
    T = make_translate(tx, ty)

    orders = [
        ('S_then_R_then_T', [S, R, T]),
        ('T_then_R_then_S', [T, R, S]),
        ('R_then_S_then_T', [R, S, T]),
        ('S_then_T_then_R', [S, T, R]),
    ]

    results = {}
    out_dir = 'output_picture/order_demo'
    os.makedirs(out_dir, exist_ok=True)

    for name, mats in orders:
        M = np.eye(3)
        for A in mats:
            M = A @ M
        dst = apply_transform(img, M)
        path = os.path.join(out_dir, f'{name}.png')
        cv2.imwrite(path, dst)
        results[name] = dst
        print(f'Saved {path}')

    # compare pairwise to show differences
    pairs = [(orders[i][0], orders[j][0]) for i in range(len(orders)) for j in range(i+1, len(orders))]
    comparisons = []
    for a, b in pairs:
        nz, mse, diff = compare_images(results[a], results[b])
        comparisons.append((a, b, nz, mse))

    # print summary
    print('\nComparison summary (nonzero pixel diff, MSE):')
    for a, b, nz, mse in comparisons:
        print(f'{a}  vs  {b}  -> nonzero: {nz}, mse: {mse:.2f}')

    # visualize results and diffs
    fig, axes = plt.subplots(2, max(4, len(orders)), figsize=(16, 8))
    for i, (name, _) in enumerate(orders):
        axes[0, i].imshow(cv2.cvtColor(results[name], cv2.COLOR_BGR2RGB))
        axes[0, i].set_title(name)
        axes[0, i].axis('off')

    # show diffs for first three pairs (or all if few)
    k = 0
    for idx, (a, b, nz, mse) in enumerate(comparisons):
        if k >= axes.shape[1]:
            break
        diff = cv2.absdiff(results[a], results[b])
        axes[1, k].imshow(cv2.cvtColor(diff, cv2.COLOR_BGR2RGB))
        axes[1, k].set_title(f'{a}\nvs\n{b}\nnonzero={nz}\nmse={mse:.1f}')
        axes[1, k].axis('off')
        k += 1

    # hide unused subplots in bottom row
    for j in range(k, axes.shape[1]):
        axes[1, j].axis('off')

    plt.tight_layout()
    vis_path = os.path.join(out_dir, 'order_comparison.png')
    fig.savefig(vis_path)
    print(f'Visualization saved to {vis_path}')
    plt.show()


if __name__ == '__main__':
    main()
