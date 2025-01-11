"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import warnings

import pandas as pd

from core.model.backtest_config import load_config
from core.data_center import prepare_data
from core.version import version_prompt

# ====================================================================================================
# ** 配置与初始化 **
# 设置必要的显示选项及忽略警告，以优化代码输出的阅读体验
# ====================================================================================================
warnings.filterwarnings('ignore')  # 忽略不必要的警告
pd.set_option('expand_frame_repr', False)  # 使数据框在控制台显示不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

if __name__ == '__main__':
    version_prompt()
    conf = load_config()
    print(conf.info())

    prepare_data(conf, boost=True)
