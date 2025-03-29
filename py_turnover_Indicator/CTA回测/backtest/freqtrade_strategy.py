# 示例策略
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd

class MAcrossStrategy(IStrategy):
    # 策略参数
    minimal_roi = {
        "0": 0.1
    }
    stoploss = -0.05
    timeframe = '1h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 添加技术指标
        dataframe['ma4'] = ta.SMA(dataframe, timeperiod=4)
        dataframe['ma16'] = ta.SMA(dataframe, timeperiod=16)
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 定义买入信号
        dataframe.loc[
            (
                (dataframe['ma4'] > dataframe['ma16']) & 
                (dataframe['ma4'].shift(1) <= dataframe['ma16'].shift(1))
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 定义卖出信号
        dataframe.loc[
            (
                (dataframe['ma4'] < dataframe['ma16']) & 
                (dataframe['ma4'].shift(1) >= dataframe['ma16'].shift(1))
            ),
            'sell'] = 1
        return dataframe 