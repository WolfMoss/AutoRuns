"""
数据加载器模块

负责从CSV文件加载数据并转换为vnpy可用的数据格式
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.trader.utility import ZoneInfo

import logging
logger = logging.getLogger(__name__)

class DataLoader:
    """数据加载器类，负责将CSV数据转换为VNPY可用的BarData对象"""
    
    def __init__(self, data_dir: str):
        """
        初始化数据加载器
        :param data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        self.timezone = ZoneInfo("Asia/Shanghai")
    
    def load_bar_data(
        self, 
        symbol: str, 
        interval: Interval,
        start_date: str,
        end_date: str
    ) -> List[BarData]:
        """
        加载K线数据
        
        :param symbol: 交易对名称
        :param interval: 时间周期
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: K线数据列表
        """
        # 构建文件路径
        filename = f"{symbol}_{interval.value}.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            logger.error(f"数据文件不存在: {filepath}")
            return []
        
        # 读取CSV文件
        try:
            df = pd.read_csv(filepath)
            df["datetime"] = pd.to_datetime(df["datetime"])
            
            # 过滤日期范围
            df = df[
                (df["datetime"].dt.strftime("%Y-%m-%d") >= start_date) &
                (df["datetime"].dt.strftime("%Y-%m-%d") <= end_date)
            ]
        except Exception as e:
            logger.error(f"读取数据文件失败: {e}")
            return []
        
        # 转换为BarData对象
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=symbol,
                exchange=Exchange.LOCAL,  # 使用本地交易所标识
                datetime=row["datetime"].replace(tzinfo=self.timezone),
                interval=interval,
                volume=float(row["volume"]),
                open_price=float(row["open"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                close_price=float(row["close"]),
                gateway_name="BACKTEST"
            )
            bars.append(bar)
        
        logger.info(f"加载了 {len(bars)} 条K线数据")
        return bars
    
    def get_available_symbols(self, interval: str) -> List[str]:
        """
        获取可用的交易对列表
        
        :param interval: 时间周期
        :return: 交易对列表
        """
        symbols = []
        suffix = f"_{interval}.csv"
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith(suffix):
                symbol = filename.replace(suffix, "")
                symbols.append(symbol)
        
        return symbols 