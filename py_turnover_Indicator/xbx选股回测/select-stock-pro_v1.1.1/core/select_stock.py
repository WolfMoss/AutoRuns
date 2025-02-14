"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List

import numpy as np
import pandas as pd
from tqdm import tqdm

from config import n_jobs, runtime_folder
from core.data_center import check_extra_data, merge_extra_data
from core.equity import calc_equity
from core.fin_essentials import merge_with_finance_data
from core.model.backtest_config import BacktestConfig
from core.model.strategy_config import get_col_name
from core.utils.factor_hub import FactorHub
from core.utils.log_kit import logger

# 因子计算之后，需要保存的行情数据
FACTOR_COLS = [
    '交易日期', '股票代码', '股票名称',
    '上市至今交易天数', '复权因子', '开盘价', '最高价', '最低价', '收盘价', '成交额', '是否交易', '流通市值', '总市值',
    '下日_开盘涨停', '下日_是否ST', '下日_是否交易', '下日_是否退市'
]
KLINE_COLS = ['交易日期', '股票代码', '股票名称']
# 计算完选股之后，保留的字段
RES_COLS = ['选股日期', '股票代码', '股票名称', '策略', '持仓周期', '换仓时间', '目标资金占比']


# ================================================================
# step2_计算因子.py
# ================================================================
def cal_strategy_factors(conf: BacktestConfig, stock_code, candle_df, fin_data: Dict[str, pd.DataFrame] = None):
    """
    计算指定股票的策略因子。

    参数:
    conf (BacktestConfig): 策略配置
    stock_code (str): 股票代码
    candle_df (DataFrame): 股票的K线数据，已经按照“交易日期”从小到大排序
    fin_data (dict): 财务数据

    返回:
    DataFrame: 包含计算因子的K线数据
    dict: 因子列的周期转换规则
    """
    factor_series_dict = {}
    before_len = len(candle_df)

    candle_df.sort_values(by='交易日期', inplace=True)  # 防止因子计算出错，计算之前，先进行排序
    for factor_name, param_list in conf.factor_params_dict.items():
        factor_file = FactorHub.get_by_name(factor_name)
        for param in param_list:
            col_name = get_col_name(factor_name, param)

            # 因子计算，factor_df是包含因子计算结果的DataFrame，必须是按照“交易日期”从小到大排序
            factor_df = factor_file.add_factor(candle_df.copy(), param, fin_data=fin_data, col_name=col_name)

            factor_series_dict[col_name] = factor_df[col_name].values
            # 检查因子计算是否出错
            if before_len != len(factor_series_dict[col_name]):
                logger.error(f'{stock_code}的{factor_name}因子({param}，{col_name})导致数据长度发生变化，请检查！')
                raise Exception('因子计算出错，请避免在cal_factors中修改数据行数')

    kline_with_factor_dict = {
        **{col_name: candle_df[col_name] for col_name in FACTOR_COLS},
        **factor_series_dict,
    }
    kline_with_factor_df = pd.DataFrame(kline_with_factor_dict)
    kline_with_factor_df.sort_values(by='交易日期', inplace=True)
    return kline_with_factor_df


def process_by_stock(conf: BacktestConfig, stock_code: str, candle_df: pd.DataFrame):
    # 导入财务数据，将个股数据与财务数据合并，并计算财务指标的衍生指标
    if conf.fin_cols:  # 前面已经做了预检，这边只需要动态台南佳即可
        # 分别为：个股数据、财务数据、原始财务数据（不抛弃废弃的报告数据）
        candle_df, fin_df, raw_fin_df = merge_with_finance_data(conf, stock_code, candle_df)
        fin_data = {'财务数据': fin_df, '原始财务数据': raw_fin_df}
    else:
        fin_data = None

    if conf.extra_data:
        # 个股数据与其他数据合并
        for data_name in conf.extra_data.keys():
            candle_df = merge_extra_data(candle_df, data_name, conf.extra_data[data_name])

    # 计算因子，并且获得新的因子列的周期转换规则
    factor_df = cal_strategy_factors(conf, stock_code, candle_df, fin_data=fin_data)

    return factor_df


