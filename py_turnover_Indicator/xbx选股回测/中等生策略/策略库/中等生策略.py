"""
邢不行™️选股框架
Python股票量化投资课程

版权所有 ©️ 邢不行
微信: xbx8662

未经授权，不得复制、修改、或使用本代码的全部或部分内容。仅限个人学习用途，禁止商业用途。

Author: 邢不行
"""
import pandas as pd
from pathlib import Path
from core.model.strategy_config import StrategyConfig
import config as cfg

"""
使用范例：
    {'name': '中等生策略', 'hold_period': 'W', 'offset_list': [0], 'select_num': 5, 'cap_weight': 1,
     'rebalance_time': 'open',
     'factor_list': [('指数相关性', False, ['sh000300', 20], 1),
                     ('指数相关性', False, ['sh932000', 20], 1),
                     ],
     'filter_list': []},
"""

def calc_select_factor(df, strategy: StrategyConfig) -> pd.DataFrame:
    """
    计算复合选股因子
    :param df: 整理好的数据，包含因子信息，并做过周期转换
    :param strategy: 策略配置
    :return: 返回过滤后的数据

    ### df 列说明
    包含基础列：  ['交易日期', '股票代码', '股票名称', '周频起始日', '月频起始日', '上市至今交易天数', '复权因子', '开盘价', '最高价',
                '最低价', '收盘价', '成交额', '是否交易', '流通市值', '总市值', '下日_开盘涨停', '下日_是否ST', '下日_是否交易',
                '下日_是否退市']
    以及config中配置好的，因子计算的结果列。

    ### strategy 数据说明
    - strategy.name: 策略名称
    - strategy.hold_period: 持仓周期
    - strategy.select_num: 选股数量
    - strategy.factor_name: 复合因子名称
    - strategy.factor_list: 选股因子列表
    - strategy.filter_list: 过滤因子列表
    - strategy.factor_columns: 选股+过滤因子的列名
    """

    # 取出所有的日期作为基准
    bench = pd.DataFrame({'交易日期': sorted(df['交易日期'].unique())})

    # 获取所有指数的列表
    index_list = sorted([factor.param[0] for factor in strategy.all_factors if factor.col_name.startswith('指数相关性')])
    # 加载指数数据
    for index in index_list:
        index_df = load_index_data(index)
        # 计算指数的动量因子
        index_df[f'Ret20_{index}'] = index_df['指数涨跌幅'].rolling(20).apply(lambda x: (x + 1).prod() - 1)
        bench = bench.merge(index_df[['交易日期', f'Ret20_{index}']], on='交易日期', how='left')

    # 选中指数中的最大动量
    bench['选中指数'] = bench[bench.columns[1:]].idxmax(axis=1)
    bench['选中指数'] = bench['选中指数'].apply(lambda x: x.split('_')[1])
    bench['最大指数涨跌幅'] = bench[bench.columns[1: -1]].max(axis=1)

    # 将数据合并到全量数据上
    df_index = df.index
    df = df.merge(bench[['交易日期', '选中指数', '最大指数涨跌幅']], on='交易日期', how='left')
    df.index = df_index

    # 计算每周期实际使用的相似度因子
    for index in index_list:
        con = df['选中指数'] == index
        col_name = [f for f in strategy.factor_columns if ('指数相关性' in f and index in f)][0]
        df.loc[con, '相似度因子'] = df[col_name]

    # 按照相似度因子排序
    df['复合因子'] = df.groupby(['交易日期'])["相似度因子"].rank(ascending=False, method='min')

    return df


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
