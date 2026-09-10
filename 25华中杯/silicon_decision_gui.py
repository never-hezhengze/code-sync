import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QComboBox, QTabWidget, QTextEdit, QMessageBox,
                            QFrame, QGridLayout, QScrollArea, QFileDialog,
                            QProgressDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from silicon_decision_assistant import SiliconDecisionAssistant
import json
from datetime import datetime
import requests
from openai import OpenAI
from scipy.optimize import minimize

# 硅基流动API配置
SILICON_API_URL = "https://api.siliconflow.com/v1/chat/completions"
SILICON_MODEL = "Pro/deepseek-ai/DeepSeek-V3"

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }
            QPushButton:pressed {
                background-color: #0D47A1;
                transform: translateY(1px);
            }
        """)

class ModernLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                color: #333333;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
                background-color: #F5F5F5;
            }
            QLineEdit:hover {
                border: 2px solid #BDBDBD;
            }
        """)

class ModernLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
        """)

class ModernComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                color: #333333;
                min-height: 20px;
            }
            QComboBox:focus {
                border: 2px solid #2196F3;
                background-color: #F5F5F5;
            }
            QComboBox:hover {
                border: 2px solid #BDBDBD;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)

class ModernTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTextEdit {
                padding: 12px;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                color: #333333;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border: 2px solid #2196F3;
                background-color: #F5F5F5;
            }
            QTextEdit:hover {
                border: 2px solid #BDBDBD;
            }
        """)

class SiliconDecisionGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.assistant = None
        self.api_key = None
        self.load_api_key()
        self.initUI()
        
    def load_api_key(self):
        """从配置文件加载API密钥"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('silicon_api_key')
            else:
                # 如果配置文件不存在，创建默认配置
                self.api_key = "sk-bhsrkzmwdwhofhyroanaandfsohbqvrgfvtfnzhxmloaiwbn"
                config = {'silicon_api_key': self.api_key}
                with open('config.json', 'w') as f:
                    json.dump(config, f)
                
            if not self.api_key:
                raise ValueError("API密钥未设置")
            
        except Exception as e:
            print(f"加载API密钥失败: {str(e)}")
            # 使用默认API密钥
            self.api_key = "sk-bhsrkzmwdwhofhyroanaandfsohbqvrgfvtfnzhxmloaiwbn"
            
    def initUI(self):
        self.setWindowTitle('硅片销售决策辅助系统')
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QTabWidget::pane {
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #E0E0E0;
                color: #333333;
                padding: 10px 20px;
                margin: 5px;
                border-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #BDBDBD;
            }
            QProgressDialog {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
            }
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # 创建标题
        title = QLabel('硅片销售决策辅助系统')
        title.setStyleSheet("""
            QLabel {
                color: #1976D2;
                font-size: 28px;
                font-weight: bold;
                padding: 20px;
                background: linear-gradient(to right, #2196F3, #1976D2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 创建加载数据按钮
        load_data_btn = ModernButton('加载数据')
        load_data_btn.clicked.connect(self.load_data)
        layout.addWidget(load_data_btn)
        
        # 创建选项卡窗口
        self.tabs = QTabWidget()
        
        # 添加各个选项卡
        self.tabs.addTab(self.createOptimizationTab(), "优化分析")
        self.tabs.addTab(self.createVisualizationTab(), "数据可视化")
        self.tabs.addTab(self.createHistoryTab(), "历史记录")
        self.tabs.addTab(self.createSettingsTab(), "系统设置")
        
        layout.addWidget(self.tabs)
        
        # 设置窗口大小和位置
        self.setMinimumSize(1200, 800)
        self.center()
        
    def center(self):
        """将窗口居中显示"""
        frame = self.frameGeometry()
        screen = self.screen().availableGeometry().center()
        frame.moveCenter(screen)
        self.move(frame.topLeft())
        
    def createOptimizationTab(self):
        """创建优化分析选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 创建输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border: 2px solid #E0E0E0;
            }
        """)
        input_layout = QGridLayout()
        
        # 添加单位变动成本输入框
        costs = ['A', 'B', 'C', 'D']
        for i, cost in enumerate(costs):
            label = ModernLabel(f'硅片{cost}单位变动成本 (元):')
            input_field = ModernLineEdit()
            input_field.setObjectName(f'硅片{cost}单位变动成本')
            input_layout.addWidget(label, i, 0)
            input_layout.addWidget(input_field, i, 1)
            
        input_frame.setLayout(input_layout)
        layout.addWidget(input_frame)
        
        # 添加优化按钮
        optimize_btn = ModernButton('开始优化')
        optimize_btn.clicked.connect(self.run_optimization)
        layout.addWidget(optimize_btn)
        
        # 添加结果显示区域
        result_text = ModernTextEdit()
        result_text.setObjectName('optimization_result')
        result_text.setReadOnly(True)
        layout.addWidget(result_text)
        
        tab.setLayout(layout)
        return tab
        
    def createVisualizationTab(self):
        """创建数据可视化选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 创建图表显示区域
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 添加图表类型选择
        chart_type = ModernComboBox()
        chart_type.setObjectName('chart_type')
        chart_type.addItems(['价格-销量关系', '利润分析', '成本构成'])
        chart_type.currentTextChanged.connect(self.update_chart)
        layout.addWidget(chart_type)
        
        tab.setLayout(layout)
        return tab
        
    def createHistoryTab(self):
        """创建历史记录选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 创建历史记录列表
        history_list = QTextEdit()
        history_list.setObjectName('history_list')
        history_list.setReadOnly(True)
        layout.addWidget(history_list)
        
        # 添加加载历史记录按钮
        load_btn = ModernButton('加载历史记录')
        load_btn.clicked.connect(self.load_history)
        layout.addWidget(load_btn)
        
        tab.setLayout(layout)
        return tab
        
    def createSettingsTab(self):
        """创建系统设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 添加API密钥设置
        api_frame = QFrame()
        api_layout = QHBoxLayout()
        api_label = ModernLabel('硅基流动API密钥:')
        api_input = ModernLineEdit()
        api_input.setObjectName('api_key_input')
        api_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self.api_key:
            api_input.setText(self.api_key)
        api_layout.addWidget(api_label)
        api_layout.addWidget(api_input)
        api_frame.setLayout(api_layout)
        layout.addWidget(api_frame)
        
        # 添加保存设置按钮
        save_btn = ModernButton('保存设置')
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        tab.setLayout(layout)
        return tab
        
    def load_data(self):
        """异步加载数据"""
        try:
            # 禁用加载按钮
            load_btn = self.findChild(QPushButton, 'load_data_btn')
            if load_btn:
                load_btn.setEnabled(False)
                load_btn.setText('正在加载数据...')
            
            # 创建进度对话框
            progress = QProgressDialog("正在加载数据...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            
            # 初始化助手
            self.assistant = SiliconDecisionAssistant()
            
            # 加载数据
            progress.setLabelText("正在读取数据...")
            progress.setValue(10)
            self.assistant.load_data('Problem A.xlsx')
            
            # 确定约束范围
            progress.setLabelText("正在确定约束范围...")
            progress.setValue(30)
            self.assistant.determine_constraints()
            
            # 归一化数据
            progress.setLabelText("正在归一化数据...")
            progress.setValue(50)
            self.assistant._normalize_data()
            
            # 拟合价格-销量关系
            progress.setLabelText("正在拟合价格-销量关系...")
            progress.setValue(70)
            self.assistant.fit_price_volume_relation()
            
            progress.setValue(100)
            
            # 启用所有选项卡
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, True)
                
            # 恢复加载按钮
            if load_btn:
                load_btn.setEnabled(True)
                load_btn.setText('数据已加载')
                
            QMessageBox.information(self, '成功', '数据加载完成！')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'数据加载失败：{str(e)}')
            # 恢复加载按钮
            load_btn = self.findChild(QPushButton, 'load_data_btn')
            if load_btn:
                load_btn.setEnabled(True)
                load_btn.setText('加载数据')
                
    def run_optimization(self):
        """运行优化分析"""
        if not self.assistant:
            QMessageBox.warning(self, '警告', '请先加载数据！')
            return
            
        try:
            # 获取输入的单位变动成本
            unit_costs = {}
            for product in ['A', 'B', 'C', 'D']:
                input_field = self.findChild(QLineEdit, f'硅片{product}单位变动成本')
                if not input_field:
                    raise ValueError(f"找不到硅片{product}单位变动成本输入框")
                cost = float(input_field.text())
                unit_costs[f'硅片{product}单位变动成本'] = cost * 10000
                
            # 创建进度对话框
            progress = QProgressDialog("正在优化...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            
            # 运行优化
            progress.setLabelText("正在初始化优化参数...")
            progress.setValue(10)
            
            # 初始化价格边界
            price_bounds = []
            for product in ['A', 'B', 'C', 'D']:
                price_bounds.append((
                    self.assistant.constraints[f'硅片{product}售价']['min'],
                    self.assistant.constraints[f'硅片{product}售价']['max']
                ))
            price_bounds = tuple(price_bounds)
            
            progress.setLabelText("正在定义目标函数...")
            progress.setValue(20)
            
            # 定义目标函数
            def objective(prices):
                price_dict = {
                    '硅片A售价': prices[0],
                    '硅片B售价': prices[1],
                    '硅片C售价': prices[2],
                    '硅片D售价': prices[3]
                }
                return -self.assistant.calculate_profit(price_dict, unit_costs)
            
            progress.setLabelText("正在设置初始值...")
            progress.setValue(30)
            
            # 设置初始值
            initial_prices = []
            for product in ['A', 'B', 'C', 'D']:
                min_price = self.assistant.constraints[f'硅片{product}售价']['min']
                max_price = self.assistant.constraints[f'硅片{product}售价']['max']
                initial_prices.append((min_price + max_price) / 2)
            
            progress.setLabelText("正在运行优化算法...")
            progress.setValue(40)
            
            # 运行优化
            result = minimize(
                objective,
                initial_prices,
                method='SLSQP',
                bounds=price_bounds,
                options={'maxiter': 100, 'ftol': 1e-6}
            )
            
            progress.setValue(60)
            
            # 处理优化结果
            if result.success:
                progress.setLabelText("正在计算最优解...")
                progress.setValue(70)
                
                # 计算最优价格、销量和利润
                optimal_prices = {
                    '硅片A售价': result.x[0],
                    '硅片B售价': result.x[1],
                    '硅片C售价': result.x[2],
                    '硅片D售价': result.x[3]
                }
                
                optimal_volumes = {}
                for product in ['A', 'B', 'C', 'D']:
                    price = optimal_prices[f'硅片{product}售价']
                    model = self.assistant.price_volume_relations[f'硅片{product}']
                    volume = model['func'](price / 10000, *model['params'])
                    optimal_volumes[f'硅片{product}销量'] = volume
                
                optimal_profit = -result.fun
                
                result_dict = {
                    'success': True,
                    'message': result.message,
                    'prices': optimal_prices,
                    'volumes': optimal_volumes,
                    'profit': optimal_profit
                }
                
                progress.setValue(80)
                
                # 显示结果
                self.show_optimization_result(result_dict)
                
                progress.setLabelText("正在生成AI分析...")
                progress.setValue(90)
                
                # 生成AI分析
                if self.api_key:
                    self.generate_ai_analysis(result_dict, unit_costs)
                
                progress.setValue(100)
                
            else:
                QMessageBox.warning(self, '警告', f'优化未找到可行解：{result.message}')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'优化过程中出现错误：{str(e)}')
            
    def show_optimization_result(self, result):
        """显示优化结果"""
        if result['success']:
            # 更新结果显示
            result_text = self.findChild(QTextEdit, 'optimization_result')
            if not result_text:
                result_text = self.findChild(QTextEdit)
            result_text.clear()
            
            # 添加优化结果
            result_text.append("优化结果：\n")
            result_text.append(f"总销售净利润: {result['profit']/10000:.2f}元\n")
            
            for product in ['A', 'B', 'C', 'D']:
                result_text.append(f"\n硅片{product}：")
                result_text.append(f"  最优售价: {result['prices'][f'硅片{product}售价']/10000:.2f}元")
                result_text.append(f"  预计销量: {result['volumes'][f'硅片{product}销量']:.2f}片")
                
            # 更新图表
            self.update_chart()
            
        else:
            QMessageBox.warning(self, '警告', '优化未找到可行解')
            
    def generate_ai_analysis(self, result, unit_costs):
        """使用OpenAI库调用硅基流动API生成AI分析"""
        try:
            if not self.api_key:
                QMessageBox.warning(self, '警告', 'API密钥未设置，无法生成AI分析')
                return
            
            # 准备分析数据
            analysis_data = {
                "优化结果": {
                    "总销售净利润": f"{result['profit']/10000:.2f}元",
                    "各产品最优方案": {}
                }
            }
            
            for product in ['A', 'B', 'C', 'D']:
                product_name = f"硅片{product}"
                analysis_data["优化结果"]["各产品最优方案"][product_name] = {
                    "最优售价": f"{result['prices'][f'硅片{product}售价']/10000:.2f}元",
                    "预计销量": f"{result['volumes'][f'硅片{product}销量']:.2f}片",
                    "单位变动成本": f"{unit_costs[f'硅片{product}单位变动成本']/10000:.2f}元",
                    "预计利润": f"{(result['prices'][f'硅片{product}售价'] - unit_costs[f'硅片{product}单位变动成本']) * result['volumes'][f'硅片{product}销量']/10000:.2f}元"
                }
            
            # 计算利润率
            for product in ['A', 'B', 'C', 'D']:
                price = result['prices'][f'硅片{product}售价'] / 10000
                cost = unit_costs[f'硅片{product}单位变动成本'] / 10000
                profit_rate = (price - cost) / price * 100
                analysis_data["优化结果"]["各产品最优方案"][f"硅片{product}"]["利润率"] = f"{profit_rate:.2f}%"
            
            # 准备提示词
            prompt = f"""
            你是一位专业的硅片行业分析师和决策顾问。请根据以下数据，为一家硅片制造企业提供详细的决策分析和建议。
            
            数据：
            {json.dumps(analysis_data, ensure_ascii=False, indent=2)}
            
            请提供以下分析：
            1. 总体决策评估：分析当前定价策略的优缺点，以及是否能够最大化企业利润
            2. 各产品分析：针对每种硅片产品，分析其定价、销量和利润情况，以及可能的改进空间
            3. 市场策略建议：基于价格-销量关系，提供市场策略建议
            4. 风险分析：指出当前决策可能面临的风险和不确定性
            5. 实施建议：提供具体的实施步骤和注意事项
            
            请用专业但易懂的语言进行分析，并提供具体的数据支持。
            """
            
            # 创建进度对话框
            progress = QProgressDialog("正在生成AI分析...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            
            # 使用OpenAI库调用硅基流动API
            progress.setLabelText("正在连接API...")
            progress.setValue(20)
            
            try:
                client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.siliconflow.cn/v1"
                )
                
                progress.setLabelText("正在生成分析...")
                progress.setValue(50)
                
                # 使用流式响应
                response = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=[
                        {"role": "system", "content": "你是一位专业的硅片行业分析师和决策顾问，擅长数据分析和决策建议。"},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                
                # 获取分析结果
                analysis = ""
                result_text = self.findChild(QTextEdit, 'optimization_result')
                if result_text:
                    result_text.append("\n\nAI决策分析：\n")
                    result_text.append("-" * 20 + "\n")
                    
                    # 流式显示结果
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            analysis += content
                            result_text.insertPlainText(content)
                            result_text.ensureCursorVisible()
                            QApplication.processEvents()  # 保持UI响应
                        if chunk.choices[0].delta.reasoning_content:
                            content = chunk.choices[0].delta.reasoning_content
                            analysis += content
                            result_text.insertPlainText(content)
                            result_text.ensureCursorVisible()
                            QApplication.processEvents()  # 保持UI响应
                    
                progress.setValue(100)
                
            except Exception as api_error:
                QMessageBox.warning(self, '警告', f'AI分析生成失败：{str(api_error)}')
                # 显示默认分析结果
                result_text = self.findChild(QTextEdit, 'optimization_result')
                if result_text:
                    result_text.append("\n\nAI分析生成失败，显示默认分析：\n")
                    result_text.append("-" * 20 + "\n")
                    result_text.append("基于优化结果，建议：\n")
                    result_text.append("1. 关注各产品的利润率，特别是利润率较低的产品\n")
                    result_text.append("2. 考虑调整价格策略，平衡销量和利润\n")
                    result_text.append("3. 分析市场需求，优化产品组合\n")
                    result_text.append("4. 关注成本控制，提高整体盈利能力\n")
            
        except Exception as e:
            QMessageBox.warning(self, '警告', f'AI分析生成失败：{str(e)}')
            
    def update_chart(self):
        """更新图表显示"""
        self.figure.clear()
        
        # 根据选择的图表类型绘制不同的图表
        chart_type = self.findChild(QComboBox, 'chart_type')
        if not chart_type:
            chart_type = self.findChild(QComboBox)
            
        if chart_type:
            chart_type_text = chart_type.currentText()
            
            if chart_type_text == '价格-销量关系':
                self.plot_price_volume_relation()
            elif chart_type_text == '利润分析':
                self.plot_profit_analysis()
            elif chart_type_text == '成本构成':
                self.plot_cost_breakdown()
                
        self.canvas.draw()
        
    def plot_price_volume_relation(self):
        """绘制价格-销量关系图"""
        ax = self.figure.add_subplot(111)
        
        # 获取数据并绘制
        for product in ['A', 'B', 'C', 'D']:
            price_data = self.assistant.data[f'硅片{product}售价'].values / 10000
            volume_data = self.assistant.data[f'硅片{product}销量'].values
            
            ax.scatter(price_data, volume_data, label=f'硅片{product}')
            
        ax.set_xlabel('价格 (元)')
        ax.set_ylabel('销量')
        ax.set_title('价格-销量关系')
        ax.legend()
        ax.grid(True)
        
    def plot_profit_analysis(self):
        """绘制利润分析图"""
        ax = self.figure.add_subplot(111)
        
        # 获取数据并绘制
        products = ['A', 'B', 'C', 'D']
        profits = []
        
        for product in products:
            price = self.assistant.data[f'硅片{product}售价'].mean() / 10000
            cost = self.assistant.data[f'硅片{product}单位变动成本'].mean() / 10000
            volume = self.assistant.data[f'硅片{product}销量'].mean()
            profit = (price - cost) * volume
            profits.append(profit)
            
        ax.bar(products, profits)
        ax.set_xlabel('产品类型')
        ax.set_ylabel('利润 (万元)')
        ax.set_title('各产品利润分析')
        ax.grid(True)
        
    def plot_cost_breakdown(self):
        """绘制成本构成图"""
        ax = self.figure.add_subplot(111)
        
        # 获取数据并绘制
        costs = ['生产公共成本', '人工成本', '折旧', '营业税费']
        values = []
        
        for cost in costs:
            value = self.assistant.data[cost].mean()
            values.append(value)
            
        ax.pie(values, labels=costs, autopct='%1.1f%%')
        ax.set_title('成本构成分析')
        
    def load_history(self):
        """加载历史记录"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择历史记录文件",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                history_text = self.findChild(QTextEdit, 'history_list')
                if history_text:
                    history_text.setText(content)
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'加载历史记录失败：{str(e)}')
                
    def save_settings(self):
        """保存系统设置"""
        try:
            api_input = self.findChild(QLineEdit, 'api_key_input')
            if not api_input:
                raise ValueError("找不到API密钥输入框")
                
            api_key = api_input.text()
            self.api_key = api_key
            
            # 保存到配置文件
            config = {
                'silicon_api_key': api_key
            }
            
            with open('config.json', 'w') as f:
                json.dump(config, f)
                
            QMessageBox.information(self, '成功', '设置已保存')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存设置失败：{str(e)}')

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = SiliconDecisionGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 