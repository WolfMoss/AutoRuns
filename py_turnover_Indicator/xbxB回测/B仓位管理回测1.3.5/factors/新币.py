"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""


import pandas as pd

def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]
    # 将 candle_begin_time 转换为 pandas Series
    candle_series = pd.to_datetime(pd.Series(df['candle_begin_time']))

    # 计算每一行与第一行的时间差
    time_deltas = candle_series - candle_series.iloc[0]

    # 将时间差转换为小时数
    total_hours = time_deltas.dt.total_seconds() / 3600

    df[factor_name] = total_hours

    return df