def calculate_factors(conf: BacktestConfig, boost: bool = True):
    """
    计算所有股票的因子，分为三步：
    1. 加载股票K线数据
    2. 计算每个股票的因子，并存储到列表
    3. 合并所有因子数据并存储

    参数:
    conf (BacktestConfig): 回测配置
    """
    logger.info(f'因子计算...')
    s_time = time.time()

    # ====================================================================================================
    # 1. 加载股票K线数据
    # ====================================================================================================
    logger.debug('🛂 配置信息检查...')
    if len(conf.fin_cols) > 0 and not conf.has_fin_data:
        logger.warning(f'策略需要财务因子{conf.fin_cols}，但缺少财务数据路径')
        raise ValueError('请在 config.py 中配置财务数据路径')
    elif len(conf.fin_cols) > 0:
        logger.debug(f'ℹ️ 检测到财务因子：{conf.fin_cols}')
    else:
        logger.debug('ℹ️ 检测到没有财务因子')

    if len(conf.extra_data.keys()) > 0:
        logger.debug(f'🔍 检测到外部数据：{list(conf.extra_data.keys())}')
        for data_name in conf.extra_data.keys():
            is_ok, msg = check_extra_data(data_name)
            if not is_ok:
                logger.error(f'外部数据检测失败：{msg}')
                exit(2)
    else:
        logger.debug('🔍 检测到没有外部数据')

    logger.debug('💿 读取股票K线数据...')
    candle_df_dict: Dict[str, pd.DataFrame] = pd.read_pickle(runtime_folder / '股票预处理数据.pkl')

    # ====================================================================================================
    # 2. 计算因子并存储结果
    # ====================================================================================================
    all_factor_df_list = []  # 计算结果会存储在这个列表
    # factor_col_info = dict()
    # ** 注意 **
    # `tqdm`是一个显示为进度条的，非常有用的工具
    # 目前是串行模式，比较适合debug和测试。
    logger.debug(f'🚀 多进程计算因子，进程数量：{n_jobs}' if boost else '🚲 单进程计算因子')
    if boost:
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
            futures = []
            for stock_code, candle_df in candle_df_dict.items():
                futures.append(executor.submit(process_by_stock, conf, stock_code, candle_df))

            for future in tqdm(futures, desc='🧮 计算因子', total=len(futures)):
                period_df = future.result()
                # factor_col_info.update(agg_dict)  # 更新因子列的周期转换规则
                all_factor_df_list.append(period_df)
    else:
        for stock_code, candle_df in tqdm(candle_df_dict.items(), desc='🧮 计算因子', total=len(candle_df_dict.keys())):
            period_df = process_by_stock(conf, stock_code, candle_df)
            # factor_col_info.update(agg_dict)  # 更新因子列的周期转换规则
            all_factor_df_list.append(period_df)

    # ====================================================================================================
    # 3. 合并因子数据并存储
    # ====================================================================================================
    all_factors_df = pd.concat(all_factor_df_list, ignore_index=True)

    # 转化一下symbol的类型为category，可以加快因子计算速度，节省内存
    # 并且排序和整理index
    all_factors_df = all_factors_df.assign(
        股票代码=all_factors_df['股票代码'].astype('category'),
        股票名称=all_factors_df['股票名称'].astype('category'),
    ).sort_values(by=['交易日期', '股票代码']).reset_index(drop=True)

    logger.debug('💾 存储因子数据...')

    all_factors_df.to_pickle(runtime_folder / '因子计算结果.pkl')

    logger.ok(f'因子计算完成，耗时：{time.time() - s_time:.2f}秒')


# ================================================================
# step3_选股.py
# ================================================================
def select_stocks(confs: BacktestConfig | List[BacktestConfig], boost=True):
    if isinstance(confs, BacktestConfig):
        # 如果是单例，就直接返回原来的结果
        return select_stock_by_conf(confs, boost=boost)

    # 否则就直接并行回测
    is_boost = False  # 怕资源溢出，强制串行
    is_silent = True  # 减少输出
    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        futures = [executor.submit(select_stock_by_conf, conf, is_boost, is_silent) for conf in confs]
        for future in tqdm(as_completed(futures), total=len(confs), desc='选股'):
            try:
                future.result()
            except Exception as e:
                logger.exception(e)
                exit(1)
    import logging
    logger.setLevel(logging.DEBUG)  # 恢复日志模式


