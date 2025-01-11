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

from core.model.backtest_config import load_config
from core.select_stock import select_stocks, concat_select_results
from core.utils.log_kit import logger, divider
from core.version import version_prompt

# ====================================================================================================
# ** 配置与初始化 **
# 忽略警告并设定显示选项，以优化代码输出的可读性
# ====================================================================================================
warnings.filterwarnings('ignore')
pd.set_option('expand_frame_repr', False)
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

if __name__ == '__main__':
    version_prompt()
    conf = load_config()
    print(conf.info())

    # 根据计算得到的因子进行选股
    divider('条件选股', '-')
    s_time = time.time()
    select_stocks(conf, boost=True)
    select_results = concat_select_results(conf)  # 合并多个策略的选币结果

    logger.debug(f'💾 选股结果数据大小：{select_results.memory_usage(deep=True).sum() / 1024 / 1024:.4f} MB')
    logger.ok(f'选股完成，总耗时：{time.time() - s_time:.3f}秒')
