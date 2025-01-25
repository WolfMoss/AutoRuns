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
from pathlib import Path
from core.model.strategy_config import StrategyConfig
import config as cfg




def calc_select_factor(df, strategy: StrategyConfig) -> pd.DataFrame:
    df['复合因子'] = df.groupby(['交易日期'])["市值_None"].rank(ascending=True, method='min')
    # 找到下跌比例因子
    decline = [factor for factor in strategy.all_factors if '开盘至今涨幅' in factor.col_name]
    if len(decline) == 0:
        raise ValueError('没有找到开盘至今涨幅因子')

    # =====定风波择时策略=====

    decl = decline[0]  # 如果配置了多个因子，只有第一个会生效
    method, ratio = decl.args
    if method == '全市场择时':
        df['下跌比例'] = df.groupby('交易日期')[decl.col_name].transform(lambda x: (x < 0).mean())
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
        decl_ratio = pd.DataFrame(tmp.groupby('交易日期')[decl.col_name].apply(lambda x: (x < 0).mean())).reset_index()
        decl_ratio.columns = ['交易日期', '下跌比例']
        df = pd.merge(df, decl_ratio, on='交易日期', how='left')
    else:
        raise ValueError('计算下跌比例的范围设置有误，应当是【前N择时】或者【前N%择时】')

    # 只保留下跌比例小于等于ratio的股票
    df = df[df['下跌比例'] <= ratio]

    return df

