"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

import gc
import os
import time
import warnings

import numpy as np
import pandas as pd
from tqdm import tqdm

from config import utc_offset, special_symbol_dict, order_path, runtime_folder
from core.model.account_config import AccountConfig
from core.model.strategy_config import StrategyConfig
from core.utils.factor_hub import FactorHub
from core.utils.log_kit import logger
from core.utils.memory_kit import reduce_mem_series
from core.utils.path_kit import get_file_path

warnings.filterwarnings('ignore')
# pandas相关的显示设置，基础课程都有介绍
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

FACTOR_KLINE_COL_LIST = ['candle_begin_time', 'symbol', 'symbol_type', 'tag', 'close']

# 创建选币文件夹，后面会用到
(runtime_folder / 'select_coin').mkdir(parents=True, exist_ok=True)


# ======================================================================================
# 因子计算相关函数
# - calc_factors_by_symbol: 计算单个币种的因子池
# - calc_factors: 计算因子池
# ======================================================================================
# region 因子计算相关函数
def calc_factors_by_candle(candle_df, account_conf: AccountConfig, run_time) -> pd.DataFrame:
    """
    针对单一比对，计算所有因子的数值
    :param candle_df: 一个币种的k线数据 dataframe
    :param account_conf: 账户配置
    :param run_time: 当前运行时间
    :return: 包含所有因子的 dataframe(目前是包含k线数据的）
    """
    # 遍历每个因子，计算每个因子的数据
    all_factor_val_list = []
    for factor_name, param_list in account_conf.factor_params_dict.items():
        factor = FactorHub.get_by_name(factor_name)  # 获取因子信息

        # 如果存在外部数据，则使用 data_bridge 中的加载函数 load 数据
        if hasattr(factor, 'extra_data_dict') and factor.extra_data_dict:
            from core.utils.datatools import merge_data
            for data_name in factor.extra_data_dict.keys():
                extra_data_dict = merge_data(candle_df, data_name, factor.extra_data_dict[data_name])
                for extra_data_name, extra_data_series in extra_data_dict.items():
                    candle_df[extra_data_name] = extra_data_series.values

        # 根据因子内部的函数，来判断是否进行加速操作
        if hasattr(factor, 'signal_multi_params'):  # 如果存在 signal_multi_params ，使用最新的因子加速写法
            result_dict = factor.signal_multi_params(candle_df, param_list)
            # 创建一个新的 DataFrame，列名为 result_dict 的键
            factor_val_df = pd.DataFrame(result_dict)
            # 给新 DataFrame 的列加上前缀
            factor_val_df = factor_val_df.add_prefix(f'{factor_name}_')
            all_factor_val_list.append(factor_val_df)
        else:  # 如果存在 signal，使用之前的老因子写法
            param_col_list = []
            legacy_candle_df = candle_df.copy()  # 如果是老的因子计算逻辑，单独拿出来一份数据
            for param in param_list:
                factor_col_name = f'{factor_name}_{str(param)}'
                param_col_list.append(factor_col_name)
                legacy_candle_df = factor.signal(legacy_candle_df, param, factor_col_name)
            all_factor_val_list.append(legacy_candle_df[param_col_list])

    # 将结果 DataFrame 与原始 DataFrame 合并
    kline_with_factor_df = pd.concat((candle_df, *all_factor_val_list), axis=1)

    # 只保留最近的数据
    if run_time and account_conf.max_hold_period:
        min_candle_time = run_time - pd.to_timedelta(account_conf.max_hold_period) - pd.Timedelta(hours=utc_offset)
        kline_with_factor_df = kline_with_factor_df[kline_with_factor_df['candle_begin_time'] >= min_candle_time]

    # 只保留需要的字段
    return kline_with_factor_df[FACTOR_KLINE_COL_LIST + account_conf.factor_col_name_list]


