"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import numpy as np
import pandas as pd

from core.model.strategy_config import PosStrategyConfig


"""
使用案例：


strategy_config = {
    'name': 'RotationStrategy',  # *必填。使用什么策略，这里是轮动策略
    'hold_period': '1H',  # *必填。聚合后策略持仓周期。目前回测支持日线级别、小时级别。例：1H，6H，3D，7D......
    'params': {
        'factor_list': [
            ('Bias', False, 336, 1)
        ],
        'rotation_period': '6H',   # 新增配置，调整轮动周期
        'offset_list': [0, 1, 2, 3, 4, 5],    #  新增配置，设置执行轮动 offset
    }
}


"""
def calc_ratio(equity_dfs: [pd.DataFrame], stg_conf: PosStrategyConfig) -> pd.DataFrame:
    """
    计算选币仓位结果，只接受两个参数，1. 资金曲线们，2. 策略配置
    :param equity_dfs: 资金曲线，是一个df的列表，里面包含配置中要求计算好的因子
    :param stg_conf: 策略配置
    :return: 返回仓位比，比如：
                         0    1
    candle_begin_time
    2021-01-01 00:00:00  1.0  0.0
    2021-01-01 06:00:00  1.0  0.0
    2021-01-01 12:00:00  1.0  0.0
    2021-01-01 18:00:00  1.0  0.0
    2021-01-02 00:00:00  1.0  0.0
    ...                  ...  ...
    2024-07-23 06:00:00  0.0  1.0
    2024-07-23 12:00:00  0.0  1.0
    2024-07-23 18:00:00  0.0  1.0

    # 说明：
    可以在这里尽情施展你的组合才华，输入中包含策略的对象，以及我们准备好的资金曲线list
    """
    # 取出factor_list、hold_period、rotation_period、offset_list、select_num
    factor_list = stg_conf.params['factor_list']
    hold_period = stg_conf.hold_period  # hold_period只能为1H
    rotation_period = stg_conf.params['rotation_period']
    offset_list = stg_conf.params['offset_list']
    select_num = 1  # 默认选择的数量为1
    if 'select_num' in list(stg_conf.params.keys()):
        select_num = stg_conf.params['select_num']
    # 处理特殊情况
    if (len(factor_list) == 0) | (len(offset_list) == 0):
        print('-----轮动参数配置有误，退出程序...-----')
        exit()
    if hold_period != '1H':
        print('-----hold_period需要设置为1H，请重新设置(注意区分hold_period和rotation_period)-----')
        exit()
    if rotation_period[-1:] in ['D', 'd']:
        print('-----rotation_period不能为D级别的持仓周期，请重新设置-----')
        exit()
    # 筛选掉不符合持仓周期的offset
    all_offset_list = list(range(0, int(rotation_period[:-1])))
    offset_list = [_offset for _offset in offset_list if _offset in all_offset_list]

    # 整理资金曲线
    for idx, df in enumerate(equity_dfs):
        df['symbol'] = idx
    all_equity_df = pd.concat(equity_dfs)
    all_equity_df = all_equity_df.sort_values(['candle_begin_time', 'symbol']).reset_index(drop=True)
    # 计算每个时间点的offset
    cal_offset_base_seconds = 3600 * 24 if rotation_period[-1:] in ['D', 'd'] else 3600
    unified_time = '2017-01-01'
    period_num = int(rotation_period[:-1])
    if all_equity_df['candle_begin_time'].dt.tz:
        reference_date = pd.to_datetime(unified_time).tz_localize('UTC')
    else:
        reference_date = pd.to_datetime(unified_time)
    time_diff_seconds = (all_equity_df['candle_begin_time'] - reference_date).dt.total_seconds()
    offset = (time_diff_seconds / cal_offset_base_seconds).mod(period_num).astype('int8')
    all_equity_df['offset'] = ((offset + 1 + period_num) % period_num).astype('int8')

    # 构建时间轴
    begin_times = equity_dfs[0]['candle_begin_time']
    # 资金曲线数量
    equity_num = len(equity_dfs)

    # 构建总轮动资金占比df
    all_rot_ratio = pd.DataFrame(index=begin_times, columns=range(equity_num))

    # 循环处理每一个offset
    for _offset in offset_list:
        print(f'正在处理轮动offset：{_offset}')
        offset_equity_dfs = all_equity_df[all_equity_df['offset'] == _offset]

        # 初始化当前offset的资金比例rot_ratio
        rot_ratio = pd.DataFrame(index=begin_times, columns=range(equity_num))

        # 循环处理每一个轮动因子
        for i, factor_info in enumerate(factor_list):
            print(f'正在处理轮动因子：{factor_info}')

            # 取出对应因子名
            factor_name = factor_info[0] + '_' + str(factor_info[2])

            # 资金曲线排名
            _offset_equity_dfs = offset_equity_dfs.copy()
            _offset_equity_dfs['rank'] = _offset_equity_dfs.groupby('candle_begin_time')[factor_name].rank(ascending=factor_info[1], method='min')

            # 根据select_num选择资金曲线
            _offset_equity_dfs = _offset_equity_dfs[_offset_equity_dfs['rank'] <= select_num]

            # 生成资金比例
            _offset_equity_dfs['ratio'] = 1 / _offset_equity_dfs.groupby('candle_begin_time').transform('size')
            _rot_ratio = pd.pivot_table(_offset_equity_dfs, index='candle_begin_time', columns='symbol', values='ratio')
            _rot_ratio.fillna(0, inplace=True)

            # 将该轮动因子的资金占比加到总资金占比中
            rot_ratio = rot_ratio.add(_rot_ratio, fill_value=0)

        # 将轮动资金占比除以覆盖的轮动参数数量，每行资金占比加总为1
        rot_ratio = rot_ratio.apply(lambda x: x / len(factor_list))
        rot_ratio = rot_ratio.fillna(method='ffill')

        # 将该offset的资金占比加到总资金占比中
        all_rot_ratio = all_rot_ratio.add(rot_ratio, fill_value=0)

    # 将总轮动资金占比除以覆盖的offset数量，每行资金占比加总为1
    all_rot_ratio = all_rot_ratio.apply(lambda x: x / len(offset_list))

    return all_rot_ratio
