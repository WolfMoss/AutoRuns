"""
数据加载工具
"""
import os
import pandas as pd
from datetime import datetime
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData

def load_csv_data(file_path, symbol, exchange, interval):
    """
    加载CSV数据并转换为VNPY的BarData格式
    
    参数:
        file_path (str): CSV文件路径
        symbol (str): 交易品种
        exchange (Exchange): 交易所
        interval (Interval): K线周期
    
    返回:
        list: BarData列表
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return []
    
    # 读取CSV文件
    df = pd.read_csv(file_path)
    
    # 如果没有列名，则添加默认列名
    if len(df.columns) == 6 and df.columns[0].startswith('20'):
        df.columns = ["datetime", "open", "high", "low", "close", "volume"]
    
    # 确保datetime列被正确解析
    if isinstance(df["datetime"].iloc[0], str):
        df["datetime"] = pd.to_datetime(df["datetime"])
    
    # 转换为BarData列表
    bars = []
    for _, row in df.iterrows():
        # 创建BarData对象
        bar = BarData(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            datetime=row["datetime"].to_pydatetime(),
            open_price=float(row["open"]),
            high_price=float(row["high"]),
            low_price=float(row["low"]),
            close_price=float(row["close"]),
            volume=float(row["volume"]),
            gateway_name="BACKTEST"
        )
        bars.append(bar)
    
    return bars 