def select_stock_by_conf(conf: BacktestConfig, boost=True, silent=False):
    """
    选股流程：
    1. 初始化策略配置
    2. 加载并清洗选股数据
    3. 计算选股因子并进行筛选
    4. 缓存选股结果

    参数:
    conf (BacktestConfig): 回测配置
    返回:
    DataFrame: 选股结果
    """
    if silent:
        import logging
        logger.setLevel(logging.WARNING)  # 可以减少中间输出的log

    result_folder = conf.get_result_folder()  # 选股结果文件夹
    period_offset = conf.load_period_offset()  # 交易日期偏移

    if boost:
        # 多进程模式
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(select_stocks_by_strategy, stg, result_folder, period_offset) for stg in
                       conf.strategy_list]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)
                    exit(1)
    else:
        for strategy in conf.strategy_list:
            select_stocks_by_strategy(strategy, result_folder, period_offset)


def select_stocks_by_strategy(strategy, result_folder, period_offset):
    # ====================================================================================================
    # 1. 初始化策略配置
    # ====================================================================================================
    s_time = time.time()
    logger.debug(f'🎯 {strategy.name} 选股启动...')

    # ====================================================================================================
    # 2. 加载并清洗选股数据
    # ====================================================================================================
    s = time.time()
    factor_df = pd.read_pickle(runtime_folder / '因子计算结果.pkl')  # 加载带有因子计算结果的数据
    # 根据持仓周期裁切
    select_dates_dict = {}
    select_dates = []
    for hold_period_name in strategy.hold_period_name_list:
        select_dates_dict[hold_period_name] = period_offset.groupby(hold_period_name)['交易日期'].last().to_list()
        select_dates += select_dates_dict[hold_period_name]

    select_dates = list(set(select_dates))

    # 过滤掉每一个周期中，没有交易的股票 & 针对选股日期进行筛选要选股的数据
    factor_df = factor_df[
        (factor_df['是否交易'] == 1) & (factor_df['交易日期'].isin(select_dates))
        ].dropna(subset=strategy.factor_columns).copy()
    factor_df.dropna(subset=['股票代码'], inplace=True)

    # 最后整理一下
    factor_df.sort_values(by=['交易日期', '股票代码'], inplace=True)
    factor_df.reset_index(drop=True, inplace=True)

    logger.debug(f'➡️ [{strategy.name}] 选股数据准备完成，耗时：{time.time() - s:.2f}s')

    # ====================================================================================================
    # 3. 因子计算和筛选流程
    # 3.1 前置筛选
    # 3.2 计算选股因子
    # 3.3 基于选股因子进行选股
    # ====================================================================================================

    # 3.1 前置筛选
    s = time.time()
    factor_df = strategy.filter_before_select(factor_df)
    factor_df = factor_df[KLINE_COLS + strategy.factor_columns]  # 裁切一下数据
    logger.debug(f'➡️ [{strategy.name}] 前置筛选耗时：{time.time() - s:.2f}s')

    # 3.2 计算选股因子
    s = time.time()
    factor_df = strategy.calc_select_factor(factor_df)
    logger.debug(f'➡️ [{strategy.name}] 选股复合因子计算耗时：{time.time() - s:.2f}s')

    # 3.3 进行选股
    s = time.time()
    result_df = select_by_factor(factor_df, strategy.select_num, strategy.factor_name)
    logger.debug(f'➡️ [{strategy.name}] 选股耗时：{time.time() - s:.2f}s')

    file_path = result_folder / f'选股结果{strategy.name}.pkl'
    # 若无选股结果则直接返回
    if result_df.empty:
        pd.DataFrame(columns=RES_COLS).to_pickle(file_path)
        return

    # ====================================================================================================
    # 4. 缓存选股结果
    # ====================================================================================================
    period_result_df_list = []
    result_df = result_df[[*KLINE_COLS, '目标资金占比']]
    for hold_period_name in strategy.hold_period_name_list:
        result_by_period = result_df[result_df['交易日期'].isin(select_dates_dict[hold_period_name])].copy()
        result_by_period['持仓周期'] = hold_period_name
        period_result_df_list.append(result_by_period)

    select_result_df = pd.concat(period_result_df_list, ignore_index=True)

    select_result_df = select_result_df.assign(
        策略=strategy.name,
        策略权重=np.float64(strategy.cap_weight),
        换仓时间=strategy.rebalance_time
    ).rename(columns={'交易日期': '选股日期'})

    select_result_df = select_result_df.assign(
        策略=select_result_df['策略'].astype('category'),
        换仓时间=select_result_df['换仓时间'].astype('category'),
        持仓周期=select_result_df['持仓周期'].astype('category'),
        目标资金占比=select_result_df['目标资金占比'] * select_result_df['策略权重'] / len(strategy.offset_list)
        # 根据策略资金权重，调整目标分配比例，并且平均分配到offset上
    )

    # 缓存到本地文件
    select_result_df = select_result_df[RES_COLS]
    select_result_df.to_pickle(file_path)
    logger.debug(f'🏁 [{strategy.name}] 选股耗时: {(time.time() - s_time):.2f}s')

    return select_result_df


