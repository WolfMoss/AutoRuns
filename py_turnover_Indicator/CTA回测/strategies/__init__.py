"""
策略模块初始化
"""
from .ma_strategy import MaStrategy
from .boll_strategy import BollStrategy

# 导出所有策略类
__all__ = [
    'MaStrategy',
    'BollStrategy',
] 