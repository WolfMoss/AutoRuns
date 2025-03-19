"""
示例策略模块

提供双均线交叉策略作为示例
"""

from typing import Dict, List, Optional

from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator, ArrayManager
# 直接继承官方的CTA策略类
from vnpy_ctastrategy import CtaTemplate
from vnpy_ctastrategy.backtesting import BacktestingEngine, OptimizationSetting


class SampleStrategy(CtaTemplate):
    """
    简单双均线交叉策略
    当快速均线上穿慢速均线时买入
    当快速均线下穿慢速均线时卖出
    """
    
    # 策略参数
    fast_window = 4  # 快速均线窗口
    slow_window = 16  # 慢速均线窗口
    
    # 策略变量
    fast_ma = 0.0  # 快速均线
    slow_ma = 0.0  # 慢速均线
    fast_ma_prev = 0.0  # 上一期快速均线
    slow_ma_prev = 0.0  # 上一期慢速均线
    
    # 参数列表，会被进行参数优化
    parameters = ["fast_window", "slow_window"]
    
    # 变量列表，会在GUI中显示
    variables = ["fast_ma", "slow_ma"]
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """
        初始化策略
        """
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # 初始化技术指标计算工具
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        
        # 将参数传递进来
        if "fast_window" in setting:
            self.fast_window = setting["fast_window"]
        if "slow_window" in setting:
            self.slow_window = setting["slow_window"]

        print("初始化成功")
    
    def on_init(self):
        """
        策略初始化完成时调用
        """
        self.write_log("策略初始化完成")
        
    def on_start(self):
        """
        策略启动时调用
        """
        self.write_log("策略启动")
    
    def on_stop(self):
        """
        策略停止时调用
        """
        self.write_log("策略停止")
        
    def on_tick(self, tick: TickData):
        """
        Tick数据更新时调用
        """
        self.bg.update_tick(tick)
    
    def on_bar(self, bar: BarData):
        """
        K线数据更新时调用的方法
        """

        
        # 更新技术指标
        am = self.am
        am.update_bar(bar)
        
        if not am.inited:
            return
        
        # 保存上一期均线数据
        self.fast_ma_prev = self.fast_ma
        self.slow_ma_prev = self.slow_ma
        
        # 计算快速均线
        self.fast_ma = am.sma(self.fast_window)
        # 计算慢速均线
        self.slow_ma = am.sma(self.slow_window)
        
        # 如果均线未完全计算好，则返回
        if not self.fast_ma or not self.slow_ma:
            return
        
        # 判断均线交叉 - 修正后的逻辑
        cross_over = (self.fast_ma > self.slow_ma) and (self.fast_ma_prev <= self.slow_ma_prev)
        cross_below = (self.fast_ma < self.slow_ma) and (self.fast_ma_prev >= self.slow_ma_prev)
        
        # 根据交叉信号交易
        if cross_over:  # 金叉买入
            if self.pos == 0:
                # 计算买入价格和数量
                price = bar.close_price  # 以收盘价买入
                volume = 1.0  # 买入1个单位
                
                # 发出买入信号
                self.buy(price, volume)
                self.write_log(f"金叉买入信号: fast_ma={self.fast_ma:.2f}, slow_ma={self.slow_ma:.2f}")
                
        elif cross_below:  # 死叉卖出
            if self.pos > 0:
                # 计算卖出价格和数量
                price = bar.close_price  # 以收盘价卖出
                volume = abs(self.pos)  # 卖出全部持仓
                
                # 发出卖出信号
                self.sell(price, volume)
                self.write_log(f"死叉卖出信号: fast_ma={self.fast_ma:.2f}, slow_ma={self.slow_ma:.2f}") 