def select_by_factor(period_df, select_num: float | int, factor_name):
    """
    基于因子选择目标股票并计算资金权重。

    参数:
    period_df (DataFrame): 筛选后的数据
    select_num (float | int): 选股数量或比例
    factor_name (str): 选股因子名称

    返回:
    DataFrame: 带目标资金占比的选股结果
    """
    period_df = calc_select_factor_rank(period_df, factor_column=factor_name, ascending=True)

    # 基于排名筛选股票
    if int(select_num) == 0:  # 选股数量是百分比
        period_df = period_df[period_df['rank'] <= period_df['总股数'] * select_num].copy()
    else:  # 选股数量是固定的数字
        period_df = period_df[period_df['rank'] <= select_num].copy()

    # 根据选股数量分配目标资金
    period_df['目标资金占比'] = 1 / period_df.groupby('交易日期')['股票代码'].transform('size')

    period_df.sort_values(by='交易日期', inplace=True)
    period_df.reset_index(drop=True, inplace=True)

    # 清理无关列
    period_df.drop(columns=['总股数', 'rank_max'], inplace=True)

    return period_df


def calc_select_factor_rank(df, factor_column='因子', ascending=True):
    """
    计算因子排名。

    参数:
    df (DataFrame): 原始数据
    factor_column (str): 因子列名
    ascending (bool): 排序顺序，True为升序

    返回:
    DataFrame: 包含排名的原数据
    """
    # 计算因子的分组排名
    df['rank'] = df.groupby('交易日期')[factor_column].rank(method='min', ascending=ascending)
    df['rank_max'] = df.groupby('交易日期')['rank'].transform('max')
    # 根据时间和因子排名排序
    df.sort_values(by=['交易日期', 'rank'], inplace=True)
    # 重新计算一下总股数
    df['总股数'] = df.groupby('交易日期')['股票代码'].transform('size')
    return df


def concat_select_results(conf: BacktestConfig) -> pd.DataFrame:
    """
    聚合策略选股结果，形成综合选股结果
    :param conf:
    :return:
    """
    # 如果是纯多头现货模式，那么就不转换合约数据，只下现货单
    all_select_df_list = []  # 存储每一个策略的选股结果
    result_folder = conf.get_result_folder()
    select_result_path = result_folder / '选股结果.pkl'
    recent_select_df_list = []

    for strategy in conf.strategy_list:
        stg_select_result = result_folder / f'选股结果{strategy.name}.pkl'
        # 如果文件不存在，就跳过
        if not stg_select_result.exists():
            continue
        # 读入单策略选股结果
        stg_select = pd.read_pickle(stg_select_result)

        # 添加到最终选股结果
        all_select_df_list.append(stg_select)
        # 裁切最新选股结果
        recent_select_df_list.append(stg_select[stg_select['选股日期'] == stg_select['选股日期'].max()])

    # 合并最终选股结果
    if all_select_df_list:
        # 聚合选股结果
        all_select_df = pd.concat(all_select_df_list, ignore_index=True)
    else:
        all_select_df = pd.DataFrame(columns=RES_COLS)
    # 合并最新选股结果
    if recent_select_df_list:
        recent_select_df = pd.concat(recent_select_df_list, ignore_index=True)
    else:
        recent_select_df = pd.DataFrame(columns=RES_COLS)

    all_select_df = all_select_df.sort_values(by=['选股日期', '持仓周期', '股票代码'])[RES_COLS].reset_index(drop=True)
    all_select_df.to_pickle(select_result_path)
    # 保存一份给你核对结果用😃
    all_select_df.to_csv(select_result_path.with_suffix('.csv'), encoding='utf-8-sig', index=False)
    # 再附赠一份最新选股结果
    recent_select_df = recent_select_df.sort_values(by=['选股日期', '持仓周期', '股票代码'])[RES_COLS]
    recent_select_df.to_csv(select_result_path.parent / '最新选股结果.csv', encoding='utf-8-sig', index=False)

    return all_select_df


