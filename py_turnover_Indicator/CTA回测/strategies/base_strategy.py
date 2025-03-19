"""
基础策略模块

定义所有策略的基类，提供统一的接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy_ctastrategy import CtaTemplate


class BaseStrategy(CtaTemplate):
    """
    基础策略类，继承自VNPY的CtaTemplate
    所有自定义策略都应继承此类
    """
    
    # 类变量，用于策略参数
    author = "CTA回测框架"
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """
        初始化策略
        
        :param cta_engine: CTA引擎
        :param strategy_name: 策略名称
        :param vt_symbol: 交易对名称
        :param setting: 策略参数
        """
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # K线周期生成器
        self.bg = BarGenerator(self.on_bar)
        
        # 技术指标计算器
        self.am = ArrayManager(size=100)  # 默认保存100根K线
        
        # 交易状态
        self.pos = 0  # 当前持仓
        
        # 自定义变量，子类可继承
        self.trading_allowed = True  # 是否允许交易
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log("策略初始化")
        self.load_bar(10)  # 默认加载10根K线
    
    def on_start(self):
        """策略启动回调"""
        self.write_log("策略启动")
    
    def on_stop(self):
        """策略停止回调"""
        self.write_log("策略停止")
    
    def on_tick(self, tick: TickData):
        """
        Tick数据回调
        """
        self.bg.update_tick(tick)
    
    def on_bar(self, bar: BarData):
        """
        K线数据回调，主要的策略计算逻辑
        子类必须实现此方法
        
        :param bar: K线数据
        """
        # 更新技术指标
        am = self.am
        am.update_bar(bar)
        
        # 指标计算完成前不进行交易
        if not am.inited:
            return
        
        # 子类实现具体的策略逻辑
        self.calculate_signals(bar)
    
    @abstractmethod
    def calculate_signals(self, bar: BarData):
        """
        计算交易信号，子类必须实现此方法
        
        :param bar: K线数据
        """
        pass
    
    def buy(self, price, volume, stop=False):
        """
        买入开仓
        
        :param price: 价格
        :param volume: 数量
        :param stop: 是否为停止单
        """
        if not self.trading_allowed:
            return
        
        return super().buy(price, volume, stop)
    
    def sell(self, price, volume, stop=False):
        """
        卖出平仓
        
        :param price: 价格
        :param volume: 数量
        :param stop: 是否为停止单
        """
        if not self.trading_allowed:
            return
        
        return super().sell(price, volume, stop)
    
    def short(self, price, volume, stop=False):
        """
        卖出开仓
        
        :param price: 价格
        :param volume: 数量
        :param stop: 是否为停止单
        """
        if not self.trading_allowed:
            return
        
        return super().short(price, volume, stop)
    
    def cover(self, price, volume, stop=False):
        """
        买入平仓
        
        :param price: 价格
        :param volume: 数量
        :param stop: 是否为停止单
        """
        if not self.trading_allowed:
            return
        
        return super().cover(price, volume, stop) 