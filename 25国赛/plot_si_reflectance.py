import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import numpy as np
import os

print("开始处理Si反射率数据...")

# 检查文件是否存在
if not os.path.exists('Si的反射率信息.xlsx'):
    print("错误：找不到文件 'Si的反射率信息.xlsx'")
    exit(1)

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 读取Excel文件
try:
    print("正在读取Excel文件...")
    # 读取Excel文件
    df = pd.read_excel('Si的反射率信息.xlsx')
    
    print("Excel文件列名:")
    print(df.columns.tolist())
    print("\n数据预览:")
    print(df.head())
    print(f"\n数据形状: {df.shape}")
    
    # 获取第一列和第二列的数据
    first_column = df.iloc[:, 0]  # 第一列
    second_column = df.iloc[:, 1]  # 第二列
    
    print(f"\n第一列数据类型: {first_column.dtype}")
    print(f"第二列数据类型: {second_column.dtype}")
    
    # 去除空值
    valid_data = pd.DataFrame({
        'x_raw': first_column,
        'y': second_column
    }).dropna()
    
    print(f"\n去除空值后数据点数量: {len(valid_data)}")
    
    # 检查是否有零值（倒数会出错）
    zero_mask = valid_data['x_raw'] == 0
    if zero_mask.any():
        print(f"警告：发现 {zero_mask.sum()} 个零值，将被排除")
        valid_data = valid_data[~zero_mask]
    
    # 计算第一列的倒数作为横坐标
    valid_data['x'] = 1 / valid_data['x_raw']
    
    print(f"\n最终数据点数量: {len(valid_data)}")
    print("数据范围:")
    print(f"横坐标 (1/第一列): {valid_data['x'].min():.6f} 到 {valid_data['x'].max():.6f}")
    print(f"纵坐标 (第二列): {valid_data['y'].min():.6f} 到 {valid_data['y'].max():.6f}")
    
    # 创建图表
    plt.figure(figsize=(10, 6))
    plt.plot(valid_data['x'], valid_data['y'], 'b-', linewidth=2, marker='o', markersize=4)
    
    # 设置图表标题和标签
    plt.title('Si反射率数据图', fontsize=16, fontweight='bold')
    plt.xlabel('1/第一列数据', fontsize=12)
    plt.ylabel('第二列数据', fontsize=12)
    
    # 添加网格
    plt.grid(True, alpha=0.3)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig('Si反射率图.png', dpi=300, bbox_inches='tight')
    
    print(f"\n成功绘制图表，共使用了 {len(valid_data)} 个数据点")
    print("图表已保存为 'Si反射率图.png'")
    
    # 不显示图表（避免在命令行环境中出现问题）
    # plt.show()
    
except Exception as e:
    print(f"读取Excel文件时出错: {e}")
    import traceback
    traceback.print_exc()
    print("请确保Excel文件存在且格式正确")
