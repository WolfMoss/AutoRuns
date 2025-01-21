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
    for roebaifenbi in ('pct:<=0.2','pct:<=0.4','pct:<=0.6','pct:<=0.8'):
        strategy_list = [{
                'name': '小市值策略',  # 策略名，对应策略库中的文件名，比如`小市值_基本面优化.py`
                'hold_period': '10D',  # 持仓周期，W 代表周，M 代表月，还支持日频：3D、5D、10D
                'offset_list': [0],
                'select_num': 5,  # 选股数量，可以是整数，也可以是小数，比如 0.1 表示选取 10% 的股票
                'cap_weight': 1,
                "factor_list": [  # 选股因子列表
                # ** 因子格式说明 **
                # 因子名称（与 '因子库' 文件中的名称一致），排序方式（True 为升序，False 为降序），因子参数，因子权重
                # ('成交额缩量因子', True, (10, 60), 1),
                # ('成交额缩波因子', True, (10, 60), 1),
                # ('Ret', True, 5, 1),
                # ('Ret', True, 10, 1),
                # ('收盘价', True, None, 1),
                ('市值', True, None, 1),
                # ('换手率', True, 5, 1),
                # ('换手率', True, 1, 1),
                # 案例说明：使用'市值.py'因子，从小到大排序（越小越是我想要），None表示无额外参数，后面计算复合选股因子的时候权重为1
                # 可添加多个选股因子
                ],
                "filter_list": [
                    # ('月份', [2], 'val:==1'),  # 只在2月份选股
                    # ('市值', None, 'pct:<=0.8'),
                    ('ROE', '单季', roebaifenbi),
                    ('代码开头', ['sh688'], 'val:!=1'),
                    ('月份', [1,4], 'val:!=1'),  # 不在4月份选股
                    # ('Ret', 5, 'pct:<=0.1'),
                    # ('收盘价', None, 'pct:<=0.5'),
                    ('换手率', 1, 'pct:<=0.8')

                    # ('成交额缩量因子', (10, 60), 'pct:<=0.6',True),

                ]
        }]
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
