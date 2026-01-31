import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import numpy as np
import os

print("开始处理Shkondin数据...")

# 检查文件是否存在
if not os.path.exists('Shkondin.csv'):
    print("错误：找不到文件 'Shkondin.csv'")
    exit(1)

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 读取CSV文件
try:
    print("正在读取CSV文件...")
    # 读取CSV文件
    df = pd.read_csv('Shkondin.csv')
    
    print("CSV文件列名:")
    print(df.columns.tolist())
    print("\n数据预览:")
    print(df.head())
    print(f"\n数据形状: {df.shape}")
    
    # 获取各列数据
    first_column = df.iloc[:, 0]  # 第一列 (wl)
    second_column = df.iloc[:, 1]  # 第二列 (n)
    third_column = df.iloc[:, 2]  # 第三列 (k)
    
    print(f"\n第一列数据类型: {first_column.dtype}")
    print(f"第二列数据类型: {second_column.dtype}")
    print(f"第三列数据类型: {third_column.dtype}")
    
    # 去除空值
    valid_data = pd.DataFrame({
        'wl': first_column,
        'n': second_column,
        'k': third_column
    }).dropna()
    
    print(f"\n去除空值后数据点数量: {len(valid_data)}")
    
    # 检查是否有零值（倒数会出错）
    zero_mask = valid_data['wl'] == 0
    if zero_mask.any():
        print(f"警告：发现 {zero_mask.sum()} 个零值，将被排除")
        valid_data = valid_data[~zero_mask]
    
    # 计算第一列的倒数乘10000作为横坐标
    valid_data['x'] = 10000 / valid_data['wl']
    
    print(f"\n最终数据点数量: {len(valid_data)}")
    print("数据范围:")
    print(f"横坐标 (10000/第一列): {valid_data['x'].min():.2f} 到 {valid_data['x'].max():.2f}")
    print(f"第二列 (n): {valid_data['n'].min():.6f} 到 {valid_data['n'].max():.6f}")
    print(f"第三列 (k): {valid_data['k'].min():.2e} 到 {valid_data['k'].max():.2e}")
    
    # 创建第一个图表：横坐标 vs 第二列
    plt.figure(figsize=(12, 8))
    
    # 子图1：横坐标 vs 第二列
    plt.subplot(2, 1, 1)
    plt.plot(valid_data['x'], valid_data['n'], 'b-', linewidth=2, marker='o', markersize=2)
    plt.title('Shkondin数据图 - 横坐标 vs 第二列(n)', fontsize=14, fontweight='bold')
    plt.xlabel('10000/第一列数据', fontsize=12)
    plt.ylabel('第二列数据 (n)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 子图2：横坐标 vs 第三列
    plt.subplot(2, 1, 2)
    plt.plot(valid_data['x'], valid_data['k'], 'r-', linewidth=2, marker='o', markersize=2)
    plt.title('Shkondin数据图 - 横坐标 vs 第三列(k)', fontsize=14, fontweight='bold')
    plt.xlabel('10000/第一列数据', fontsize=12)
    plt.ylabel('第三列数据 (k)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图片
    plt.savefig('Shkondin数据图.png', dpi=300, bbox_inches='tight')
    
    print(f"\n成功绘制图表，共使用了 {len(valid_data)} 个数据点")
    print("图表已保存为 'Shkondin数据图.png'")
    
    # 创建单独的图表文件
    # 图表1：横坐标 vs 第二列
    plt.figure(figsize=(10, 6))
    plt.plot(valid_data['x'], valid_data['n'], 'b-', linewidth=2, marker='o', markersize=2)
    plt.title('Shkondin数据图 - 横坐标 vs 第二列(n)', fontsize=16, fontweight='bold')
    plt.xlabel('10000/第一列数据', fontsize=12)
    plt.ylabel('第二列数据 (n)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('Shkondin_第二列.png', dpi=300, bbox_inches='tight')
    
    # 图表2：横坐标 vs 第三列
    plt.figure(figsize=(10, 6))
    plt.plot(valid_data['x'], valid_data['k'], 'r-', linewidth=2, marker='o', markersize=2)
    plt.title('Shkondin数据图 - 横坐标 vs 第三列(k)', fontsize=16, fontweight='bold')
    plt.xlabel('10000/第一列数据', fontsize=12)
    plt.ylabel('第三列数据 (k)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('Shkondin_第三列.png', dpi=300, bbox_inches='tight')
    
    print("单独图表已保存为:")
    print("- 'Shkondin_第二列.png'")
    print("- 'Shkondin_第三列.png'")
    
except Exception as e:
    print(f"读取CSV文件时出错: {e}")
    import traceback
    traceback.print_exc()
    print("请确保CSV文件存在且格式正确")


