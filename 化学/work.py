"""
平推流反应器（PFR）数值模拟GUI
AI工具：使用Deepseek和Claude进行代码框架设计
主要功能：根据用户输入的参数，模拟反应物A在PFR中的浓度分布
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib
import math

# 配置matplotlib支持中文显示
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class PFRSimulator:
    """平推流反应器模拟器"""
    
    def __init__(self):
        # 反应器参数（给定条件）
        self.C_A0 = 1.0  # 入口浓度 mol/L
        self.D = 1.0  # 反应器直径 dm
        self.V_total = 10.0  # 反应器总体积 L
        
        # 计算截面积 dm^2
        self.A = math.pi * (self.D / 2) ** 2
        
        # 计算反应器长度 dm
        self.L_total = self.V_total / self.A
        
    def pfr_ode(self, C_A, z, k, n, v):
        """
        PFR微分方程
        dC_A/dz = -r_A / u
        其中：
        - r_A = k * C_A^n (反应速率)
        - u = v / A (线性速度，v为体积流速L/s，A为截面积dm^2)
        
        参数：
        - C_A: 浓度 mol/L
        - z: 反应器管长 dm
        - k: 速率常数
        - n: 反应级数
        - v: 体积流量 L/s
        """
        # 线性速度 dm/s
        # 注意: 1 L = 1 dm^3, 所以 v(L/s) = v(dm^3/s)
        u = v / self.A  # dm/s = (dm^3/s) / (dm^2) = dm/s
        
        # 反应速率 mol/(L·s)
        if C_A <= 0:
            r_A = 0
        else:
            r_A = k * (C_A ** n)
        
        # 返回浓度对管长的导数
        dC_A_dz = -r_A / u
        
        return dC_A_dz
    
    def simulate(self, v, k, n, num_points=100):
        """
        进行PFR数值求解
        
        参数：
        - v: 体积流量 L/s
        - k: 速率常数
        - n: 反应级数
        - num_points: 计算点数
        
        返回：
        - L_array: 管长数组 dm
        - C_A_array: 浓度数组 mol/L
        - X_A: 出口转化率 %
        """
        try:
            # 验证输入
            if v <= 0 or k < 0:
                raise ValueError("体积流量和速率常数必须为正数")
            
            # 生成管长数组 dm
            L_array = np.linspace(0, self.L_total, num_points)
            
            # 初始条件
            C_A_initial = [self.C_A0]
            
            # 使用ODE求解器求解
            C_A_array = odeint(self.pfr_ode, C_A_initial, L_array, args=(k, n, v))
            C_A_array = C_A_array.flatten()
            
            # 确保浓度非负
            C_A_array = np.maximum(C_A_array, 0)
            
            # 计算出口转化率
            C_A_exit = C_A_array[-1]
            X_A = (1 - C_A_exit / self.C_A0) * 100
            X_A = max(0, min(100, X_A))  # 限制在0-100%
            
            return L_array, C_A_array, X_A
            
        except Exception as e:
            raise Exception(f"模拟计算出错: {str(e)}")


class PFRGUI:
    """PFR模型GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("平推流反应器（PFR）数值模拟")
        self.root.geometry("1000x700")
        
        self.simulator = PFRSimulator()
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ===== 左侧控制面板 =====
        control_frame = ttk.LabelFrame(main_frame, text="参数设置", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # 体积流量输入
        ttk.Label(control_frame, text="体积流量 v (L/s):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_v = ttk.Entry(control_frame, width=15)
        self.entry_v.insert(0, "0.5")
        self.entry_v.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 速率常数输入
        ttk.Label(control_frame, text="速率常数 k:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_k = ttk.Entry(control_frame, width=15)
        self.entry_k.insert(0, "0.1")
        self.entry_k.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 反应级数输入
        ttk.Label(control_frame, text="反应级数 n:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_n = ttk.Entry(control_frame, width=15)
        self.entry_n.insert(0, "1.0")
        self.entry_n.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 计算按钮
        self.btn_calculate = ttk.Button(control_frame, text="计算", command=self.calculate)
        self.btn_calculate.grid(row=3, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))
        
        # 出口转化率显示
        ttk.Label(control_frame, text="出口转化率:").grid(row=4, column=0, sticky=tk.W, pady=10)
        self.label_conversion = ttk.Label(control_frame, text="未计算", font=("Arial", 12, "bold"), foreground="blue")
        self.label_conversion.grid(row=4, column=1, sticky=tk.W, pady=10)
        
        # 信息标签
        info_text = (
            f"反应器参数（固定）:\n"
            f"• 入口浓度: {self.simulator.C_A0} mol/L\n"
            f"• 直径: {self.simulator.D} dm\n"
            f"• 总体积: {self.simulator.V_total} L\n"
            f"• 总长度: {self.simulator.L_total:.2f} dm\n"
            f"• 反应: A → 产物"
        )
        ttk.Label(control_frame, text=info_text, justify=tk.LEFT, foreground="gray").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # ===== 右侧图形区域 =====
        graph_frame = ttk.LabelFrame(main_frame, text="浓度分布曲线", padding="5")
        graph_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # 创建Figure对象
        self.fig = Figure(figsize=(6, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # 创建Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 初始化图表
        self.init_plot()

        # 设置可交互悬浮标注
        self.current_L = np.array([])
        self.current_CA = np.array([])
        self.line_plot = None
        self.annot = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->")
        )
        self.annot.set_visible(False)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("axes_leave_event", self.on_leave)
        
        # 配置行列权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
    
    def init_plot(self):
        """初始化图表"""
        self.ax.clear()
        self.ax.set_xlabel("管长 L (dm)", fontsize=11, fontproperties='SimHei')
        self.ax.set_ylabel("浓度 $C_A$ (mol/L)", fontsize=11, fontproperties='SimHei')
        self.ax.set_title("反应物A浓度分布", fontsize=12, fontweight='bold', fontproperties='SimHei')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, self.simulator.L_total)
        self.ax.set_ylim(0, 1.0)
        self.canvas.draw()
    
    def on_motion(self, event):
        """处理鼠标移动事件"""
        if event.inaxes != self.ax:
            self.annot.set_visible(False)
            self.canvas.draw_idle()
            return

        if self.current_L.size == 0:
            return

        x = event.xdata
        y = event.ydata
        if x is None or y is None:
            return

        # 找到最接近鼠标x坐标的曲线点
        idx = np.argmin(np.abs(self.current_L - x))
        x0 = float(self.current_L[idx])
        y0 = float(self.current_CA[idx])

        # 计算鼠标到该点的数据空间距离
        x_span = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
        y_span = self.ax.get_ylim()[1] - self.ax.get_ylim()[0]
        
        # 加权距离（y方向权重更大，因为浓度变化范围较小）
        dx_norm = (x - x0) / x_span if x_span > 0 else 0
        dy_norm = (y - y0) / y_span if y_span > 0 else 0
        dist = np.sqrt(dx_norm**2 + dy_norm**2)

        # 距离阈值较宽松，确保容易触发
        if dist <= 0.08:
            self.annot.xy = (x0, y0)
            text = f"L = {x0:.3f} dm\nC_A = {y0:.4f} mol/L"
            self.annot.set_text(text)
            self.annot.set_visible(True)
            self.canvas.draw_idle()
        else:
            self.annot.set_visible(False)

    def on_leave(self, event):
        """处理鼠标离开事件"""
        self.annot.set_visible(False)
        self.canvas.draw_idle()

    def calculate(self):
        """计算并绘制结果"""
        try:
            # 获取输入参数
            v = float(self.entry_v.get())
            k = float(self.entry_k.get())
            n = float(self.entry_n.get())
            
            # 验证参数合理性
            if v <= 0:
                messagebox.showerror("输入错误", "体积流量必须大于0")
                return
            if k < 0:
                messagebox.showerror("输入错误", "速率常数不能为负")
                return
            
            # 进行模拟计算
            L_array, C_A_array, X_A = self.simulator.simulate(v, k, n)
            self.current_L = L_array
            self.current_CA = C_A_array
            
            # 更新图表
            self.ax.clear()
            self.line_plot, = self.ax.plot(L_array, C_A_array, 'b-', linewidth=2.5, label='$C_A(L)$')
            self.ax.scatter(L_array[0], C_A_array[0], color='green', s=100, marker='o', 
                           label='入口', zorder=5)
            self.ax.scatter(L_array[-1], C_A_array[-1], color='red', s=100, marker='s', 
                           label='出口', zorder=5)
            
            self.ax.set_xlabel("管长 L (dm)", fontsize=11, fontproperties='SimHei')
            self.ax.set_ylabel("浓度 $C_A$ (mol/L)", fontsize=11, fontproperties='SimHei')
            self.ax.set_title(f"PFR浓度分布 (v={v} L/s, k={k}, n={n})", fontsize=12, fontweight='bold', fontproperties='SimHei')
            self.ax.grid(True, alpha=0.3)
            legend = self.ax.legend(loc='best')
            plt.setp(legend.get_texts(), fontproperties='SimHei')
            self.ax.set_xlim(0, self.simulator.L_total)
            self.ax.set_ylim(0, max(1.0, C_A_array[0] * 1.1))
            
            # 重新创建悬浮标注（因为ax.clear()会清除之前的annotate）
            self.annot = self.ax.annotate(
                "",
                xy=(0, 0),
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round", fc="w"),
                arrowprops=dict(arrowstyle="->")
            )
            self.annot.set_visible(False)
            
            self.canvas.draw()
            
            # 更新转化率显示
            self.label_conversion.config(text=f"{X_A:.2f}%", foreground="darkgreen")
            
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数值")
        except Exception as e:
            messagebox.showerror("计算错误", f"模拟过程出错：\n{str(e)}")


def main():
    """主程序入口"""
    root = tk.Tk()
    app = PFRGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
