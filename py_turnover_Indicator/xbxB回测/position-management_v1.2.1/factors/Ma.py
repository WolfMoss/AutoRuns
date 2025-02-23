"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import os
import numpy as np
import pandas as pd


def signal(*args):
    df = args[0]
    n = args[1][0]  # 计算MA使用的K线数
    m = args[1][1]  # 连续m根K线处于ma下方
    factor_name = args[2]

    # 计算MA
    df['ma'] = df['close'].rolling(n).mean()

    # 生成条件序列：收盘价低于MA（True/False）
    condition = df['close'] < df['ma']

    # 判断连续m根满足条件（将NaN填充为False）
    rolling_condition = (condition.rolling(m, min_periods=m)
                         .apply(lambda x: np.all(x), raw=True)
                         .fillna(False).astype(bool))

    df['ma16'] = df['close'].rolling(16).mean()
    df['ma48'] = df['close'].rolling(48).mean()
    #ma_decreasing = (df['ma4'] < df['ma16']).fillna(False)
    ma_decreasing = ((df['ma16'] < df['ma48']) &
                     ((df['ma48'] - df['ma16']) >= df['ma48'] * 0.02)
                     ).fillna(False)

    # 同时满足连续m根条件且MA下降，才标记为1
    #df[factor_name] = (rolling_condition & ma_decreasing).astype(int)
    df[factor_name] = (rolling_condition).astype(int)
    return df

