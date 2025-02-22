from strategy.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, symbol):
        self.symbol = symbol
        self.window = 4  # 移动平均窗口期
        self.prices = []  # 存储收盘价
        self.oscillation_threshold = 0.05  # 当两个均线之差比例小于1%时，视为震荡市场，不进仓

    def init_strategy(self, engine):
        super().init_strategy(engine)
        print(f"策略初始化: {self.symbol}")

    def on_bar(self, bar):
        close_price = bar['close']
        ma4 = bar['ma4']
        ma16 = bar['ma16']
        self.prices.append(close_price)
        if len(self.prices) < self.window:
            return  # 数据不足，暂不操作

        # 计算两个均线之差的比例，判断是否处于震荡状态
        ratio = abs(ma4 - ma16) / ma16 if ma16 != 0 else 0
        if ratio < self.oscillation_threshold:
            print("市场震荡，暂不开仓")
            return

        # 趋势跟踪策略逻辑
        if ma4 > ma16:
            if self.engine.position < 0:
                # 当前持空，买入平仓
                volume = abs(self.engine.position)
                self.engine.execute_order('buy', close_price, volume)
            elif self.engine.position == 0:
                # 空仓时看涨，开多
                self.engine.execute_order('buy', close_price, 1)
        elif ma4 < ma16:
            if self.engine.position > 0:
                # 当前持多，看跌，卖出平仓
                volume = self.engine.position
                self.engine.execute_order('sell', close_price, volume)
            elif self.engine.position == 0:
                # 空仓时看跌，开空
                self.engine.execute_order('sell', close_price, 1)
    
    def on_backtest_end(self):
        print("策略回测结束") 