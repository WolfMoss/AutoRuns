#!/usr/bin/env python
# -*- coding: utf-8 -*-
import backtrader as bt
import datetime
import pandas as pd
import os

# 定义策略
class MACrossStrategy(bt.Strategy):
    params = (
        ('fast_length', 4),
        ('slow_length', 16),
    )

    def __init__(self):
        # 初始化移动平均线指标
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast_length)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow_length)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # 跟踪订单和持仓
        self.order = None
        self.position_size = 0

    def next(self):
        # 如果有未完成的订单，不操作
        if self.order:
            return
            
        # 没有持仓
        if not self.position:
            # 金叉买入信号
            if self.crossover > 0:
                self.order = self.buy()
                print(f'买入信号 - 价格: {self.data.close[0]}')
        # 有持仓
        else:
            # 死叉卖出信号
            if self.crossover < 0:
                self.order = self.sell()
                print(f'卖出信号 - 价格: {self.data.close[0]}')

# 主函数
def run_backtest(data_path):
    # 创建引擎
    cerebro = bt.Cerebro()
    
    # 加载数据
    data = pd.read_csv(data_path)
    data['datetime'] = pd.to_datetime(data['datetime'])
    data.set_index('datetime', inplace=True)
    
    # 转换为Backtrader数据格式
    feed = bt.feeds.PandasData(
        dataname=data,
        datetime=None,  # 已经设置为索引
        open=0,
        high=1,
        low=2,
        close=3,
        volume=5,
        openinterest=-1
    )
    
    cerebro.adddata(feed)
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    
    # 设置佣金
    cerebro.broker.setcommission(commission=0.001)  # 0.1%
    
    # 添加策略
    cerebro.addstrategy(MACrossStrategy)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # 运行回测
    print(f'初始资金: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    print(f'最终资金: {cerebro.broker.getvalue():.2f}')
    
    # 输出分析结果
    strat = results[0]
    print(f'夏普比率: {strat.analyzers.sharpe.get_analysis()["sharperatio"]:.3f}')
    print(f'最大回撤: {strat.analyzers.drawdown.get_analysis()["max"]["drawdown"]:.2f}%')
    print(f'年化收益率: {strat.analyzers.returns.get_analysis()["rnorm100"]:.2f}%')
    
    # 绘制结果
    cerebro.plot(style='candle')

if __name__ == '__main__':
    data_file = "datas/DOGE_USDT_1h.csv"
    run_backtest(data_file) 