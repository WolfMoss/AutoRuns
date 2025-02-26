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

    # 计算布林线上轨：中轨 + 2 * 标准差
    bollinger_upper = df['ma'] + 2 * df['std']
    df[factor_name] = bollinger_upper - df['close'] # 现价与上轨的距离，正值表示现价在布林上轨下方，负值表示现价在布林上轨上方，数值越小越要卖出

    return df 