def calc_factors(account_conf: AccountConfig, run_time):
    """
    选币因子计算
    :param account_conf:       账户信息
    :param run_time:           回测时间
    :return:
    """
    # ====================================================================================================
    # 1. ** k线数据整理及参数准备 **
    # - is_use_spot: True的时候，使用现货数据和合约数据;
    # - False的时候，只使用合约数据。所以这个情况更简单
    # ====================================================================================================
    # hold_period的作用是计算完因子之后，
    # 获取最近 hold_period 个小时内的数据信息，
    # 同时用于offset字段计算使用

    # ====================================================================================================
    # 2. ** 因子计算 **
    # 遍历每个币种，计算相关因子数据
    # ====================================================================================================
    all_factor_df_list = []
    for index in list(range(0, account_conf.chunk_num, 1)):
        candle_df_list = pd.read_pickle(runtime_folder / f'all_candle_df_list_{index}.pkl')

        # 针对每一个币种的k线数据，按照策略循环计算因子信息
        for candle_df in tqdm(candle_df_list, desc='🧮 因子计算', total=len(candle_df_list)):
            # 转换格式，节省内存
            candle_df['symbol'] = pd.Categorical(candle_df['symbol'])
            candle_df.reset_index(drop=True, inplace=True)

            # ==== 计算因子 ====
            # 针对单个币种的K线数据计算
            # 返回带有因子数值的K线数据
            factor_df = calc_factors_by_candle(candle_df, account_conf, run_time)

            if factor_df is None or factor_df.empty:
                continue

            all_factor_df_list.append(factor_df)
            del candle_df
            del factor_df

    # ====================================================================================================
    # 3. ** 合并因子结果 **
    # 合并并整理所有K线，到这里因子计算完成
    # ====================================================================================================
    all_factors_df = pd.concat(all_factor_df_list, ignore_index=True)
    del all_factor_df_list

    # ====================================================================================================
    # 4. ** 因子结果分片存储 **
    # 分片存储计算结果，节省内存占用，提高选币效率
    # - 将合并好的df，分成2个部分：k线和因子列
    # - k线数据存储为一个pkl，每一列因子存储为一个pkl，在选币时候按需读入合并成df
    # ====================================================================================================
    logger.debug('💾 分片存储因子结果...')
    # 选币需要的k线
    all_factors_df[FACTOR_KLINE_COL_LIST].to_pickle(runtime_folder / 'all_factors_kline.pkl')

    # 针对每一个因子进行存储
    for factor_col_name in account_conf.factor_col_name_list:
        all_factors_df[factor_col_name].to_pickle(runtime_folder / f'all_factors_{factor_col_name}.pkl')

    del all_factors_df

    gc.collect()
    return None  # 这边就不返回了，节省内存支出


# endregion

# ======================================================================================
# 选币相关函数
# - calc_select_factor_rank: 计算因子排序
# - select_long_and_short_coin: 选做多和做空的币种
# - select_coins_by_strategy: 根据策略选币
# - select_coins: 选币，循环策略调用 `select_coins_by_strategy`
# ======================================================================================
# region 选币相关函数
def calc_select_factor_rank(df, factor_column='因子', ascending=True):
    """
    计算因子排名
    :param df:              原数据
    :param factor_column:   需要计算排名的因子名称
    :param ascending:       计算排名顺序，True：从小到大排序；False：从大到小排序
    :return:                计算排名后的数据框
    """
    # 计算因子的分组排名
    df['rank'] = df.groupby('candle_begin_time')[factor_column].rank(method='min', ascending=ascending)
    df['rank_max'] = df.groupby('candle_begin_time')['rank'].transform('max')
    # 根据时间和因子排名排序
    df.sort_values(by=['candle_begin_time', 'rank'], inplace=True)
    # 重新计算一下总币数
    df['总币数'] = df.groupby('candle_begin_time')['symbol'].transform('size')
    return df


