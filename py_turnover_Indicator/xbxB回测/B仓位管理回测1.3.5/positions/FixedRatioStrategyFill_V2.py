from re import X
import numpy as np
import pandas as pd

from core.model.strategy_config import PosStrategyConfig


def calc_ratio(equity_dfs: list[pd.DataFrame], stg_conf: PosStrategyConfig) -> pd.DataFrame:
    """
    计算选币仓位结果，只接受两个参数，1. 资金曲线们，2. 策略配置
    :param equity_dfs: 资金曲线，是一个df的列表，里面包含配置中要求计算好的因子
    :param stg_conf: 策略配置
    :return: 返回仓位比
    """
    # 取出对应参数
    cap_ratios = stg_conf.params['cap_ratios']  # 默认资金分配
    pos_limit = stg_conf.params['pos_limit']
    monitor_strategy = pos_limit['monitor_strategy']  # 监控的策略
    
    # 获取各种情况下的资金分配方案
    alt_ratios_0 = pos_limit.get('alt_ratios_0', cap_ratios)  # 空仓时的资金分配
    alt_ratios_1 = pos_limit.get('alt_ratios_1', cap_ratios)  # 选1个币时的资金分配
    alt_ratios_2 = pos_limit.get('alt_ratios_2', cap_ratios)  # 选2个币时的资金分配
    alt_ratios_3 = pos_limit.get('alt_ratios_3', cap_ratios)  # 选3个币时的资金分配
    alt_ratios_4 = pos_limit.get('alt_ratios_4', cap_ratios)  # 选4个币时的资金分配
    alt_ratios_5plus = pos_limit.get('alt_ratios_5plus', cap_ratios)  # 选5个及以上币时的资金分配

    monitor_df = None
    monitor_index = None

    print(f"策略列表长度: {len(stg_conf.strategy_cfg_list)}")
    for i, cfg in enumerate(stg_conf.strategy_cfg_list):
        print(f"策略{i}: {cfg.name}")

    # 找到需要监控的策略
    for index, cfg in enumerate(stg_conf.strategy_cfg_list):
        if cfg.name.endswith(monitor_strategy):
            equity_df = pd.read_csv(cfg.get_result_folder() / '资金曲线.csv', encoding='utf-8-sig', parse_dates=['candle_begin_time'])
            monitor_df = equity_df
            monitor_index = index
            break
    
    if monitor_df is None:
        print(f"未找到监控策略: {monitor_strategy}，使用默认资金分配...")
        
    # 判断资金占比的参数数量是否与资金曲线的数量一致
    all_ratios = [cap_ratios, alt_ratios_0, alt_ratios_1, alt_ratios_2, alt_ratios_3, alt_ratios_4, alt_ratios_5plus]
    for ratios in all_ratios:
        if len(ratios) != len(equity_dfs):
            print(f'资金比例数量与资金曲线数量不同，请检查配置: {ratios}')
            exit()

    # 构建时间轴
    begin_times = equity_dfs[0]['candle_begin_time']
    monitor_df = monitor_df.set_index('candle_begin_time').reindex(begin_times, method='ffill').reset_index()
    monitor_df = monitor_df.rename(columns={'index': 'candle_begin_time'})

    # 创建一个全 0 的 NDArray
    cap_weights = np.zeros([len(begin_times), len(equity_dfs)])

    # 分配默认权重
    for i in range(len(cap_ratios)):
        cap_weights[:, i] = cap_ratios[i]

    # 根据监控策略的选币数量动态调整资金分配
    if monitor_df is not None:
        # 创建选币数量掩码
        long_num = monitor_df['symbol_long_num'].values
        short_num = monitor_df['symbol_short_num'].values
        
        # 确保长度匹配
        if len(long_num) != len(begin_times):
            print('警告：监控策略的时间轴与其他策略不一致，可能导致结果不准确')
            # 创建DataFrame时需要转换index类型
            return pd.DataFrame(cap_weights, columns=range(cap_weights.shape[1]), index=begin_times)
        
        # 计算总选币数量
        total_num = np.add(long_num, short_num)  # 使用numpy的add函数
        
        # 创建不同选币数量的掩码
        mask_0 = (total_num == 0)  # 空仓
        mask_1 = (total_num == 1)  # 选1个币
        mask_2 = (total_num == 2)  # 选2个币
        mask_3 = (total_num == 3)  # 选3个币
        mask_4 = (total_num == 4)  # 选4个币
        mask_5plus = (total_num >= 5)  # 选5个及以上币
        
        # 根据不同选币数量应用不同的资金分配方案
        for i in range(len(equity_dfs)):
            # 空仓情况
            cap_weights[mask_0, i] = alt_ratios_0[i]
            # 选1个币情况
            cap_weights[mask_1, i] = alt_ratios_1[i]
            # 选2个币情况
            cap_weights[mask_2, i] = alt_ratios_2[i]
            # 选3个币情况
            cap_weights[mask_3, i] = alt_ratios_3[i]
            # 选4个币情况
            cap_weights[mask_4, i] = alt_ratios_4[i]
            # 选5个及以上币情况
            cap_weights[mask_5plus, i] = alt_ratios_5plus[i]

    # 将结果转换回 DataFrame，注意index可能需要转换
    cap_weights = pd.DataFrame(cap_weights, columns=range(cap_weights.shape[1]), index=begin_times)

    return cap_weights