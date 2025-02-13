"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import pandas as pd
import numpy as np


def dynamic_leverage(equity: pd.Series, *args) -> pd.Series:
    """
    根据资金曲线，动态调整杠杆
    :param equity: 资金曲线
    :param args: 其他参数
    :return: 返回包含 leverage 的数据
    """

    # ===== 获取策略参数
    n = int(args[0])

    # 默认nan
    leverage = pd.Series(np.nan, index=equity.index)

    # ===== 计算指标
    ma = equity.rolling(n, min_periods=1).mean()
    std = equity.rolling(n, min_periods=1).std()
    zscore = (equity - ma) / std
    m = zscore.abs().rolling(n, min_periods=1).mean()
    down = ma - m * std

    # ===== 计算开平仓信号
    # 1.equity上穿ma 开多
    long_con1 = equity.shift() < ma.shift()
    long_con2 = equity > ma
    leverage.loc[long_con1 & long_con2] = 1

    # 2.equity下穿down 平多
    short_con1 = equity.shift() > down.shift()
    short_con2 = equity < down
    leverage.loc[short_con1 & short_con2] = 0

    # 向后填充择时信号
    leverage.fillna(method='ffill', inplace=True)
    leverage.fillna(0, inplace=True)

    return leverage