def select_long_and_short_coin(strategy: StrategyConfig, long_df: pd.DataFrame, short_df: pd.DataFrame):
    """
    选币，添加多空资金权重后，对于无权重的情况，减少选币次数

    :param strategy:                策略，包含：多头选币数量，空头选币数量，做多因子名称，做空因子名称，多头资金权重，空头资金权重
    :param long_df:                 多头选币的df
    :param short_df:                空头选币的df
    :return:
    """
    """
    # 做多选币
    """
    if strategy.long_cap_weight > 0:
        long_df = calc_select_factor_rank(long_df, factor_column=strategy.long_factor, ascending=True)

        long_df = strategy.select_by_coin_num(long_df, strategy.long_select_coin_num)

        long_df['方向'] = 1
        long_df['target_alloc_ratio'] = 1 / long_df.groupby('candle_begin_time')['symbol'].transform('size')
    else:
        long_df = pd.DataFrame()

    """
    # 做空选币
    """
    if strategy.short_cap_weight > 0:
        short_df = calc_select_factor_rank(short_df, factor_column=strategy.short_factor, ascending=False)

        if strategy.short_select_coin_num == 'long_nums':  # 如果参数是long_nums，则空头与多头的选币数量保持一致
            # 获取到多头的选币数量并整理数据
            long_select_num = long_df.groupby('candle_begin_time')['symbol'].size().to_frame()
            long_select_num = long_select_num.rename(columns={'symbol': '多头数量'}).reset_index()
            # 将多头选币数量整理到short_df
            short_df = short_df.merge(long_select_num, on='candle_begin_time', how='left')
            # 使用多头数量对空头数据进行选币
            short_df = short_df[short_df['rank'] <= short_df['多头数量']]
            del short_df['多头数量']
        else:
            short_df = strategy.select_by_coin_num(short_df, strategy.short_select_coin_num)

        short_df['方向'] = -1
        short_df['target_alloc_ratio'] = 1 / short_df.groupby('candle_begin_time')['symbol'].transform('size')
    else:
        short_df = pd.DataFrame()

    # ===整理数据
    df = pd.concat([long_df, short_df], ignore_index=True)  # 将做多和做空的币种数据合并
    df.sort_values(by=['candle_begin_time', '方向'], ascending=[True, False], inplace=True)
    df.reset_index(drop=True, inplace=True)

    del df['总币数'], df['rank_max']

    return df


