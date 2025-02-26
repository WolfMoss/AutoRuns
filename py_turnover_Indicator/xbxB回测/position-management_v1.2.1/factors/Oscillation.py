#!/usr/bin/python3
# -*- coding: utf-8 -*-

def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    # 计算中轨：以收盘价计算移动平均线
    df['ma'] = df['close'].rolling(window=n, min_periods=1).mean()
    # 计算滚动标准差
    df['std'] = df['close'].rolling(window=n, min_periods=1).std()

    # 计算布林带宽归一化指标
    # 布林带上轨 = 中轨 + 2 * 标准差，下轨 = 中轨 - 2 * 标准差
    # 带宽 = 上轨 - 下轨 = 4 * 标准差
    # 归一化带宽 = 带宽 / 中轨 = 4 * 标准差 / 中轨
    df[factor_name] = 4 * df['std'] / df['ma']

    return df 