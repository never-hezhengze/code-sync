"""数据加载模块 - 读取所有附件Excel数据"""
import numpy as np
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data')

def load_load_profile():
    """加载附件1：常规电负荷标幺功率曲线，返回24h实际功率(MW)"""
    df = pd.read_excel(os.path.join(DATA_DIR, '附件1：园区典型日常规电负荷标幺功率曲线.xlsx'))
    load_pu = df.iloc[:, 1].values.astype(float)
    return load_pu * 6.0  # 峰值6MW

def load_typical_wind_pv():
    """加载附件2：典型日风光标幺功率，返回(wind_MW, pv_MW)各24h"""
    df = pd.read_excel(os.path.join(DATA_DIR, '附件2：典型日风电、光伏标幺功率表.xlsx'))
    wind_pu = df.iloc[:, 1].values.astype(float)
    pv_pu = df.iloc[:, 2].values.astype(float)
    return wind_pu * 40.0, pv_pu * 64.0  # 风电40MW, 光伏64MW

def load_wind_scenarios():
    """加载附件3：6种风电场景标幺功率，返回shape=(6,24)的MW数组"""
    df = pd.read_excel(os.path.join(DATA_DIR, '附件3：园区6种场景的风电标幺功率表.xlsx'))
    scenarios = np.zeros((6, 24))
    for i in range(6):
        scenarios[i] = df.iloc[:, i+1].values.astype(float) * 40.0
    return scenarios

def load_pv_scenarios():
    """加载附件4：4种光伏场景标幺功率，返回shape=(4,24)的MW数组"""
    df = pd.read_excel(os.path.join(DATA_DIR, '附件4：园区4种场景的光伏标幺功率表.xlsx'))
    scenarios = np.zeros((4, 24))
    for i in range(4):
        scenarios[i] = df.iloc[:, i+1].values.astype(float) * 64.0
    return scenarios

def load_electricity_prices():
    """加载附件7-8：分时电价和上网电价，返回(buy_price[24], sell_price)"""
    # 分时购电电价 (元/kWh)
    # t=0对应0:00-1:00, t=23对应23:00-24:00
    buy_price = np.zeros(24)
    for t in range(24):
        if t in range(0, 7) or t == 23:  # 23:00-07:00 低谷
            buy_price[t] = 0.3424
        elif t in [7, 8, 9, 15, 16, 17, 21, 22]:  # 平时
            buy_price[t] = 0.6074
        else:  # 10-14, 18-20 高峰
            buy_price[t] = 0.8024
    
    sell_price = 0.3779  # 风电/光伏上网电价
    return buy_price, sell_price

def get_equipment_params(Q_capacity=36):
    """根据产能获取设备参数（线性缩放）"""
    scale = Q_capacity / 36.0
    return {
        'P_ALKEL_max': 10.0 * scale,   # MW
        'P_PEMEL_max': 10.0 * scale,   # MW
        'P_NH3_max': 0.75 * scale,     # MW
        'P_H2NH3_max': 20.75 * scale,  # MW (总功率)
        'r_H2_ALKEL': 140.0 * scale,   # kg/h
        'r_H2_PEMEL': 160.0 * scale,   # kg/h
        'r_NH3': 1.5 * scale,          # 吨/h
        'c_ALKEL': 0.10,               # 元/kWh 运维
        'c_PEMEL': 0.15,               # 元/kWh 运维
        'c_NH3': 0.002,                # 元/kWh 运维
        'c_wind': 0.15,                # 元/kWh 度电成本
        'c_pv': 0.12,                  # 元/kWh 度电成本
    }

def get_storage_params():
    """储能设备参数"""
    return {
        'eta_c': 0.90,          # 充电效率
        'eta_d': 0.90,          # 放电效率
        'sigma': 0.002,         # 自损耗率 /h
        'invest_cost': 1000,    # 元/kWh 投资成本
        'om_cost': 0.01,        # 元/kWh 运维
        'lifetime': 15,         # 年
    }

def get_all_scenarios():
    """生成24种风光组合场景，返回(wind_scenarios[24,24], pv_scenarios[24,24])
    场景编号: wind_i * 4 + pv_j (i=0..5, j=0..3)
    """
    wind_s = load_wind_scenarios()  # (6, 24)
    pv_s = load_pv_scenarios()      # (4, 24)
    
    wind_all = np.zeros((24, 24))  # (场景数, 时段数)
    pv_all = np.zeros((24, 24))
    
    idx = 0
    for i in range(6):
        for j in range(4):
            wind_all[idx] = wind_s[i]
            pv_all[idx] = pv_s[j]
            idx += 1
    
    return wind_all, pv_all

def get_scenario_labels():
    """返回24种场景的标签"""
    labels = []
    for i in range(6):
        for j in range(4):
            labels.append(f"W{i+1}P{j+1}")
    return labels


if __name__ == '__main__':
    # 数据验证
    P_load = load_load_profile()
    print(f"常规负荷: min={P_load.min():.2f}, max={P_load.max():.2f}, sum={P_load.sum():.2f} MWh")
    
    P_wind_typ, P_pv_typ = load_typical_wind_pv()
    print(f"典型风电: min={P_wind_typ.min():.2f}, max={P_wind_typ.max():.2f}, sum={P_wind_typ.sum():.2f} MWh")
    print(f"典型光伏: min={P_pv_typ.min():.2f}, max={P_pv_typ.max():.2f}, sum={P_pv_typ.sum():.2f} MWh")
    
    buy_price, sell_price = load_electricity_prices()
    print(f"购电电价: {buy_price}")
    print(f"售电电价: {sell_price}")
    
    wind_all, pv_all = get_all_scenarios()
    print(f"\n24种场景总发电量(MWh):")
    for s in range(24):
        total = wind_all[s].sum() + pv_all[s].sum()
        print(f"  场景{s+1}: 风电={wind_all[s].sum():.1f}, 光伏={pv_all[s].sum():.1f}, 总计={total:.1f}")
