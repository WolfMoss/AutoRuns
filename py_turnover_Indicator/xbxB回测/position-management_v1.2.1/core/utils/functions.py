"""
邢不行｜策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

import gc
import shutil
import warnings
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from config import stable_symbol, swap_path, spot_path
from core.model.backtest_config import BacktestConfig
from core.utils.log_kit import logger
from core.utils.path_kit import get_file_path

warnings.filterwarnings('ignore')


# =====策略相关函数
def del_insufficient_data(symbol_candle_data) -> Dict[str, pd.DataFrame]:
    """
    删除数据长度不足的币种信息

    :param symbol_candle_data:
    :return
    """
    # ===删除成交量为0的线数据、k线数不足的币种
    symbol_list = list(symbol_candle_data.keys())
    for symbol in symbol_list:
        # 删除空的数据
        if symbol_candle_data[symbol] is None or symbol_candle_data[symbol].empty:
            del symbol_candle_data[symbol]
            continue
        # 删除该币种成交量=0的k线
        # symbol_candle_data[symbol] = symbol_candle_data[symbol][symbol_candle_data[symbol]['volume'] > 0]

    return symbol_candle_data


def ignore_error(anything):
    return anything


def load_min_qty(file_path: Path) -> (int, Dict[str, int]):
    # 读取min_qty文件并转为dict格式
    min_qty_df = pd.read_csv(file_path, encoding='utf-8-sig')
    min_qty_df['最小下单量'] = -np.log10(min_qty_df['最小下单量']).round().astype(int)
    default_min_qty = min_qty_df['最小下单量'].max()
    min_qty_df.set_index('币种', inplace=True)
    min_qty_dict = min_qty_df['最小下单量'].to_dict()

    return default_min_qty, min_qty_dict


def is_trade_symbol(symbol, black_list, white_list) -> bool:
    """
    过滤掉不能用于交易的币种，比如稳定币、非USDT交易对，以及一些杠杆币
    :param symbol: 交易对
    :param black_list: 黑名单
    :param white_list: 白名单
    :return: 是否可以进入交易，True可以参与选币，False不参与
    """
    symbol = symbol.upper().replace('-USDT', 'USDT')
    if white_list:
        if symbol in white_list:
            return True
        else:
            return False

    # 稳定币和黑名单币不参与
    if not symbol or not symbol.endswith('USDT') or symbol in black_list:
        return False

    # 筛选杠杆币
    base_symbol = symbol[:-4]
    if base_symbol.endswith(('UP', 'DOWN', 'BEAR', 'BULL')) and base_symbol != 'JUP' or base_symbol in stable_symbol:
        return False
    else:
        return True


def align_spot_swap_mapping(df, column_name, n):
    """
    处理spot和swap的映射关系
    :param df: 原始k线数据
    :param column_name: 需要处理的列
    :param n: 需要调整映射的周期数量
    :return: 调整好的k线数据
    """
    # 创建新组标识列
    df['is_new_group'] = (df[column_name].ne('') & df[column_name].shift().eq('')).astype(int)
    # 累积求和生成组号
    df['group'] = df['is_new_group'].cumsum()
    # 将空字符串对应的组号设为NaN
    df.loc[df['symbol_swap'].eq(''), 'group'] = np.nan
    # 通过 groupby 添加 grp_seq
    df['grp_seq'] = df.groupby('group').cumcount()
    # 过滤条件并修改前 n 行
    df.loc[df['grp_seq'] < n, column_name] = ''

    # 删除辅助列
    df.drop(columns=['is_new_group', 'group', 'grp_seq'], inplace=True)

    return df


def load_spot_and_swap_data(conf: BacktestConfig) -> (pd.DataFrame, pd.DataFrame):
    """
    加载现货和合约数据
    :param conf: 回测配置
    :return:
    """
    logger.debug('🧹 清理数据缓存')
    cache_path = get_file_path('data', 'cache', as_path_type=True)
    if cache_path.exists():
        shutil.rmtree(cache_path)

    logger.debug('💿 加载现货和合约数据...')
    # 读入合约数据
    symbol_swap_candle_data = pd.read_pickle(swap_path)
    # 过滤掉不能用于交易的币种
    symbol_swap_candle_data = {
        k: align_spot_swap_mapping(v, 'symbol_spot', conf.min_kline_num)
        for k, v in symbol_swap_candle_data.items()
        if is_trade_symbol(k, conf.black_list, conf.white_list)
    }

    # 过滤掉数据不足的币种
    all_candle_df_list = list(del_insufficient_data(symbol_swap_candle_data).values())
    all_symbol_list = set(symbol_swap_candle_data.keys())

    # 读入现货数据
    if conf.is_use_spot:
        symbol_spot_candle_data = pd.read_pickle(spot_path)
        # 过滤掉不能用于交易的币种
        symbol_spot_candle_data = {
            k: align_spot_swap_mapping(v, 'symbol_swap', conf.min_kline_num)
            for k, v in symbol_spot_candle_data.items()
            if is_trade_symbol(k, conf.black_list, conf.white_list)
        }

        # 过滤掉数据不足的币种
        all_candle_df_list = all_candle_df_list + list(del_insufficient_data(symbol_spot_candle_data).values())
        all_symbol_list = list(all_symbol_list | set(symbol_spot_candle_data.keys()))
        del symbol_spot_candle_data

    # 保存数据
    pkl_path = get_file_path('data', 'cache', 'all_candle_df_list.pkl')
    pd.to_pickle(all_candle_df_list, pkl_path)

    del symbol_swap_candle_data
    del all_candle_df_list

    gc.collect()

    return tuple(all_symbol_list)  # 节省内存，包装成tuple


def save_performance_df_csv(conf: BacktestConfig, **kwargs):
    # logger.debug(f'💾 保存回测结果到文件夹: {conf.get_result_folder()}')
    for name, df in kwargs.items():
        file_path = conf.get_result_folder() / f'{name}.csv'
        df.to_csv(file_path, encoding='utf-8-sig')


# ===============================================================================================================
# 额外数据源
# ===============================================================================================================
def merge_data(df: pd.DataFrame, data_name: str, save_cols: List[str], symbol: str = '') -> dict[str, pd.Series]:
    """
    导入数据，最终只返回带有同index的数据
    :param df: （只读）原始的行情数据，主要是对齐数据用的
    :param data_name: 数据中心中的数据英文名
    :param save_cols: 需要保存的列
    :param symbol: 币种
    :return: 合并后的数据
    """
    import core.data_bridge as db
    from config import data_source_dict

    func_name, file_path = data_source_dict[data_name]

    if hasattr(db, func_name):
        extra_df: pd.DataFrame = getattr(db, func_name)(file_path, df, save_cols, symbol)
    else:
        print(f'⚠️ 未实现数据源：{data_name}')
        return {col: pd.Series([np.nan] * len(df)) for col in save_cols}

    if extra_df is None or extra_df.empty:
        return {col: pd.Series([np.nan] * len(df)) for col in save_cols}

    return {col: extra_df[col] for col in save_cols}


def check_cfg():
    """
    检查 data_source_dict 配置
    检查加载数据源函数是否存在
    检查数据源文件是否存在
    :return:
    """
    import core.data_bridge as db
    from config import data_source_dict
    for key, value in data_source_dict.items():
        func_name, file_path = value
        if not hasattr(db, func_name):
            raise Exception(f"【{key}】加载数据源方法未实现：{func_name}")

        if not (file_path and Path(file_path).exists()):
            raise Exception(f"【{key}】数据源文件不存在：{file_path}")

    print('✅ data_source_dict 配置检查通过')


def check_factor(factors: list):
    """
    检查因子中的配置
    检查是否有 extra_data_dict
    检查 extra_data_dict 中的数据源是否在 data_source_dict 中

    因子中的外部数据使用案例:

    extra_data_dict = {
        'coin-cap': ['circulating_supply']
    }

    :param factors:
    :return:
    """
    from core.utils.factor_hub import FactorHub
    for factor_name in factors:
        factor = FactorHub.get_by_name(factor_name)  # 获取因子信息
        if not (hasattr(factor, 'extra_data_dict') and factor.extra_data_dict):
            raise Exception(f"未找到【{factor_name}】因子中 extra_data_dict 配置")

        for data_source in factor.extra_data_dict.keys():
            from config import data_source_dict
            if data_source not in data_source_dict:
                raise Exception(f"未找到 extra_data_dict 配置的数据源：{data_source}")

    print(f'✅ {factors} 因子配置检查通过')
