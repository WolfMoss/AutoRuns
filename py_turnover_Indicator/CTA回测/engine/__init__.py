"""
回测引擎模块

该模块提供VNPY回测引擎相关组件，用于CTA策略回测
"""

from .backtest_engine import BacktestEngine
from .loader import DataLoader

__all__ = [
    'BacktestEngine',
    'DataLoader'
] 