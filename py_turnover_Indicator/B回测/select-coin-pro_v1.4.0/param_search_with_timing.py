"""
邢不行｜策略分享会
选币策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import warnings

import pandas as pd

from core.backtest import find_best_params
from core.model.backtest_config import BacktestConfigFactory
from core.utils.log_kit import logger
from core.version import version_prompt

# ====================================================================================================
# ** 脚本运行前配置 **
# 主要是解决各种各样奇怪的问题们
# ====================================================================================================
# region 脚本运行前准备
warnings.filterwarnings('ignore')  # 过滤一下warnings，不要吓到老实人

# pandas相关的显示设置，基础课程都有介绍
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

if __name__ == '__main__':
    version_prompt()
    logger.info(f'系统启动中，稍等...')

    # ====================================================================================================
    # 1. 配置需要遍历的参数
    # ====================================================================================================
    backtest_name = '低价币中性策略（带择时）遍历'

    strategies = []
    for param in range(3, 10, 1):
        strategy_list = [
            # === 低价币中性策略
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_低价币多空策略",
                "offset_list": list(range(0, 24, 1)),  # 只选部分offset[1, 3, 6]；
                "hold_period": "24H",  # 小时级别可选1H到24H；也支持1D交易日级别
                "is_use_spot": True,  # 多头支持交易现货；
                # 资金权重。程序会自动根据这个权重计算你的策略占比
                'cap_weight': 1,
                'long_cap_weight': 1,  # 可以多空比例不同，多空不平衡对策略收益影响大
                'short_cap_weight': 1,
                # 选币数量
                'long_select_coin_num': 0.1,  # 可适当减少选币数量，对策略收益影响大
                'short_select_coin_num': 0.1,  # 四种形式：整数， 小数，'long_nums', 区间选币：(0.1, 0.2), (1, 3)
                # 选币因子信息列表，用于2_选币_单offset.py，3_计算多offset资金曲线.py共用计算资金曲线
                "factor_list": [
                    ('LowPrice', True, param * 24, 1),  # 多空因子名（和factors文件中相同），排序方式，参数，权重。支持多空分离，多空选币因子不一样；
                ],
                "filter_list": [
                    ('LowPrice', param * 24, 'rank:>1', False),
                    # 后置过滤filter_list_post，三种形式：pct, rank, val；支持多空分离，多空过滤因子不一样；
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
        ]
        # 把大杂烩的策略，添加到需要遍历的候选项中
        strategies.append(strategy_list)

    re_timing_strategies = []
    for timing_param in range(100, 301, 50):
        re_timing = {'name': 'MovingAverage', 'params': [timing_param]}
        # 把大杂烩的择时策略，添加到需要遍历的候选项中
        re_timing_strategies.append(re_timing)

    factory = BacktestConfigFactory(backtest_name=backtest_name)
    factory.generate_configs_by_strategies(strategies=strategies, re_timing_strategies=re_timing_strategies)

    # ====================================================================================================
    # 2. 执行遍历
    # ====================================================================================================
    find_best_params(factory)
