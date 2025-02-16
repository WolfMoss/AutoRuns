"""
邢不行™️选股框架
Python股票量化投资课程

版权所有 ©️ 邢不行
微信: xbx8662

未经授权，不得复制、修改、或使用本代码的全部或部分内容。仅限个人学习用途，禁止商业用途。

Author: 邢不行
"""
import pandas as pd
from core.model.strategy_config import StrategyConfig
import numpy as np

"""
使用范例：
{
    'name': '小市值_周黎明',
    'hold_period': 'W',
    'offset_list': [0],
    'select_num': 5,
    'cap_weight': 1,
    'rebalance_time': 'open',
    'factor_list': [('Ret', False, 5, 100),
                    ('Ret', False, 20, 0.2),
                    ('一级行业', False, '', 2),
                    ('市值', True, '', 1),],
    'filter_list': [('成交额Mean', 5, 'val:>=5000_0000', True)]
}
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
    # 读取因子信息
    ret_short, ret_long, industry, mcap = strategy.factor_list

    # 读取参数
    short_rank = ret_short.args         # 短动量排名
    industry_rank = industry.args       # 行业排名
    long_quantile = ret_long.args       # 长动量分位数

    df['Ret_short排名'] = df.groupby('交易日期')[ret_short.col_name].rank(ascending=ret_short.is_sort_asc, method='min')
    df['排名靠前'] = np.where(df['Ret_short排名'] <= short_rank, 1, 0)
    ind_strength = df.groupby(['交易日期', industry.col_name])['排名靠前'].sum().reset_index()
    ind_strength['排名靠前_排名'] = ind_strength.groupby('交易日期')['排名靠前'].rank(ascending=industry.is_sort_asc, method='min')
    ind_strength = ind_strength[ind_strength['排名靠前_排名'] <= industry_rank]
    df = pd.merge(df, ind_strength[['交易日期', industry.col_name]], on=['交易日期', industry.col_name])

    # 计算Ret20排名  衡量超跌
    df['Ret_long分位数'] = df.groupby('交易日期')[ret_long.col_name].rank(ascending=ret_long.is_sort_asc, method='min', pct=True)
    df = df[df['Ret_long分位数'] > long_quantile]

    # 总市值排名
    df['市值排名'] = df.groupby('交易日期')[mcap.col_name].rank(ascending=mcap.is_sort_asc, method='min')

    # 计算复合因子
    df['复合因子'] = df['市值排名']

    return df
