#!/usr/bin/python3
# -*- coding: utf-8 -*-

def signal(*args):
    df = args[0]
    factor_name = args[2]

    # 条件1：60根K线之前被250均线托住超过168根
    df['ma250'] = df['close'].rolling(window=250, min_periods=1).mean()
    if len(df) > 60:
        prior_section = df.iloc[:-60]
    else:
        prior_section = df
    support_count = (prior_section['close'] > prior_section['ma250']).sum()
    cond1 = support_count > 168

    # 条件2：近60根K线（除当前K线）处于顶部震荡盘整状态
    if len(df) >= 61:
        recent_zone = df.iloc[-61:-1]  # 最近60根K线（不包含当前K线）
        min_recent = recent_zone['close'].min()
        max_recent = recent_zone['close'].max()
        # 归一化区间（以最高价为基准），要求较窄
        relative_range = (max_recent - min_recent) / max_recent if max_recent != 0 else 1
        cond2a = relative_range <= 0.1  # 区间宽度不超过10%
        mean_recent = recent_zone['close'].mean()
        # 均价接近最高价
        cond2b = ((max_recent - mean_recent) / max_recent <= 0.1) if max_recent != 0 else False
        consolidation = cond2a and cond2b
    else:
        consolidation = False

    # 条件3：当前价格从顶部盘整区间向下突破（使用最近60根K线的最低价）
    if len(df) >= 61:
        recent_zone = df.iloc[-61:-1]
        min_recent = recent_zone['close'].min()
        current_close = df['close'].iloc[-1]
        breakdown = current_close < min_recent
    else:
        breakdown = False

    # 条件4：当前均线排列条件：MA5 < MA10 且 MA10 < MA20（均线死叉排列）
    ma5 = df['close'].rolling(window=5, min_periods=1).mean().iloc[-1]
    ma10 = df['close'].rolling(window=10, min_periods=1).mean().iloc[-1]
    ma20 = df['close'].rolling(window=20, min_periods=1).mean().iloc[-1]
    cond_ma = (ma5 < ma10) and (ma10 < ma20)

    # 同时满足所有条件，指标赋值1，否则为0
    if cond1 and consolidation and breakdown and cond_ma:
        df[factor_name] = 1
    else:
        df[factor_name] = 0

    return df 