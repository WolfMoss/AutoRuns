"""
邢不行™️选股框架
Python股票量化投资课程

版权所有 ©️ 邢不行
微信: xbx8662

未经授权，不得复制、修改、或使用本代码的全部或部分内容。仅限个人学习用途，禁止商业用途。

Author: 邢不行
"""
import numpy as np
import pandas as pd
import config as cfg
from pathlib import Path

fin_cols = []  # 财务因子列


# noinspection PyUnusedLocal
def add_factor(df: pd.DataFrame, param=None, **kwargs) -> pd.DataFrame:
    """
    计算并将新的因子列添加到股票行情数据中，并返回包含计算因子的DataFrame及其聚合方式。

    工作流程：
    1. 根据提供的参数计算股票的因子值。
    2. 将因子值添加到原始行情数据DataFrame中。

    :param df: pd.DataFrame，包含单只股票的K线数据，必须包括市场数据（如收盘价等）。
    :param param: 因子计算所需的参数，格式和含义根据因子类型的不同而有所不同。
    :param kwargs: 其他关键字参数，包括：
        - col_name: 新计算的因子列名。
        - fin_data: 财务数据字典，格式为 {'财务数据': fin_df, '原始财务数据': raw_fin_df}，其中fin_df为处理后的财务数据，raw_fin_df为原始数据，后者可用于某些因子的自定义计算。
        - 其他参数：根据具体需求传入的其他因子参数。
    :return:
        - pd.DataFrame: 包含新计算的因子列，与输入的df具有相同的索引。

    注意事项：
    - 如果因子的计算涉及财务数据，可以通过`fin_data`参数提供相关数据。
    """
    # 从额外参数中获取因子名称
    corr_name = kwargs['col_name']

    index_code = param[0]
    n = param[1]

    index_df = load_index_data(index_code)
    tmp = pd.merge(df[['交易日期', '涨跌幅']], index_df, on='交易日期', how='left')
    corr = tmp['涨跌幅'].rolling(n).corr(tmp['指数涨跌幅'])

    # 创建包含指定因子的DataFrame
    factor_df = pd.DataFrame({corr_name: corr}, index=df.index)

    return factor_df


def load_index_data(index_code):
    index_path = Path(cfg.data_center_path) / f'stock-main-index-data/{index_code}.csv'
    try:
        index_df = pd.read_csv(index_path, encoding='gbk', parse_dates=['candle_end_time'])
    except:
        index_df = pd.read_csv(index_path, encoding='gbk', parse_dates=['candle_end_time'], skiprows=1)

    index_df['指数涨跌幅'] = index_df['close'].pct_change()
    index_df['指数涨跌幅'] = index_df['指数涨跌幅'].fillna(value=index_df['close'] / index_df['open'] - 1)
    index_df.rename(columns={'candle_end_time': '交易日期'}, inplace=True)
    index_df = index_df[['交易日期', '指数涨跌幅']]
    return index_df