def select_coins_by_strategy(factor_df, stg_conf: StrategyConfig):
    """
    针对每一个策略，进行选币，具体分为以下4步：
    - 4.1 数据清洗
    - 4.2 计算目标选币因子
    - 4.3 前置过滤筛选
    - 4.4 根据选币因子进行选币
    :param factor_df: 所有币种K线数据，仅包含部分行情数据和选币需要的因子列
    :param stg_conf: 策略配置
    :return: 选币数据
    """

    """
    4.1 数据预处理
    **实盘专属操作** - 在实盘过程中裁切最后一个周期的数据
    """
    # 裁切当前策略需要的数据长度，保留最后一个周期的交易和因子数据
    max_candle_time = factor_df['candle_begin_time'].max() + pd.to_timedelta(f"1{stg_conf.hold_period[-1]}")
    min_candle_time = max_candle_time - pd.to_timedelta(stg_conf.hold_period)  # k线本身就是utc时间，不用做时区处理
    factor_df = factor_df[factor_df['candle_begin_time'] >= min_candle_time]
    # 最终选币结果，也只有最后一个周期的

    """
    4.2 计算目标选币因子
    - 计算详情在 `strategy -> *.py`
    """
    # 缓存计算前的列名
    prev_cols = factor_df.columns
    # 计算因子
    # result_df = stg_conf.calc_factor(factor_df, external_list=stg_conf.factor_list)
    result_df = stg_conf.calc_select_factor(factor_df)
    # 合并新的因子
    factor_df = factor_df[prev_cols].join(result_df[list(set(result_df.columns) - set(prev_cols))])

    """
    4.3 前置过滤筛选
    - 计算详情在 `strategy -> *.py`
    """
    # long_df, short_df = stg_conf.before_filter(factor_df, ex_filter_list=stg_conf.filter_list)
    long_df, short_df = stg_conf.filter_before_select(factor_df)
    if stg_conf.is_use_spot:  # 使用现货数据，则在现货中进行过滤，并选币
        short_df = short_df[short_df['tag'] == 1]  # 保留有合约的现货

    """
    4.4 根据选币因子进行选币
    """
    # 多头选币数据、空头选币数据、策略配置
    factor_df = select_long_and_short_coin(stg_conf, long_df, short_df)

    """
    4.5 后置过滤筛选
    """
    factor_df = stg_conf.filter_after_select(factor_df)

    """
    4.6 根据多空比调整币种的权重
    """
    long_ratio = stg_conf.long_cap_weight / (stg_conf.long_cap_weight + stg_conf.short_cap_weight)
    factor_df.loc[factor_df['方向'] == 1, 'target_alloc_ratio'] = factor_df['target_alloc_ratio'] * long_ratio
    factor_df.loc[factor_df['方向'] == -1, 'target_alloc_ratio'] = factor_df['target_alloc_ratio'] * (1 - long_ratio)
    factor_df = factor_df[factor_df['target_alloc_ratio'].abs() > 1e-9]  # 去除权重为0的数据

    return factor_df[['candle_begin_time', 'symbol', 'symbol_type', 'close', 'tag', '方向', 'target_alloc_ratio']]


