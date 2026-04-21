import argparse
import os
import glob
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = BASE_DIR
OUTPUT_DIR = os.path.join(BASE_DIR, "packing_3d_output")
# =========================
# 可按需要修改的参数
# =========================
DPI = 220
FIGSIZE = (12, 9)
ALPHA = 0.82                         # 箱体透明度
EDGE_COLOR = "black"
EDGE_WIDTH = 0.35
SHOW_TEXT = False                    # 是否显示每个箱子的type_id文字
TEXT_SIZE = 6
ELEV = 22                            # 俯仰角
AZIM = -58                           # 方位角

# 车型尺寸自动匹配。
# 如果想固定某个车厢尺寸，可把 TRUCK_DIMS 设为具体值。
TRUCK_DIMENSIONS = {
    "车型1": (420, 210, 220),
    "车型2": (680, 245, 250),
}
TRUCK_DIMS = None

# 类型配色（可继续补充）
TYPE_COLORS = {
    "G1": "#4E79A7",
    "G2": "#F28E2B",
    "G3": "#E15759",
    "G4": "#76B7B2",
    "G5": "#59A14F",
    "G6": "#EDC948",
    "G7": "#B07AA1",
    "G8": "#FF9DA7",
}
CATEGORY_COLORS = {
    "fragile": "#E15759",
    "oriented": "#76B7B2",
    "standard": "#4E79A7",
}


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def get_color(row):
    t = str(row.get("type_id", "")).strip()
    c = str(row.get("category", "")).strip().lower()
    if t in TYPE_COLORS:
        return TYPE_COLORS[t]
    if c in CATEGORY_COLORS:
        return CATEGORY_COLORS[c]
    return "#9C755F"


def normalize_truck_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    clean = name.strip()
    if "车型1" in clean:
        return "车型1"
    if "车型2" in clean:
        return "车型2"
    return clean


def cuboid_faces(x, y, z, dx, dy, dz):
    p000 = [x, y, z]
    p100 = [x + dx, y, z]
    p110 = [x + dx, y + dy, z]
    p010 = [x, y + dy, z]
    p001 = [x, y, z + dz]
    p101 = [x + dx, y, z + dz]
    p111 = [x + dx, y + dy, z + dz]
    p011 = [x, y + dy, z + dz]
    faces = [
        [p000, p100, p110, p010],  # bottom
        [p001, p101, p111, p011],  # top
        [p000, p100, p101, p001],  # front
        [p010, p110, p111, p011],  # back
        [p000, p010, p011, p001],  # left
        [p100, p110, p111, p101],  # right
    ]
    return faces


def draw_container_wireframe(ax, L, W, H):
    corners = np.array([
        [0, 0, 0], [L, 0, 0], [L, W, 0], [0, W, 0],
        [0, 0, H], [L, 0, H], [L, W, H], [0, W, H]
    ])
    edges = [
        (0,1),(1,2),(2,3),(3,0),
        (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7)
    ]
    for i, j in edges:
        xs = [corners[i,0], corners[j,0]]
        ys = [corners[i,1], corners[j,1]]
        zs = [corners[i,2], corners[j,2]]
        ax.plot(xs, ys, zs, color="black", linewidth=1.0, alpha=0.9)


def set_axes_equal(ax, xlim, ylim, zlim):
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    z_range = zlim[1] - zlim[0]
    max_range = max(x_range, y_range, z_range)

    x_mid = sum(xlim) / 2
    y_mid = sum(ylim) / 2
    z_mid = sum(zlim) / 2

    ax.set_xlim(x_mid - max_range/2, x_mid + max_range/2)
    ax.set_ylim(y_mid - max_range/2, y_mid + max_range/2)
    ax.set_zlim(z_mid - max_range/2, z_mid + max_range/2)


