"""
邢不行｜策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import itertools
import time
import warnings
from typing import List

import pandas as pd

from config import raw_data_path, backtest_name
from core.backtest import step6_simulate_performance
from core.model.backtest_config import MultiEquityBacktestConfig
from core.utils.log_kit import logger, divider
from core.utils.path_kit import get_file_path
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


def dict_itertools(dict_):
    keys = list(dict_.keys())
    values = list(dict_.values())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def find_best_params(strategies: List[dict]):
    # ====================================================================================================
    # ** 1. 初始化 **
    # 根据 config.py 中的配置，初始化回测
    # ====================================================================================================
    # 需要携带所有回测组的因子列表
    import config as default_config
    default_strategy = default_config.strategy_config.copy()
    factor_list = set()
    for strategy in strategies:
        factor_list = factor_list | set(strategy.get('params', {}).get('factor_list', []))
        default_strategy['hold_period'] = strategy['hold_period']
        default_strategy['name'] = strategy['name']
    default_strategy['params']['factor_list'] = factor_list

    # 用聚合的数据进行me conf初始化
    me_conf = MultiEquityBacktestConfig(strategy_config=default_strategy)

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
    # ** 4. 初始化遍历的配置列表 **
    # ====================================================================================================
    divider('初始化遍历', sep='-')
    logger.warning(f'子策略结果仍在 {me_conf.factory.result_folder} 中(节约存储)')
    me_conf_list: List[MultiEquityBacktestConfig] = []
    for index, strategy in enumerate(strategies):
        new_me_conf = MultiEquityBacktestConfig.duplicate_conf(me_conf, f'{backtest_name}_参数{index + 1}', strategy)
        me_conf_list.append(new_me_conf)

    # ====================================================================================================
    # ** 5. 逐个进行仓位管理回测 **
    # ====================================================================================================
    divider('逐个回测', sep='-')
    pivot_dict_spot = pd.read_pickle(raw_data_path / 'market_pivot_spot.pkl')
    pivot_dict_swap = pd.read_pickle(raw_data_path / 'market_pivot_swap.pkl')

    report_list = []
    for i, me_conf_i in enumerate(me_conf_list):
        # ====================================================================================================
        # ** 5-1. 计算仓位比例 **
        # 仓位管理策略接入，计算每一个时间周期中，子策略应该持仓的资金比例
        # ====================================================================================================
        seq = f'({i + 1} / {len(me_conf_list)})'
        logger.debug(f'🗄️ {seq} {me_conf_i}')
        s_time = time.time()
        pos_ratio = me_conf_i.calc_ratios()

        # ====================================================================================================
        # ** 5-2. 聚合选币结果 **
        # 根据子策略的资金比例，重新聚合成一个选币结果，及对应周期内币种的资金分配
        # ====================================================================================================
        df_spot_ratio, df_swap_ratio = me_conf_i.agg_pos_ratio(pos_ratio)
        logger.ok(f'完成仓位管理模块的计算，已花费时间{time.time() - s_time:.3f}秒')

        # ====================================================================================================
        # ** 5-3. 模拟交易 **
        # 根据生成好的选币结果+资金配比，重新模拟交易，得到回测报告
        # ====================================================================================================
        conf_all = me_conf_i.factory.generate_all_factor_config()
        conf_all.name = me_conf_i.factory.backtest_name
        # 用于参数遍历场景
        conf_all.is_param_search = True

        # 让我们荡起双桨🎵～
        report = step6_simulate_performance(
            conf_all,
            df_spot_ratio, df_swap_ratio, pivot_dict_spot, pivot_dict_swap,
            if_show_plot=False,  # 是否显示图表
            description=str(me_conf),  # 图表描述替换为仓位管理策略
        )

        report_list.append(report)

        logger.ok(f'{seq} {me_conf_i}')

    # ====================================================================================================
    # 6. 展示最优参数
    # - 根据回测结果筛选最优参数组合，并保存到 Excel 文件
    # ====================================================================================================
    divider('展示最优参数', sep='-')
    s_time = time.time()
    if len(report_list) > 65535:
        logger.warning(f'回测参数列表超过 65535，会占用大量内存，请手动合并结果')
        return None

    all_params_map = pd.concat(report_list, ignore_index=True)
    report_cols = all_params_map.columns
    all_me_conf_name_list = [me_conf_i.factory.backtest_name for me_conf_i in me_conf_list]
    all_me_conf_str_list = [str(me_conf_i) for me_conf_i in me_conf_list]
    all_params_map['仓位管理策略'] = all_me_conf_str_list
    all_params_map = all_params_map.assign(
        策略名=all_me_conf_name_list,
        仓位管理参数=all_me_conf_str_list
    )

    # 合并参数细节
    # 按累积净值排序并保存结果
    all_params_map.sort_values(by='累积净值', ascending=False, inplace=True)
    all_params_map = all_params_map[['策略名', '仓位管理策略', *report_cols]].drop(columns=['param'])
    all_params_map.to_excel(get_file_path('data', backtest_name, '最优参数.xlsx'), index=False)
    print(all_params_map)
    logger.ok(f'完成展示最优参数，花费时间：{time.time() - s_time:.3f}秒，累计时间：{(time.time() - s_time):.3f}秒')


if __name__ == '__main__':
    version_prompt()
    print()
    divider('[仓位管理框架遍历脚本_beta]', with_timestamp=False)
    logger.debug(f'# 本脚本为 BETA 版本，目前存在一个已知问题：')
    logger.debug(f'# 本脚本聚合遍历的参数进行计算，在处理轮动因子时，会清理空值数据，这里会按照遍历的最大参数进行处理')
    logger.debug(f'# 因此，本脚本遍历之后的结果会出现与直接跑回测存在部分误差')
    divider('[仓位管理框架遍历脚本_beta]', with_timestamp=False)

    # ====================================================================================================
    # backtest_name和strategy_pool都默认使用config.py中的同名变量
    # ====================================================================================================
    # 参数设置
    batch = {
        "cci": range(6, 30, 5),
    }

    strategy_config_list = []

    for param_dict in dict_itertools(batch):
        strategy_config = {
            'name': 'RotationStrategy',  # *必填。使用什么策略，这里是轮动策略
            'hold_period': '24H',  # *必填。聚合后策略持仓周期。目前回测支持日线级别、小时级别。例：1H，6H，3D，7D......
            'params': {  # 非必填。聚合类策略的参数，这里的案例是在轮动策略场景下，我们需要提供轮动因子。
                'factor_list': [
                    ('Cci', False, param_dict["cci"], 1),
                ]
            }
        }
        strategy_config_list.append(strategy_config)

    find_best_params(strategy_config_list)
