"""
回测系统配置文件
"""

import os

# 路径配置
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "datas")  # 修正为当前目录下的datas文件夹


# 回测参数配置
BACKTEST_CONFIG = {
    "start_date": "2023-01-01",  # 回测开始日期
    "end_date": "2025-01-01",    # 回测结束日期
    "initial_capital": 100000,   # 初始资金
    "commission_rate": 0.0002,   # 手续费率
    "slippage": 1,               # 滑点
    "size": 1,                   # 合约乘数
    "pricetick": 0.01,           # 最小价格变动
    "capital_base": 100000,      # 基准资金
    "symbol": "BTC_USDT",        # 默认交易对
    "interval": "1h",            # 时间周期
}

# 交易对配置
SYMBOLS = [
    "BTC_USDT",    # 简化交易对名称
    "ETH_USDT",
    "BNB_USDT",
    "DOGE_USDT",
]

# ... existing code ...


# 时间周期配置
TIMEFRAME = "1h"

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(ROOT_DIR, "backtest.log")

# 策略参数，不同的策略使用不同的参数字典
STRATEGY_PARAMS = {
    "SampleStrategy": {
        "fast_window": 4,
        "slow_window": 16,
    },
    # 可以添加其他策略的参数
} 