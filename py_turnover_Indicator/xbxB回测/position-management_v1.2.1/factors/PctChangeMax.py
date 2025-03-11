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
    n = args[1]
    factor_name = args[2]

    df['pct'] = df['close'].pct_change().abs()
    df[factor_name] = df['pct'].rolling(n, min_periods=1).max()

    return df


def signal_multi_params(df, param_list) -> dict:
    """
    使用同因子多参数聚合计算，可以有效提升回测、实盘 cal_factor 的速度，
    相对于 `signal` 大概提升3倍左右
    :param df: k线数据的dataframe
    :param param_list: 参数列表
    """
    df['pct'] = df['close'].pct_change().abs()
    ret = dict()
    for param in param_list:
        n = int(param)
        ret[str(param)] = df['pct'].rolling(n, min_periods=1).max()
    return ret
