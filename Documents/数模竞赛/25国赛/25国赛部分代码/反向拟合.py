import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from math import exp, asin, sin, cos, pi

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取Si的详细参数数据
try:
    data = pd.read_csv('Si的详细参数.csv', encoding='utf-8')
    print(f"成功读取数据，共{len(data)}行")
except:
    try:
        data = pd.read_csv('Si的详细参数.csv', encoding='gbk')
        print(f"成功读取数据（GBK编码），共{len(data)}行")
    except:
        try:
            data = pd.read_csv('Si的详细参数.csv', encoding='latin-1')
            print(f"成功读取数据（Latin-1编码），共{len(data)}行")
        except Exception as e:
            print(f"读取数据时出错: {e}")
            exit()

# 提取各列数据
line1 = data.iloc[:, 0].values  # 第一列：波数
line2 = data.iloc[:, 1].values  # 第二列：折射率
line4 = data.iloc[:, 3].values  # 第四列：吸收系数

# 设置参数
n1 = 1
n3 = 9
d = 4.0

# 初始化结果数组
R_values = []

# 对每个数据点进行计算
for i in range(len(line1)):
    n2 = 3.2 #line2[i]
    x = line1[i]
    alpha = 3
    
    # 计算反射系数
    r12 = (n1 - n2)/(n1 + n2)
    r23 = (n2 - n3)/(n2 + n3)
    
    # 计算A
    A = 6 * exp(- alpha * x * d * (0.0001))
    
    # 计算角度和相位
    sita = asin(sin(10/(2*pi))/n2)
    sigema = 4 * pi * n2 * d * x * cos(sita) * (0.0001)
    B = cos(sigema)
    
    # 计算反射率
    Poinmoleculart = r12 ** 2 + r23 ** 2 - 2 * r12 * r23 * B
    Denominator = 1 + (r12 * r23) ** 2 - 2 * r12 * r23 * B
    R = (Poinmoleculart / Denominator) * A
    
    R_values.append(R)

# 绘制图像
plt.figure(figsize=(10, 6))
plt.plot(line1, R_values, 'b-', linewidth=1)
plt.xlabel('Wavenumber (cm-1)')
plt.ylabel('Reflectance R')
plt.title('Si Material Reflectance vs Wavenumber')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# 保存图像
plt.savefig('Si反向拟合结果.png', dpi=300, bbox_inches='tight')
print("图像已保存为 'Si反向拟合结果.png'")
print(f"数据范围: 波数 {min(line1):.2f} - {max(line1):.2f} cm⁻¹")
print(f"反射率范围: {min(R_values):.4f} - {max(R_values):.4f}")

# 关闭图像以释放内存
plt.close()
print("计算完成！")