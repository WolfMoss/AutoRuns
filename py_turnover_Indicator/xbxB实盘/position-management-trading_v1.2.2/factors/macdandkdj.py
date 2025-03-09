"""
MACD+KDJ多空共振策略
"""
import numpy as np
import pandas as pd

def signal(*args):
    df = args[0]
    # 参数：MACD参数（short,long,signal），KDJ参数（n, m）
    macd_short, macd_long, macd_signal = args[1][:3]  # 默认(12,26,9)
    kdj_n, kdj_m = args[1][3:]  # 默认(9,3)
    factor_name = args[2]

    # 计算MACD（保持不变）
    df['EMA12'] = df['close'].ewm(span=macd_short, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=macd_long, adjust=False).mean()
    df['DIF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIF'].ewm(span=macd_signal, adjust=False).mean()

    # 计算KDJ（保持不变）
    low_min = df['low'].rolling(kdj_n).min()
    high_max = df['high'].rolling(kdj_n).max()
    df['RSV'] = (df['close'] - low_min) / (high_max - low_min) * 100
    df['K'] = df['RSV'].ewm(alpha=1 / kdj_m, adjust=False).mean()
    df['D'] = df['K'].rolling(kdj_m).mean()

    # ========== 信号生成逻辑优化 ==========
    # 生成多空信号
    macd_gold = df['DIF'] > df['DEA']  # MACD金叉
    macd_death = df['DIF'] < df['DEA']  # MACD死叉
    kdj_gold = df['K'] > df['D']  # KDJ金叉
    kdj_death = df['K'] < df['D']  # KDJ死叉

    # 多空信号独立判断
    long_signal = (macd_gold & kdj_gold).astype(int)
    short_signal = (macd_death & kdj_death).astype(int) * (-1)

    # 合并信号并清理异常值
    df[factor_name] = (long_signal + short_signal).clip(-1, 1)

    # 清理中间列（保持不变）
    df.drop(['EMA12', 'EMA26', 'DIF', 'DEA', 'RSV', 'K', 'D', 'J'],
            axis=1, inplace=True, errors='ignore')

    return df