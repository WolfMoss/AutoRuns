"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
from pathlib import Path

import numpy as np
import pandas as pd

from config import data_center_path
from core.utils.log_kit import logger

data_center_path = Path(data_center_path)


def load_hk_stock(file_path: str, candle_df: pd.DataFrame, save_cols: list) -> pd.DataFrame | None:
    hkd_cny_path = data_center_path / 'stock-cny-rate' / 'HKD_CNY_rate.csv'
    if not hkd_cny_path.exists():
        logger.error(f'港股数据依赖港元汇率数据：{hkd_cny_path}，请在数据中心订阅“CNY汇率数据”后重试')
        raise FileNotFoundError

    hkd_cny = pd.read_csv(hkd_cny_path, encoding='gbk', skiprows=1, parse_dates=['日期'])
    # 个股股票代码
    code = candle_df['股票代码'].iloc[0]
    # 港股个股数据路径
    hk_stock_path = Path(file_path) / (code + '_HK.csv')
    # 如果可以找到这个港股的个股数据
    if hk_stock_path.exists():
        # 读取港股个股数据
        hk_df = pd.read_csv(hk_stock_path, encoding='gbk', parse_dates=['交易日期'],
                            usecols=['交易日期', '收盘价', '前收盘价'],
                            skiprows=1)
        hk_df['收盘价'].fillna(method='ffill', inplace=True)
        hk_df['前收盘价'].fillna(method='ffill', inplace=True)
        # 计算复权因子
        hk_df['复权因子'] = (hk_df['收盘价'] / hk_df['前收盘价']).cumprod()
        # 计算前复权、后复权收盘价
        hk_df['收盘价_复权'] = hk_df['复权因子'] * (hk_df.iloc[0]['收盘价'] / hk_df.iloc[0]['复权因子'])

        # 合并该股票的A股和港股数据
        temp = pd.merge_ordered(hk_df.rename(columns={'交易日期': '交易日期_港股'}), candle_df,
                                left_on='交易日期_港股',
                                right_on='交易日期', fill_method='ffill', suffixes=('_港股', ''))

        temp.dropna(subset=['交易日期'], inplace=True)
        # 按照交易日期列作为subset，遇到重复的日期，保留最新的数据
        temp = temp.drop_duplicates(subset='交易日期', keep='last')

        # 判断该股票在港股是不是已经退市：如果A股和港股的最新交易日期相差10天以上，就认为该股票已经退市
        if (temp['交易日期'].iloc[-1] - temp['交易日期_港股'].iloc[-1]).days > 10:
            # 获取hk_df最新的交易日期，将data里的收盘价_港股超过这个日期的数据赋值为nan
            last_date = hk_df['交易日期'].iloc[-1]
            temp.loc[temp['交易日期'] > last_date, '收盘价_港股'] = pd.NA

        # 删除港股交易日期列
        temp.drop(columns=['交易日期_港股'], inplace=True)

        # 合并股票数据和汇率数据
        temp = pd.merge_ordered(left=temp, right=hkd_cny[['日期', '收盘价']], left_on='交易日期', right_on='日期',
                                fill_method='ffill', suffixes=('', '_汇率'))
        temp.dropna(subset=['交易日期'], inplace=True)
        # 按照交易日期列作为subset，遇到重复的日期，保留最新的数据
        temp = temp.drop_duplicates(subset='交易日期', keep='last')
        # 删除汇率交易日期列
        temp.drop(columns=['日期'], inplace=True)

        candle_df = pd.merge(candle_df, temp[['交易日期', '收盘价_港股', '收盘价_汇率', '收盘价_复权_港股']],
                             on='交易日期',
                             how='left')

    # 找不到个股数据，就给个nan值
    else:
        candle_df['收盘价_港股'] = np.nan
        candle_df['收盘价_汇率'] = np.nan
        candle_df['收盘价_复权_港股'] = np.nan
    return candle_df


presets = {
    'hk-stock': (load_hk_stock, Path(data_center_path) / 'stock-hk-stock-data')
    # "coin-cap": ('load_coin_cap', '/Users/xxxx/Downloads/coin-cap-test',)
}
