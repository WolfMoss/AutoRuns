"""
回测引擎模块

提供基于VNPY的回测引擎，用于执行策略回测
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Type

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy_ctastrategy import CtaTemplate
from vnpy_ctastrategy.backtesting import BacktestingEngine, OptimizationSetting

from .loader import DataLoader
from utils.performance import calculate_statistics

import logging
logger = logging.getLogger(__name__)

import vnpy
print(f"VNPy版本: {vnpy.__version__}")

class BacktestEngine:
    """回测引擎，封装VNPY的回测功能"""
    
    def __init__(self, config: Dict, data_dir: str):
        """
        初始化回测引擎
        
        :param config: 回测配置
        :param data_dir: 数据目录
        """
        self.config = config
        self.data_dir = data_dir
        self.data_loader = DataLoader(data_dir)
        
        # 创建VNPY回测引擎
        self.engine = BacktestingEngine()
        self.setup_engine()
        
        # 结果统计
        self.result = None
        self.daily_df = None
    
    def setup_engine(self):
        """配置回测引擎参数"""
        config = self.config
        
        # 设置回测参数
        self.engine.set_parameters(
            vt_symbol=f"{config.get('symbol', 'BTC_USDT')}.LOCAL",  # 使用LOCAL作为本地回测的交易所标识
            interval=Interval(config.get("interval", "1h")),
            start=datetime.strptime(config.get("start_date", "2023-01-01"), "%Y-%m-%d"),
            end=datetime.strptime(config.get("end_date", "2025-01-01"), "%Y-%m-%d"),
            rate=config.get("commission_rate", 0.0002),  # 手续费率
            slippage=config.get("slippage", 1),  # 滑点
            size=config.get("size", 1),  # 合约乘数
            pricetick=config.get("pricetick", 0.01),  # 最小价格变动
            capital=config.get("initial_capital", 100000)  # 初始资金
        )
    
    def add_data(self, symbol: str, interval: Interval = Interval.HOUR):
        """
        添加K线数据
        
        :param symbol: 交易对名称
        :param interval: 时间周期
        """
        # 如果symbol包含交易所后缀，去除它
        if "." in symbol:
            symbol = symbol.split(".")[0]
        
        # 加载数据
        bars = self.data_loader.load_bar_data(
            symbol=symbol,
            interval=interval,
            start_date=self.config.get("start_date", "2023-01-01"),
            end_date=self.config.get("end_date", "2025-01-01")
        )
        
        if not bars:
            logger.error(f"未能加载任何{symbol}的历史数据")
            return False
        
        # 将数据保存到历史数据列表中，稍后一次性加载
        if not hasattr(self, 'history_bars'):
            self.history_bars = []
        
        # 为每个bar添加交易所信息
        for bar in bars:
            bar.exchange = Exchange.LOCAL
            bar.symbol = symbol
        
        self.history_bars.extend(bars)
        return True
    
    def add_strategy(self, strategy_class: Type[CtaTemplate], strategy_params: Dict = None):
        """
        添加策略
        
        :param strategy_class: 策略类
        :param strategy_params: 策略参数
        """
        if not strategy_params:
            strategy_params = {}
        
        # 打印策略参数
        print(f"添加策略: {strategy_class.__name__}, 参数: {strategy_params}")
        
        # 添加策略到回测引擎
        self.engine.add_strategy(strategy_class, strategy_params)
        
        # 验证策略是否添加成功
        if hasattr(self.engine, 'strategy') and self.engine.strategy is not None:
            print(f"策略添加成功: {self.engine.strategy.__class__.__name__}")
        else:
            print("警告: 策略添加可能失败，engine.strategy为None")
    
    def run_backtest(self):
        """运行回测"""
        logger.info("开始回测...")
        
        # 确保已经添加了策略和数据
        if not hasattr(self, 'history_bars') or not self.history_bars:
            logger.error("没有加载历史数据，请先调用add_data方法")
            return None, None
        
        # 将历史数据按照时间排序
        self.history_bars.sort(key=lambda x: x.datetime)
        
        # 按照vt_symbol分组数据
        symbol_data = {}
        for bar in self.history_bars:
            vt_symbol = bar.vt_symbol
            if vt_symbol not in symbol_data:
                symbol_data[vt_symbol] = []
            symbol_data[vt_symbol].append(bar)
        
        # 打印调试信息
        for vt_symbol, bars in symbol_data.items():
            print(f"交易对 {vt_symbol} 的数据量: {len(bars)}")
            print(f"数据时间范围: {bars[0].datetime} 到 {bars[-1].datetime}")
        
        # 获取主交易对
        main_symbol = list(symbol_data.keys())[0]
        print(f"使用主交易对: {main_symbol}")
        
        # 使用feed_data方法直接馈送数据到引擎
        main_data = symbol_data[main_symbol]
        main_data.sort(key=lambda x: x.datetime)
        
        try:
            # 尝试使用feed_data方法
            print("尝试使用feed_data方法")
            self.engine.feed_data(main_data)
        except Exception as e:
            print(f"feed_data方法失败: {e}")
            # 如果失败，尝试直接设置数据
            try:
                print("尝试直接设置history_data")
                self.engine.history_data = main_data
            except Exception as e2:
                print(f"直接设置history_data失败: {e2}")
                return None, None
        
        # 运行回测
        self.engine.run_backtesting()
        
        # 计算回测结果
        try:
            self.result = self.engine.calculate_result()
            self.daily_df = self.engine.calculate_daily_result()
            
            # 确保daily_df的列名正确
            if self.daily_df is not None and not self.daily_df.empty:
                # 重命名列以匹配期望的格式
                column_mapping = {
                    'datetime': 'date',
                    'balance': 'balance',
                    'drawdown': 'drawdown',
                    'net_pnl': 'net_pnl'
                }
                self.daily_df = self.daily_df.rename(columns=column_mapping)
            
            logger.info("回测完成")
        except Exception as e:
            logger.error(f"计算回测结果时出错: {e}")
            self.result = None
            self.daily_df = None
        
        return self.result, self.daily_df
    
    def show_results(self):
        """显示回测结果"""
        if self.result is None:
            logger.error("没有回测结果，请先运行回测")
            return
        
        # 计算统计指标
        stats = calculate_statistics(self.result, self.daily_df)
        
        # 输出统计结果
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        
        # 返回统计结果
        return stats
    
    def plot_results(self, save_path: str = None):
        """
        绘制回测结果
        
        :param save_path: 保存路径
        """
        if self.result is None:
            logger.error("没有回测结果，请先运行回测")
            return
        
        # 使用VNPY的绘图功能
        self.engine.show_chart(save_path=save_path)
        
    def optimize(self, strategy_class: Type[CtaTemplate], setting: OptimizationSetting):
        """
        参数优化
        
        :param strategy_class: 策略类
        :param setting: 优化设置
        :return: 优化结果
        """
        self.engine.clear_strategy()
        self.engine.add_strategy(strategy_class, {})
        
        logger.info("开始参数优化...")
        self.engine.load_data()
        results = self.engine.run_optimization(setting, output=True)
        
        logger.info("参数优化完成")
        return results

    def print_available_methods(self):
        """打印VNPY回测引擎的可用方法"""
        print([method for method in dir(self.engine) if not method.startswith('_')]) 