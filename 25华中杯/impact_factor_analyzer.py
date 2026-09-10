import numpy as np
import pandas as pd
from data_processor import DataProcessor
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import os

class ImpactFactorAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data_processor = DataProcessor(file_path)
        self.impact_factors = {}
        self.visualization_dir = "visualizations"
        
        # 创建可视化目录
        if not os.path.exists(self.visualization_dir):
            os.makedirs(self.visualization_dir)
    
    def analyze_all_factors(self):
        """分析所有影响因子"""
        print("开始分析所有影响因子...")
        
        # 读取所有数据
        self.data_processor.read_all_data()
        
        # 准备数据
        X, y = self._prepare_data()
        
        # 标准化数据
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 训练多元回归模型
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        # 计算各个因子的影响程度
        self._calculate_impact_factors(X.columns, model.coef_, scaler.scale_)
        
        # 计算各个因子的变化幅度
        self._calculate_factor_changes()
        
        # 生成可视化
        self._generate_visualizations()
        
        print("影响因子分析完成")
        return self.impact_factors
    
    def _prepare_data(self):
        """准备用于分析的数据"""
        # 获取月度汇总数据
        summary_data = self.data_processor.get_monthly_summary_data()
        
        # 获取销售数据
        sales_data = self.data_processor.get_sales_data()
        
        # 获取硅片成本数据
        silicon_cost_data = self.data_processor.get_silicon_cost_data()
        
        # 准备特征矩阵
        features = []
        target = []
        
        # 只使用1-8月的数据
        for month in range(1, 9):
            feature_row = []
            
            # 添加成本相关特征
            feature_row.extend([
                summary_data['生产变动成本'][month-1],
                summary_data['生产公共成本'][month-1],
                summary_data['人工成本'][month-1],
                summary_data['折旧'][month-1],
                summary_data['营业税费'][month-1],
                summary_data['销售费用'][month-1],
                summary_data['管理费用'][month-1],
                summary_data['财务费用'][month-1]
            ])
            
            # 添加各类型硅片的成本单价、销售单价和销量
            for silicon_type in ['N1', 'N2', 'N3', 'P']:
                # 成本单价
                feature_row.append(silicon_cost_data[month][silicon_type])
                
                # 销售单价
                feature_row.append(sales_data[month]['price'][silicon_type])
                
                # 销量
                feature_row.append(sales_data[month]['demand'][silicon_type])
            
            features.append(feature_row)
            target.append(summary_data['销售利润'][month-1])
        
        return pd.DataFrame(features, columns=[
            '生产变动成本', '生产公共成本', '人工成本', '折旧', '营业税费', 
            '销售费用', '管理费用', '财务费用',
            'N1成本单价', 'N1销售单价', 'N1销量',
            'N2成本单价', 'N2销售单价', 'N2销量',
            'N3成本单价', 'N3销售单价', 'N3销量',
            'P成本单价', 'P销售单价', 'P销量'
        ]), np.array(target)
    
    def _calculate_impact_factors(self, feature_names, coefficients, scales):
        """计算各个因子的影响程度"""
        # 计算标准化后的影响系数
        impact_coefficients = coefficients * scales
        
        # 归一化影响系数 (将系数映射到0-1范围)
        min_coef = np.min(impact_coefficients)
        max_coef = np.max(impact_coefficients)
        range_coef = max_coef - min_coef
        
        if range_coef > 0:
            normalized_coefficients = (impact_coefficients - min_coef) / range_coef
        else:
            normalized_coefficients = np.zeros_like(impact_coefficients)
        
        # 计算每个因子的相对影响程度
        total_impact = np.sum(np.abs(impact_coefficients))
        relative_impacts = np.abs(impact_coefficients) / total_impact * 100
        
        # 保存影响因子结果
        self.impact_factors['影响程度'] = {
            name: {
                '绝对影响系数': float(coef),
                '归一化影响系数': float(norm_coef),
                '相对影响程度': float(rel_impact)
            }
            for name, coef, norm_coef, rel_impact in zip(feature_names, impact_coefficients, normalized_coefficients, relative_impacts)
        }
    
    def _calculate_factor_changes(self):
        """计算各个因子的变化幅度"""
        # 获取月度汇总数据
        summary_data = self.data_processor.get_monthly_summary_data()
        
        # 获取销售数据
        sales_data = self.data_processor.get_sales_data()
        
        # 获取硅片成本数据
        silicon_cost_data = self.data_processor.get_silicon_cost_data()
        
        # 计算各个因子的变化幅度
        changes = {}
        
        # 计算成本相关因子的变化
        cost_factors = [
            '生产变动成本', '生产公共成本', '人工成本', '折旧', 
            '营业税费', '销售费用', '管理费用', '财务费用'
        ]
        
        for factor in cost_factors:
            values = [v for v in summary_data[factor] if v is not None]
            if len(values) >= 2:
                changes[factor] = {
                    '总变化率': float((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
                    '月均变化率': float(np.mean(np.diff(values)) / values[0] * 100) if values[0] != 0 else 0,
                    '最大变化率': float(np.max(np.abs(np.diff(values))) / values[0] * 100) if values[0] != 0 else 0
                }
            else:
                changes[factor] = {
                    '总变化率': 0,
                    '月均变化率': 0,
                    '最大变化率': 0
                }
        
        # 计算各类型硅片的成本单价、销售单价和销量的变化
        for silicon_type in ['N1', 'N2', 'N3', 'P']:
            # 成本单价变化
            costs = [data[silicon_type] for data in silicon_cost_data.values() if data[silicon_type] is not None]
            if len(costs) >= 2:
                changes[f'{silicon_type}成本单价'] = {
                    '总变化率': float((costs[-1] - costs[0]) / costs[0] * 100) if costs[0] != 0 else 0,
                    '月均变化率': float(np.mean(np.diff(costs)) / costs[0] * 100) if costs[0] != 0 else 0,
                    '最大变化率': float(np.max(np.abs(np.diff(costs))) / costs[0] * 100) if costs[0] != 0 else 0
                }
            else:
                changes[f'{silicon_type}成本单价'] = {
                    '总变化率': 0,
                    '月均变化率': 0,
                    '最大变化率': 0
                }
            
            # 销售单价变化
            prices = [data['price'][silicon_type] for data in sales_data.values() if data['price'][silicon_type] is not None]
            if len(prices) >= 2:
                changes[f'{silicon_type}销售单价'] = {
                    '总变化率': float((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0,
                    '月均变化率': float(np.mean(np.diff(prices)) / prices[0] * 100) if prices[0] != 0 else 0,
                    '最大变化率': float(np.max(np.abs(np.diff(prices))) / prices[0] * 100) if prices[0] != 0 else 0
                }
            else:
                changes[f'{silicon_type}销售单价'] = {
                    '总变化率': 0,
                    '月均变化率': 0,
                    '最大变化率': 0
                }
            
            # 销量变化
            demands = [data['demand'][silicon_type] for data in sales_data.values() if data['demand'][silicon_type] is not None]
            if len(demands) >= 2:
                changes[f'{silicon_type}销量'] = {
                    '总变化率': float((demands[-1] - demands[0]) / demands[0] * 100) if demands[0] != 0 else 0,
                    '月均变化率': float(np.mean(np.diff(demands)) / demands[0] * 100) if demands[0] != 0 else 0,
                    '最大变化率': float(np.max(np.abs(np.diff(demands))) / demands[0] * 100) if demands[0] != 0 else 0
                }
            else:
                changes[f'{silicon_type}销量'] = {
                    '总变化率': 0,
                    '月均变化率': 0,
                    '最大变化率': 0
                }
        
        self.impact_factors['变化幅度'] = changes
    
    def _generate_visualizations(self):
        """生成可视化图表"""
        print("生成可视化图表...")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 1. 影响程度条形图
        self._plot_impact_degrees()
        
        # 2. 变化幅度热力图
        self._plot_change_heatmap()
        
        # 3. 归一化影响系数雷达图
        self._plot_normalized_impact_radar()
        
        # 4. 主要影响因子变化趋势图
        self._plot_main_factors_trend()
        
        # 5. 影响因子相关性热力图
        self._plot_correlation_heatmap()
        
        # 6. 影响因子贡献饼图
        self._plot_impact_pie_chart()
        
        # 7. 主要因子与销售利润的关系图
        self._plot_profit_correlation()
        
        # 8. 综合影响因子雷达图
        self._plot_comprehensive_radar()
        
        print("可视化图表生成完成")
    
    def _plot_impact_degrees(self):
        """绘制影响程度条形图"""
        impact_degrees = self.impact_factors['影响程度']
        
        # 准备数据
        factors = list(impact_degrees.keys())
        degrees = [impact_degrees[factor]['相对影响程度'] for factor in factors]
        
        # 按影响程度排序
        sorted_indices = np.argsort(degrees)[::-1]
        sorted_factors = [factors[i] for i in sorted_indices]
        sorted_degrees = [degrees[i] for i in sorted_indices]
        
        # 只显示前10个因子
        top_n = min(10, len(sorted_factors))
        top_factors = sorted_factors[:top_n]
        top_degrees = sorted_degrees[:top_n]
        
        # 创建图表
        plt.figure(figsize=(12, 8))
        bars = plt.bar(top_factors, top_degrees, color='skyblue')
        
        # 设置图表属性
        plt.title('各因子对销售净利润的相对影响程度 (前10名)', fontsize=16)
        plt.xlabel('影响因子', fontsize=14)
        plt.ylabel('相对影响程度 (%)', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}%',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'impact_degrees.png'), dpi=300)
        plt.close()
    
    def _plot_change_heatmap(self):
        """绘制变化幅度热力图"""
        changes = self.impact_factors['变化幅度']
        
        # 准备数据
        factors = list(changes.keys())
        change_types = ['总变化率', '月均变化率', '最大变化率']
        
        # 创建数据矩阵
        data = np.zeros((len(factors), len(change_types)))
        for i, factor in enumerate(factors):
            for j, change_type in enumerate(change_types):
                data[i, j] = changes[factor][change_type]
        
        # 创建热力图
        plt.figure(figsize=(12, len(factors) * 0.4))
        sns.heatmap(data, annot=True, fmt='.2f', cmap='RdYlBu_r',
                   xticklabels=change_types, yticklabels=factors)
        
        plt.title('各因子变化幅度热力图', fontsize=16)
        plt.xlabel('变化类型', fontsize=14)
        plt.ylabel('影响因子', fontsize=14)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'change_heatmap.png'), dpi=300)
        plt.close()
    
    def _plot_normalized_impact_radar(self):
        """绘制归一化影响系数雷达图"""
        impact_degrees = self.impact_factors['影响程度']
        
        # 准备数据
        factors = list(impact_degrees.keys())
        normalized_coefficients = [impact_degrees[factor]['归一化影响系数'] for factor in factors]
        
        # 按归一化影响系数排序
        sorted_indices = np.argsort(normalized_coefficients)[::-1]
        sorted_factors = [factors[i] for i in sorted_indices]
        sorted_coefficients = [normalized_coefficients[i] for i in sorted_indices]
        
        # 只显示前8个因子
        top_n = min(8, len(sorted_factors))
        top_factors = sorted_factors[:top_n]
        top_coefficients = sorted_coefficients[:top_n]
        
        # 创建雷达图
        angles = np.linspace(0, 2*np.pi, top_n, endpoint=False)
        angles = np.concatenate((angles, [angles[0]]))  # 闭合雷达图
        top_coefficients = np.concatenate((top_coefficients, [top_coefficients[0]]))  # 闭合雷达图
        
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, top_coefficients, 'o-', linewidth=2)
        ax.fill(angles, top_coefficients, alpha=0.25)
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(top_factors, fontsize=10)
        
        # 设置标题
        plt.title('主要影响因子归一化雷达图', fontsize=16)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'normalized_impact_radar.png'), dpi=300)
        plt.close()
    
    def _plot_main_factors_trend(self):
        """绘制主要影响因子的变化趋势图"""
        # 获取月度汇总数据
        summary_data = self.data_processor.get_monthly_summary_data()
        
        # 获取销售数据
        sales_data = self.data_processor.get_sales_data()
        
        # 获取硅片成本数据
        silicon_cost_data = self.data_processor.get_silicon_cost_data()
        
        # 找出主要影响因子
        sorted_impacts = sorted(
            self.impact_factors['影响程度'].items(),
            key=lambda x: x[1]['相对影响程度'],
            reverse=True
        )
        main_factors = sorted_impacts[:3]
        
        # 准备数据
        months = list(range(1, 9))  # 1-8月
        factor_values = {}
        
        for factor, _ in main_factors:
            if factor == '生产变动成本':
                values = [summary_data['生产变动成本'][i] for i in range(8)]
            elif factor == 'N2销量':
                values = [sales_data[month]['demand']['N2'] for month in months]
            elif factor == 'P销量':
                values = [sales_data[month]['demand']['P'] for month in months]
            elif factor == 'N1销量':
                values = [sales_data[month]['demand']['N1'] for month in months]
            elif factor == '生产公共成本':
                values = [summary_data['生产公共成本'][i] for i in range(8)]
            elif factor == 'N3销量':
                values = [sales_data[month]['demand']['N3'] for month in months]
            elif factor == '人工成本':
                values = [summary_data['人工成本'][i] for i in range(8)]
            elif factor == '管理费用':
                values = [summary_data['管理费用'][i] for i in range(8)]
            elif factor == '销售费用':
                values = [summary_data['销售费用'][i] for i in range(8)]
            elif factor == 'N1成本单价':
                values = [silicon_cost_data[month]['N1'] for month in months]
            elif factor == 'N2成本单价':
                values = [silicon_cost_data[month]['N2'] for month in months]
            elif factor == 'N3成本单价':
                values = [silicon_cost_data[month]['N3'] for month in months]
            elif factor == 'P成本单价':
                values = [silicon_cost_data[month]['P'] for month in months]
            elif factor == 'N2销售单价':
                values = [sales_data[month]['price']['N2'] for month in months]
            elif factor == 'N1销售单价':
                values = [sales_data[month]['price']['N1'] for month in months]
            elif factor == 'N3销售单价':
                values = [sales_data[month]['price']['N3'] for month in months]
            elif factor == 'P销售单价':
                values = [sales_data[month]['price']['P'] for month in months]
            else:
                continue
            
            # 归一化数据
            min_val = min(values)
            max_val = max(values)
            if max_val > min_val:
                normalized_values = [(v - min_val) / (max_val - min_val) for v in values]
            else:
                normalized_values = [0.5 for _ in values]
            
            factor_values[factor] = normalized_values
        
        # 创建趋势图
        plt.figure(figsize=(12, 8))
        
        for factor, values in factor_values.items():
            plt.plot(months, values, marker='o', linewidth=2, label=factor)
        
        plt.title('主要影响因子变化趋势 (归一化)', fontsize=16)
        plt.xlabel('月份', fontsize=14)
        plt.ylabel('归一化值', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(loc='best')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'main_factors_trend.png'), dpi=300)
        plt.close()
    
    def _plot_correlation_heatmap(self):
        """绘制影响因子相关性热力图"""
        # 获取月度汇总数据
        summary_data = self.data_processor.get_monthly_summary_data()
        
        # 获取销售数据
        sales_data = self.data_processor.get_sales_data()
        
        # 获取硅片成本数据
        silicon_cost_data = self.data_processor.get_silicon_cost_data()
        
        # 准备数据
        months = list(range(1, 9))  # 1-8月
        
        # 创建数据框
        data = {}
        
        # 添加成本相关特征
        cost_factors = [
            '生产变动成本', '生产公共成本', '人工成本', '折旧', 
            '营业税费', '销售费用', '管理费用', '财务费用'
        ]
        
        for factor in cost_factors:
            data[factor] = [summary_data[factor][i] for i in range(8)]
        
        # 添加各类型硅片的成本单价、销售单价和销量
        for silicon_type in ['N1', 'N2', 'N3', 'P']:
            # 成本单价
            data[f'{silicon_type}成本单价'] = [silicon_cost_data[month][silicon_type] for month in months]
            
            # 销售单价
            data[f'{silicon_type}销售单价'] = [sales_data[month]['price'][silicon_type] for month in months]
            
            # 销量
            data[f'{silicon_type}销量'] = [sales_data[month]['demand'][silicon_type] for month in months]
        
        # 添加销售利润
        data['销售利润'] = [summary_data['销售利润'][i] for i in range(8)]
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 计算相关性
        corr = df.corr()
        
        # 创建热力图
        plt.figure(figsize=(16, 14))
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', linewidths=0.5)
        
        plt.title('影响因子相关性热力图', fontsize=16)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'correlation_heatmap.png'), dpi=300)
        plt.close()
    
    def _plot_impact_pie_chart(self):
        """绘制影响因子贡献饼图"""
        impact_degrees = self.impact_factors['影响程度']
        
        # 准备数据
        factors = list(impact_degrees.keys())
        degrees = [impact_degrees[factor]['相对影响程度'] for factor in factors]
        
        # 按影响程度排序
        sorted_indices = np.argsort(degrees)[::-1]
        sorted_factors = [factors[i] for i in sorted_indices]
        sorted_degrees = [degrees[i] for i in sorted_indices]
        
        # 分离大于5%和小于5%的因子
        major_factors = []
        major_degrees = []
        other_degrees_sum = 0
        
        for factor, degree in zip(sorted_factors, sorted_degrees):
            if degree >= 5.0:  # 大于等于5%的因子单独显示
                major_factors.append(factor)
                major_degrees.append(degree)
            else:  # 小于5%的因子归类为其他
                other_degrees_sum += degree
        
        # 如果有小于5%的因子，添加到"其他"类别
        if other_degrees_sum > 0:
            major_factors.append('其他因子')
            major_degrees.append(other_degrees_sum)
        
        # 设置颜色方案
        colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC', '#99CCFF', '#FFB366', '#CC99FF']
        
        # 创建饼图
        plt.figure(figsize=(12, 10))
        wedges, texts, autotexts = plt.pie(major_degrees, 
                                          labels=major_factors,
                                          autopct='%1.1f%%',
                                          startangle=90,
                                          colors=colors[:len(major_factors)],
                                          shadow=True,
                                          explode=[0.05] * len(major_factors))
        
        # 设置标签样式
        plt.setp(autotexts, size=9, weight="bold")
        plt.setp(texts, size=10)
        
        # 添加标题
        plt.title('影响因子贡献饼图', fontsize=16, pad=20)
        
        # 添加图例
        plt.legend(wedges, major_factors,
                  title="影响因子",
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'impact_pie_chart.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_comprehensive_radar(self):
        """绘制综合影响因子雷达图"""
        impact_degrees = self.impact_factors['影响程度']
        
        # 准备数据
        factors = list(impact_degrees.keys())
        degrees = [impact_degrees[factor]['相对影响程度'] for factor in factors]
        
        # 按影响程度排序
        sorted_indices = np.argsort(degrees)[::-1]
        sorted_factors = [factors[i] for i in sorted_indices]
        sorted_degrees = [degrees[i] for i in sorted_indices]
        
        # 创建雷达图
        angles = np.linspace(0, 2*np.pi, len(factors), endpoint=False)
        angles = np.concatenate((angles, [angles[0]]))  # 闭合雷达图
        values = np.concatenate((sorted_degrees, [sorted_degrees[0]]))  # 闭合雷达图
        
        # 创建图表
        fig = plt.figure(figsize=(15, 15))
        ax = fig.add_subplot(111, polar=True)
        
        # 绘制雷达图
        ax.plot(angles, values, 'o-', linewidth=2, label='影响程度')
        ax.fill(angles, values, alpha=0.25)
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(sorted_factors, fontsize=10)
        
        # 设置标题
        plt.title('影响因子综合雷达图', fontsize=16, pad=20)
        
        # 添加图例
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'comprehensive_radar.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_profit_correlation(self):
        """绘制主要因子与销售利润的关系图"""
        # 获取月度汇总数据
        summary_data = self.data_processor.get_monthly_summary_data()
        
        # 获取销售数据
        sales_data = self.data_processor.get_sales_data()
        
        # 获取硅片成本数据
        silicon_cost_data = self.data_processor.get_silicon_cost_data()
        
        # 找出主要影响因子
        sorted_impacts = sorted(
            self.impact_factors['影响程度'].items(),
            key=lambda x: x[1]['相对影响程度'],
            reverse=True
        )
        main_factors = sorted_impacts[:3]
        
        # 准备数据
        months = list(range(1, 9))  # 1-8月
        profit = [summary_data['销售利润'][i] for i in range(8)]
        
        # 创建子图
        fig, axes = plt.subplots(1, len(main_factors), figsize=(18, 6))
        
        for i, (factor, _) in enumerate(main_factors):
            if factor == '生产变动成本':
                values = [summary_data['生产变动成本'][i] for i in range(8)]
            elif factor == 'N2销量':
                values = [sales_data[month]['demand']['N2'] for month in months]
            elif factor == 'P销量':
                values = [sales_data[month]['demand']['P'] for month in months]
            elif factor == 'N1销量':
                values = [sales_data[month]['demand']['N1'] for month in months]
            elif factor == '生产公共成本':
                values = [summary_data['生产公共成本'][i] for i in range(8)]
            elif factor == 'N3销量':
                values = [sales_data[month]['demand']['N3'] for month in months]
            elif factor == '人工成本':
                values = [summary_data['人工成本'][i] for i in range(8)]
            elif factor == '管理费用':
                values = [summary_data['管理费用'][i] for i in range(8)]
            elif factor == '销售费用':
                values = [summary_data['销售费用'][i] for i in range(8)]
            elif factor == 'N1成本单价':
                values = [silicon_cost_data[month]['N1'] for month in months]
            elif factor == 'N2成本单价':
                values = [silicon_cost_data[month]['N2'] for month in months]
            elif factor == 'N3成本单价':
                values = [silicon_cost_data[month]['N3'] for month in months]
            elif factor == 'P成本单价':
                values = [silicon_cost_data[month]['P'] for month in months]
            elif factor == 'N2销售单价':
                values = [sales_data[month]['price']['N2'] for month in months]
            elif factor == 'N1销售单价':
                values = [sales_data[month]['price']['N1'] for month in months]
            elif factor == 'N3销售单价':
                values = [sales_data[month]['price']['N3'] for month in months]
            elif factor == 'P销售单价':
                values = [sales_data[month]['price']['P'] for month in months]
            else:
                continue
            
            # 计算相关系数
            corr = np.corrcoef(values, profit)[0, 1]
            
            # 绘制散点图
            axes[i].scatter(values, profit, alpha=0.7)
            
            # 添加趋势线
            z = np.polyfit(values, profit, 1)
            p = np.poly1d(z)
            axes[i].plot(values, p(values), "r--", alpha=0.8)
            
            # 设置标题和标签
            axes[i].set_title(f'{factor} vs 销售利润\n相关系数: {corr:.2f}', fontsize=14)
            axes[i].set_xlabel(factor, fontsize=12)
            axes[i].set_ylabel('销售利润', fontsize=12)
            axes[i].grid(True, linestyle='--', alpha=0.7)
        
        plt.suptitle('主要影响因子与销售利润的关系', fontsize=16)
        plt.tight_layout()
        plt.savefig(os.path.join(self.visualization_dir, 'profit_correlation.png'), dpi=300)
        plt.close()

if __name__ == "__main__":
    # 测试代码
    analyzer = ImpactFactorAnalyzer("Problem A.xlsx")
    impact_factors = analyzer.analyze_all_factors()
    
    # 打印分析结果
    print("\n影响因子分析结果：")
    print("\n1. 影响程度：")
    for factor, impact in impact_factors['影响程度'].items():
        print(f"{factor}:")
        print(f"  绝对影响系数: {impact['绝对影响系数']:.4f}")
        print(f"  归一化影响系数: {impact['归一化影响系数']:.4f}")
        print(f"  相对影响程度: {impact['相对影响程度']:.2f}%")
    
    print("\n2. 变化幅度：")
    for factor, changes in impact_factors['变化幅度'].items():
        print(f"{factor}:")
        for change_type, value in changes.items():
            print(f"  {change_type}: {value:.2f}%") 