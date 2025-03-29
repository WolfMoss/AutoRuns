#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class PerformanceAnalyzer:
    """性能分析模块"""
    
    def __init__(self, returns):
        self.returns = returns  # 日收益率序列
        
    def calculate_metrics(self):
        """计算各种性能指标"""
        metrics = {}
        
        # 累计收益
        metrics['cumulative_return'] = np.cumprod(1 + self.returns) - 1
        
        # 年化收益率
        total_return = metrics['cumulative_return'].iloc[-1]
        days = len(self.returns)
        metrics['annual_return'] = (1 + total_return) ** (365 / days) - 1
        
        # 波动率
        metrics['volatility'] = self.returns.std() * np.sqrt(365)
        
        # 夏普比率
        risk_free_rate = 0.02  # 假设无风险利率为2%
        metrics['sharpe_ratio'] = (metrics['annual_return'] - risk_free_rate) / metrics['volatility']
        
        # 最大回撤
        cum_returns = np.cumprod(1 + self.returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = (running_max - cum_returns) / running_max
        metrics['max_drawdown'] = drawdown.max()
        
        # 卡玛比率
        metrics['calmar_ratio'] = metrics['annual_return'] / metrics['max_drawdown']
        
        return metrics
    
    def plot_performance(self):
        """绘制性能图表"""
        metrics = self.calculate_metrics()
        
        plt.figure(figsize=(12, 10))
        
        # 绘制累计收益
        plt.subplot(2, 1, 1)
        plt.plot(metrics['cumulative_return'])
        plt.title('累计收益')
        plt.grid(True)
        
        # 绘制回撤
        cum_returns = np.cumprod(1 + self.returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = (running_max - cum_returns) / running_max
        
        plt.subplot(2, 1, 2)
        plt.plot(drawdown)
        plt.title('回撤')
        plt.grid(True)
        
        plt.tight_layout()
        plt.show()
        
        # 打印性能指标
        print(f"年化收益率: {metrics['annual_return']:.2%}")
        print(f"波动率: {metrics['volatility']:.2%}")
        print(f"夏普比率: {metrics['sharpe_ratio']:.4f}")
        print(f"最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"卡玛比率: {metrics['calmar_ratio']:.4f}") 