# 选币数据整理 & 选币
def select_coins(account_config: AccountConfig):
    """
    ** 策略选币 **
    - is_use_spot: True的时候，使用现货数据和合约数据;
    - False的时候，只使用合约数据。所以这个情况更简单

    :param account_config: 账户配置
    :return:
    """
    # ====================================================================================================
    # 1. ** 相关变量初始化 **
    # ====================================================================================================

    # ====================================================================================================
    # 2. ** 循环每一个策略计算 **
    # ====================================================================================================
    for _index, stg_conf in enumerate(account_config.strategy_list):
        # ====================================================================================================
        # 2.1 初始化
        # ====================================================================================================
        s = time.time()
        logger.info(f'{_index + 1} / {len(account_config.strategy_list)}: {stg_conf.name} 开始选币...')

        # 获取当前策略信息
        # - 可以通过strategy来访问策略的参数和方法
        # - 策略详情在 `strategy -> *.py`
        # - 可以通过 strategy. 来访问py文件中定义的变量，或者使用定义的方法
        if account_config.is_pure_long:
            stg_conf.long_cap_weight = 1
            stg_conf.short_cap_weight = 0
            stg_conf.short_select_coin_num = 0

        # ====================================================================================================
        # 2.2 准备选币用数据，
        # - 筛选策略选币要用的指标列名
        # - 删除选币因子为空的数据
        # - 打印一下被删除的币种信息
        # ====================================================================================================
        # 选币因子专用的列，筛选出来
        factor_col_name_list = list(stg_conf.factor_columns)

        # 裁切k线数据备用
        factor_df = pd.read_pickle(runtime_folder / 'all_factors_kline.pkl')
        for factor_col_name in factor_col_name_list:
            factor_df[factor_col_name] = pd.read_pickle(runtime_folder / f'all_factors_{factor_col_name}.pkl')
        # 裁切k线数据备用
        condition = (factor_df['symbol_type'] == ('spot' if stg_conf.is_use_spot else 'swap'))
        factor_df = factor_df.loc[condition, :].copy()

        # 保存原始的symbol和symbol_type列的组合，并去重
        original_symbols = set(factor_df['symbol'].unique())

        # 删除选币因子为空的数据
        factor_df.dropna(subset=factor_col_name_list, inplace=True)  # 删除选币因子为空的数据

        # 找出被删除的symbol
        deleted_symbols = original_symbols - set(factor_df['symbol'].unique())

        # 输出被删除的symbol和symbol_type组合
        if deleted_symbols:
            logger.warning(
                f'{stg_conf.name}原始数据中，以下选币因子{factor_col_name_list}为空的数据被删除:')
            logger.debug(deleted_symbols)

        # 整理一下数据结构，准备选币
        factor_df.sort_values(by=['candle_begin_time', 'symbol'], inplace=True)
        factor_df.reset_index(drop=True, inplace=True)

        # ====================================================================================================
        # 2.3 计算选币结果
        # ====================================================================================================
        result_df = select_coins_by_strategy(factor_df, stg_conf)

        # 如果选币为空，直接继续计算
        if result_df.empty:
            continue  # 这里不能返回 pd.Dataframe ,因为缺少后面计算的字段

        del factor_df

        # ====================================================================================================
        # 2.4 筛选合适的offset
        # ====================================================================================================
        cal_offset_base_seconds = 3600 * 24 if stg_conf.is_day_period else 3600
        reference_date = pd.to_datetime('2017-01-01')
        time_diff_seconds = (result_df['candle_begin_time'] - reference_date).dt.total_seconds()
        offset = (time_diff_seconds / cal_offset_base_seconds).mod(stg_conf.period_num).astype('int8')
        # 下单之后，开始持仓offset
        result_df['offset'] = ((offset + 1 + stg_conf.period_num) % stg_conf.period_num).astype('int8')
        # 保留配置中的offset数据
        result_df = result_df[result_df['offset'].isin(stg_conf.offset_list)]

        if result_df.empty:  # 如果选币为空，直接返回空的all_df
            continue

        # ====================================================================================================
        # 2.5 添加其他的相关选币信息
        # ====================================================================================================
        result_df['strategy'] = np.int8(_index)
        result_df['cap_weight'] = np.float16(stg_conf.cap_weight)
        result_df['offset_num'] = np.int8(len(stg_conf.offset_list))
        result_df['换仓时间'] = result_df['candle_begin_time'] + pd.to_timedelta(stg_conf.hold_period)
        # 数据结构优化
        result_df['close'] = result_df['close']
        result_df['方向'] = reduce_mem_series(result_df['方向'])
        result_df['offset'] = reduce_mem_series(result_df['offset'])
        result_df['offset_num'] = reduce_mem_series(result_df['offset_num'])
        result_df['target_alloc_ratio'] = result_df['target_alloc_ratio'] * result_df['cap_weight'] / result_df[
            'offset_num']

        # ====================================================================================================
        # 2.6 缓存到本地文件，一个策略的选币结果一个文件
        # ====================================================================================================
        result_df[
            [*FACTOR_KLINE_COL_LIST, 'strategy', 'cap_weight', 'offset_num', '方向', '换仓时间', 'offset',
             'target_alloc_ratio']].to_pickle(get_file_path(runtime_folder, 'select_coin', f'{stg_conf.name}.pkl'))

        logger.ok(f'{stg_conf.name} 完成. 耗时: {(time.time() - s):.2f}s')

    # ====================================================================================================
    # 3. 缓存一下配置的所有策略的信息
    # 保证和我们index是对齐的（不依赖于config）
    # ====================================================================================================
    gc.collect()
    return


# endregion

