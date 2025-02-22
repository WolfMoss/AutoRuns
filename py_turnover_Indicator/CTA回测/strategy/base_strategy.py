class BaseStrategy:
    def init_strategy(self, engine):
        """
        初始化策略，通常用于绑定回测引擎
        """
        self.engine = engine
    
    def on_bar(self, bar):
        """
        每个bar的回调处理，必须实现
        """
        raise NotImplementedError

    def on_backtest_end(self):
        """
        回测结束时的回调（可选）
        """
        pass 