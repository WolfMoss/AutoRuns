"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

import numpy as np
import pandas as pd


def split_order_twap(orders_df: pd.DataFrame, order_amount_limit):
    """
    对超额订单进行拆分,并进行调整,尽可能每批中子订单、每批订单让多空平衡
    :param orders_df 原始下单信息
    :param order_amount_limit:单次下单最大金额
    """

    # 对下单资金进行拆单
    orders_df['拆单金额'] = orders_df['实际下单资金'].apply(
        lambda x: [x] if abs(x) < order_amount_limit else [(1 if x > 0 else -1) * order_amount_limit] * int(
            abs(x) / order_amount_limit) + [x % (order_amount_limit if x > 0 else -order_amount_limit)])
    orders_df['拆单金额'] = orders_df['拆单金额'].apply(np.array)  # 将list转成numpy的array
    # 计算拆单金额对应多少的下单量
    orders_df['实际下单量'] = orders_df['实际下单量'] / orders_df['实际下单资金'] * orders_df['拆单金额']
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
