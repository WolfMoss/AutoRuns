#!/usr/bin/python3
# -*- coding: utf-8 -*-

def signal(*args):
    df = args[0]
    n = args[1]  # 使用的K线数
    factor_name = args[2]

    # 计算中轨：以收盘价计算移动平均线
    df['ma'] = df['close'].rolling(window=n, min_periods=1).mean()
    # 计算滚动标准差
    df['std'] = df['close'].rolling(window=n, min_periods=1).std()

    # 计算布林下轨：中轨 - 2 * 标准差
    bollinger_lower = df['ma'] - 2 * df['std']
    df[factor_name] = bollinger_lower - df['close'] # 现价与下轨的距离，正值表示现价在布林下轨下方，负值表示现价在布林下轨上方，数值越小越要买入

    return df 