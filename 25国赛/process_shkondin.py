import pandas as pd
import numpy as np
import os

print("开始处理Shkondin.csv文件...")

# 检查文件是否存在
if not os.path.exists('Shkondin.csv'):
    print("错误：找不到文件 'Shkondin.csv'")
    exit(1)

try:
    print("正在读取CSV文件...")
    # 读取CSV文件
    df = pd.read_csv('Shkondin.csv')
    
    print("原始数据预览:")
    print(df.head())
    print(f"\n原始数据形状: {df.shape}")
    print(f"原始列名: {df.columns.tolist()}")
    
    # 创建新的DataFrame副本
    new_df = df.copy()
    
    # 修改第一列的列名
    new_df.columns = ['wn'] + list(new_df.columns[1:])
    
    print(f"\n修改后的列名: {new_df.columns.tolist()}")
    
    # 处理第一列的数据：将数值改为倒数乘10000
    # 检查是否有零值
    zero_mask = new_df['wn'] == 0
    if zero_mask.any():
        print(f"警告：发现 {zero_mask.sum()} 个零值，将被排除")
        new_df = new_df[~zero_mask]
    
    # 计算倒数乘10000
    new_df['wn'] = 10000 / new_df['wn']
    
    print("\n处理后的数据预览:")
    print(new_df.head())
    print(f"\n处理后数据形状: {new_df.shape}")
    
    # 显示数据范围
    print(f"\n数据范围:")
    print(f"wn列: {new_df['wn'].min():.2f} 到 {new_df['wn'].max():.2f}")
    print(f"n列: {new_df['n'].min():.6f} 到 {new_df['n'].max():.6f}")
    print(f"k列: {new_df['k'].min():.2e} 到 {new_df['k'].max():.2e}")
    
    # 保存为新的CSV文件
    output_filename = 'Shkondin_processed.csv'
    new_df.to_csv(output_filename, index=False)
    
    print(f"\n成功处理数据并保存为 '{output_filename}'")
    print(f"共处理了 {len(new_df)} 行数据")
    
    # 验证保存的文件
    print("\n验证保存的文件:")
    verification_df = pd.read_csv(output_filename)
    print(verification_df.head())
    print(f"验证文件形状: {verification_df.shape}")
    
except Exception as e:
    print(f"处理文件时出错: {e}")
    import traceback
    traceback.print_exc()
    print("请确保CSV文件存在且格式正确")


