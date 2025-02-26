#!/usr/bin/python3
# -*- coding: utf-8 -*-

def signal(*args):
    df = args[0]
    # 当前指标的名称
    factor_name = args[2]

    # 条件1：60根K线之前被250均线压制超过168根
    df['ma250'] = df['close'].rolling(window=250, min_periods=1).mean()
    if len(df) > 60:
        prior_section = df.iloc[:-60]
    else:
        prior_section = df
    suppression_count = (prior_section['close'] < prior_section['ma250']).sum()
    cond1 = suppression_count > 168

    # 条件2：近60根K线（除当前K线）处于底部震荡盘整状态
    if len(df) >= 61:
        recent_zone = df.iloc[-61:-1]  # 最近60根K线（不包含当前K线）
        min_recent = recent_zone['close'].min()
        max_recent = recent_zone['close'].max()
        # 归一化区间，要求较窄
        relative_range = (max_recent - min_recent) / min_recent if min_recent != 0 else 1
        cond2a = relative_range <= 0.05  # 区间宽度不超过5%
        mean_recent = recent_zone['close'].mean()
        cond2b = ((mean_recent - min_recent) / min_recent <= 0.1) if min_recent != 0 else False  # 均价与最低价差距不大
        consolidation = cond2a and cond2b
    else:
        consolidation = False

    # 条件3：当前价格突破盘整区间（使用除当前K线的最近60根K线的最高价）
    if len(df) >= 61:
        recent_zone = df.iloc[-61:-1]
        max_recent = recent_zone['close'].max()
        current_close = df['close'].iloc[-1]
        breakout = current_close > max_recent
    else:
        breakout = False

    # 条件4：当前均线排列条件：MA5 > MA10 且 MA10 > MA20
    ma5 = df['close'].rolling(window=5, min_periods=1).mean().iloc[-1]
    ma10 = df['close'].rolling(window=10, min_periods=1).mean().iloc[-1]
    ma20 = df['close'].rolling(window=20, min_periods=1).mean().iloc[-1]
    cond_ma = (ma5 > ma10) and (ma10 > ma20)

    # 同时满足所有条件，指标取1，否则为0
    if cond1 and consolidation and breakout and cond_ma:
        df[factor_name] = 1
    else:
        df[factor_name] = 0

    return df 