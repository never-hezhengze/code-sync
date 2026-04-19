import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from matplotlib.patches import Patch
import os

BASE_DIR = os.path.dirname(__file__)

json_file = os.path.join(
    BASE_DIR,
    "problem1_1_sa_lns_truck_1_solution.json"
)

# =========================
# 2. 颜色映射：同类货物同色
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
    p000 = [x,      y,      z]
    p100 = [x + dx, y,      z]
    p110 = [x + dx, y + dy, z]
    p010 = [x,      y + dy, z]
    p001 = [x,      y,      z + dz]
    p101 = [x + dx, y,      z + dz]
    p111 = [x + dx, y + dy, z + dz]
    p011 = [x,      y + dy, z + dz]

    faces = [
        [p000, p100, p110, p010],  # bottom
        [p001, p101, p111, p011],  # top
        [p000, p100, p101, p001],  # front
        [p010, p110, p111, p011],  # back
        [p000, p010, p011, p001],  # left
        [p100, p110, p111, p101],  # right
    ]
    return faces


# =========================
# 4. 画车厢边界线
# =========================
def truck_wireframe_edges(L, W, H):
    pts = {
        "000": (0, 0, 0),
        "100": (L, 0, 0),
        "110": (L, W, 0),
        "010": (0, W, 0),
        "001": (0, 0, H),
        "101": (L, 0, H),
        "111": (L, W, H),
        "011": (0, W, H),
    }

    edges = [
        [pts["000"], pts["100"]],
        [pts["100"], pts["110"]],
        [pts["110"], pts["010"]],
        [pts["010"], pts["000"]],

        [pts["001"], pts["101"]],
        [pts["101"], pts["111"]],
        [pts["111"], pts["011"]],
        [pts["011"], pts["001"]],

        [pts["000"], pts["001"]],
        [pts["100"], pts["101"]],
        [pts["110"], pts["111"]],
        [pts["010"], pts["011"]],
    ]
    return edges


# =========================
# 5. 主绘图函数
# =========================
def plot_packing_from_json(
    json_path,
    alpha=0.65,
    edge_linewidth=0.25,
    show_item_id=False,
    save_path=None
):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    truck = data["truck"]
    placements = data["placements"]

    L = truck["length"]
    W = truck["width"]
    H = truck["height"]
    truck_name = truck.get("name", "Truck")

    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection="3d")

    # -------------------------
    # 画车厢边界
    # -------------------------
    edges = truck_wireframe_edges(L, W, H)
    ax.add_collection3d(
        Line3DCollection(edges, colors="black", linewidths=1.2)
    )

    # -------------------------
    # 画每个货物
    # -------------------------
    types_present = set()

    for item in placements:
        x = item["x"]
        y = item["y"]
        z = item["z"]
        dx = item["length"]
        dy = item["width"]
        dz = item["height"]
        t = item["type_id"]
        item_id = item["item_id"]

        color = COLOR_MAP.get(t, "#7f7f7f")
        types_present.add(t)

        faces = cuboid_faces(x, y, z, dx, dy, dz)
        poly = Poly3DCollection(
            faces,
            facecolors=color,
            edgecolors="k",
            linewidths=edge_linewidth,
            alpha=alpha
        )
        ax.add_collection3d(poly)

        if show_item_id:
            ax.text(
                x + dx / 2,
                y + dy / 2,
                z + dz / 2,
                item_id,
                fontsize=6,
                ha="center",
                va="center"
            )

    # -------------------------
    # 坐标轴设置
    # -------------------------
    ax.set_xlim(0, L)
    ax.set_ylim(0, W)
    ax.set_zlim(0, H)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    try:
        ax.set_box_aspect((L, W, H))
    except Exception:
        pass

    summary = data.get("summary", {})
    loaded_items = summary.get("loaded_items", len(placements))
    space_util = summary.get("space_utilization", None)
    weight_util = summary.get("weight_utilization", None)
    composite_score = summary.get("composite_score", None)

    title_lines = [f"{truck_name} 3D装箱可视化"]
    title_lines.append(f"已装载货物数: {loaded_items}")

    if space_util is not None and weight_util is not None and composite_score is not None:
        title_lines.append(
            f"空间利用率={space_util:.4f}，载重利用率={weight_util:.4f}，综合得分={composite_score:.4f}"
        )

    ax.set_title("\n".join(title_lines), fontsize=13)

    # -------------------------
    # 图例
    # -------------------------
    legend_handles = [
        Patch(facecolor=COLOR_MAP[t], edgecolor="k", label=t, alpha=alpha)
        for t in sorted(types_present)
        if t in COLOR_MAP
    ]
    ax.legend(handles=legend_handles, loc="upper right")

    # -------------------------
    # 视角
    # -------------------------
    ax.view_init(elev=24, azim=-58)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()


# =========================
# 6. 运行
# =========================
if __name__ == "__main__":
    plot_packing_from_json(
        json_file,
        alpha=0.65,
        edge_linewidth=0.22,
        show_item_id=False,
        # save_path="truck1_3d_packing.png"   # 不想保存可改成 None
    )