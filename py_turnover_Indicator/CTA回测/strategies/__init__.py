"""
策略模块

该模块包含所有回测策略类，提供统一的策略接口
"""

from vnpy_ctastrategy import CtaTemplate
# 导入所有策略类
from .sample_strategy import SampleStrategy

__all__ = [
    'CtaTemplate',
    'SampleStrategy'
] 