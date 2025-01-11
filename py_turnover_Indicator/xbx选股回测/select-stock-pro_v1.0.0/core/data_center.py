"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from config import n_jobs, runtime_folder
from core.market_essentials import cal_fuquan_price, cal_zdt_price, merge_with_index_data
from core.model.backtest_config import BacktestConfig
from core.utils.log_kit import logger

# 定义股票数据所需的列
STOCK_DATA_COLS = [
    '股票代码', '股票名称', '交易日期', '开盘价', '最高价', '最低价', '收盘价', '前收盘价', '成交量', '成交额',
    '流通市值', '总市值', '新版申万一级行业名称', '09:35收盘价', '09:45收盘价', '09:55收盘价',
]


# ================================================================
# step1_整理数据.py
# ================================================================
def prepare_data(conf: BacktestConfig, boost: bool = True):
    logger.info(f'读取数据中心数据...')
    start_time = time.time()  # 记录数据准备开始时间

    # 1. 获取股票代码列表
    stock_code_list = []  # 用于存储股票代码
    # 遍历文件夹下，所有csv文件
    for filename in conf.stock_data_path.glob('*.csv'):
        # 排除北交所股票和隐藏文件
        if filename.stem.startswith(('bj', '.')):
            continue
        stock_code_list.append(filename.stem)
    stock_code_list = sorted(stock_code_list)
    logger.debug(f'📂 读取到股票数量：{len(stock_code_list)}，不包括北交所股票')

    # 2. 读取并处理指数数据，确保股票数据与指数数据的时间对齐
    index_data = conf.load_index_data()
    all_candle_data_dict = {}  # 用于存储所有股票的K线数据

    logger.debug(f'🚀 多进程处理数据，进程数量：{n_jobs}' if boost else '🚲 单进程处理数据')
    if boost:
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
            futures = []
            for code in stock_code_list:
                file_path = conf.stock_data_path / f'{code}.csv'
                futures.append(executor.submit(pre_process, file_path, index_data))

            for future in tqdm(futures, desc='📦 处理数据', total=len(futures)):
                df = future.result()
                if not df.empty:
                    code = df['股票代码'].iloc[0]
                    all_candle_data_dict[code] = df  # 仅存储非空数据
    else:
        for code in tqdm(stock_code_list, desc='📦 处理数据', total=len(stock_code_list)):
            file_path = conf.stock_data_path / f'{code}.csv'
            df = pre_process(file_path, index_data)
            if not df.empty:
                all_candle_data_dict[code] = df

    # 3. 缓存预处理后的数据
    cache_path = runtime_folder / '股票预处理数据.pkl'
    logger.debug(f'📈 保存股票预处理数据: {cache_path}')
    pd.to_pickle(all_candle_data_dict, cache_path)

    # 4. 准备并缓存pivot透视表数据，用于后续回测
    logger.debug('📄 生成行情数据透视表...')
    market_pivot_dict = make_market_pivot(all_candle_data_dict)
    pivot_cache_path = runtime_folder / '全部股票行情pivot.pkl'
    logger.debug(f'🗄️ 保存行情数据透视表: {pivot_cache_path}')
    pd.to_pickle(market_pivot_dict, pivot_cache_path)

    logger.ok(f'数据准备耗时：{(time.time() - start_time):.2f} 秒')


