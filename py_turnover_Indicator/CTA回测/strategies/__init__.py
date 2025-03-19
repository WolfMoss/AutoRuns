"""
策略模块

该模块包含所有回测策略类，提供统一的策略接口
"""

from .base_strategy import BaseStrategy
# 导入所有策略类
from .sample_strategy import SampleStrategy

__all__ = [
    'BaseStrategy',
    'SampleStrategy'
] 