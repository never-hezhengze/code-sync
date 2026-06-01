import pandas as pd
import numpy as np
from scipy.optimize import minimize
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Tuple, List
import json
from data_processor import DataProcessor
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import PolynomialFeatures
from scipy.optimize import curve_fit
from datetime import datetime
import matplotlib as mpl

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']  # 优先使用微软雅黑
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
plt.rcParams['mathtext.fontset'] = 'stix'  # 用来正常显示数学公式

class ProfitOptimizationModel:
    def __init__(self):
        self.data_processor = None
        self.data = None
        self.scalers = {}
        self.constraints = {}
        self.price_volume_relation = None
        self.normalization_params = {}
        self.models = {}  # 存储不同模型的拟合结果
        
    def load_data(self, file_path: str):
        """加载数据并进行预处理"""
        # 使用DataProcessor加载数据
        self.data_processor = DataProcessor(file_path)
        self.data_processor.read_all_data()
        self.data_processor.read_unit_variable_cost_data()
        
        # 将数据转换为DataFrame格式
        self._convert_to_dataframe()
        
    def _convert_to_dataframe(self):
        """将DataProcessor中的数据转换为DataFrame格式"""
        # 获取月度汇总数据
        monthly_data = self.data_processor.get_monthly_summary_data()
        
        # 获取销售数据
        sales_data = self.data_processor.get_sales_data()
        
        # 获取单位变动成本数据
        unit_variable_cost_data = self.data_processor.get_unit_variable_cost_data()
        
        # 创建DataFrame
        data_dict = {
            '月份': [],
            '硅片A销量': [], '硅片B销量': [], '硅片C销量': [], '硅片D销量': [],
            '硅片A售价': [], '硅片B售价': [], '硅片C售价': [], '硅片D售价': [],
            '硅片A单位变动成本': [], '硅片B单位变动成本': [], '硅片C单位变动成本': [], '硅片D单位变动成本': [],
            '生产公共成本': [], '人工成本': [], '折旧': [], '营业税费': [],
            '销售费用': [], '管理费用': [], '财务费用': [], '所得税费用': []
        }
        
        # 填充数据
        for month in range(1, 9):
            data_dict['月份'].append(month)
            
            # 销量数据
            data_dict['硅片A销量'].append(sales_data[month]['demand']['N1'])
            data_dict['硅片B销量'].append(sales_data[month]['demand']['N2'])
            data_dict['硅片C销量'].append(sales_data[month]['demand']['N3'])
            data_dict['硅片D销量'].append(sales_data[month]['demand']['P'])
            
            # 售价数据（万元转换为元）
            data_dict['硅片A售价'].append(sales_data[month]['price']['N1'] * 10000)
            data_dict['硅片B售价'].append(sales_data[month]['price']['N2'] * 10000)
            data_dict['硅片C售价'].append(sales_data[month]['price']['N3'] * 10000)
            data_dict['硅片D售价'].append(sales_data[month]['price']['P'] * 10000)
            
            # 单位变动成本数据
            data_dict['硅片A单位变动成本'].append(unit_variable_cost_data[month]['N1'])
            data_dict['硅片B单位变动成本'].append(unit_variable_cost_data[month]['N2'])
            data_dict['硅片C单位变动成本'].append(unit_variable_cost_data[month]['N3'])
            data_dict['硅片D单位变动成本'].append(unit_variable_cost_data[month]['P'])
            
            # 固定成本数据
            data_dict['生产公共成本'].append(monthly_data[month]['生产公共成本'])
            data_dict['人工成本'].append(monthly_data[month]['人工成本'])
            data_dict['折旧'].append(monthly_data[month]['折旧'])
            data_dict['营业税费'].append(monthly_data[month]['营业税费'])
            data_dict['销售费用'].append(monthly_data[month]['销售费用'])
            data_dict['管理费用'].append(monthly_data[month]['管理费用'])
            data_dict['财务费用'].append(monthly_data[month]['财务费用'])
            data_dict['所得税费用'].append(monthly_data[month]['所得税费用'])
        
        # 创建DataFrame
        self.data = pd.DataFrame(data_dict)
        
    def determine_constraints(self):
        """确定各变量的约束范围"""
        for col in self.data.columns:
            if '销量' in col or '售价' in col:
                min_val = self.data[col].min()
                max_val = self.data[col].max()
                
                # 设置约束范围：最小值的0.8倍到最大值的1.2倍
                self.constraints[col] = {
                    'min': min_val * 0.8,
                    'max': max_val * 1.2
                }
                
                print(f"\n{col}的约束范围：")
                print(f"最小值：{self.constraints[col]['min']:.2f}")
                print(f"最大值：{self.constraints[col]['max']:.2f}")
            elif '单位变动成本' in col:
                min_val = self.data[col].min() / 10000  # 单位变动成本需要除以10000
                max_val = self.data[col].max() / 10000
                
                # 设置约束范围：最小值的0.8倍到最大值的1.2倍
                self.constraints[col] = {
                    'min': min_val * 0.8,
                    'max': max_val * 1.2
                }
                
                print(f"\n{col}的约束范围：")
                print(f"最小值：{self.constraints[col]['min']:.2f}")
                print(f"最大值：{self.constraints[col]['max']:.2f}")

    def _normalize_data(self):
        """对每种硅片的影响因子分别进行归一化"""
        self.scalers = {}
        
        # 对每种硅片分别进行归一化
        for product in ['A', 'B', 'C', 'D']:
            print(f"\n硅片{product}的归一化参数：")
            
            # 创建该产品的归一化器
            price_scaler = MinMaxScaler()
            volume_scaler = MinMaxScaler()
            cost_scaler = MinMaxScaler()
            
            # 获取数据
            price_data = self.data[f'硅片{product}售价'].values.reshape(-1, 1)
            volume_data = self.data[f'硅片{product}销量'].values.reshape(-1, 1)
            cost_data = self.data[f'硅片{product}单位变动成本'].values.reshape(-1, 1) / 10000  # 单位变动成本需要除以10000
            
            # 进行归一化
            normalized_price = price_scaler.fit_transform(price_data)
            normalized_volume = volume_scaler.fit_transform(volume_data)
            normalized_cost = cost_scaler.fit_transform(cost_data)
            
            # 保存归一化后的数据
            self.data[f'硅片{product}售价_归一化'] = normalized_price
            self.data[f'硅片{product}销量_归一化'] = normalized_volume
            self.data[f'硅片{product}单位变动成本_归一化'] = normalized_cost
            
            # 保存归一化器
            self.scalers[f'硅片{product}售价'] = price_scaler
            self.scalers[f'硅片{product}销量'] = volume_scaler
            self.scalers[f'硅片{product}单位变动成本'] = cost_scaler
            
            # 打印归一化参数
            print(f"售价 - 最小值：{price_scaler.min_[0]:.2f}, 最大值：{price_scaler.min_[0] + 1/price_scaler.scale_[0]:.2f}")
            print(f"销量 - 最小值：{volume_scaler.min_[0]:.2f}, 最大值：{volume_scaler.min_[0] + 1/volume_scaler.scale_[0]:.2f}")
            print(f"单位变动成本 - 最小值：{cost_scaler.min_[0]:.2f}, 最大值：{cost_scaler.min_[0] + 1/cost_scaler.scale_[0]:.2f}")

    def fit_price_volume_relation(self):
        """使用多种函数形式拟合价格-销量关系"""
        print("\n价格-销量关系拟合结果：")
        self.price_volume_relations = {}
        
        # 定义各种函数形式
        def quadratic_func(x, a, b, c):
            """二次函数：y = ax² + bx + c"""
            return a * x**2 + b * x + c
        
        def cubic_func(x, a, b, c, d):
            """三次函数：y = ax³ + bx² + cx + d"""
            return a * x**3 + b * x**2 + c * x + d
        
        def quartic_func(x, a, b, c, d, e):
            """四次函数：y = ax⁴ + bx³ + cx² + dx + e"""
            return a * x**4 + b * x**3 + c * x**2 + d * x + e
        
        def log_func(x, a, b):
            """对数函数：y = a * ln(x) + b"""
            return a * np.log(x) + b
        
        # 定义所有函数及其名称
        functions = {
            'quadratic': (quadratic_func, ['a', 'b', 'c']),
            'cubic': (cubic_func, ['a', 'b', 'c', 'd']),
            'quartic': (quartic_func, ['a', 'b', 'c', 'd', 'e']),
            'logarithmic': (log_func, ['a', 'b'])
        }
        
        for product in ['A', 'B', 'C', 'D']:
            print(f"\n硅片{product}：")
            
            # 获取数据
            price_data = self.data[f'硅片{product}售价'].values
            volume_data = self.data[f'硅片{product}销量'].values
            
            # 存储所有模型的拟合结果
            models = {}
            
            # 对每种函数进行拟合
            for func_name, (func, param_names) in functions.items():
                try:
                    # 设置初始值
                    if func_name == 'quadratic':
                        # 初始值：使用最小二乘法估计
                        X = np.column_stack([price_data**2, price_data, np.ones_like(price_data)])
                        p0 = np.linalg.lstsq(X, volume_data, rcond=None)[0]
                    elif func_name == 'cubic':
                        # 初始值
                        X = np.column_stack([price_data**3, price_data**2, price_data, np.ones_like(price_data)])
                        p0 = np.linalg.lstsq(X, volume_data, rcond=None)[0]
                    elif func_name == 'quartic':
                        # 初始值
                        X = np.column_stack([price_data**4, price_data**3, price_data**2, price_data, np.ones_like(price_data)])
                        p0 = np.linalg.lstsq(X, volume_data, rcond=None)[0]
                    elif func_name == 'logarithmic':
                        # 初始值
                        X = np.column_stack([np.log(price_data), np.ones_like(price_data)])
                        p0 = np.linalg.lstsq(X, volume_data, rcond=None)[0]
                    else:
                        # 初始值
                        X = np.column_stack([price_data, np.ones_like(price_data)])
                        p0 = np.linalg.lstsq(X, volume_data, rcond=None)[0]
                    
                    # 使用curve_fit进行拟合，不添加边界条件
                    popt, pcov = curve_fit(func, price_data, volume_data, 
                                         p0=p0, maxfev=10000)
                    
                    # 计算预测值
                    y_pred = func(price_data, *popt)
                    
                    # 计算R²和RMSE
                    r2 = 1 - np.sum((volume_data - y_pred)**2) / np.sum((volume_data - np.mean(volume_data))**2)
                    rmse = np.sqrt(np.mean((volume_data - y_pred)**2))
                    
                    # 存储模型结果
                    models[func_name] = {
                        'func': func,
                        'params': popt,
                        'r2': r2,
                        'rmse': rmse,
                        'param_names': param_names
                    }
                    
                    # 打印模型性能
                    print(f"{func_name} - R²: {r2:.4f}, RMSE: {rmse:.4f}")
                    
                    # 打印函数表达式
                    expr = f"y = "
                    for i, (param, name) in enumerate(zip(popt, param_names)):
                        if i > 0:
                            expr += " + " if param >= 0 else " - "
                        expr += f"{abs(param):.4f}*{name}"
                    print(f"{func_name}: {expr}")
                    
                except Exception as e:
                    print(f"{func_name} 拟合失败: {str(e)}")
            
            if not models:
                print(f"警告：硅片{product}没有找到合适的模型")
                continue
                
            # 选择最佳模型
            # best_model = max(models.items(), key=lambda x: x[1]['r2'])
            # print(f"\n最佳模型: {best_model[0]}, R²: {best_model[1]['r2']:.4f}")
            
            # 选择R²值最小的模型作为最佳模型
            best_model = min(models.items(), key=lambda x: x[1]['r2'])
            print(f"\n最佳模型: {best_model[0]}, R²: {best_model[1]['r2']:.4f}")
            
            # 保存所有模型结果
            self.price_volume_relations[product] = models
            
            # 绘制拟合结果
            self._plot_fitting_results(product, price_data, volume_data, models)

    def _plot_fitting_results(self, product, price_data, volume_data, models):
        """绘制不同模型的拟合结果"""
        plt.figure(figsize=(12, 8))
        
        # 将价格数据除以10000
        price_data = price_data / 10000
        
        # 绘制原始数据点
        plt.scatter(price_data, volume_data, color='blue', label='实际数据', alpha=0.7, s=100)
        
        # 生成平滑的预测曲线
        x_smooth = np.linspace(min(price_data) * 0.9, max(price_data) * 1.1, 1000)
        
        # 为每个模型绘制拟合曲线
        colors = ['red', 'green', 'purple', 'orange']
        for (func_name, model), color in zip(models.items(), colors):
            try:
                # 对于预测，需要将x_smooth乘以10000来匹配原始模型的尺度
                y_smooth = model['func'](x_smooth * 10000, *model['params'])
                plt.plot(x_smooth, y_smooth, color=color, 
                        label=f'{func_name}\n$R^2$ = {model["r2"]:.4f}\nRMSE = {model["rmse"]:.0f}', 
                        linewidth=2)
            except:
                continue
        
        plt.title(f'硅片{product}价格-销量关系拟合结果', fontsize=14)
        plt.xlabel('价格 (元)', fontsize=12)
        plt.ylabel('销量', fontsize=12)
        plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        
        # 添加数据点标签
        for i, (x, y) in enumerate(zip(price_data, volume_data)):
            plt.annotate(f'月份{i+1}', (x, y), xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        # 设置坐标轴范围
        plt.xlim(min(price_data) * 0.9, max(price_data) * 1.1)
        plt.ylim(min(volume_data) * 0.9, max(volume_data) * 1.1)
        
        # 调整布局以适应图例
        plt.tight_layout()
        
        # 保存图片
        plt.savefig(f'fitting_results_{product}.png', dpi=300, bbox_inches='tight')
        plt.close()

    def analyze_price_volume_relations(self):
        """分析价格-销量关系并生成报告"""
        print("\n==================================================")
        print("价格-销量关系分析")
        print("==================================================\n")
        
        print("各硅片的价格-销量关系：\n")
        
        for product in ['A', 'B', 'C', 'D']:
            print(f"\n硅片{product}：")
            print("价格-销量对应关系示例：")
            
            try:
                # 获取R²值最小的模型
                best_model_name = min(self.price_volume_relations[product].items(), 
                                    key=lambda x: x[1]['r2'])[0]
                best_model = self.price_volume_relations[product][best_model_name]
                
                # 生成一系列价格点
                price_data = self.data[f'硅片{product}售价']
                price_min, price_max = price_data.min(), price_data.max()
                test_prices = np.linspace(price_min, price_max, 5)
                
                print(f"\n使用{best_model_name}模型预测：")
                print(f"{'价格':>12} | {'预测销量':>12}")
                print("-" * 27)
                
                for price in test_prices:
                    # 使用最佳模型预测销量
                    volume = best_model['func'](price, *best_model['params'])
                    print(f"{price:>12.2f} | {volume:>12.2f}")
                    
            except Exception as e:
                print(f"Error processing 硅片{product}: {str(e)}")
                continue
            
        print("\n")
        
        # 保存报告到文件
        with open('optimization_report.txt', 'w', encoding='utf-8') as f:
            f.write("价格-销量关系分析报告\n")
            f.write("=" * 50 + "\n\n")
            
            for product in ['A', 'B', 'C', 'D']:
                f.write(f"\n硅片{product}价格-销量关系：\n")
                try:
                    # 获取R²值最小的模型
                    best_model_name = min(self.price_volume_relations[product].items(), 
                                        key=lambda x: x[1]['r2'])[0]
                    best_model = self.price_volume_relations[product][best_model_name]
                    
                    # 生成一系列价格点
                    price_data = self.data[f'硅片{product}售价']
                    price_min, price_max = price_data.min(), price_data.max()
                    test_prices = np.linspace(price_min, price_max, 10)
                    
                    f.write(f"\n使用{best_model_name}模型预测：\n")
                    f.write(f"{'价格':>12} | {'预测销量':>12}\n")
                    f.write("-" * 27 + "\n")
                    
                    for price in test_prices:
                        # 使用最佳模型预测销量
                        volume = best_model['func'](price, *best_model['params'])
                        f.write(f"{price:>12.2f} | {volume:>12.2f}\n")
                        
                except Exception as e:
                    f.write(f"Error processing 硅片{product}: {str(e)}\n")
                    continue
                
            f.write("\n\n报告生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        print("报告已保存到 optimization_report.txt")

    def calculate_profit(self, prices: Dict[str, float], unit_costs: Dict[str, float]) -> float:
        """计算给定价格和单位成本下的利润"""
        total_profit = 0
        
        # 计算销售收入和变动成本
        for product in ['A', 'B', 'C', 'D']:
            price = prices[f'硅片{product}售价']
            unit_cost = unit_costs[f'硅片{product}单位变动成本']
            
            # 检查是否存在价格-销量关系
            if product not in self.price_volume_relations or not self.price_volume_relations[product]:
                print(f"警告：硅片{product}没有有效的价格-销量关系模型")
                return float('-inf')
            
            # 获取R²值最小的模型
            try:
                best_model_name = min(self.price_volume_relations[product].items(), 
                                    key=lambda x: x[1]['r2'])[0]
                best_model = self.price_volume_relations[product][best_model_name]
            except Exception as e:
                print(f"错误：获取硅片{product}的最佳模型失败: {str(e)}")
                return float('-inf')
            
            # 使用最佳模型预测销量
            try:
                volume = best_model['func'](price, *best_model['params'])
                if volume < 0:  # 如果预测销量为负，返回一个很小的利润
                    return float('-inf')
            except Exception as e:
                print(f"错误：预测硅片{product}的销量失败: {str(e)}")
                return float('-inf')
            
            # 计算该产品的利润
            product_profit = volume * (price - unit_cost)
            total_profit += product_profit
        
        # 获取月度汇总数据
        monthly_data = self.data_processor.get_monthly_summary_data()
        if not monthly_data or 1 not in monthly_data:
            print("错误：无法获取月度汇总数据")
            return float('-inf')
        
        # 减去固定成本和费用
        try:
            total_profit -= monthly_data[1]['生产公共成本']  # 生产公共成本
            total_profit -= monthly_data[1]['人工成本']      # 人工成本
            total_profit -= monthly_data[1]['折旧']          # 折旧
            total_profit -= monthly_data[1]['营业税费']      # 营业税费
            total_profit -= monthly_data[1]['销售费用']      # 销售费用
            total_profit -= monthly_data[1]['管理费用']      # 管理费用
            total_profit -= monthly_data[1]['财务费用']      # 财务费用
        except KeyError as e:
            print(f"错误：缺少必要的成本数据: {str(e)}")
            return float('-inf')
        
        # 计算销售利润
        sales_profit = total_profit
        
        # 计算所得税（销售利润的15%）
        income_tax = sales_profit * 0.15
        total_profit -= income_tax
        
        # 加上硅泥核减
        try:
            silicon_reduction = self.data_processor.get_silicon_reduction_data()
            if silicon_reduction and 1 in silicon_reduction:
                total_profit += silicon_reduction[1]  # 使用第1个月的数据作为预测
            else:
                print("警告：无法获取硅泥核减数据")
        except Exception as e:
            print(f"警告：获取硅泥核减数据失败: {str(e)}")
        
        return total_profit

    def optimize(self, unit_costs: Dict[str, float]) -> Dict:
        """优化模型，返回最优售价和对应的销量"""
        # 检查是否所有产品都有价格-销量关系模型
        for product in ['A', 'B', 'C', 'D']:
            if product not in self.price_volume_relations or not self.price_volume_relations[product]:
                return {
                    'success': False,
                    'message': f'硅片{product}没有有效的价格-销量关系模型',
                    'prices': None,
                    'volumes': None,
                    'profit': None
                }
        
        # 定义优化目标函数
        def objective(prices_array):
            prices = {
                '硅片A售价': prices_array[0],
                '硅片B售价': prices_array[1],
                '硅片C售价': prices_array[2],
                '硅片D售价': prices_array[3]
            }
            profit = self.calculate_profit(prices, unit_costs)
            return -profit if profit != float('-inf') else 1e10  # 转换无效解为大的正数

        # 设置价格约束
        bounds = []
        for product in ['A', 'B', 'C', 'D']:
            try:
                unit_cost = unit_costs[f'硅片{product}单位变动成本'] / 10000  # 只对单位变动成本除以10000
                price_data = self.data[f'硅片{product}售价']
                min_price = max(unit_cost * 1.1, price_data.min())  # 确保至少有10%的利润率
                max_price = price_data.max() * 1.2  # 允许比历史最高价高20%
                
                # 确保上限大于下限
                if max_price <= min_price:
                    max_price = min_price * 1.2  # 如果上限小于等于下限，则设置为下限的1.2倍
                    
                bounds.append((min_price, max_price))
            except Exception as e:
                return {
                    'success': False,
                    'message': f'设置硅片{product}的价格约束失败: {str(e)}',
                    'prices': None,
                    'volumes': None,
                    'profit': None
                }

        # 设置初始值（使用历史平均价格）
        try:
            x0 = []
            for product in ['A', 'B', 'C', 'D']:
                price_data = self.data[f'硅片{product}售价']
                x0.append(price_data.mean())
        except Exception as e:
            return {
                'success': False,
                'message': f'设置初始价格失败: {str(e)}',
                'prices': None,
                'volumes': None,
                'profit': None
            }

        # 使用多个初始点进行优化
        best_result = None
        best_profit = float('-inf')
        
        # 生成多个初始点
        initial_points = [x0]  # 第一个初始点是历史平均价格
        for _ in range(4):  # 再添加4个随机初始点
            random_point = []
            for i, (low, high) in enumerate(bounds):
                random_point.append(np.random.uniform(low, high))
            initial_points.append(random_point)
        
        # 对每个初始点进行优化
        for init_point in initial_points:
            try:
                result = minimize(objective, init_point, method='SLSQP', bounds=bounds)
                profit = -result.fun if result.success else float('-inf')
                
                if profit > best_profit:
                    best_profit = profit
                    best_result = result
            except Exception as e:
                print(f"警告：使用初始点 {init_point} 优化失败: {str(e)}")
                continue

        # 如果没有找到可行解，返回错误
        if best_result is None or not best_result.success:
            return {
                'success': False,
                'message': '未找到可行解',
                'prices': None,
                'volumes': None,
                'profit': None
            }

        # 计算最优解对应的销量和价格
        optimal_prices = {
            '硅片A售价': best_result.x[0],
            '硅片B售价': best_result.x[1],
            '硅片C售价': best_result.x[2],
            '硅片D售价': best_result.x[3]
        }

        optimal_volumes = {}
        for product in ['A', 'B', 'C', 'D']:
            try:
                price = optimal_prices[f'硅片{product}售价']
                
                # 获取R²值最小的模型
                best_model_name = min(self.price_volume_relations[product].items(), 
                                    key=lambda x: x[1]['r2'])[0]
                best_model = self.price_volume_relations[product][best_model_name]
                
                # 使用最佳模型预测销量
                volume = best_model['func'](price, *best_model['params'])
                if volume < 0:  # 如果预测销量为负，设为0
                    volume = 0
                
                optimal_volumes[f'硅片{product}销量'] = volume
            except Exception as e:
                return {
                    'success': False,
                    'message': f'计算硅片{product}的最优销量失败: {str(e)}',
                    'prices': None,
                    'volumes': None,
                    'profit': None
                }

        return {
            'success': True,
            'message': '优化成功',
            'prices': optimal_prices,
            'volumes': optimal_volumes,
            'profit': best_profit
        }
        
    def save_normalization_params(self, file_path: str):
        """保存归一化参数"""
        params = {
            'constraints': self.constraints,
            'scalers': {k: {'min_': v.min_.tolist(), 'scale_': v.scale_.tolist()} 
                       for k, v in self.scalers.items()}
        }
        with open(file_path, 'w') as f:
            json.dump(params, f, indent=4)
            
    def load_normalization_params(self, file_path: str):
        """加载归一化参数"""
        with open(file_path, 'r') as f:
            params = json.load(f)
        self.constraints = params['constraints']
        # 重建scaler对象
        for k, v in params['scalers'].items():
            scaler = MinMaxScaler()
            scaler.min_ = np.array(v['min_'])
            scaler.scale_ = np.array(v['scale_'])
            self.scalers[k] = scaler

    def generate_report(self, unit_costs: Dict[str, float]) -> str:
        """生成模型优化报告"""
        result = self.optimize(unit_costs)
        
        report = "销售净利润优化模型报告\n"
        report += "=" * 50 + "\n\n"
        
        # 输入参数
        report += "输入参数：\n"
        report += "-" * 20 + "\n"
        for product, cost in unit_costs.items():
            report += f"{product}: {cost/10000:.2f}元\n"
        report += "\n"
        
        # 优化结果
        report += "优化结果：\n"
        report += "-" * 20 + "\n"
        report += f"总销售净利润: {result['profit']/10000:.2f}元\n\n"
        
        # 各产品最优售价和销量
        report += "各产品最优方案：\n"
        report += "-" * 20 + "\n"
        for product in ['A', 'B', 'C', 'D']:
            report += f"\n硅片{product}：\n"
            report += f"  最优售价: {result['prices'][f'硅片{product}售价']/10000:.2f}元\n"
            report += f"  预计销量: {result['volumes'][f'硅片{product}销量']:.2f}\n"
            report += f"  预计利润: {(result['prices'][f'硅片{product}售价'] - unit_costs[f'硅片{product}单位变动成本']) * result['volumes'][f'硅片{product}销量']/10000:.2f}元\n"
        
        # 优化状态
        report += "\n优化状态：\n"
        report += "-" * 20 + "\n"
        report += f"优化是否成功: {'是' if result['success'] else '否'}\n"
        report += f"优化信息: {result['message']}\n"
        
        return report

    def main(self):
        """主函数"""
        # 加载数据
        self.load_data('Problem A.xlsx')
        
        # 确定约束范围
        self.determine_constraints()
        
        # 归一化数据
        self._normalize_data()
        
        # 拟合价格-销量关系
        self.fit_price_volume_relation()
        
        # 分析价格-销量关系
        self.analyze_price_volume_relations()
        
        # 保存归一化参数
        self.save_normalization_params('normalization_params.json')
        
        # 设置单位变动成本
        unit_costs = {
            '硅片A单位变动成本': 0.858 * 10000,  # 1万元
            '硅片B单位变动成本': 1.1504 * 10000,  # 1.2万元
            '硅片C单位变动成本': 0.9959 * 10000,  # 1.5万元
            '硅片D单位变动成本': 1.1971 * 10000   # 1.8万元
        }
        
        # 生成报告
        report = self.generate_report(unit_costs)
        
        # 保存报告
        with open('optimization_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
            
        print("\n报告已保存到 optimization_report.txt")

if __name__ == "__main__":
    # 创建模型实例
    model = ProfitOptimizationModel()
    # 运行主函数
    model.main() 