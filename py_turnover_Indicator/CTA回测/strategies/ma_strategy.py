"""
移动平均线策略
"""
from vnpy.trader.constant import Direction
from vnpy.trader.object import TickData, BarData, TradeData, OrderData
from vnpy.trader.utility import BarGenerator, ArrayManager
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
)
from vnpy_ctastrategy.backtesting import BacktestingEngine

class MaStrategy(CtaTemplate):
    """
    移动平均线策略
    
    策略逻辑：
    1. 当快速均线上穿慢速均线时，做多
    2. 当快速均线下穿慢速均线时，做空
    3. 采用百分比风险管理和追踪止损
    """
    
    author = "VN Trader"
    
    # 策略参数
    fast_window = 10              # 快速均线周期
    slow_window = 30              # 慢速均线周期
    trailing_percent = 0.8        # 追踪止损百分比
    risk_percent = 0.02           # 风险百分比
    
    # 策略变量
    fast_ma0 = 0.0                # 当前快速均线
    fast_ma1 = 0.0                # 上一周期快速均线
    slow_ma0 = 0.0                # 当前慢速均线
    slow_ma1 = 0.0                # 上一周期慢速均线
    
    # 参数列表，用于GUI显示
    parameters = [
        "fast_window",
        "slow_window",
        "trailing_percent",
        "risk_percent"
    ]
    
    # 变量列表，用于GUI显示
    variables = [
        "fast_ma0",
        "fast_ma1",
        "slow_ma0",
        "slow_ma1",
    ]
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """
        初始化策略
        """
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # 创建K线生成器
        self.bg = BarGenerator(self.on_bar)
        # 创建技术指标计算器
        self.am = ArrayManager(max(self.slow_window, self.fast_window) + 10)
        
        # 记录最高价
        self.high_price = 0
        # 记录最低价
        self.low_price = float('inf')
        
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
        
        # 计算均线指标
        fast_ma_array = am.sma(self.fast_window, array=True)
        self.fast_ma0 = fast_ma_array[-1]
        self.fast_ma1 = fast_ma_array[-2]
        
        slow_ma_array = am.sma(self.slow_window, array=True)
        self.slow_ma0 = slow_ma_array[-1]
        self.slow_ma1 = slow_ma_array[-2]
        
        # 判断金叉和死叉
        cross_over = self.fast_ma1 < self.slow_ma1 and self.fast_ma0 > self.slow_ma0
        cross_below = self.fast_ma1 > self.slow_ma1 and self.fast_ma0 < self.slow_ma0
        
        # 更新最高最低价格
        if self.pos > 0:
            self.high_price = max(self.high_price, bar.high_price)
        elif self.pos < 0:
            self.low_price = min(self.low_price, bar.low_price)
        
        # 多头入场
        if cross_over:
            # 如果有空仓，先平仓
            if self.pos < 0:
                self.cover(bar.close_price, abs(self.pos))
            
            # 计算头寸大小
            price = bar.close_price
            atr_value = am.atr(20)
            risk_amount = self.risk_percent * self.cta_engine.capital
            size = max(1, int(risk_amount / (atr_value * 2)))
            
            # 开多仓
            self.buy(price, size)
            # 重置最高价
            self.high_price = price
        
        # 空头入场
        elif cross_below:
            # 如果有多仓，先平仓
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos))
            
            # 计算头寸大小
            price = bar.close_price
            atr_value = am.atr(20)
            risk_amount = self.risk_percent * self.cta_engine.capital
            size = max(1, int(risk_amount / (atr_value * 2)))
            
            # 开空仓
            self.short(price, size)
            # 重置最低价
            self.low_price = price
        
        # 追踪止损
        elif self.pos > 0:
            # 多头追踪止损
            if bar.close_price < self.high_price * (1 - self.trailing_percent / 100):
                self.sell(bar.close_price, abs(self.pos))
                self.high_price = 0
        
        elif self.pos < 0:
            # 空头追踪止损
            if bar.close_price > self.low_price * (1 + self.trailing_percent / 100):
                self.cover(bar.close_price, abs(self.pos))
                self.low_price = float('inf')
        
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