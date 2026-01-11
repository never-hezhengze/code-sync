import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# 读取数据，指定日期为索引列
data = pd.read_csv(
    'E:\\Documents\\data.csv',
    index_col='Month',encoding='GB2312'
)


# 绘图过程中
import matplotlib.pyplot as plt
# 用来正常显示中文标签
plt.rcParams['font.sans-serif'] = ['SimHei']
# 用来正常显示负号
plt.rcParams['axes.unicode_minus'] = False
# 查看趋势图
data.plot()  # 有增长趋势，不平稳
plt.show()