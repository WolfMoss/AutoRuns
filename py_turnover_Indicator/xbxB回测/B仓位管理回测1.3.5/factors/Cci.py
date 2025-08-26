"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

def signal(*args):
    df = args[0]
    n = args[1]  # CCI的周期参数
    factor_name = args[2]

    # 第一步：计算平均价格TP = (最高价 + 最低价 + 收盘价) ÷ 3
    df['TP'] = (df['high'] + df['low'] + df['close']) / 3

    # 第二步：计算TP的n日移动平均值MA
    df['MA'] = df['TP'].rolling(n, min_periods=1).mean()

    # 第三步：计算(MA - 收盘价)的绝对值的n日移动平均值MD
    df['MD'] = abs(df['TP'] - df['MA']).rolling(n, min_periods=1).mean()

    # 第四步：计算CCI = (TP - MA) ÷ MD ÷ 0.015
    df[factor_name] = (df['TP'] - df['MA']) / (df['MD'] * 0.015)

    # 清理中间变量
    del df['TP']
    del df['MA']
    del df['MD']

    return df