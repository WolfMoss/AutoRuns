"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import random
import math
import numpy as np
import pandas as pd


def _round_by_type(value: float, precision: int, symbol_type: str) -> float:
    """
    根据交易类型进行精度处理
    :param value: 原始数量
    :param precision: 精度
    :param symbol_type: 交易类型 'spot'/'swap'
    """
    _m = 10 ** precision
    if symbol_type == 'swap':
        # 合约都向上取整
        return value / abs(value) * math.ceil(abs(value) * _m) / _m
    else:  # spot
        if value > 0:  # 现货买入向上取整
            return math.ceil(value * _m) / _m
        else:  # 现货卖出向下取整
            return -math.floor(abs(value) * _m) / _m


def _random_split(x, order_amount_limit):
    if abs(x) < order_amount_limit:
        return [x]

    result = []
    remaining = abs(x)

    while remaining > 0:
        random_amount = random.uniform(0.5 * order_amount_limit, 1.2 * order_amount_limit)
        amount = min(random_amount, remaining)
        result.append(amount if x > 0 else -amount)
        remaining -= amount

    return result


def split_order_twap(orders_df: pd.DataFrame, order_amount_limit):
    """
    对超额订单进行随机拆分,并进行调整,尽可能每批中子订单、每批订单让多空平衡
    :param orders_df: 原始下单信息
    :param order_amount_limit: 目标下单金额（非限额）
    """
    """
         @我已无心战斗 老板提供，随机拆单优化代码以及最后一笔碎单处理
    """
    from core.binance.base_client import BinanceClient

    # 保存原始下单量
    original_order_amount = orders_df['实际下单量'].copy()

    # 随机拆单
    orders_df['拆单金额'] = orders_df['实际下单资金'].apply(lambda x: _random_split(x, order_amount_limit))
    orders_df['拆单金额'] = orders_df['拆单金额'].apply(np.array)  # 将list转成numpy的array
    # 计算拆单金额对应多少的下单量
    orders_df['实际下单量'] = orders_df['实际下单量'] / orders_df['实际下单资金'] * orders_df['拆单金额']

    # 对每个币种进行精度调整
    for idx, row in orders_df.iterrows():
        symbol = row['symbol']
        symbol_type = row['symbol_type']
        market_info = BinanceClient.market_info[symbol_type]
        min_qty = market_info['min_qty']
        if symbol not in min_qty:
            print(f"symbol {symbol} not in min_qty")
            continue

        remaining_amount = original_order_amount[idx]  # 原始下单量
        split_amounts = orders_df.loc[idx, '实际下单量']  # 拆分后的数量列表
        precision = min_qty[symbol]

        # 计算向上取整后的总量会超出多少
        total_after_round = sum(_round_by_type(amt, precision, symbol_type) for amt in split_amounts[:-1])

        # 最后一笔用剩余量，确保总量不变
        if len(split_amounts) > 0:
            last_amount = remaining_amount - total_after_round
            # 如果最后一笔方向相反或太小，就合并到前一笔
            if (last_amount * split_amounts[0] < 0) or abs(last_amount) < 10**(-precision):
                split_amounts = split_amounts[:-1]
                if len(split_amounts) > 0:
                    split_amounts[-1] += last_amount
            else:
                split_amounts[-1] = last_amount

    # 继续原有的处理流程
    orders_df.reset_index(inplace=True)
    del orders_df['拆单金额']

    # 将拆单量进行数据进行展开
    orders_df = orders_df.explode('实际下单量')

    # 定义拆单list
    twap_orders_df_list = []
    # 分组
    group = orders_df.groupby(by='index')
    # 获取分组里面最大的长度
    max_group_len = group['index'].size().max()
    if max_group_len > 0:
        # 批量构建拆单数据
        for i in range(max_group_len):
            twap_orders_df_list.append(
                group.nth(i).sort_values('实际下单资金', ascending=False).reset_index(drop=True))

    return twap_orders_df_list
