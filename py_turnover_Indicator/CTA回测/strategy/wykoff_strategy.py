import numpy as np
from strategy.base_strategy import BaseStrategy

class WykoffStrategy(BaseStrategy):
    def __init__(self, symbol):
        self.symbol = symbol
        self.prices = []  # 存储收盘价
        self.volumes = []  # 存储成交量
        self.threshold = 1.5  # 成交量阈值
        self.stop_loss_pct = 0.02  # 止损百分比
        self.take_profit_pct = 0.05  # 止盈百分比
        self.short_window = 5  # 短期移动平均窗口
        self.long_window = 20  # 长期移动平均窗口

    def init_strategy(self, engine):
        super().init_strategy(engine)
        print(f"威科夫策略初始化: {self.symbol}")

    def calculate_rsi(self, prices, period=14):
        if len(prices) < period:
            return None
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0).mean()
        loss = -np.where(deltas < 0, deltas, 0).mean()
        rs = gain / loss if loss != 0 else 0
        return 100 - (100 / (1 + rs))

    def on_bar(self, bar):
        close_price = bar['close']
        volume = bar['volume']
        self.prices.append(close_price)
        self.volumes.append(volume)

        if len(self.prices) < self.long_window:
            return  # 数据不足，暂不操作

        # 计算移动平均线
        short_ma = np.mean(self.prices[-self.short_window:])
        long_ma = np.mean(self.prices[-self.long_window:])

        # 计算RSI
        rsi = self.calculate_rsi(self.prices)

        # 检查止损和止盈
        if self.engine.position > 0:  # 持有多仓
            if close_price <= self.entry_price * (1 - self.stop_loss_pct):
                self.engine.execute_order('sell', close_price, self.engine.position)  # 止损
            elif close_price >= self.entry_price * (1 + self.take_profit_pct):
                self.engine.execute_order('sell', close_price, self.engine.position)  # 止盈

        elif self.engine.position < 0:  # 持有空仓
            if close_price >= self.entry_price * (1 + self.stop_loss_pct):
                self.engine.execute_order('buy', close_price, abs(self.engine.position))  # 止损
            elif close_price <= self.entry_price * (1 - self.take_profit_pct):
                self.engine.execute_order('buy', close_price, abs(self.engine.position))  # 止盈

        # 反转市场趋势判断
        if short_ma > long_ma and rsi < 30:  # 看涨信号
            if self.engine.position <= 0:
                self.entry_price = close_price  # 记录开仓价格
                self.engine.execute_order('buy', close_price, 1)
        elif short_ma < long_ma and rsi > 70:  # 看跌信号
            if self.engine.position >= 0:
                self.entry_price = close_price  # 记录开仓价格
                self.engine.execute_order('sell', close_price, 1)

    def on_backtest_end(self):
        print("威科夫策略回测结束") 