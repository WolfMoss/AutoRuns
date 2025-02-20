"""
邢不行™️选股框架
Python股票量化投资课程

版权所有 ©️ 邢不行
微信: xbx8662

未经授权，不得复制、修改、或使用本代码的全部或部分内容。仅限个人学习用途，禁止商业用途。

Author: 邢不行
"""
import os
import re
import pandas as pd
from pathlib import Path
from core.model.strategy_config import StrategyConfig
import config as cfg

"""
使用范例：
    {'name': '中等生策略_定风波择时', 'hold_period': 'W', 'offset_list': [0], 'select_num': 5, 'cap_weight': 1,
     'rebalance_time': '0955-0955',
     'factor_list': [('指数相关性', False, ['sh000300', 20], 1),
                     ('指数相关性', False, ['sh932000', 20], 1),
                     ('开盘至今涨幅', False, '0945', ('全市场择时', 0.4)), ],
     'filter_list': []},
     
开盘涨跌幅参数解析     
    参数1：计算下跌比例的范围
        可填三种类型：全市场择时，前N择时，前N%择时。
        按照规则写即可实现动态调整范围，例如：前100择时，前10%择时
    参数2：下跌比例
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
    index_list = sorted(
        [factor.param[0] for factor in strategy.all_factors if factor.col_name.startswith('指数相关性')])
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

    # =====定风波择时策略=====
    # 找到下跌比例因子
    decline = [factor for factor in strategy.all_factors if '开盘至今涨幅' in factor.col_name]
    if len(decline) > 0:
        df = calm_the_storm(decline[0], df, strategy)

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


def calm_the_storm(decl, df, strategy):
    method, ratio = decl.args
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
