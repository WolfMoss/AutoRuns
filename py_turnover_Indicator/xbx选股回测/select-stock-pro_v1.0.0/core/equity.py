"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import time

import numba as nb
import numpy as np
import pandas as pd
from numba.typed import List

from core.evaluate import strategy_evaluate
from core.figure import draw_equity_curve_plotly, draw_table, merge_html
from core.market_essentials import import_index_data, get_most_stock_by_year
from core.model.backtest_config import BacktestConfig
from core.model.type_def import (BSE_MAIN, SimuParams, StockMarketData, get_symbol_type, AdjustRatios)
from core.rebalance import RebAlways
from core.simulator import Simulator
from core.utils.log_kit import logger

pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行


def parse_rebalance_time(reb_time) -> tuple[int, int]:
    price_array = ['open', '0935', '0945', '0955', 'close']
    match reb_time:
        case 'open':
            return 0, 0
        case 'close':
            return -1, -1
        case 'close-open':
            return -1, 0
        case _:
            sell_time, buy_time = reb_time.split('-')
            return price_array.index(sell_time), price_array.index(buy_time)


def get_stock_market(pivot_dict_stock, trading_dates, symbols, symbol_types) -> StockMarketData:
    df_open: pd.DataFrame = pivot_dict_stock['open'].loc[trading_dates, symbols]
    df_close: pd.DataFrame = pivot_dict_stock['close'].loc[trading_dates, symbols]
    df_preclose: pd.DataFrame = pivot_dict_stock['preclose'].loc[trading_dates, symbols]
    # Not sure if necessary
    should_copy = True

    hour_prices = []
    for hour in sorted(pivot_dict_stock.keys()):
        if hour in ['open', 'close', 'preclose']:
            continue
        hour_prices.append(pivot_dict_stock[hour].loc[trading_dates, symbols].to_numpy(copy=should_copy))

    data = StockMarketData(candle_begin_ts=(trading_dates.astype(np.int64) // 1000000000).to_numpy(copy=should_copy),
                           op=df_open.to_numpy(copy=should_copy),
                           cl=df_close.to_numpy(copy=should_copy),
                           pre_cl=df_preclose.to_numpy(copy=should_copy),
                           types=np.array(symbol_types, dtype=np.int16),
                           hour_prices=hour_prices)

    return data


def get_adjust_ratios(df_stock_ratio: pd.DataFrame, start_date, end_date, symbols, reb_time) -> AdjustRatios:
    df_stock_ratio = df_stock_ratio.loc[start_date:end_date, symbols]

    adj_dts = df_stock_ratio.index.to_numpy().astype(np.int64) // 1000000000
    ratios = df_stock_ratio.to_numpy(dtype=np.float64)

    return AdjustRatios(adj_dts=adj_dts, ratios=ratios, reb_time=parse_rebalance_time(reb_time))


def calc_equity(conf: BacktestConfig,
                pivot_dict_stock: dict,
                period_ratio_df: dict[tuple, pd.DataFrame],
                symbols: list[str],
                select_result: pd.DataFrame,
                leverage: float | pd.Series = None,
                show_plot=True):
    """
    模拟投资组合的表现，生成资金曲线以跟踪组合收益变化。
    :param conf: 回测配置
    :param pivot_dict_stock: 原始数据
    :param period_ratio_df: 持仓周期权重
    :param symbols: 股票代码
    :param select_result: 选股结果
    :param leverage: 杠杆
    :param show_plot: 是否显示回测结果图表
    :return:
    """
    symbol_types = [get_symbol_type(sym) for sym in symbols]
    if any(x == BSE_MAIN for x in symbol_types):
        raise ValueError(f'BSE not supported')  # No Beijing stocks

    # 确定回测区间
    start_date = pd.to_datetime(conf.start_date)
    trading_dates = conf.read_trading_dates(start_date, conf.end_date)

    # 读取行情
    market = get_stock_market(pivot_dict_stock, trading_dates, symbols, symbol_types)

    if leverage is None:
        leverage = conf.total_cap_usage

    if isinstance(leverage, pd.Series):
        leverages = leverage.to_numpy(dtype=np.float64)
    else:
        leverages = np.full(len(market.candle_begin_ts), leverage, dtype=np.float64)

    # 开始回测
    params = SimuParams(
        init_cash=conf.initial_cash,  # 初始资金
        stamp_tax_rate=conf.t_rate,  # 印花税率
        commission_rate=conf.c_rate,  # 券商佣金费率
    )
    logger.debug(f'ℹ️ 实际模拟资金:{params.init_cash:,.2f}(整体使用率:{conf.total_cap_usage * 100:.2f}%), '
                 f'印花税率:{params.stamp_tax_rate * 100 :.2f}%, '
                 f'券商佣金费率:{params.commission_rate * 100 :.2f}%')

    adj_ratios = List()
    for (period, reb_time), df_stock_ratio in period_ratio_df.items():
        adj_ratio = get_adjust_ratios(df_stock_ratio, conf.start_date, conf.end_date, symbols, reb_time)
        adj_ratios.append(adj_ratio)

    pos_calc = RebAlways(market.types)

    s_time = time.perf_counter()
    logger.debug('🎯 开始模拟交易...')
    cashes, pos_values, stamp_taxes, commissions = start_simulation(market, params, adj_ratios, leverages, pos_calc)

    logger.ok(f'完成模拟交易，花费时间: {time.perf_counter() - s_time:.3f}秒')
    account_df = pd.DataFrame({
        '交易日期': trading_dates,
        '账户可用资金': cashes,
        '持仓市值': pos_values,
        '印花税': stamp_taxes,
        '券商佣金': commissions,
    }).reset_index(drop=True)

    account_df['总资产'] = account_df['账户可用资金'] + account_df['持仓市值']
    account_df['净值'] = account_df['总资产'] / conf.initial_cash

    account_df = account_df.assign(
        手续费=account_df['印花税'] + account_df['券商佣金'],
        涨跌幅=account_df['净值'].pct_change(),
        杠杆=leverages,
        实际杠杆=account_df['持仓市值'] / account_df['总资产'])

    account_df.to_csv(conf.get_result_folder() / '资金曲线.csv', encoding='utf-8-sig')

    # 策略评价
    rtn, year_return, month_return, quarter_return = strategy_evaluate(account_df, net_col='净值', pct_col='涨跌幅')
    conf.set_report(rtn.T)
    rtn.to_csv(conf.get_result_folder() / '策略评价.csv', encoding='utf-8-sig')
    year_return.to_csv(conf.get_result_folder() / '年度账户收益.csv', encoding='utf-8-sig')
    quarter_return.to_csv(conf.get_result_folder() / '季度账户收益.csv', encoding='utf-8-sig')
    month_return.to_csv(conf.get_result_folder() / '月度账户收益.csv', encoding='utf-8-sig')

    if show_plot:
        # 添加指数数据
        for index_code, index_name in zip(['sh000300', 'sh000852'], ['沪深300', '中证1000']):
            index_path = conf.index_data_path / f'{index_code}.csv'
            if not index_path.exists():
                logger.warning(f'{index_name}({index_code})指数数据不存在，无法添加指数数据')
                continue
            index_df = import_index_data(index_path, [start_date, conf.end_date])
            account_df = pd.merge(left=account_df, right=index_df[['交易日期', '指数涨跌幅']], on=['交易日期'],
                                  how='left')
            account_df[index_name + '指数'] = (account_df['指数涨跌幅'] + 1).cumprod()
            del account_df['指数涨跌幅']

        logger.debug(f"""📈 策略评价 --------------------------------
{rtn}

📊 分年收益率 --------------------------------
{year_return}""")
        logger.debug(f'💰 总手续费: ￥{account_df["手续费"].sum():,.2f}\n')

        logger.info('开始绘制资金曲线...')

        # 生成画图数据字典，可以画出所有offset资金曲线以及各个offset资金曲线
        data_dict = {'资金曲线': '净值', '沪深300指数': '沪深300指数', '中证1000指数': '中证1000指数'}
        right_axis = {'最大回撤': '净值dd2here'}

        # 如果画资金曲线，同时也会画上回撤曲线
        date_start = account_df['交易日期'].min().strftime('%Y/%m/%d')
        date_end = account_df['交易日期'].max().strftime('%Y/%m/%d')
        ann_ret, max_dd, calmar = rtn.at['年化收益', 0], rtn.at['最大回撤', 0], rtn.at['年化收益/回撤比', 0]
        pic_title = f"年化收益:{ann_ret}  最大回撤:{max_dd}  收益回撤比:{calmar}  回测区间：{date_start} - {date_end}"
        pic_desc = ''
        # for stg in conf.strategy_list_raw:
        #     pic_desc += f'{stg["name"]}_{stg["hold_period"]}{stg["offset_list"]}_选{stg["select_num"]}_权{stg["cap_weight"]}_{stg["rebalance_time"]}+'

        fig_path = conf.get_result_folder() / '资金曲线.html'
        # 调用画图函数
        fig1 = draw_equity_curve_plotly(account_df, data_dict=data_dict, date_col='交易日期', right_axis=right_axis,
                                        title=pic_title, desc=pic_desc[:-1], rtn_add=rtn)

        # 获取每年选股最多的股票
        most_stock = get_most_stock_by_year(select_result)
        fig2 = draw_table(most_stock)

        # 绘制图片
        merge_html(fig_path, [fig1, fig2])


@nb.njit(boundscheck=True)
def start_simulation(market, simu_params, adj_ratios, leverages, pos_calc):
    """
    模拟股票交易的函数，逐 K 线模拟交易过程，计算账户资金、仓位价值、印花税和佣金等。

    参数:
    - market: StockMarketData 类型，包含市场数据（如 K 线时间戳、价格等）。
    - simu_params: SimuParams 类型，包含模拟参数（如初始资金、佣金率、印花税率等）。
    - adj_ratios: AdjustRatios 类型，包含策略调仓信息（如调仓日期、目标权重、买卖价格索引等）。
    - leverages: np.array 类型，包含动态杠杆
    - pos_calc: 仓位计算函数，用于计算目标买入仓位。

    返回:
    - cashes: 每根 K 线收盘时的账户可用资金。
    - pos_values: 每根 K 线收盘时的仓位价值。
    - stamp_taxes: 每根 K 线产生的印花税。
    - commissions: 每根 K 线产生的券商佣金。
    """
    # K 线数量
    n_bars = len(market.candle_begin_ts)

    # 股票品种数量
    n_syms = len(market.types)

    # 策略数量
    n_ratios = len(adj_ratios)

    # 账户可用资金 = 初始资金
    available_cash = simu_params.init_cash

    # 记录每根 K 线收盘时的仓位价值
    pos_values = np.zeros(n_bars, dtype=np.float64)

    # 记录每根 K 线收盘时的账户可用资金
    cashes = np.zeros(n_bars, dtype=np.float64)

    # 记录每根 K 线产生的印花税
    stamp_taxes = np.zeros(n_bars, dtype=np.float64)

    # 记录每根 K 线产生的券商佣金
    commissions = np.zeros(n_bars, dtype=np.float64)

    # 为每个策略创建模拟器
    sims = List()
    for i in range(n_ratios):
        sim = Simulator(0, simu_params.commission_rate, simu_params.stamp_tax_rate, np.zeros(n_syms, dtype=np.float64))
        sims.append(sim)

    # 策略的调仓周期索引，用于跟踪每个策略的调仓日期
    adj_idxes = np.zeros(n_ratios, dtype=np.int64)

    # 策略的调仓日期索引：
    # - sell_dt_idxes: 卖出调仓日期索引，-1 表示不调仓，0 表示 T+0 调仓，1 表示 T+1 调仓。
    # - buy_dt_idxes: 买入调仓日期索引，-1 表示不调仓，0 表示 T+0 调仓，1 表示 T+1 调仓。
    sell_dt_idxes = np.full(n_ratios, -1, dtype=np.int8)
    buy_dt_idxes = np.full(n_ratios, -1, dtype=np.int8)

    # 策略的调仓价格索引：
    # - sell_price_idxes: 卖出价格索引，与 market.prices 对应。
    # - buy_price_idxes: 买入价格索引，与 market.prices 对应。
    sell_price_idxes = np.zeros(n_ratios, dtype=np.int8)
    buy_price_idxes = np.zeros(n_ratios, dtype=np.int8)

    # 策略的买入权重矩阵，形状为: 策略数 * 股票品种数
    buy_ratios = np.zeros((n_ratios, n_syms), dtype=np.float64)

    # 逐 K 线模拟交易
    for idx_bar in range(n_bars):
        # 初始化本周期印花税和券商佣金
        stamp_tax = commission = 0.

        # K 线开盘前操作：用前收盘价更新模拟器的持仓价格
        for sim in sims:
            sim.fill_last_prices(market.pre_cl[idx_bar])

        # 开盘前判断每个策略是否需要调仓，并确定具体的买卖日期和时间点
        for idx_ratio, (idx_adj, adj_ratio) in enumerate(zip(adj_idxes, adj_ratios)):
            # 如果当前 K 线日期等于调仓日期
            if idx_adj < len(adj_ratio.adj_dts) and adj_ratio.adj_dts[idx_adj] == market.candle_begin_ts[idx_bar]:
                # 设置卖出调仓日期和价格索引
                if adj_ratio.sp_idx < 0:  # T+0 卖出
                    sell_dt_idxes[idx_ratio] = 0
                    sell_price_idxes[idx_ratio] = len(market.prices) + adj_ratio.sp_idx
                else:  # T+1 卖出
                    sell_dt_idxes[idx_ratio] = 1
                    sell_price_idxes[idx_ratio] = adj_ratio.sp_idx

                # 设置买入调仓日期和价格索引
                if adj_ratio.bp_idx < 0:  # T+0 买入
                    buy_dt_idxes[idx_ratio] = 0
                    buy_price_idxes[idx_ratio] = len(market.prices) + adj_ratio.bp_idx
                else:  # T+1 买入
                    buy_dt_idxes[idx_ratio] = 1
                    buy_price_idxes[idx_ratio] = adj_ratio.bp_idx

                buy_ratios[idx_ratio, :] = adj_ratio.ratios[idx_adj]

                # 更新调仓周期索引
                adj_idxes[idx_ratio] += 1

        # 连续竞价阶段：逐价格点模拟交易
        for idx_price, last_price in enumerate(market.prices):
            # 更新每个模拟器的持仓价值和最新价格
            for sim in sims:
                sim.settle_pos_values(last_price[idx_bar])
                sim.fill_last_prices(last_price[idx_bar])

            # 判断需要卖出的策略
            need_sell = np.logical_and(sell_dt_idxes == 0, sell_price_idxes == idx_price)

            # 判断需要买入的策略
            need_buy = np.logical_and(buy_dt_idxes == 0, buy_price_idxes == idx_price)

            # 处理仅需要卖出不需要买入的策略
            for idx_ratio, sim in enumerate(sims):
                if need_sell[idx_ratio] and not need_buy[idx_ratio]:
                    # 卖出全部股票，并计算印花税和佣金
                    sim_stamp_tax, sim_commission = sim.sell_all(last_price[idx_bar])
                    stamp_tax += sim_stamp_tax
                    commission += sim_commission

                    # 将模拟器可用资金转回账户总可用资金
                    sim_cash = sim.withdraw_all()
                    available_cash += sim_cash

            # 计算账户总权益（可用资金 + 所有模拟器的仓位价值）
            total_equity = available_cash + sum([sim.get_pos_value() for sim in sims])
            total_equity *= leverages[idx_bar]

            # 处理需要买入的策略
            for idx_ratio, (sim, idx_adj, ratios) in enumerate(zip(sims, adj_idxes, buy_ratios)):
                if need_buy[idx_ratio]:
                    # 计算策略目标建仓权益
                    ratio_sum = np.sum(ratios)
                    target_equity = total_equity * ratio_sum

                    # 最大可达权益 = 策略仓位价值 + 总可用资金
                    max_possible_equity = sim.get_pos_value() + available_cash

                    # 如果最大可达权益小于目标建仓权益，即将全部可用现金转入策略，都无法达到目标建仓权益
                    if max_possible_equity < target_equity:
                        # 则将目标建仓权益降低为最大可达权益
                        target_equity = max_possible_equity

                    # 如果目标建仓权益大于仓位价值，则需要转入资金
                    if target_equity > sim.get_pos_value():
                        # 计算建仓所需资金：目标建仓权益减去当前仓位价值
                        required_cash = target_equity - sim.get_pos_value()

                    # 将建仓所需资金存入策略模拟器
                    available_cash -= required_cash
                    sim.deposit(required_cash)

                    # 归一化持仓权重
                    if abs(ratio_sum) < 1e-8:
                        ratios_norm = np.zeros(n_syms, dtype=np.float64)
                    else:
                        ratios_norm = ratios / ratio_sum

                    # 基于目标建仓权益和权重，计算目标买入仓位
                    target_pos = pos_calc.calc_lots(target_equity, last_price[idx_bar], ratios_norm)

                    # 调整仓位，并计算印花税和佣金
                    sim_stamp_tax, sim_commission = sim.adjust_positions(last_price[idx_bar], target_pos)
                    commission += sim_commission
                    stamp_tax += sim_stamp_tax

                    # 将模拟器可用资金转回账户总可用资金
                    sim_cash = sim.withdraw_all()
                    available_cash += sim_cash

        # 更新调仓日期索引
        buy_dt_idxes[buy_dt_idxes >= 0] -= 1
        sell_dt_idxes[sell_dt_idxes >= 0] -= 1

        # 记录本周期数据
        stamp_taxes[idx_bar] = stamp_tax
        commissions[idx_bar] = commission
        pos_values[idx_bar] = sum([sim.get_pos_value() for sim in sims])
        cashes[idx_bar] = available_cash

    return cashes, pos_values, stamp_taxes, commissions
