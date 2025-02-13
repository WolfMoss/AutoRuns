"""
邢不行｜策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

import time
import warnings

import pandas as pd

from config import raw_data_path
from core.backtest import step6_simulate_performance
from core.model.backtest_config import MultiEquityBacktestConfig
from core.utils.log_kit import logger, divider
from core.version import version_prompt

# ====================================================================================================
# ** 脚本运行前配置 **
# 主要是解决各种各样奇怪的问题们
# ====================================================================================================
warnings.filterwarnings('ignore')  # 过滤一下warnings，不要吓到老实人

# pandas相关的显示设置，基础课程都有介绍
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

if __name__ == '__main__':
    version_prompt()
    logger.info(f'初始化中，稍等...')

    # ====================================================================================================
    # ** 1. 初始化 **
    # 根据 config.py 中的配置，初始化回测
    # ====================================================================================================
    me_conf = MultiEquityBacktestConfig()

    # ====================================================================================================
    # ** 2. 子策略回测 **
    # 运行子策略回测，计算每一个子策略的资金曲线
    # 💡小技巧：如果你仓位管理的子策略不变化，调试的时候可以注释这个步骤，可以加快调试的速度
    # ====================================================================================================
    me_conf.backtest_strategies()

    # ====================================================================================================
    # ** 3. 整理子策略的资金曲线 **
    # 获取所有子策略的资金曲线信息，并且针对仓位管理策略做周期转换，并计算因子
    # ====================================================================================================
    me_conf.process_equities()

    # ====================================================================================================
    # ** 4. 计算仓位比例 **
    # 仓位管理策略接入，计算每一个时间周期中，子策略应该持仓的资金比例
    # ====================================================================================================
    divider('计算仓位', sep='-')
    s_time = time.time()
    pos_ratio = me_conf.calc_ratios()

    # ====================================================================================================
    # ** 5. 聚合选币结果 **
    # 根据子策略的资金比例，重新聚合成一个选币结果，及对应周期内币种的资金分配
    # ====================================================================================================
    df_spot_ratio, df_swap_ratio = me_conf.agg_pos_ratio(pos_ratio)
    logger.ok(f'完成仓位管理模块的计算，已花费时间{time.time() - s_time:.3f}秒')

    # ====================================================================================================
    # ** 6. 模拟交易 **
    # 根据生成好的选币结果+资金配比，重新模拟交易，得到回测报告
    # ====================================================================================================
    divider('模拟交易', sep='-')
    conf = me_conf.factory.generate_all_factor_config()
    pivot_dict_spot = pd.read_pickle(raw_data_path / 'market_pivot_spot.pkl')
    pivot_dict_swap = pd.read_pickle(raw_data_path / 'market_pivot_swap.pkl')

    # 读入子策略的资金曲线，传入给模拟交易，最后绘图的时候会用
    extra_equities = {}
    for index, sub_conf in enumerate(me_conf.factory.config_list):
        equity_path = sub_conf.get_final_equity_path()
        extra_equities[sub_conf.name + '资金曲线'] = pd.read_csv(equity_path, encoding='utf-8-sig')['净值']

    # 让我们荡起双桨🎵～
    step6_simulate_performance(
        conf, df_spot_ratio, df_swap_ratio, pivot_dict_spot, pivot_dict_swap,
        if_show_plot=True,  # 是否显示图表
        description=str(me_conf),  # 图表描述替换为仓位管理策略
        extra_equities=extra_equities  # 传入子策略的资金曲线
    )
