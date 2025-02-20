"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import time
import warnings

import pandas as pd

from core.backtest import run_backtest_multi
from core.model.backtest_config import create_factory
from core.version import version_prompt

# ====================================================================================================
# ** 脚本运行前配置 **
# 主要是解决各种各样奇怪的问题们
# ====================================================================================================
warnings.filterwarnings('ignore')  # 过滤一下warnings，不要吓到老实人

# pandas相关的显示设置，基础课程都有介绍
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

if __name__ == '__main__':
    version_prompt()
    print(f'🌀 系统启动中，稍等...')
    r_time = time.time()
    # ====================================================================================================
    # 1. 配置需要遍历的参数
    # ====================================================================================================
    # 因子遍历的参数范围
    strategies = []
    for hold_period in ('W'):
        for Percentage in('0.098','0.09','0.08','0.07','0.06','0.05','0.04','0.03',):
            for Proportion in ('0.098','0.09','0.08','0.07','0.06','0.05','0.04','0.03',):
                strategy_list = [
                    {
                        "name": "小市值_基本面优化_定风波择时",
                        "hold_period": "W",
                        "offset_list": [0, 1, 2, 3, 4],
                        "select_num": 5,
                        "cap_weight": 1,
                        "rebalance_time": "0955-0955",
                        "factor_list": [
                            ("市值", True, "", 1),
                            ("归母净利润同比增速", False, 60, 1),
                            ("开盘至今涨幅", False, "0945", ("前40%择时", 0.5)),
                        ],
                        "filter_list": [
                            ("ROE", "单季", "pct:<=0.8", False),
                            ("成交额相关因子", ("均值", 5), "val:>=2000_0000", True),
                            ("收盘价", "", "val:<20", True),
                            ("涨跌幅", "", "val:>-0.08", True),
                            ("涨跌幅", "", "val:<=0.07", True),
                            ("日内涨跌幅", "", f"val:>-{Percentage}", True),
                            ("日内涨跌幅", "", f"val:<={Proportion}", True),
                            ('代码开头', ['sh688'], 'val:!=1'),
                            # ('月份', [1,4], 'val:!=1'),  # 不在4月份选股
                        ],
                    },
                ]
                strategies.append(strategy_list)

    # ====================================================================================================
    # 2. 生成策略配置
    # ====================================================================================================
    print(f'🌀 生成策略配置...')
    backtest_factory = create_factory(strategies)

    # ====================================================================================================
    # 3. 寻找最优参数
    # ====================================================================================================
    # boost为True：并行选股；boost为False：串行选股
    # 第一次运行，且不太确定的时候，可以考虑使用 `boost=False`，回测组不多的时候，不会慢太多的哈~
    report_list = run_backtest_multi(backtest_factory, boost=True)

    # ====================================================================================================
    # 4. 根据回测参数列表，展示最优参数
    # ====================================================================================================
    s_time = time.time()
    print(f'🌀 展示最优参数...')
    all_params_map = pd.concat(report_list, ignore_index=True)
    report_columns = all_params_map.columns  # 缓存列名

    # 合并参数细节
    sheet = backtest_factory.get_name_params_sheet()
    all_params_map = all_params_map.merge(sheet, left_on='param', right_on='策略详情', how='left')

    # 按照累积净值排序，并整理结果
    all_params_map.sort_values(by='累积净值', ascending=False, inplace=True)
    all_params_map = all_params_map[[*sheet.columns, *report_columns]].drop(columns=['param'])
    all_params_map.to_excel(backtest_factory.result_folder / f'最优参数.xlsx', index=False)
    print(all_params_map)
    print(f'✅ 完成展示最优参数，花费时间：{time.time() - s_time:.2f}秒，累计时间：{(time.time() - r_time):.3f}秒')
    print()
