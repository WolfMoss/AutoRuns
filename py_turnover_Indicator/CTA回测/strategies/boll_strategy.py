"""
布林带策略
"""
from vnpy.trader.constant import Direction
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
)
from vnpy_ctastrategy.backtesting import BacktestingEngine

class BollStrategy(CtaTemplate):
    """
    布林带策略
    
    策略逻辑：
    1. 价格突破上轨，做多
    2. 价格跌破下轨，做空
    3. 价格回归中轨，平仓
    """
    
    author = "VN Trader"
    
    # 策略参数
    boll_window = 20              # 布林带周期
    boll_dev = 2.0                # 布林带宽度
    risk_percent = 0.02           # 风险百分比
    
    # 策略变量
    boll_up = 0.0                 # 布林带上轨
    boll_down = 0.0               # 布林带下轨
    boll_mid = 0.0                # 布林带中轨
    
    # 参数列表，用于GUI显示
    parameters = [
        "boll_window",
        "boll_dev",
        "risk_percent",
    ]
    
    # 变量列表，用于GUI显示
    variables = [
        "boll_up",
        "boll_down",
        "boll_mid",
    ]
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """
        初始化策略
        """
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # 创建K线生成器
        self.bg = BarGenerator(self.on_bar)
        # 创建技术指标计算器
        self.am = ArrayManager(self.boll_window + 100)
    
    def on_init(self):
        """
        策略初始化回调
        """
        self.write_log("策略初始化")
        self.load_bar(10)  # 加载10天的历史数据
    
    def on_start(self):
        """
        策略启动回调
        """
        self.write_log("策略启动")
    
    def on_stop(self):
        """
        策略停止回调
        """
        self.write_log("策略停止")
    
    def on_tick(self, tick: TickData):
        """
        Tick数据回调
        """
        self.bg.update_tick(tick)
    
    def on_bar(self, bar: BarData):
        """
        K线数据回调
        """
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        
        # 计算布林带指标 - 新版VNPY的boll()方法返回(mid, std_dev)
        self.boll_mid, std_dev = am.boll(self.boll_window, self.boll_dev)
        
        # 手动计算上轨和下轨
        self.boll_up = self.boll_mid + self.boll_dev * std_dev
        self.boll_down = self.boll_mid - self.boll_dev * std_dev
        
        # 多头入场条件：突破上轨
        if bar.close_price > self.boll_up and self.pos == 0:
            # 计算头寸大小
            atr_value = am.atr(20)
            risk_amount = self.risk_percent * self.cta_engine.capital
            size = max(1, int(risk_amount / (atr_value * 2)))
            
            # 开多仓
            self.buy(bar.close_price, size)
        
        # 空头入场条件：跌破下轨
        elif bar.close_price < self.boll_down and self.pos == 0:
            # 计算头寸大小
            atr_value = am.atr(20)
            risk_amount = self.risk_percent * self.cta_engine.capital
            size = max(1, int(risk_amount / (atr_value * 2)))
            
            # 开空仓
            self.short(bar.close_price, size)
        
        # 多头平仓条件：回归中轨
        elif self.pos > 0 and bar.close_price < self.boll_mid:
            self.sell(bar.close_price, abs(self.pos))
        
        # 空头平仓条件：回归中轨
        elif self.pos < 0 and bar.close_price > self.boll_mid:
            self.cover(bar.close_price, abs(self.pos))
        
        # 更新图表
        self.put_event()
    
    def on_trade(self, trade: TradeData):
        """
        交易回调
        """
        self.put_event()
    
    def on_order(self, order: OrderData):
        """
        订单回调
        """
        self.put_event()
    
    def on_stop_order(self, stop_order: StopOrder):
        """
        停止单回调
        """
        self.put_event() 