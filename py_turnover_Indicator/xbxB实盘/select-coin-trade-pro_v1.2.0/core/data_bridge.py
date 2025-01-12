"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

from pathlib import Path

import numpy as np
import pandas as pd

from core.utils.log_kit import logger
from config import special_symbol_dict


def load_coin_cap(file_path: str, candle_df: pd.DataFrame, save_cols: list, symbol: str) -> pd.DataFrame | None:
    """
    加载coinmarketcap数据
    :param file_path: 文件路径
    :param candle_df: 原始k线数据
    :param save_cols: 需要保存的列
    :param symbol: 币种
    :return: 一个 df 数据
    """
    data_path = Path(file_path)
    symbol_name = candle_df['symbol'].iloc[-1].replace('USDT', '')
    # 合并选币名称并剔除空字符串
    symbols = (
        {symbol} if symbol else {
            special_symbol_dict.get(symbol_name,
                                    (symbol_name.split('1000')[1] if '1000' in symbol_name else symbol_name))
        }
    )
    # 兼容 回测 & 实盘。
    # 回测币种带 -USDT，实盘币种带 USDT
    all_file_paths = [data_path / f'{symbol}-USDT.csv' for symbol in symbols]

    # 读取数据
    extra_df = None
    for file_path in all_file_paths:
        try:
            extra_df = pd.read_csv(file_path, encoding='gbk', skiprows=1, parse_dates=['candle_begin_time'])
            extra_df.drop_duplicates(subset=['candle_begin_time'], keep='last', inplace=True)
            extra_df.sort_values('candle_begin_time', inplace=True)  # 通过candle_begin_time排序
            break
        except BaseException as e:
            continue

    if extra_df is None or extra_df.empty:
        logger.warning(f'coin_cap 没有找到任何数据，symbol={symbols}')
        return None

    if len(candle_df) == 1:
        logger.warning(f'{candle_df["symbol"].iloc[0]}币种K线数据不足，跳过')
        return None

    # 预处理
    time_diff = candle_df['candle_begin_time'].iloc[1] - candle_df['candle_begin_time'].iloc[0]
    hour_diff = time_diff.components.days * 24 + time_diff.components.hours
    hold_period_type = 'D' if hour_diff == 24 else 'H'

    if hold_period_type == 'H':
        extra_df['candle_begin_time'] += pd.Timedelta('23H')

    # 合并数据(这里是兼容分钟偏移)
    merge_df = pd.merge_asof(candle_df[['candle_begin_time', 'close']], extra_df, on='candle_begin_time', direction='backward')

    # 处理 cmc 数据中的 usd_price与close 数据的不一致
    # 例：
    # 1000SATS usd_price = 0.0000001， 但是close = 0.0001
    times = merge_df['close'] / merge_df['usd_price']
    times = times.map(lambda x: 10 ** np.log10(x).round(0))
    times = [times.mode().iloc[0] if times.notna().sum() > 0 else np.nan] * len(merge_df)

    # 筛选指定列
    columns = save_cols if save_cols else merge_df.columns
    for col in columns:
        if 'supply' in col:
            merge_df[col] = merge_df[col] / times
        merge_df[col].fillna(method='ffill', inplace=True)

    return merge_df[columns]
