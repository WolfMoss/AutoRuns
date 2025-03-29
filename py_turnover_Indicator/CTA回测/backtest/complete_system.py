#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib.pyplot as plt
import backtrader as bt
from datetime import datetime
from datacore.calculate_factors import calculate_factors

class TradingSystem:
    """完整的量化交易系统"""
    
    def __init__(self, data_dir="datas"):
        self.data_dir = data_dir
        self.available_symbols = self._get_available_symbols()
        print(f"可用交易对: {self.available_symbols}")
        
    def _get_available_symbols(self):
        """获取可用的交易对列表"""
        files = os.listdir(self.data_dir)
        return [f.replace(".csv", "") for f in files if f.endswith(".csv")]
    
    def preprocess_data(self, symbol):
        """预处理数据，计算因子"""
        filepath = os.path.join(self.data_dir, f"{symbol}.csv")
        if not os.path.exists(filepath):
            print(f"找不到交易对数据: {filepath}")
            return None
        
        df = pd.read_csv(filepath)
        print(f"读取 {symbol} 数据: {len(df)} 行")
        
        # 计算技术指标/因子
        df = calculate_factors(df)
        return df
    
    def run_backtest(self, symbol, strategy_class, **kwargs):
        """运行回测"""
        # 预处理数据
        df = self.preprocess_data(symbol)
        if df is None:
            return None
        
        # 创建回测引擎
        cerebro = bt.Cerebro()
        
        # 设置数据
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,
            open=df.columns.get_loc('open'),
            high=df.columns.get_loc('high'),
            low=df.columns.get_loc('low'),
            close=df.columns.get_loc('close'),
            volume=df.columns.get_loc('volume'),
            openinterest=-1
        )
        
        cerebro.adddata(data)
        
        # 设置初始资金
        cerebro.broker.setcash(100000.0)
        
        # 设置佣金
        cerebro.broker.setcommission(commission=0.001)
        
        # 添加策略
        cerebro.addstrategy(strategy_class, **kwargs)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # 运行回测
        print(f"开始回测 {symbol} 使用 {strategy_class.__name__}")
        print(f"初始资金: {cerebro.broker.getvalue():.2f}")
        results = cerebro.run()
        print(f"最终资金: {cerebro.broker.getvalue():.2f}")
        
        # 分析结果
        self._analyze_results(results[0])
        
        # 绘制图表
        cerebro.plot(style='candle', volume=True)
        
        return results
    
    def _analyze_results(self, strat):
        """分析回测结果"""
        print("\n==== 回测性能分析 ====")
        
        # 夏普比率
        try:
            sharpe = strat.analyzers.sharpe.get_analysis()['sharperatio']
            print(f"夏普比率: {sharpe:.4f}")
        except:
            print("无法计算夏普比率")
        
        # 最大回撤
        try:
            dd = strat.analyzers.drawdown.get_analysis()
            print(f"最大回撤: {dd['max']['drawdown']:.2f}%")
            print(f"最大回撤金额: {dd['max']['moneydown']:.2f}")
        except:
            print("无法计算最大回撤")
        
        # 收益率
        try:
            returns = strat.analyzers.returns.get_analysis()
            print(f"总收益率: {returns['rtot']:.4f}")
            print(f"年化收益率: {returns['rnorm100']:.2f}%")
        except:
            print("无法计算收益率")
        
        # 交易统计
        try:
            trades = strat.analyzers.trades.get_analysis()
            print(f"总交易次数: {trades['total']['total']}")
            print(f"盈利交易次数: {trades['won']['total']}")
            print(f"亏损交易次数: {trades['lost']['total']}")
            if trades['won']['total'] > 0:
                print(f"平均盈利: {trades['won']['pnl']['average']:.4f}")
                print(f"最大盈利: {trades['won']['pnl']['max']:.4f}")
            if trades['lost']['total'] > 0:
                print(f"平均亏损: {trades['lost']['pnl']['average']:.4f}")
                print(f"最大亏损: {trades['lost']['pnl']['max']:.4f}")
            win_rate = trades['won']['total'] / trades['total']['total'] if trades['total']['total'] > 0 else 0
            print(f"胜率: {win_rate:.2%}")
        except:
            print("无法计算交易统计")

# 定义一个移动平均交叉策略
class MAcrossStrategy(bt.Strategy):
    params = (
        ('fast_period', 4),
        ('slow_period', 16),
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        self.order = None
    
    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.crossover > 0:  # 金叉
                self.order = self.buy()
        else:
            if self.crossover < 0:  # 死叉
                self.order = self.sell()

if __name__ == "__main__":
    # 创建交易系统
    system = TradingSystem()
    
    # 运行回测
    symbol = "DOGE_USDT_1h"
    system.run_backtest(symbol, MAcrossStrategy) 