def plot_single_csv(csv_path, output_path=None):
    df = pd.read_csv(csv_path)
    required_cols = ["x", "y", "z", "length", "width", "height"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"文件 {csv_path} 缺少字段: {missing}")

    # 数值化
    for c in required_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required_cols).copy()

    if df.empty:
        raise ValueError(f"文件 {csv_path} 无有效装箱数据")

    truck_name = str(df["truck_id"].iloc[0]) if "truck_id" in df.columns else os.path.splitext(os.path.basename(csv_path))[0]

    max_L = float((df["x"] + df["length"]).max())
    max_W = float((df["y"] + df["width"]).max())
    max_H = float((df["z"] + df["height"]).max())
    if TRUCK_DIMS is None:
        L, W, H = max_L, max_W, max_H
    else:
        L, W, H = TRUCK_DIMS

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111, projection="3d")

    # 先画车厢边框
    draw_container_wireframe(ax, L, W, H)

    # 为了让高层箱子不遮挡过多，可按z从低到高画
    df = df.sort_values(by=["z", "x", "y"], ascending=[True, True, True]).reset_index(drop=True)

    legend_items = {}

    for _, row in df.iterrows():
        x, y, z = row["x"], row["y"], row["z"]
        dx, dy, dz = row["length"], row["width"], row["height"]
        color = get_color(row)

        faces = cuboid_faces(x, y, z, dx, dy, dz)
        poly = Poly3DCollection(
            faces,
            facecolors=color,
            edgecolors=EDGE_COLOR,
            linewidths=EDGE_WIDTH,
            alpha=ALPHA,
        )
        ax.add_collection3d(poly)

        label = str(row.get("type_id", row.get("category", "货物")))
        legend_items[label] = color

        if SHOW_TEXT:
            ax.text(
                x + dx/2, y + dy/2, z + dz/2,
                str(row.get("type_id", "")),
                fontsize=TEXT_SIZE,
                ha="center", va="center"
            )

    ax.set_title(f"{truck_name}  3D Packing View\nBoxes = {len(df)}", fontsize=14, pad=18)
    ax.set_xlabel("X / Length")
    ax.set_ylabel("Y / Width")
    ax.set_zlabel("Z / Height")

    ax.view_init(elev=ELEV, azim=AZIM)
    ax.grid(True, linestyle="--", alpha=0.35)
    set_axes_equal(ax, (0, L), (0, W), (0, H))

    handles = [Patch(facecolor=c, edgecolor='black', label=k) for k, c in sorted(legend_items.items())]
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.)

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
        plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description="批量生成 3D 装箱图像")
    parser.add_argument(
        "--input-dir",
        default=INPUT_DIR,
        help="输入CSV文件夹，默认使用当前脚本所在目录",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="输出图片文件夹，默认创建 packing_3d_output",
    )
    parser.add_argument(
        "--pattern",
        default="*装箱明细*.csv",
        help="读取CSV的glob模式，例如 '*.csv' 或 '*明细*.csv'",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)
    required_cols = ["x", "y", "z", "length", "width", "height"]

    ensure_dir(output_dir)
    csv_files = sorted(glob.glob(os.path.join(input_dir, args.pattern)))
    if not csv_files:
        raise FileNotFoundError(f"在 {input_dir} 下未找到匹配模式: {args.pattern}")

    print(f"共找到 {len(csv_files)} 个CSV文件，模式={args.pattern}")
    valid_files = []
    for csv_path in csv_files:
        try:
            df_header = pd.read_csv(csv_path, nrows=0)
            missing = [c for c in required_cols if c not in df_header.columns]
            if missing:
                print(f"跳过 {os.path.basename(csv_path)}：缺少字段 {missing}")
                continue
            valid_files.append(csv_path)
        except Exception as e:
            print(f"跳过 {os.path.basename(csv_path)}：无法读取文件，原因: {e}")

    if not valid_files:
        raise FileNotFoundError(f"没有找到包含装箱字段的CSV文件，模式={args.pattern}")

    for i, csv_path in enumerate(valid_files, 1):
        base = os.path.splitext(os.path.basename(csv_path))[0]
        out_path = os.path.join(output_dir, f"{base}_3D.png")
        try:
            plot_single_csv(csv_path, out_path)
            print(f"[{i:02d}/{len(valid_files):02d}] 已生成: {out_path}")
        except Exception as e:
            print(f"[{i:02d}/{len(valid_files):02d}] 生成失败: {csv_path}\n原因: {e}")

    print("全部完成。")


if __name__ == "__main__":
    main()
