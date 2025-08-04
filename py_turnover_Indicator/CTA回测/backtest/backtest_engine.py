#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测引擎
提供完整的回测功能和性能分析
"""

import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_cash=100000, commission=0.001):
        """
        初始化回测引擎
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.cerebro = None
        self.results = None
        
    def setup_cerebro(self):
        """设置回测环境"""
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(self.initial_cash)
        
        # 设置手续费
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # 添加性能分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        print(f"回测环境设置完成:")
        print(f"  - 初始资金: {self.initial_cash:,.2f}")
        print(f"  - 手续费率: {self.commission:.4f}")
        
    def add_strategy(self, strategy_class, **kwargs):
        """
        添加策略
        
        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **kwargs)
        print(f"策略已添加: {strategy_class.__name__}")
        if kwargs:
            print(f"策略参数: {kwargs}")
            
    def add_data(self, data_feed, name=None):
        """
        添加数据
        
        Args:
            data_feed: backtrader数据对象
            name: 数据名称
        """
        self.cerebro.adddata(data_feed, name=name)
        print(f"数据已添加: {name or '未命名'}")
        
    def run_backtest(self, plot=True):
        """
        运行回测
        
        Args:
            plot: 是否绘制图表
            
        Returns:
            回测结果
        """
        if self.cerebro is None:
            raise ValueError("请先调用setup_cerebro()设置回测环境")
            
        print(f"\n开始回测...")
        print(f"初始资金: {self.cerebro.broker.getvalue():,.2f}")
        
        # 运行回测
        self.results = self.cerebro.run()
        
        final_value = self.cerebro.broker.getvalue()
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100
        
        print(f"\n回测完成!")
        print(f"最终资金: {final_value:,.2f}")
        print(f"总收益: {total_return:.2f}%")
        print(f"总收益金额: {final_value - self.initial_cash:,.2f}")
        
        # 绘制图表
        if plot:
            self.plot_results()
            
        return self.results
        
    def plot_results(self, save_path=None):
        """
        绘制回测结果图表
        
        Args:
            save_path: 图表保存路径
        """
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 绘制图表
            self.cerebro.plot(style='candlestick', barup='red', bardown='green')
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"图表已保存到: {save_path}")
                
            plt.show()
            
        except Exception as e:
            print(f"绘制图表失败: {e}")
            print("提示: 可能需要安装matplotlib和设置中文字体")
            
    def get_performance_report(self):
        """
        获取详细的性能报告
        
        Returns:
            dict: 性能指标字典
        """
        if not self.results:
            print("请先运行回测")
            return {}
            
        strat = self.results[0]
        
        # 基本信息
        final_value = self.cerebro.broker.getvalue()
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100
        
        # 获取分析器结果
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        returns_analysis = strat.analyzers.returns.get_analysis()
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        trades_analysis = strat.analyzers.trades.get_analysis()
        sqn_analysis = strat.analyzers.sqn.get_analysis()
        
        # 构建报告
        report = {
            '基本信息': {
                '初始资金': f"{self.initial_cash:,.2f}",
                '最终资金': f"{final_value:,.2f}",
                '总收益': f"{total_return:.2f}%",
                '总收益金额': f"{final_value - self.initial_cash:,.2f}",
                '手续费率': f"{self.commission:.4f}"
            },
            '收益指标': {
                '年化收益率': f"{returns_analysis.get('ravg', 0) * 100:.2f}%",
                '夏普比率': f"{sharpe_ratio:.4f}" if sharpe_ratio else "N/A",
                'SQN评分': f"{sqn_analysis.get('sqn', 0):.4f}"
            },
            '风险指标': {
                '最大回撤': f"{drawdown_analysis.get('max', {}).get('drawdown', 0):.2f}%",
                '最大回撤期间': f"{drawdown_analysis.get('max', {}).get('len', 0)}天",
                '平均回撤': f"{drawdown_analysis.get('drawdown', 0):.2f}%"
            },
            '交易统计': {
                '总交易次数': trades_analysis.get('total', {}).get('total', 0),
                '盈利交易': trades_analysis.get('won', {}).get('total', 0),
                '亏损交易': trades_analysis.get('lost', {}).get('total', 0),
                '胜率': f"{trades_analysis.get('won', {}).get('total', 0) / max(trades_analysis.get('total', {}).get('total', 1), 1) * 100:.2f}%",
                '平均盈利': f"{trades_analysis.get('won', {}).get('pnl', {}).get('average', 0):.2f}",
                '平均亏损': f"{trades_analysis.get('lost', {}).get('pnl', {}).get('average', 0):.2f}",
                '盈亏比': f"{abs(trades_analysis.get('won', {}).get('pnl', {}).get('average', 1) / trades_analysis.get('lost', {}).get('pnl', {}).get('average', -1)):.2f}" if trades_analysis.get('lost', {}).get('pnl', {}).get('average', 0) != 0 else "N/A"
            }
        }
        
        return report
        
    def print_performance_report(self):
        """打印性能报告"""
        report = self.get_performance_report()
        
        print("\n" + "="*60)
        print("回测性能报告".center(60))
        print("="*60)
        
        for category, metrics in report.items():
            print(f"\n{category}:")
            print("-" * 30)
            for key, value in metrics.items():
                print(f"  {key:<15}: {value}")
                
    def save_report_to_file(self, filename="backtest_report.txt"):
        """
        保存报告到文件
        
        Args:
            filename: 文件名
        """
        report = self.get_performance_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("回测性能报告\n")
            f.write("="*60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for category, metrics in report.items():
                f.write(f"{category}:\n")
                f.write("-" * 30 + "\n")
                for key, value in metrics.items():
                    f.write(f"  {key:<15}: {value}\n")
                f.write("\n")
                
        print(f"报告已保存到: {filename}")


class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, strategy_class, data_feed, initial_cash=100000):
        """
        初始化参数优化器
        
        Args:
            strategy_class: 策略类
            data_feed: 数据对象
            initial_cash: 初始资金
        """
        self.strategy_class = strategy_class
        self.data_feed = data_feed
        self.initial_cash = initial_cash
        
    def optimize_parameters(self, param_ranges, optimization_target='return'):
        """
        优化策略参数
        
        Args:
            param_ranges: 参数范围字典
            optimization_target: 优化目标 ('return', 'sharpe', 'sqn')
            
        Returns:
            优化结果
        """
        print(f"开始参数优化...")
        print(f"优化目标: {optimization_target}")
        print(f"参数范围: {param_ranges}")
        
        # 设置回测环境
        cerebro = bt.Cerebro(optreturn=False)
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.adddata(self.data_feed)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        # 添加优化策略
        cerebro.optstrategy(self.strategy_class, **param_ranges)
        
        # 运行优化
        optimization_results = cerebro.run()
        
        # 分析结果
        best_result = None
        best_value = float('-inf')
        
        results_summary = []
        
        for result in optimization_results:
            strat = result[0]
            
            # 获取参数
            params = {
                param: getattr(strat.params, param) 
                for param in param_ranges.keys()
            }
            
            # 获取性能指标
            final_value = strat.broker.getvalue()
            total_return = (final_value - self.initial_cash) / self.initial_cash * 100
            sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            sqn = strat.analyzers.sqn.get_analysis().get('sqn', 0)
            
            # 根据优化目标选择评价指标
            if optimization_target == 'return':
                target_value = total_return
            elif optimization_target == 'sharpe':
                target_value = sharpe if sharpe else 0
            elif optimization_target == 'sqn':
                target_value = sqn
            else:
                target_value = total_return
                
            # 记录结果
            result_dict = {
                'params': params,
                'total_return': total_return,
                'sharpe_ratio': sharpe,
                'sqn': sqn,
                'final_value': final_value,
                'target_value': target_value
            }
            results_summary.append(result_dict)
            
            # 更新最优结果
            if target_value > best_value:
                best_value = target_value
                best_result = result_dict
                
        # 排序结果
        results_summary.sort(key=lambda x: x['target_value'], reverse=True)
        
        print(f"\n优化完成!")
        print(f"测试了 {len(results_summary)} 组参数")
        print(f"最优参数: {best_result['params']}")
        print(f"最优{optimization_target}: {best_result['target_value']:.4f}")
        
        return {
            'best_params': best_result['params'],
            'best_result': best_result,
            'all_results': results_summary
        } 