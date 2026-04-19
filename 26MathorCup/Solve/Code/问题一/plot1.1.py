import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Patch
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
# =========================
# 1. 文件路径
# =========================
file1 = r"result1.1/车型1_问题1_1_增强版装箱明细.csv"
file2 = r"result1.1/车型2_问题1_1_增强版装箱明细.csv"

# =========================
# 2. 颜色映射：同一种货物同一种颜色
# =========================
COLOR_MAP = {
    "G1": "#1f77b4",  # 蓝
    "G2": "#ff7f0e",  # 橙
    "G3": "#2ca02c",  # 绿
    "G4": "#d62728",  # 红
    "G5": "#9467bd",  # 紫
}

# =========================
# 3. 构造长方体的6个面
# =========================
def cuboid_faces(x, y, z, dx, dy, dz):
    """
    根据左下后角坐标 (x, y, z) 和尺寸 (dx, dy, dz)
    返回长方体6个面的顶点列表
    """
    p000 = [x,      y,      z]
    p100 = [x + dx, y,      z]
    p110 = [x + dx, y + dy, z]
    p010 = [x,      y + dy, z]
    p001 = [x,      y,      z + dz]
    p101 = [x + dx, y,      z + dz]
    p111 = [x + dx, y + dy, z + dz]
    p011 = [x,      y + dy, z + dz]

    faces = [
        [p000, p100, p110, p010],  # 底面
        [p001, p101, p111, p011],  # 顶面
        [p000, p100, p101, p001],  # 前面
        [p010, p110, p111, p011],  # 后面
        [p000, p010, p011, p001],  # 左面
        [p100, p110, p111, p101],  # 右面
    ]
    return faces

# =========================
# 4. 绘图函数
# =========================
def plot_packing_3d(csv_file, title=None):
    df = pd.read_csv(csv_file)

    required_cols = ["type_id", "x", "y", "z", "length", "width", "height"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"文件 {csv_file} 缺少必要列: {col}")

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")

    # 逐个货物绘制
    for _, row in df.iterrows():
        x = row["x"]
        y = row["y"]
        z = row["z"]
        dx = row["length"]
        dy = row["width"]
        dz = row["height"]
        t = row["type_id"]

        color = COLOR_MAP.get(t, "#7f7f7f")
        faces = cuboid_faces(x, y, z, dx, dy, dz)

        poly = Poly3DCollection(
            faces,
            facecolors=color,
            edgecolors="k",
            linewidths=0.3,
            alpha=0.65
        )
        ax.add_collection3d(poly)

    # 坐标范围
    x_max = (df["x"] + df["length"]).max()
    y_max = (df["y"] + df["width"]).max()
    z_max = (df["z"] + df["height"]).max()

    ax.set_xlim(0, x_max)
    ax.set_ylim(0, y_max)
    ax.set_zlim(0, z_max)

    # 标签
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    # 标题
    if title is None:
        title = csv_file
    ax.set_title(title, fontsize=14)

    # 尽量让三轴比例接近真实
    try:
        ax.set_box_aspect((x_max, y_max, z_max))
    except:
        pass

    # 图例
    types_in_file = [t for t in df["type_id"].unique() if t in COLOR_MAP]
    legend_handles = [
        Patch(facecolor=COLOR_MAP[t], edgecolor="k", label=t, alpha=0.65)
        for t in types_in_file
    ]
    ax.legend(handles=legend_handles, loc="upper right")

    # 视角
    ax.view_init(elev=22, azim=-58)

    plt.tight_layout()
    plt.show()

# =========================
# 5. 主程序：分别画车型1和车型2
# =========================
if __name__ == "__main__":
    plot_packing_3d(file1, title="问题1.1 - 车型1 装箱三维可视化")
    plot_packing_3d(file2, title="问题1.1 - 车型2 装箱三维可视化")