# ======================================================================================
# 选币结果聚合
# ======================================================================================
# region 选币结果聚合
def transfer_swap(select_coin, df_swap):
    """
    将现货中的数据替换成合约数据，主要替换：close
    :param select_coin:     选币数据
    :param df_swap:         合约数据
    :return:
    """
    # 反转k,v的对应关系。现货对应合约，转换 ，合约对应现货
    _special_symbol_dict = {v: k for k, v in special_symbol_dict.items()}
    # 整理币种名称，使合约和现货的币种名称相同
    df_swap['symbol_spot'] = df_swap['symbol'].apply(lambda x: _special_symbol_dict.get(x.replace('USDT', ''), (
        x.split('1000')[1] if '1000' in x else x).replace('USDT', '')) + 'USDT')
    # 设置指定字段
    df_swap = df_swap[['candle_begin_time', 'symbol', 'symbol_type', 'close', 'tag', 'symbol_spot']]

    # 将选币结果中是否含有合约的数据筛选出来
    not_swap_df = select_coin[select_coin['tag'] == 0]
    has_swap_df = select_coin[select_coin['tag'] == 1]  # 对含有合约的现货数据进行处理

    # 设置需要替换的字段
    other_cols = list(set(select_coin.columns) - set(df_swap.columns))
    has_swap_df = pd.merge(left=has_swap_df[['candle_begin_time', 'symbol'] + other_cols], right=df_swap,
                           left_on=['candle_begin_time', 'symbol'], right_on=['candle_begin_time', 'symbol_spot'],
                           how='left', suffixes=('', '_swap'))
    failed_merge_df = has_swap_df[has_swap_df['symbol_swap'].isna()].copy()
    has_swap_df = has_swap_df[~has_swap_df['symbol_swap'].isna()]
    has_swap_df['symbol'] = has_swap_df['symbol_swap']
    del has_swap_df['symbol_swap'], has_swap_df['symbol_spot']

    # 将拆分的选币数据，合并回去
    failed_merge_select_coin = failed_merge_df.merge(
        select_coin, on=['candle_begin_time', 'symbol', 'strategy', '方向', 'offset', 'offset_num'],
        how='left', suffixes=('_swap', ''))
    failed_merge_select_coin.drop(columns=[_ for _ in failed_merge_select_coin.columns if _.endswith('_swap')],
                                  inplace=True)
    failed_merge_select_coin['方向'] = 1
    del failed_merge_select_coin['symbol_spot']
    select_coin = pd.concat([not_swap_df, has_swap_df, failed_merge_select_coin], axis=0)
    select_coin.sort_values(['candle_begin_time', '方向'], inplace=True)
    select_coin.reset_index(inplace=True, drop=True)

    return select_coin


def concat_select_results(account_config: AccountConfig) -> None:
    """
    聚合策略选币结果，形成综合选币结果
    :param account_config:
    :return:
    """
    # 如果是纯多头现货模式，那么就不转换合约数据，只下现货单
    logger.debug('💿 读入选币结果...')
    all_select_result_df_list = []  # 存储每一个策略的选币结果

    for stg_conf in account_config.strategy_list:
        file_path = get_file_path(runtime_folder, 'select_coin', f'{stg_conf.name}.pkl')

        # 如果文件不存在，就跳过
        if not os.path.exists(file_path):
            continue

        all_select_result_df_list.append(pd.read_pickle(file_path))

    # 如果没有任何策略的选币结果，就直接返回
    if not all_select_result_df_list:
        return

    # 聚合选币结果
    all_select_result_df = pd.concat(all_select_result_df_list, ignore_index=True)
    del all_select_result_df_list
    gc.collect()
    all_select_result_df.to_pickle(runtime_folder / 'all_select_result_df.pkl')


def process_select_results(account_config: AccountConfig) -> pd.DataFrame:
    logger.debug('🔄 SPOT替换为SWAP来节省手续费...')
    all_select_result_file_path = runtime_folder / 'all_select_result_df.pkl'
    if not os.path.exists(all_select_result_file_path):
        return pd.DataFrame(columns=['candle_begin_time', 'symbol', 'symbol_type'])

    all_select_result_df = pd.read_pickle(all_select_result_file_path)

    # 不是纯多，且是现货策略
    if (not account_config.is_pure_long) and account_config.use_spot:
        all_factors_df = pd.read_pickle(runtime_folder / 'all_factors_kline.pkl')

        # 将含有现货的币种，替换掉其中close价格
        df_swap = all_factors_df[all_factors_df['symbol_type'] == 'swap']
        all_select_result_df = transfer_swap(all_select_result_df, df_swap)

    return all_select_result_df


