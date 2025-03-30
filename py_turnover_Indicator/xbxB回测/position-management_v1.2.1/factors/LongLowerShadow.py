"""
长下影线指标

检测亏损K线且具有较长下引线的情况：
1. 亏损K线（收盘价低于开盘价）
2. 下引线价差与实体价差比例大于等于1
3. 下引线价差百分比大于等于1%
"""
import os
import numpy as np
import pandas as pd


def signal(*args):
    df = args[0]
    # 这个指标不需要参数，但为保持一致性，仍然保留参数位置
    # 如果需要可配置的参数，可以通过args[1]获取
    n1 = args[1]
    factor_name = args[2]

    # 计算亏损K线（收盘价低于开盘价）
    bearish = df['close'] < df['open']
    
    # 对于亏损K线，计算下引线长度（收盘价到最低价）
    lower_shadow = np.where(bearish, df['close'] - df['low'], 0)
    
    # 计算实体部分的价差（开盘价-收盘价，对于亏损K线）
    body = np.where(bearish, df['open'] - df['close'], 1)  # 避免除零错误，非亏损K线设为1
    
    # 计算比例：下引线价差与实体价差的比例
    ratio = lower_shadow / body
    
    # 计算下引线价差百分比
    lower_shadow_percent = np.where(bearish, (lower_shadow / df['close']) * 100, 0)
    
    # 判断是否同时满足所有条件
    condition = bearish & (ratio >= 1.5) & (lower_shadow_percent >= n1)
    
    # 将满足条件的值设为1，不满足条件的设为0
    df[factor_name] = condition.astype(int)

    return df 