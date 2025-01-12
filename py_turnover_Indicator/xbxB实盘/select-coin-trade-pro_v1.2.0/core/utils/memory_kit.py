"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import numpy as np


def reduce_mem_series(series):
    """
    来自F1框架的馈赠
    :param series:
    :return: series
    """
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64', 'object']
    series_type = series.dtypes
    if series_type in numerics:
        c_min = series.min()
        c_max = series.max()
        if str(series_type)[:3] == 'int':
            if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                series = series.astype(np.int8)
            elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                series = series.astype(np.int16)
            elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                series = series.astype(np.int32)
            elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                series = series.astype(np.int64)
        elif str(series_type)[:5] == 'float':
            if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                series = series.astype(np.float16)
            elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                series = series.astype(np.float32)
            else:
                series = series.astype(np.float64)
        else:
            num_unique_values = len(series.unique())
            num_total_values = len(series)
            rate = num_unique_values / num_total_values
            if rate < 0.5:
                series = series.astype('category')
    return series
