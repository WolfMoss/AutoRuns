"""
性能分析模块

提供回测结果分析和可视化功能
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any

def calculate_statistics(result: Dict[str, Any], daily_df: pd.DataFrame) -> Dict[str, Any]:
    """
    计算回测结果的统计指标
    
    :param result: 回测结果
    :param daily_df: 每日回测结果
    :return: 统计指标字典
    """
    # 确保结果非空
    if not result or daily_df.empty:
        return {"error": "回测结果为空"}
    
    # 提取回测结果的关键指标
    statistics = {
        "起始资金": result.get("capital"),
        "结束资金": result.get("end_balance"),
        "总收益率": f"{result.get('total_return', 0):.2%}",
        "年化收益率": f"{result.get('annual_return', 0):.2%}",
        "最大回撤": f"{result.get('max_drawdown', 0):.2%}",
        "收益回撤比": round(result.get("return_drawdown_ratio", 0), 2),
        "夏普比率": round(result.get("sharpe_ratio", 0), 2),
        "索提诺比率": round(result.get("sortino_ratio", 0), 2),
        "交易次数": result.get("total_trade_count", 0),
        "胜率": f"{result.get('win_ratio', 0):.2%}",
        "盈亏比": round(result.get("profit_loss_ratio", 0), 2),
        "平均收益": round(result.get("average_profit", 0), 2),
        "平均亏损": round(result.get("average_loss", 0), 2),
        "最大连续盈利次数": result.get("max_winning_streak", 0),
        "最大连续亏损次数": result.get("max_losing_streak", 0),
        "最大单笔盈利": round(result.get("max_profit_trade", 0), 2),
        "最大单笔亏损": round(result.get("max_loss_trade", 0), 2),
    }
    
    # 计算额外的自定义指标
    
    # 月度收益率
    if "date" in daily_df.columns:
        daily_df["date"] = pd.to_datetime(daily_df["date"])
        monthly_return = daily_df.set_index("date").resample("M")["net_pnl"].sum()
        statistics["月度盈利次数"] = len(monthly_return[monthly_return > 0])
        statistics["月度亏损次数"] = len(monthly_return[monthly_return < 0])
        statistics["月度胜率"] = f"{statistics['月度盈利次数'] / (statistics['月度盈利次数'] + statistics['月度亏损次数']):.2%}"
    
    # 年度收益率
    if "date" in daily_df.columns:
        yearly_return = daily_df.set_index("date").resample("Y")["net_pnl"].sum()
        statistics["年度盈利次数"] = len(yearly_return[yearly_return > 0])
        statistics["年度亏损次数"] = len(yearly_return[yearly_return < 0])
        
    # 平均持仓时间
    if "trade_count" in result:
        hold_times = result.get("holding_periods", [])
        if hold_times:
            statistics["平均持仓时间(小时)"] = round(np.mean(hold_times) / 3600, 2)
    
    return statistics


def plot_performance(result: Dict[str, Any], daily_df: pd.DataFrame, save_path: Optional[str] = None) -> None:
    """
    绘制回测性能图表
    
    :param result: 回测结果
    :param daily_df: 每日回测结果
    :param save_path: 图表保存路径
    """
    if daily_df.empty:
        return
    
    plt.figure(figsize=(16, 12))
    
    # 设置中文字体
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei'] 
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass
    
    # 绘制权益曲线
    plt.subplot(3, 1, 1)
    plt.title("权益曲线")
    plt.plot(daily_df["date"], daily_df["balance"])
    plt.grid(True)
    
    # 绘制回撤曲线
    plt.subplot(3, 1, 2)
    plt.title("回撤曲线")
    plt.fill_between(daily_df["date"], daily_df["drawdown"])
    plt.grid(True)
    
    # 绘制每日盈亏
    plt.subplot(3, 1, 3)
    plt.title("每日盈亏")
    plt.bar(daily_df["date"], daily_df["net_pnl"], color=['r' if x < 0 else 'g' for x in daily_df["net_pnl"]])
    plt.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show() 