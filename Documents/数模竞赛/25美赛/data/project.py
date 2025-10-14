# Python随机森林回归
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
path = 'C:\Users\贺正泽\Desktop\data\Data_RandomForest.csv' #数据路径
rawdata = pd.read_csv(path).set_index('index')  #加载数据
print(rawdata.head()) #数据预览
x = rawdata.drop('y_value',axis = 1) #输入特征
y = rawdata['y_value']  #目标变量
x_train,x_test,y_train,y_test = train_test_split(x,y,test_size = 0.3,random_state=0) #30%为测试集，则70%为训练集
rfr = RandomForestRegressor(n_estimators=100, random_state=0)
rfr.fit(x_train,y_train) #使用训练数据集训练随机森林模型
y_pred = rfr.predict(x_test) #使用分类器预测测试集
# 评估回归性能
print('Mean Squared Error:',mean_squared_error(y_test,y_pred))
print('Mean Absolute Error:',mean_absolute_error(y_test,y_pred))
print('Root Mean Squared Error:',np.sqrt(mean_squared_error(y_test,y_pred)))
importances = rfr.feature_importances_ # 计算特征重要性
print("Importances:",importances)
r2 = r2_score(y_test, y_pred)
print("R²:",r2)
# 绘制测试集散点图和斜线
plt.scatter(y_test, y_pred, alpha=0.7)
plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], linestyle='--', color='grey', linewidth=2)
plt.title(f'Scatter plot of y_test vs. y_pred\nR² = {r2:.2f}')
plt.xlabel('True Values (y_test)')
plt.ylabel('Predictions (y_pred)')
plt.show()