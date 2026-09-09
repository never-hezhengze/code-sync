import csv
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.patches as mpatches
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def draw_box(ax, x, y, z, l, w, h, color):
    # 定义货物的 8 个顶点
    vertices = np.array([
        [x, y, z], [x + l, y, z], [x + l, y + w, z], [x, y + w, z],
        [x, y, z + h], [x + l, y, z + h], [x + l, y + w, z + h], [x, y + w, z + h]
    ])

    faces = [
        [vertices[0], vertices[1], vertices[2], vertices[3]],  # 底面
        [vertices[4], vertices[5], vertices[6], vertices[7]],  # 顶面
        [vertices[0], vertices[1], vertices[5], vertices[4]],  # 前面
        [vertices[2], vertices[3], vertices[7], vertices[6]],  # 后面
        [vertices[1], vertices[2], vertices[6], vertices[5]],  # 右面
        [vertices[0], vertices[3], vertices[7], vertices[4]]  # 左面
    ]

    poly3d = Poly3DCollection(faces, facecolors=color, linewidths=0.5, edgecolors='k', alpha=0.7)
    ax.add_collection3d(poly3d)


def visualize_specific_csv(csv_file_path, truck_type=1):
    """
    可视化指定的装箱 CSV 文件
    :param csv_file_path: CSV 文件路径
    :param truck_type: 车型编号 (1 或 2)
    """
    if truck_type == 1:
        L, W, H = 420, 210, 220
        truck_display_name = "车型1"
    elif truck_type == 2:
        L, W, H = 680, 245, 250
        truck_display_name = "车型2"
    else:
        # 默认兜底（可根据需要修改）
        L, W, H = 420, 210, 220
        truck_display_name = f"车型{truck_type}"

    placements = []
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            placements.append({
                'type_id': row['type_id'],
                'x': float(row['x']),
                'y': float(row['y']),
                'z': float(row['z']),
                'length': float(row['length']),
                'width': float(row['width']),
                'height': float(row['height'])
            })

    # 货物类型色彩映射
    color_map = {
        # 'G1': '#1f77b4', 'G2': '#2ca02c', 'G3': '#d62728', 'G4': '#ff7f0e', 'G5': '#9467bd'
        'G1': '#f8d4a0', 'G2': '#bca6cd', 'G3': '#f59694', 'G4': '#9bc2ee', 'G5': '#a6df91'
    }

    # 创建画布
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    for item in placements:
        color = color_map.get(item['type_id'], '#cccccc')
        draw_box(ax,
                 item['x'], item['y'], item['z'],
                 item['length'], item['width'], item['height'],
                 color)

    # 设置坐标轴范围
    ax.set_xlim([0, L])
    ax.set_ylim([0, W])
    ax.set_zlim([0, H])

    # 开启并自定义网格线样式
    ax.grid(True)
    grid_style = {'color': '#cccccc', 'linewidth': 1, 'linestyle': '-'}
    ax.xaxis._axinfo['grid'].update(grid_style)
    ax.yaxis._axinfo['grid'].update(grid_style)
    ax.zaxis._axinfo['grid'].update(grid_style)

    # 将背景平面设为灰色
    ax.xaxis.set_pane_color((0.95, 0.95, 0.95, 1.0))
    ax.yaxis.set_pane_color((0.95, 0.95, 0.95, 1.0))
    ax.zaxis.set_pane_color((0.95, 0.95, 0.95, 1.0))

    # 设置视角
    ax.view_init(elev=25, azim=-135)

    ax.set_box_aspect((L, W, H))

    # 设置轴标签
    ax.set_xlabel('x / cm', labelpad=5, fontstyle='italic', fontsize=12)
    ax.set_ylabel('y / cm', labelpad=5, fontstyle='italic', fontsize=12)
    ax.set_zlabel('z / cm', labelpad=5, fontstyle='italic', fontsize=12)

    legend_handles = [
        mpatches.Patch(color='#f8d4a0', label='G1: 标准件'),
        mpatches.Patch(color='#bca6cd', label='G2: 标准件'),
        mpatches.Patch(color='#f59694', label='G3: 易碎件'),
        mpatches.Patch(color='#9bc2ee', label='G4: 定向件'),
        mpatches.Patch(color='#a6df91', label='G5: 定向件')
    ]

    # 图例设置
    legend = ax.legend(
        handles=legend_handles,
        loc='upper left',
        bbox_to_anchor=(0.02, 0.85),
        title=None,
        shadow=False,
        frameon=True,
        fontsize=10,
        handletextpad=0.5,
        borderaxespad=0.1
    )

    frame = legend.get_frame()
    frame.set_edgecolor('black')
    frame.set_linewidth(0.5)
    frame.set_facecolor('white')

    # 标题使用手动指定的车型名称
    plt.title(f"{truck_display_name} 单车装载可视化", y=-0.01)

    plt.tight_layout()

    # 保存图片
    output_filename = f'1_2_truck{truck_type}_006.png'
    fig.savefig(output_filename, dpi=600, bbox_inches=None)
    print(f"可视化图片已成功保存为：{output_filename}")

    plt.close(fig)


if __name__ == "__main__":
    # 指定选择哪个车型 (1 或 2)
    target_truck_type = 2
    target_csv = "1_2_车型2_006_装箱明细.csv"

    visualize_specific_csv(target_csv, truck_type=target_truck_type)