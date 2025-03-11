# -*- coding: utf-8 -*-
"""
中性策略框架 | 邢不行 | 2024分享会
author: 邢不行
微信: xbx6660
"""

import numpy as np

def signal(*args):
    # Rsi
    df = args[0]
    n = args[1]
    factor_name = args[2]

    '''
    CLOSEUP=IF(CLOSE>REF(CLOSE,1),CLOSE-REF(CLOSE,1),0) 
    CLOSEDOWN=IF(CLOSE<REF(CLOSE,1),ABS(CLOSE-REF(CLOSE,1)),0)
    CLOSEUP_MA=SMA(CLOSEUP,N,1)
    CLOSEDOWN_MA=SMA(CLOSEDOWN,N,1) 
    RSI=100*CLOSEUP_MA/(CLOSEUP_MA+CLOSEDOWN_MA)
    RSI 反映一段时间内平均收益与平均亏损的对比。
    通常认为当 RSI 大于 70，市场处于强势上涨甚至达到超买的状态;
    当 RSI 小于 30，市 场处于强势下跌甚至达到超卖的状态。
    当 RSI 跌到 30 以下又上穿 30 时，通常认为股价要从超卖的状态反弹;
    当 RSI 超过 70 又下穿 70 时，通常认为市场要从超买的状态回落了。
    实际应用中，不一定要使 用 70/30 的阈值选取。这里我们用 60/40 作为信号产生的阈值。 
    RSI 上穿 40 则产生买入信号; RSI 下穿 60 则产生卖出信号。
    '''

    diff = df['close'].diff()  # CLOSE-REF(CLOSE,1) 计算当前close 与前一周期的close的差值
    # IF(CLOSE>REF(CLOSE,1),CLOSE-REF(CLOSE,1),0) 表示当前是上涨状态，记录上涨幅度
    df['up'] = np.where(diff > 0, diff, 0)
    # IF(CLOSE<REF(CLOSE,1),ABS(CLOSE-REF(CLOSE,1)),0) 表示当前为下降状态，记录下降幅度
    df['down'] = np.where(diff < 0, abs(diff), 0)
    sma_A = df['up'].rolling(n).sum()  # SMA(CLOSEUP,N,1) 计算周期内的上涨幅度的sma
    sma_B = df['down'].rolling(n).sum()  # SMA(CLOSEDOWN,N,1)计算周期内的下降幅度的sma
    # RSI=100*CLOSEUP_MA/(CLOSEUP_MA+CLOSEDOWN_MA)  没有乘以100   没有量纲即可
    df[factor_name] = 100 * sma_A / (sma_A + sma_B)

    # 删除多余列
    del df['up'], df['down']

    return df


