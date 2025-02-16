"""
邢不行™️选股框架
Python股票量化投资课程

版权所有 ©️ 邢不行
微信: xbx8662

未经授权，不得复制、修改、或使用本代码的全部或部分内容。仅限个人学习用途，禁止商业用途。

Author: 邢不行
"""
import re
import pandas as pd
from core.model.strategy_config import StrategyConfig
import os
import config as cfg
from pathlib import Path
"""
使用范例：
{
    'name': '小市值_基本面优化_定风波择时',
    'hold_period': 'W',
    'offset_list': [0],
    'select_num': 5,
    'cap_weight': 1,
    'rebalance_time': '0955-0955',
    'factor_list': [('市值', True, None, 1),
                    ('归母净利润同比增速', False, 60, 1),
                    ('开盘至今涨幅', False, '0945', ('全市场择时', 0.4)),
                    ],
    'filter_list': [('ROE', '单季', 'pct:<=0.8', False),
                  ('成交额Mean', 5, 'val:>=5000_0000', True)]
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
    mcap, profit_growth, decl = strategy.factor_list

    df['净利润增速排名'] = df.groupby('交易日期')[profit_growth.col_name].rank(ascending=profit_growth.is_sort_asc,
                                                                               method='min')
    df['市值_排名'] = df.groupby('交易日期')[mcap.col_name].rank(ascending=mcap.is_sort_asc, method='min')

    # 计算复合因子
    df['复合因子'] = df['净利润增速排名'] + df['市值_排名']

    # =====定风波择时策略=====

    method, ratio = decl.args
    stock_list = []  # 保存最后一个交易日的股票代码，用于实盘计算下跌比例
    if method == '全市场择时':
        df['下跌比例'] = df.groupby('交易日期')[decl.col_name].transform(lambda x: (x < 0).mean())
        stock_list = df[df['交易日期'] == df['交易日期'].max()]['股票代码'].to_list()

    elif len(re.findall(r'前(\d+)择时', method)) > 0 or len(re.findall(r'前(\d+)%择时', method)) > 0:
        if '%' in method:
            num = float(re.findall(r'前(\d+)%择时', method)[0]) / 100
            pct = True
        else:
            # 找到排名占比
            num = int(re.findall(r'前(\d+)择时', method)[0])
            pct = False
        df['因子排名'] = df.groupby('交易日期')['复合因子'].rank(method='min', ascending=True, pct=pct)
        tmp = df[df['因子排名'] <= num]
        stock_list = tmp[tmp['交易日期'] == tmp['交易日期'].max()]['股票代码'].to_list()
        decl_ratio = pd.DataFrame(tmp.groupby('交易日期')[decl.col_name].apply(lambda x: (x < 0).mean())).reset_index()
        decl_ratio.columns = ['交易日期', '下跌比例']
        df = pd.merge(df, decl_ratio, on='交易日期', how='left')
    else:
        raise ValueError('计算下跌比例的范围设置有误，应当是【前N择时】或者【前N%择时】')

        # 只保留下跌比例小于等于ratio的股票
    df = df[df['下跌比例'] <= ratio]
    # 保存最后一个交易日的股票代码，用于实盘计算下跌比例
    save_path = Path(cfg.runtime_data_path) / f'定风波择时/'
    os.makedirs(save_path, exist_ok=True)
    with open(save_path / f'{strategy.name}.txt', 'w') as f:
        f.write(str(stock_list))

    return df
