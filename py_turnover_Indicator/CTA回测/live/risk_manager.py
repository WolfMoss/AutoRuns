#!/usr/bin/env python
# -*- coding: utf-8 -*-

class RiskManager:
    """风险管理模块"""
    
    def __init__(self, max_position_size=0.1, max_drawdown=0.1, stop_loss_pct=0.05):
        self.max_position_size = max_position_size  # 最大持仓比例
        self.max_drawdown = max_drawdown  # 可接受的最大回撤
        self.stop_loss_pct = stop_loss_pct  # 止损比例
        self.current_drawdown = 0
        self.peak_value = 0
        
    def calculate_position_size(self, account_value, price):
        """计算头寸大小"""
        max_amount = account_value * self.max_position_size
        return max_amount / price
    
    def update_drawdown(self, current_value):
        """更新并检查回撤"""
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        if self.peak_value > 0:
            self.current_drawdown = (self.peak_value - current_value) / self.peak_value
        
        return self.current_drawdown <= self.max_drawdown
    
    def should_stop_trading(self, current_value):
        """是否应该停止交易"""
        return not self.update_drawdown(current_value) 