def save_and_merge_select(account_config: AccountConfig, select_coin, run_time):
    if select_coin.empty:
        return select_coin

    account_config.update_account_info()

    # 构建本次存放选币下单的文件
    order_file = os.path.join(order_path, f'{account_config.name}_order.csv')

    # 杠杆为0，表示清仓
    if account_config.leverage == 0:
        select_coin.drop(select_coin.index, inplace=True)
        # 清仓之后删除本地文件
        if os.path.exists(order_file):
            os.remove(order_file)
        return select_coin

    # ==计算目标持仓量
    # 获取当前账户总资金
    all_equity = account_config.swap_equity + account_config.spot_equity
    # 判断是否是纯多头交易
    if (len(select_coin['方向'].unique()) == 1) and (1 in select_coin['方向']):
        # 如果手续费占总资金的比例 超过 千1，动态调整一下杠杆
        if account_config.buy_bnb_value / (account_config.swap_equity + account_config.spot_equity) >= 0.001:
            # 如果当前选币为纯多，自动降低下单杠杆5%，防止现货下单滑点的影响（因为现货杠杆不能超过1，所以直接设置0.95）
            all_equity = all_equity * min(0.95, 0.95 * account_config.leverage)
        else:  # 如果手续费占总资金的比例 小于 千1，减去300
            all_equity = all_equity * min(1, account_config.leverage) - 300
    else:  # 其他交易状态
        all_equity = all_equity * account_config.leverage

    # 引入'target_alloc_ratio' 字段，在选币的时候 target_alloc_ratio = 1 * 多空比 / 选币数量 / offset_num * cap_weight
    select_coin['单币下单金额'] = all_equity * select_coin['target_alloc_ratio'].astype(np.float64) / 1.001

    # 获取最新价格
    swap_price = account_config.bn.get_swap_ticker_price_series()
    spot_price = account_config.bn.get_spot_ticker_price_series()

    select_coin.dropna(subset=['symbol'], inplace=True)
    select_coin = select_coin[select_coin['symbol'].isin([*swap_price.index, *spot_price.index])]
    select_coin['最新价格'] = select_coin.apply(
        lambda res_row: swap_price[res_row['symbol']] if res_row['symbol_type'] == 'swap' else spot_price[
            res_row['symbol']], axis=1
    )
    select_coin['目标持仓量'] = select_coin['单币下单金额'] / select_coin['最新价格'] * select_coin['方向']

    # 设置指定字段保留
    cols = ['candle_begin_time', '换仓时间', 'symbol', 'symbol_type', 'close', '方向', 'offset', 'strategy',
            'cap_weight', 'offset_num', 'target_alloc_ratio', '单币下单金额', '目标持仓量', '最新价格']
    select_coin = select_coin[cols]
    if account_config.if_rebalance:
        return select_coin

    # 判断本地是否存在下单文件
    # if os.path.exists(order_file):
    #     # 读取本地文件
    #     local_order_df = pd.read_csv(order_file, encoding='gbk', parse_dates=['candle_begin_time', '换仓时间'])
    #
    #     local_order_df['最新价格'] = local_order_df.apply(
    #         lambda price_row: swap_price[price_row['symbol']] if price_row['symbol_type'] == 'swap' else spot_price[
    #             price_row['symbol']],
    #         axis=1
    #     )
    #
    #     # 当前持仓的资金是多少
    #     spot_df = local_order_df[local_order_df['symbol_type'] == 'spot']
    #     swap_df = local_order_df[local_order_df['symbol_type'] == 'swap']
    #     pos_equity = swap_df['单币下单金额'].sum() + sum(spot_df['目标持仓量'] * spot_df['最新价格'])
    #     # 加减仓的资金
    #     dynamic_equity = all_equity - pos_equity
    #     # 按照策略资金比例分配加仓金额
    #     local_order_df['加仓金额'] = dynamic_equity * local_order_df['target_alloc_ratio'].astype(np.float64)
    #
    #     # 获取当前最新的策略信息
    #     strategy_list = pd.concat([local_order_df[['strategy', 'offset']], select_coin[['strategy', 'offset']]])
    #     strategy_list.drop_duplicates(subset=['strategy', 'offset'], keep='last', inplace=True)
    #     strategy_list.reset_index(inplace=True, drop=True)
    #
    #     # 按照策略进行遍历
    #     for index, row in strategy_list.iterrows():
    #         # 本地当前策略数据
    #         cond1 = (local_order_df['strategy'] == row['strategy']) & (local_order_df['offset'] == row['offset'])
    #         _local_df = local_order_df[cond1]
    #         # 最新选币的策略数据
    #         cond2 = (select_coin['strategy'] == row['strategy']) & (select_coin['offset'] == row['offset'])
    #         _select_df = select_coin[cond2]
    #         # 本地存储数据为空，表示是新增的策略需要按照最新的资金进行分配处理，直接将 _select_df 数据追加到 local_order_df 中
    #         if _local_df.empty:
    #             local_order_df = pd.concat([local_order_df, _select_df], ignore_index=True)
    #             continue
    #
    #         # 选币数据为空，表示是移除的策略需要按照最新的资金进行分配处理，直接将 _local_df 数据移除 local_order_df
    #         if _select_df.empty:
    #             local_order_df = local_order_df.loc[~cond1]
    #             continue
    #
    #         # 本地文件数据进入换仓阶段，
    #         if _local_df.iloc[0]['换仓时间'] + pd.Timedelta(hours=utc_offset) <= run_time:
    #             # 删除掉本地需要换仓的数据
    #             local_order_df.drop(_local_df.index, inplace=True)
    #             # 计算平仓资金，用来进行换仓时使用
    #             pos_net = (_local_df['close'] + _local_df['方向'] * (_local_df['最新价格'] - _local_df['close'])) * abs(
    #                 _local_df['目标持仓量'])
    #             pos_net = sum(pos_net)
    #             if _local_df.iloc[0]['换仓时间'] + pd.Timedelta(hours=utc_offset) == run_time:
    #                 pos_net += _local_df['加仓金额'].sum()
    #             # 根据上周期平仓时仓位价值，来开下周期的仓位
    #             _select_df['单币下单金额'] = pos_net * _select_df['target_alloc_ratio'].astype(np.float64)
    #             # 将需要换仓的数据合并过来
    #             local_order_df = pd.concat([local_order_df, _select_df], ignore_index=True)
    #         else:
    #             # 计算当前最新的资金比例
    #             local_order_df.loc[cond1, 'cap_weight'] = _select_df['cap_weight'].iloc[0]  # 同一个策略下的资金占比是一样的
    #             # 计算当前最新的单币下单金额
    #             local_order_df.loc[cond1, '单币下单金额'] = local_order_df.loc[cond1, 'cap_weight'] / np.array(
    #                 _local_df['cap_weight']) * _local_df['单币下单金额'] + _local_df['加仓金额']
    #
    #     # 计算最新的目标持仓量
    #     local_order_df['目标持仓量'] = local_order_df['单币下单金额'] / local_order_df['close'] * local_order_df['方向']
    #
    #     # 覆盖掉 select_coin
    #     select_coin = local_order_df.copy()
    # else:
    #     select_coin['加仓金额'] = 0  # 首次默认设置加仓金额为0
    #
    # # 保存筛选后的选币文件
    # select_coin.reset_index(inplace=True, drop=True)
    # select_coin.to_csv(order_file, encoding='gbk', index=False)

    return select_coin
# endregion