def pre_process(stock_file_path: Union[str, Path], index_data: pd.DataFrame) -> pd.DataFrame:
    """
    对股票数据进行预处理，包括合并指数数据和计算未来交易日状态。

    参数:
    stock_file_path (str | Path): 股票日线数据的路径
    index_data (DataFrame): 指数数据

    返回:
    df (DataFrame): 预处理后的数据
    """
    # 计算涨跌幅、换手率等关键指标
    df = pd.read_csv(stock_file_path, encoding='gbk', skiprows=1, parse_dates=['交易日期'], usecols=STOCK_DATA_COLS)
    pct_change = df['收盘价'] / df['前收盘价'] - 1
    turnover_rate = df['成交额'] / df['流通市值']
    trading_days = df.index.astype('int') + 1
    avg_price = df['成交额'] / df['成交量']

    # 一次性赋值提高性能
    df = df.assign(
        涨跌幅=pct_change,
        换手率=turnover_rate,
        上市至今交易天数=trading_days,
        均价=avg_price,
    )

    # 复权价计算及涨跌停价格计算
    df = cal_fuquan_price(df, fuquan_type='后复权')
    df = cal_zdt_price(df)

    # 合并股票与指数数据，补全停牌日期等信息
    df = merge_with_index_data(df, index_data.copy(), fill_0_list=['换手率'])

    # 股票退市时间小于指数开始时间，就会出现空值
    if df.empty:
        # 如果出现这种情况，返回空的DataFrame用于后续操作
        return pd.DataFrame(columns=STOCK_DATA_COLS)

    # 计算开盘买入涨跌幅和未来交易日状态
    df = df.assign(
        下日_是否交易=df['是否交易'].astype('int8').shift(-1),
        下日_一字涨停=df['一字涨停'].astype('int8').shift(-1),
        下日_开盘涨停=df['开盘涨停'].astype('int8').shift(-1),
        下日_是否ST=df['股票名称'].str.contains('ST').astype('int8').shift(-1),
        下日_是否S=df['股票名称'].str.contains('S').astype('int8').shift(-1),
        下日_是否退市=df['股票名称'].str.contains('退').astype('int8').shift(-1),
    )

    # 处理最后一根K线的数据：最后一根K线默认沿用前一日的数据
    state_cols = ['下日_是否交易', '下日_是否ST', '下日_是否S', '下日_是否退市']
    df[state_cols] = df[state_cols].ffill()

    # 清理退市数据，保留有效交易数据
    if ('退' in df['股票名称'].iloc[-1]) or ('S' in df['股票名称'].iloc[-1]):
        if df['成交额'].iloc[-1] == 0 and np.all(df['成交额'] == 0):
            return pd.DataFrame(columns=STOCK_DATA_COLS)
        # @马超 同学于2024年11月20日提供退市逻辑优化处理。
        # 解决因为起始时间太靠前，导致数据可能为空报错的问题，加入了empty情况的容错
        df_tmp = df[(df['成交额'] != 0) & (df['成交额'].shift(-1) == 0)]
        if df_tmp.empty:
            end_date = df['交易日期'].iloc[-1]
        else:
            end_date = df_tmp.iloc[-1]['交易日期']
        df = df[df['交易日期'] <= end_date]

    return df if not df.empty else pd.DataFrame(columns=STOCK_DATA_COLS)


def make_market_pivot(market_dict):
    """
    构建市场数据的pivot透视表，便于回测计算。

    参数:
    market_dict (dict): 股票K线数据字典

    返回:
    dict: 包含开盘价、收盘价及前收盘价的透视表数据
    """
    cols = ['交易日期', '股票代码', '开盘价', '收盘价', '前收盘价', '09:35收盘价', '09:45收盘价', '09:55收盘价']
    logger.debug('⚗️ 合成整体市场数据...')
    df_list = [df[cols].dropna(subset='股票代码') for df in market_dict.values()]
    df_all_market = pd.concat(df_list, ignore_index=True)
    logger.debug('[1/6] 开盘价pivot透视表...')
    df_open = df_all_market.pivot(values='开盘价', index='交易日期', columns='股票代码')
    logger.debug('[2/6] 收盘价pivot透视表...')
    df_close = df_all_market.pivot(values='收盘价', index='交易日期', columns='股票代码')
    logger.debug('[3/6] 前收盘价pivot透视表...')
    df_preclose = df_all_market.pivot(values='前收盘价', index='交易日期', columns='股票代码')
    logger.debug('[4/6] 09:35收盘价pivot透视表...')
    df_0935 = df_all_market.pivot(values='09:35收盘价', index='交易日期', columns='股票代码')
    logger.debug('[5/6] 09:45收盘价pivot透视表...')
    df_0945 = df_all_market.pivot(values='09:45收盘价', index='交易日期', columns='股票代码')
    logger.debug('[6/6] 09:55收盘价pivot透视表...')
    df_0955 = df_all_market.pivot(values='09:55收盘价', index='交易日期', columns='股票代码')

    return {
        'open': df_open, 'close': df_close, 'preclose': df_preclose,
        '0935': df_0935, '0945': df_0945, '0955': df_0955
    }


# ===============================================================================================================
# 额外数据源
# ===============================================================================================================
def merge_data(df: pd.DataFrame, data_name: str) -> dict[str, pd.Series]:
    """
    导入数据，最终只返回带有同index的数据
    :param df: （只读）原始的行情数据，主要是对齐数据用的
    :param data_name: 数据中心中的数据英文名
    :return: 合并后的数据
    """
    print(f'⚠️ 未实现数据源：{data_name}')
    print(df)
    return {}
