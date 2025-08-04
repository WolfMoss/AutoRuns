#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测系统主入口
整合策略、数据加载器和回测引擎
提供完整的回测示例
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_strategy import SimpleMAStrategy, RSIStrategy
from data_loader import CSVDataLoader, DataValidator
from backtest_engine import BacktestEngine, ParameterOptimizer

def main():
    """主函数 - 演示完整的回测流程"""
    
    print("="*70)
    print("交易策略回测系统".center(70))
    print("基于 Backtrader 框架".center(70))
    print("="*70)
    
    # 1. 数据准备
    print("\n📊 步骤1: 数据准备")
    print("-" * 50)
    
    # 获取项目根目录路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    datas_dir = os.path.join(project_root, "datas")
    
    print(f"项目根目录: {project_root}")
    print(f"数据目录: {datas_dir}")
    
    # 创建数据加载器
    loader = CSVDataLoader(data_dir=datas_dir)
    
    # 列出可用数据
    available_files = loader.list_available_data()
    print(f"可用的数据文件: {available_files}")
    
    if not available_files:
        print("❌ 没有找到数据文件，请确保datas目录中有CSV文件")
        return
    
    # 选择数据文件（这里选择第一个）
    data_file = available_files[0]
    print(f"✅ 选择数据文件: {data_file}")
    
    # 预览数据
    loader.preview_data(data_file, rows=5)
    
    # 加载数据
    try:
        data_feed = loader.load_data(
            data_file,
            start_date="2025-01-19",  # 可以指定开始日期
            # end_date="2025-01-21"   # 可以指定结束日期
        )
        print("✅ 数据加载成功")
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return
    
    # 2. 策略回测
    print("\n🎯 步骤2: 策略回测")
    print("-" * 50)
    
    # 创建回测引擎
    engine = BacktestEngine(
        initial_cash=100000,    # 初始资金10万
        commission=0.001        # 手续费0.1%
    )
    
    # 设置回测环境
    engine.setup_cerebro()
    
    # 添加数据
    engine.add_data(data_feed, name=data_file)
    
    # 添加策略（可以选择不同策略）
    strategy_choice = "MA"  # 可选: "MA", "RSI"
    
    if strategy_choice == "MA":
        engine.add_strategy(
            SimpleMAStrategy,
            ma_short=10,    # 短期均线
            ma_long=30,     # 长期均线
            printlog=False  # 关闭详细日志，避免输出过多
        )
        print("✅ 已添加移动平均线策略")
        
    elif strategy_choice == "RSI":
        engine.add_strategy(
            RSIStrategy,
            rsi_period=14,  # RSI周期
            rsi_upper=70,   # 超买线
            rsi_lower=30,   # 超卖线
            printlog=False
        )
        print("✅ 已添加RSI策略")
    
    # 运行回测
    results = engine.run_backtest(plot=False)  # 设置为False避免图表显示问题
    
    # 3. 性能分析
    print("\n📈 步骤3: 性能分析")
    print("-" * 50)
    
    # 打印详细报告
    engine.print_performance_report()
    
    # 保存报告到文件
    report_filename = f"backtest_report_{strategy_choice}_{data_file.replace('.csv', '')}.txt"
    engine.save_report_to_file(report_filename)
    
    # 4. 参数优化示例
    print("\n🔧 步骤4: 参数优化示例")
    print("-" * 50)
    
    run_optimization = input("是否运行参数优化？(y/n): ").lower().strip() == 'y'
    
    if run_optimization:
        print("开始参数优化（这可能需要几分钟）...")
        
        # 创建参数优化器
        optimizer = ParameterOptimizer(
            strategy_class=SimpleMAStrategy,
            data_feed=data_feed,
            initial_cash=100000
        )
        
        # 定义参数范围
        param_ranges = {
            'ma_short': range(5, 20, 2),    # 短期均线: 5,7,9,11,13,15,17,19
            'ma_long': range(20, 50, 5),    # 长期均线: 20,25,30,35,40,45
            'printlog': [False]             # 固定参数
        }
        
        # 运行优化
        optimization_results = optimizer.optimize_parameters(
            param_ranges=param_ranges,
            optimization_target='return'    # 优化目标：总收益
        )
        
        # 显示优化结果
        best_params = optimization_results['best_params']
        best_result = optimization_results['best_result']
        
        print(f"\n🎉 优化结果:")
        print(f"最优参数: {best_params}")
        print(f"最优收益: {best_result['total_return']:.2f}%")
        print(f"夏普比率: {best_result['sharpe_ratio']:.4f}")
        
        # 显示前5个最优结果
        print(f"\n📊 前5个最优参数组合:")
        for i, result in enumerate(optimization_results['all_results'][:5], 1):
            print(f"{i}. 参数: {result['params']} -> 收益: {result['total_return']:.2f}%")
    
    # 5. 总结
    print("\n🎊 回测完成!")
    print("-" * 50)
    print("✅ 成功完成策略回测")
    print("✅ 生成详细性能报告")
    print(f"✅ 报告已保存到: {report_filename}")
    
    if run_optimization:
        print("✅ 完成参数优化")
    
    print("\n💡 提示:")
    print("1. 可以修改策略参数来测试不同的配置")
    print("2. 可以尝试不同的数据文件进行回测")
    print("3. 可以创建自己的策略类进行测试")
    print("4. 建议在不同市场条件下测试策略的稳健性")


def quick_backtest_example():
    """快速回测示例"""
    print("快速回测示例")
    print("=" * 50)
    
    # 获取正确的数据目录路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    datas_dir = os.path.join(project_root, "datas")
    
    # 简化的回测流程
    loader = CSVDataLoader(data_dir=datas_dir)
    files = loader.list_available_data()
    
    if not files:
        print("没有找到数据文件")
        print(f"检查路径: {datas_dir}")
        return
    
    # 加载数据
    data = loader.load_data(files[0])
    
    # 创建并运行回测
    engine = BacktestEngine(initial_cash=50000, commission=0.001)
    engine.setup_cerebro()
    engine.add_data(data)
    engine.add_strategy(SimpleMAStrategy, ma_short=5, ma_long=20, printlog=False)
    
    # 运行回测
    engine.run_backtest(plot=False)
    engine.print_performance_report()


if __name__ == '__main__':
    # 选择运行模式
    mode = input("选择运行模式 (1: 完整回测, 2: 快速示例): ").strip()
    
    if mode == "2":
        quick_backtest_example()
    else:
        main() 