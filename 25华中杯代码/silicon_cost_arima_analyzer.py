import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from data_processor import DataProcessor
import os
import itertools

class SiliconCostAnalyzer:
    def __init__(self, excel_file_path):
        """初始化分析器
        
        Args:
            excel_file_path (str): Excel文件路径
        """
        self.data_processor = DataProcessor(excel_file_path)
        self.data_processor.read_all_data()
        self.variable_cost_data = self.data_processor.get_variable_cost_data()
        self.silicon_types = ['N1', 'N2', 'N3', 'P']
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        self.predictions = {}
        self.adf_results = {}
        self.best_params = {}
        
    def prepare_time_series(self, silicon_type):
        """准备时间序列数据
        
        Args:
            silicon_type (str): 硅片类型
            
        Returns:
            pd.Series: 时间序列数据
        """
        data = []
        for month in range(1, 9):
            data.append(self.variable_cost_data[month][silicon_type])
        return pd.Series(data, index=pd.date_range(start='2023-01-01', periods=8, freq='ME'))
    
    def perform_adf_test(self, series, d=1):
        """执行ADF检验
        
        Args:
            series (pd.Series): 时间序列数据
            d (int): 差分阶数
            
        Returns:
            tuple: (p值, 检验统计量)
        """
        # 进行d阶差分
        diff_series = series
        for _ in range(d):
            diff_series = diff_series.diff().dropna()
        
        result = adfuller(diff_series)
        return result[1], result[0]  # 返回p值和检验统计量
    
    def find_best_arima(self, series, silicon_type):
        """寻找最佳ARIMA模型参数
        
        Args:
            series (pd.Series): 时间序列数据
            silicon_type (str): 硅片类型
            
        Returns:
            tuple: (p, d, q) 最佳参数组合
        """
        best_aic = float('inf')
        best_params = None
        best_p_value = 1.0
        
        # 首先确定最佳的差分阶数d，最多进行两次差分
        optimal_d = 0
        for d in range(0, 3):  # 限制最多两次差分
            adf_p_value, _ = self.perform_adf_test(series, d)
            if adf_p_value < 0.05:
                optimal_d = d
                break
        # 如果两次差分后仍然不满足平稳性要求，使用d=2作为默认值
        if optimal_d == 0 and self.perform_adf_test(series, 2)[0] >= 0.05:
            optimal_d = 2
        
        # 定义参数范围，p固定为1
        p = 1  # AR阶数固定为1
        q_range = range(0, 4)  # MA阶数
        
        print(f"\n正在为{silicon_type}型硅片寻找最佳ARIMA参数...")
        
        # 遍历所有可能的参数组合，使用已确定的差分阶数和固定的p值
        for q in q_range:
            try:
                # 尝试拟合ARIMA模型
                model = ARIMA(series, order=(p, optimal_d, q))
                results = model.fit()
                
                # 更新最佳参数
                if results.aic < best_aic:
                    best_aic = results.aic
                    best_params = (p, optimal_d, q)
                    best_p_value = adf_p_value
                    
                print(f"ARIMA({p},{optimal_d},{q}) - AIC: {results.aic:.2f}, ADF p值: {adf_p_value:.4f}")
                
            except:
                continue
        
        if best_params is None:
            print(f"警告：未找到{silicon_type}型硅片的合适参数，使用默认值(1,{optimal_d},1)")
            return (1, optimal_d, 1)
        
        print(f"找到{silicon_type}型硅片的最佳参数：ARIMA{best_params}, AIC: {best_aic:.2f}, ADF p值: {best_p_value:.4f}")
        return best_params
    
    def forecast_next_month(self, series, params):
        """预测下一个月的数据
        
        Args:
            series (pd.Series): 时间序列数据
            params (tuple): ARIMA模型参数 (p, d, q)
            
        Returns:
            tuple: (预测值, 置信区间下限, 置信区间上限)
        """
        try:
            model = ARIMA(series, order=params)
            results = model.fit()
            
            # 获取预测值和预测区间
            forecast = results.forecast(steps=1)
            forecast_ci = results.get_prediction(start=len(series), end=len(series)).conf_int(alpha=0.2)  # 80%置信区间
            
            return float(forecast.iloc[0]), float(forecast_ci.iloc[0, 0]), float(forecast_ci.iloc[0, 1])
        except Exception as e:
            print(f"预测失败: {str(e)}")
            # 如果ARIMA预测失败，使用简单的移动平均作为备选方案
            mean_value = series.mean()
            std_value = series.std()
            # 使用正态分布近似计算置信区间
            ci_lower = mean_value - 1.28 * std_value  # 80%置信区间，z值约为1.28
            ci_upper = mean_value + 1.28 * std_value
            return mean_value, ci_lower, ci_upper
    
    def analyze_all_types(self):
        """分析所有硅片类型"""
        for silicon_type in self.silicon_types:
            series = self.prepare_time_series(silicon_type)
            
            # 寻找最佳ARIMA参数
            best_params = self.find_best_arima(series, silicon_type)
            self.best_params[silicon_type] = best_params
            
            # 执行ADF检验
            p_value, test_stat = self.perform_adf_test(series, best_params[1])
            self.adf_results[silicon_type] = {'p_value': p_value, 'test_stat': test_stat}
            
            # 预测下一个月
            forecast, ci_lower, ci_upper = self.forecast_next_month(series, best_params)
            
            self.predictions[silicon_type] = {
                'series': series,
                'params': best_params,
                'forecast': forecast,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper
            }
    
    def plot_results(self):
        """绘制分析结果"""
        # 设置Seaborn样式
        sns.set_style("whitegrid")
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('硅片单位变动成本ARIMA分析', fontsize=16, y=0.95)
        
        for idx, (silicon_type, color) in enumerate(zip(self.silicon_types, self.colors)):
            row = idx // 2
            col = idx % 2
            ax = axes[row, col]
            
            # 绘制历史数据
            series = self.predictions[silicon_type]['series']
            months = range(1, 9)
            ax.plot(months, series.values, 'o-', color=color, label='历史数据', linewidth=2, markersize=8)
            
            # 获取预测值和置信区间
            forecast = self.predictions[silicon_type]['forecast']
            ci_lower = self.predictions[silicon_type]['ci_lower']
            ci_upper = self.predictions[silicon_type]['ci_upper']
            
            # 绘制预测点
            ax.plot(9, forecast, '*', color=color, markersize=20, label='预测值')
            ax.plot([8, 9], [series.values[-1], forecast], '--', color=color, linewidth=2)
            
            # 绘制置信区间 - 改进版本
            # 创建平滑的曲线连接历史数据和预测区间
            x_smooth = np.linspace(8, 9, 100)
            y_lower = np.linspace(series.values[-1], ci_lower, 100)
            y_upper = np.linspace(series.values[-1], ci_upper, 100)
            
            # 填充置信区间区域 - 加深背景颜色并添加黑色虚线边框
            ax.fill_between(x_smooth, y_lower, y_upper, color=color, alpha=0.3, label='80%置信区间')
            
            # 绘制完整的三角形边框
            # 下边界线
            ax.plot(x_smooth, y_lower, '--', color='black', linewidth=1.5, alpha=0.7)
            # 上边界线
            ax.plot(x_smooth, y_upper, '--', color='black', linewidth=1.5, alpha=0.7)
            # 连接最后一个历史数据点到预测区间的线段
            ax.plot([8, 9], [series.values[-1], ci_lower], '--', color='black', linewidth=1.5, alpha=0.7)
            ax.plot([8, 9], [series.values[-1], ci_upper], '--', color='black', linewidth=1.5, alpha=0.7)
            
            # 添加参数标注
            params = self.predictions[silicon_type]['params']
            adf_p = self.adf_results[silicon_type]['p_value']
            
            # 创建参数说明文本
            param_text = f'ARIMA{params}\n差分后ADF p值: {adf_p:.4f}'
            if adf_p < 0.05:
                param_text += '\n(序列平稳)'
            else:
                param_text += '\n(序列不平稳)'
            
            # 添加置信区间信息
            param_text += f'\n预测值: {forecast:.2f}'
            param_text += f'\n置信区间: [{ci_lower:.2f}, {ci_upper:.2f}]'
                
            ax.text(0.05, 0.95, param_text,
                   transform=ax.transAxes, 
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor=color),
                   verticalalignment='top')
            
            # 设置标题和标签
            ax.set_title(f'{silicon_type}型硅片', fontsize=12, pad=10)
            ax.set_xlabel('月份', fontsize=10)
            ax.set_ylabel('单位变动成本', fontsize=10)
            
            # 设置x轴刻度
            ax.set_xticks(range(1, 10))
            ax.set_xticklabels([f'{i}月' for i in range(1, 10)])
            
            # 添加网格
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            # 设置y轴范围
            y_min = min(min(series.values), ci_lower) * 0.9
            y_max = max(max(series.values), ci_upper) * 1.1
            ax.set_ylim(y_min, y_max)
        
        plt.tight_layout()
        
        # 创建保存目录
        if not os.path.exists('silicon_cost_plots'):
            os.makedirs('silicon_cost_plots')
        
        # 保存图片
        plt.savefig('silicon_cost_plots/silicon_cost_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 打印最佳参数汇总
        print("\n最佳ARIMA参数汇总：")
        print("=" * 50)
        for silicon_type in self.silicon_types:
            params = self.best_params[silicon_type]
            adf_p = self.adf_results[silicon_type]['p_value']
            forecast = self.predictions[silicon_type]['forecast']
            ci_lower = self.predictions[silicon_type]['ci_lower']
            ci_upper = self.predictions[silicon_type]['ci_upper']
            print(f"{silicon_type}型硅片: ARIMA{params}, ADF p值: {adf_p:.4f}")
            print(f"  预测值: {forecast:.2f}, 80%置信区间: [{ci_lower:.2f}, {ci_upper:.2f}]")
        print("=" * 50)

def main():
    analyzer = SiliconCostAnalyzer('Problem A.xlsx')
    analyzer.analyze_all_types()
    analyzer.plot_results()
    print("分析完成，图表已保存至 silicon_cost_plots 目录")

if __name__ == "__main__":
    main() 