# ================================================================
# step4_实盘模拟.py
# ================================================================
def simulate_performance(conf: BacktestConfig, show_plot=True):
    """
    模拟投资组合的表现，生成资金曲线以跟踪组合收益变化。

    参数:
    conf (BacktestConfig): 回测配置
    select_results (DataFrame): 选股结果数据
    show_plot (bool): 是否显示回测结果图表

    返回:
    None
    """
    # ====================================================================================================
    # 1. 聚合选股结果中的权重
    # ====================================================================================================
    s_time = time.time()
    select_results = pd.read_pickle(conf.get_result_folder() / '选股结果.pkl')

    logger.debug('🔀 持仓周期权重聚合...')
    symbols = sorted(select_results['股票代码'].unique())
    period_ratio_df = {}
    for (period, reb_time), grp_df in select_results.groupby(['持仓周期', '换仓时间']):
        pivot_table_df = grp_df.pivot_table(
            index='选股日期',
            columns='股票代码',
            values='目标资金占比',
            aggfunc='sum',
            fill_value=0
        )
        period_ratio_df[(period, reb_time)] = pivot_table_df

    logger.debug(f'👌 权重聚合完成，耗时：{time.time() - s_time:.3f}秒')

    # 防御性编程
    if len(period_ratio_df) == 0:
        logger.critical('权重聚合结果为空，请检查选股结果')
        logger.debug('⏏️ 退出试盘模拟，因为选股结果为空')
        exit()

    # ====================================================================================================
    # 2. 对数据进行处理
    # ====================================================================================================
    min_ratio_dt = min(ratio_df.index.min() for ratio_df in period_ratio_df.values()).date()
    min_ratio_date_str = min_ratio_dt.strftime('%Y-%m-%d')

    max_ratio_dt = max(ratio_df.index.max() for ratio_df in period_ratio_df.values()).date()
    max_ratio_date_str = max_ratio_dt.strftime('%Y-%m-%d')

    # 确定回测区间
    conf.start_date = max(conf.start_date, min_ratio_date_str)
    conf.end_date = min(conf.end_date or max_ratio_date_str, max_ratio_date_str)
    logger.debug(f'🗓️ 回测区间:{conf.start_date}~{conf.end_date}')

    period_offset = conf.load_period_offset()

    # 对于交易日可能为空的周期进行重新填充
    for (period, reb_time), df_stock_ratio in period_ratio_df.items():
        rebalance_dates = period_offset.groupby(period)['交易日期'].last()
        # 对于交易日可能为空的周期进行重新填充，不存在的 symbol 填充 ratio 为 0
        period_ratio_df[(period, reb_time)] = df_stock_ratio.reindex(
            index=rebalance_dates,
            columns=symbols,
            fill_value=0
        ).sort_index()

    # ====================================================================================================
    # 3. 计算资金曲线
    # ====================================================================================================
    pivot_dict_stock = pd.read_pickle(runtime_folder / '全部股票行情pivot.pkl')
    backtest_days = (max_ratio_dt - min_ratio_dt).days
    logger.info(f'开始模拟日线交易，回溯 {backtest_days:,} 天...')

    # 计算资金曲线及收益数据
    calc_equity(conf, pivot_dict_stock, period_ratio_df, symbols, select_results, show_plot=show_plot)

    return conf.report
