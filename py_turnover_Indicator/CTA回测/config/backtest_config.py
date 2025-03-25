"""
回测配置文件
"""

# 回测设置
SETTINGS = {
    "start_date": "2022-12-31",  # 回测开始日期
    "end_date": "2025-03-1",    # 回测结束日期
    "init_capital": 100000,      # 初始资金
    "contract_multiplier": 1,    # 合约乘数
    "commission_rate": 0.0006,   # 手续费率
    "slippage": 0,               # 滑点
    "mode": "bar",               # 回测模式，bar代表K线回测
    "interval": "1h",            # 回测时间周期
}

# 交易品种
SYMBOL_CONFIG = {
    "symbol": "DOGE",            # 交易品种
    "exchange": "BINANCE",       # 交易所名称（会被映射到枚举值）
    "currency": "USDT",          # 计价货币
}

# 策略配置
STRATEGY_CONFIG = {
    "name": "MaStrategy",        # 策略名称，可选：MaStrategy, BollStrategy
    "class_name": "MaStrategy",  # 策略类名
    "parameters": {
        # 快速均线周期
        "fast_window": 10,
        "slow_window": 30,
        "trailing_percent": 0.8,
        "risk_percent": 0.02,
    }
}

# 数据路径配置
DATA_CONFIG = {
    "data_folder": "datas",      # 数据文件夹路径
} 