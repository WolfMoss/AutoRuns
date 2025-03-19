"""
回测执行入口

用于运行策略回测
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List

from vnpy.trader.constant import Exchange, Interval
from vnpy_ctastrategy.backtesting import OptimizationSetting

from engine import BacktestEngine
from strategies import BaseStrategy, SampleStrategy
from utils.performance import plot_performance
from config import BACKTEST_CONFIG, DATA_DIR, SYMBOLS, TIMEFRAME, STRATEGY_PARAMS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backtest")


def run_single_backtest(strategy_class, params=None):
    """
    运行单一策略回测
    
    :param strategy_class: 策略类
    :param params: 策略参数
    """
    logger.info(f"开始回测策略: {strategy_class.__name__}")
    
    # 创建回测引擎
    engine = BacktestEngine(BACKTEST_CONFIG, DATA_DIR)
    
    # 加载所有交易对数据
    for symbol in SYMBOLS:
        logger.info(f"正在加载交易对数据: {symbol}")
        # 如果symbol包含交易所后缀，去除它
        if "." in symbol:
            symbol = symbol.split(".")[0]
        engine.add_data(
            symbol=symbol,
            interval=Interval(TIMEFRAME)
        )
    
    # 使用默认参数或指定参数
    if params is None:
        strategy_name = strategy_class.__name__
        params = STRATEGY_PARAMS.get(strategy_name, {})
    
    logger.info(f"添加策略: {strategy_class.__name__}, 参数: {params}")
    # 添加策略
    engine.add_strategy(strategy_class, params)
    
    # 运行回测
    logger.info("开始运行回测...")
    result, daily_df = engine.run_backtest()
    
    # 显示结果
    stats = engine.show_results()
    
    # 绘制图表
    engine.plot_results(save_path=f"{strategy_class.__name__}_result.png")
    
    logger.info(f"回测完成: {strategy_class.__name__}")
    
    return result, daily_df, stats


def run_optimization(strategy_class):
    """
    运行参数优化
    
    :param strategy_class: 策略类
    """
    logger.info(f"开始参数优化: {strategy_class.__name__}")
    
    # 创建回测引擎
    engine = BacktestEngine(BACKTEST_CONFIG, DATA_DIR)
    
    # 加载所有交易对数据
    for symbol in SYMBOLS:
        engine.add_data(
            symbol=symbol,
            interval=Interval(TIMEFRAME)
        )
    
    # 创建优化设置
    setting = OptimizationSetting()
    
    # 针对双均线策略设置优化参数范围
    if strategy_class.__name__ == "SampleStrategy":
        setting.add_parameter("fast_window", 2, 20, 1)
        setting.add_parameter("slow_window", 10, 60, 5)
        # 设置优化目标
        setting.set_target("sharpe_ratio")
    else:
        # 针对其他策略设置不同的参数范围
        pass
    
    # 运行优化
    results = engine.optimize(strategy_class, setting)
    
    # 输出结果
    for result in results:
        msg = f"参数: {result[0]}, 目标值: {result[1]:.2f}"
        logger.info(msg)
    
    logger.info(f"参数优化完成: {strategy_class.__name__}")
    
    return results


def main():
    """主函数"""
    # 检查数据目录
    if not os.path.exists(DATA_DIR):
        logger.error(f"数据目录不存在: {DATA_DIR}")
        return
    
    # 运行回测
    run_single_backtest(SampleStrategy)
    
    # 运行参数优化
    # run_optimization(SampleStrategy)


if __name__ == "__main__":
    main() 