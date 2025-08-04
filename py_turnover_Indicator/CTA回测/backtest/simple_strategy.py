#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单交易策略示例
基于移动平均线的经典策略
适合新手理解回测逻辑
"""

import backtrader as bt
import pandas as pd
from datetime import datetime

class SimpleMAStrategy(bt.Strategy):
    """
    简单移动平均线策略
    - 当短期均线上穿长期均线时买入
    - 当短期均线下穿长期均线时卖出
    """
    
    # 策略参数
    params = (
        ('ma_short', 10),    # 短期移动平均线周期
        ('ma_long', 30),     # 长期移动平均线周期
        ('printlog', True),  # 是否打印交易日志
    )

    def __init__(self):
        """初始化策略"""
        # 获取数据的收盘价
        self.dataclose = self.datas[0].close
        
        # 计算移动平均线
        self.ma_short = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.ma_short)
        self.ma_long = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.ma_long)
        
        # 计算移动平均线交叉信号
        self.crossover = bt.indicators.CrossOver(self.ma_short, self.ma_long)
        
        # 记录订单状态
        self.order = None
        
        # 记录交易统计
        self.buy_count = 0
        self.sell_count = 0

    def next(self):
        """策略主逻辑 - 每个数据点都会调用"""
        
        # 如果有未执行的订单，跳过
        if self.order:
            return

        # 如果当前没有持仓
        if not self.position:
            # 金叉信号：短期均线上穿长期均线，买入
            if self.crossover[0] > 0:
                # 买入信号
                self.log(f'买入信号, 价格: {self.dataclose[0]:.2f}')
                # 下买单
                self.order = self.buy()
                self.buy_count += 1
                
        else:
            # 如果已经持仓
            # 死叉信号：短期均线下穿长期均线，卖出
            if self.crossover[0] < 0:
                # 卖出信号
                self.log(f'卖出信号, 价格: {self.dataclose[0]:.2f}')
                # 下卖单
                self.order = self.sell()
                self.sell_count += 1

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需处理
            return

        # 检查订单是否完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'手续费: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'手续费: {order.executed.comm:.2f}')

            # 重置订单状态
            self.order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
            self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        self.log(f'交易完成, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def log(self, txt, dt=None):
        """统一的日志输出函数"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    def stop(self):
        """策略结束时调用"""
        self.log(f'策略结束, MA短期: {self.params.ma_short}, MA长期: {self.params.ma_long}, '
                f'最终资金: {self.broker.getvalue():.2f}')
        self.log(f'交易统计 - 买入次数: {self.buy_count}, 卖出次数: {self.sell_count}')


class RSIStrategy(bt.Strategy):
    """
    RSI策略示例
    - RSI < 30 时买入（超卖）
    - RSI > 70 时卖出（超买）
    """
    
    params = (
        ('rsi_period', 14),  # RSI周期
        ('rsi_upper', 70),   # RSI上限
        ('rsi_lower', 30),   # RSI下限
        ('printlog', True),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.datas[0], period=self.params.rsi_period)
        self.order = None
        self.buy_count = 0
        self.sell_count = 0

    def next(self):
        if self.order:
            return

        if not self.position:
            # RSI超卖，买入
            if self.rsi[0] < self.params.rsi_lower:
                self.log(f'RSI超卖买入, RSI: {self.rsi[0]:.2f}, 价格: {self.dataclose[0]:.2f}')
                self.order = self.buy()
                self.buy_count += 1
        else:
            # RSI超买，卖出
            if self.rsi[0] > self.params.rsi_upper:
                self.log(f'RSI超买卖出, RSI: {self.rsi[0]:.2f}, 价格: {self.dataclose[0]:.2f}')
                self.order = self.sell()
                self.sell_count += 1

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}')
            self.order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单失败')
            self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'交易完成, 净利润: {trade.pnlcomm:.2f}')

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    def stop(self):
        self.log(f'RSI策略结束, 最终资金: {self.broker.getvalue():.2f}')
        self.log(f'交易统计 - 买入: {self.buy_count}, 卖出: {self.sell_count}') 