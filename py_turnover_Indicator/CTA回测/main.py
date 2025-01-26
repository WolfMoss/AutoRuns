import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from itertools import product


# ==================== 增强版数据生成模块 ====================
def generate_sample_data(days=365, initial_price=100):
    """
    生成模拟的股票价格数据
    参数:
        days: 生成的天数
        initial_price: 初始股票价格
    返回:
        带有每日收盘价的DataFrame
    """
    np.random.seed(42)  # 设置随机种子，确保结果可重现
    dates = pd.date_range(end=datetime.today(), periods=days)  # 生成日期序列
    returns = np.random.normal(0, 0.015, days)  # 生成服从正态分布的每日收益率
    prices = initial_price * np.exp(np.cumsum(returns))  # 通过收益率计算价格序列
    return pd.DataFrame({'close': prices}, index=dates)


# ==================== 增强版策略类 ====================
class EnhancedDualMAStrategy:
    def __init__(self, fast_period=4, slow_period=20):
        """
        双均线策略类的初始化
        参数:
            fast_period: 短期均线周期（默认4日）
            slow_period: 长期均线周期（默认20日）
        """
        self.fast_ma = None
        self.slow_ma = None
        self.position = 0
        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period
        }
        self.trade_log = []
        self.current_trade = None

    def calculate_ma(self, data):
        """计算当前和上一期的快慢均线"""
        # 计算当前均线
        data['fast_ma'] = data['close'].rolling(self.params['fast_period']).mean()
        data['slow_ma'] = data['close'].rolling(self.params['slow_period']).mean()
        
        # 计算上一期均线
        data['prev_fast_ma'] = data['fast_ma'].shift(1)
        data['prev_slow_ma'] = data['slow_ma'].shift(1)
        
        return data.dropna()

    def generate_signal(self, row):
        """
        生成交易信号
        多头开仓：当前双均线都上升
        空头开仓：当前双均线都下降
        多头平仓：快线下穿慢线
        空头平仓：快线上穿慢线
        """
        # 当前持有多头仓位
        if self.position == 1:
            # 多头平仓条件：当前快线小于上期快线
            if row['fast_ma'] < row['prev_fast_ma']:
                return -1  # 平仓信号
            return 0  # 保持现有仓位
            
        # 当前持有空头仓位
        elif self.position == -1:
            # 空头平仓条件：当前快线大于上期快线
            if row['fast_ma'] > row['prev_fast_ma']:
                return 1  # 平仓信号
            return 0  # 保持现有仓位
            
        # 当前无仓位，判断开仓
        else:
            # 多头开仓条件：当前双均线都上升
            if (row['slow_ma'] > row['prev_slow_ma'] and 
                row['fast_ma'] > row['prev_fast_ma']):
                return 1
            # 空头开仓条件：当前双均线都下降
            elif (row['slow_ma'] < row['prev_slow_ma'] and 
                  row['fast_ma'] < row['prev_fast_ma']):
                return -1
            return 0


# ==================== 增强版回测引擎 ====================
class EnhancedBacktestEngine:
    def __init__(self, data, strategy,
                 initial_capital=1000000,
                 commission=0.001,  # 交易手续费率（0.1%）
                 slippage=0.0005):  # 滑点成本（0.05%）
        """
        回测引擎类
        参数:
            data: 历史价格数据
            strategy: 交易策略实例
            initial_capital: 初始资金
            commission: 交易手续费率
            slippage: 滑点成本（反映市场冲击成本）
        """
        self.data = data
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.results = None

    def run_backtest(self):
        """
        运行回测的主要逻辑
        包含:
        - 计算技术指标
        - 生成交易信号
        - 模拟交易执行
        - 计算收益和权益
        """
        df = self.strategy.calculate_ma(self.data.copy())

        # 初始化账户
        df['equity'] = float(self.initial_capital)
        df['returns'] = 0.0
        position = 0
        entry_price = 0

        for i, (index, row) in enumerate(df.iterrows()):
            if i == 0: continue

            signal = self.strategy.generate_signal(row)
            prev_equity = df.iloc[i - 1]['equity']

            # 平仓逻辑
            if position != 0 and signal != 0:
                # 计算平仓价格（考虑滑点）
                if position == 1:
                    exit_price = row['close'] * (1 - self.slippage)
                else:
                    exit_price = row['close'] * (1 + self.slippage)

                # 计算平仓收益
                pnl = (exit_price / entry_price - 1) * position
                current_equity = prev_equity * (1 + pnl)

                # 扣除平仓手续费
                current_equity *= (1 - self.commission)

                # 记录交易
                trade_duration = (index - self.strategy.current_trade['entry_date']).days
                self.strategy.trade_log.append({
                    'entry_date': self.strategy.current_trade['entry_date'],
                    'exit_date': index,
                    'direction': 'LONG' if position == 1 else 'SHORT',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'duration': trade_duration
                })

                df.loc[index, 'equity'] = current_equity
                prev_equity = current_equity  # 更新权益基准

            # 开仓逻辑
            if signal != 0:
                # 计算开仓价格（考虑滑点）
                if signal == 1:
                    entry_price = row['close'] * (1 + self.slippage)
                else:
                    entry_price = row['close'] * (1 - self.slippage)

                # 扣除开仓手续费
                current_equity = prev_equity * (1 - self.commission)

                # 更新仓位记录
                position = signal
                self.strategy.current_trade = {
                    'entry_date': index,
                    'entry_price': entry_price
                }
                df.loc[index, 'equity'] = current_equity

            # 计算当日收益
            df.loc[index, 'returns'] = df.loc[index, 'equity'] / prev_equity - 1

        df['cumulative_return'] = (1 + df['returns']).cumprod()
        self.results = df
        return df


# ==================== 增强版绩效分析 ====================
def enhanced_analyze_performance(results, trade_log, risk_free_rate=0):
    """
    策略绩效分析
    增加了标的价格走势对比
    """
    # 基础指标
    total_return = results['cumulative_return'].iloc[-1] - 1
    annual_return = (1 + total_return) ** (252 / len(results)) - 1

    # 最大回撤
    max_drawdown = (results['cumulative_return'].cummax() - results['cumulative_return']).max()

    # 夏普比率
    excess_returns = results['returns'] - risk_free_rate / 252
    sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std()

    # 胜率指标
    if len(trade_log) > 0:
        win_rate = len([t for t in trade_log if t['pnl'] > 0]) / len(trade_log)
        avg_profit = np.mean([t['pnl'] for t in trade_log if t['pnl'] > 0])
        avg_loss = np.mean([t['pnl'] for t in trade_log if t['pnl'] < 0])
        profit_factor = -avg_profit / avg_loss if avg_loss != 0 else np.inf
    else:
        win_rate = avg_profit = avg_loss = profit_factor = 0

    # 修改绘图部分
    plt.figure(figsize=(12, 6))
    
    # 绘制策略收益曲线
    ax1 = plt.gca()
    ax1.plot(results.index, results['cumulative_return'], 
             label='策略收益', color='blue', linewidth=2)
    ax1.set_ylabel('策略收益率', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # 绘制标的价格走势（归一化处理）
    ax2 = ax1.twinx()
    normalized_price = results['close'] / results['close'].iloc[0]
    ax2.plot(results.index, normalized_price, 
             label='标的走势', color='red', linewidth=1, linestyle='--')
    ax2.set_ylabel('标的价格走势（归一化）', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    
    # 设置图表属性
    plt.title('策略表现 vs 标的走势对比')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.grid(True)
    plt.show()

    # 输出绩效指标
    print("\n增强版策略绩效报告:")
    print(f"累计收益率: {total_return:.2%}")
    print(f"年化收益率: {annual_return:.2%}")
    print(f"最大回撤: {max_drawdown:.2%}")
    print(f"夏普比率: {sharpe_ratio:.2f}")
    print(f"胜率: {win_rate:.2%}")
    print(f"平均盈利/平均亏损: {avg_profit:.2%}/{avg_loss:.2%}")
    print(f"盈亏比: {profit_factor:.2f}")


# ==================== 参数优化模块 ====================
def parameter_optimization(data,
                           fast_range=range(5, 30, 5),
                           slow_range=range(30, 100, 10),
                           initial_capital=1000000,
                           commission=0.001,
                           slippage=0.0005):
    """
    参数优化模块
    通过遍历不同的参数组合，寻找最优的策略参数
    参数:
        fast_range: 短期均线周期的范围
        slow_range: 长期均线周期的范围
    优化目标:
        - 按夏普比率排序
        - 同时考虑总收益、年化收益、胜率等指标
    """
    results = []

    for fast, slow in product(fast_range, slow_range):
        if fast >= slow: continue

        # 运行回测
        strategy = EnhancedDualMAStrategy(fast_period=fast, slow_period=slow)
        engine = EnhancedBacktestEngine(data, strategy,
                                        initial_capital=initial_capital,
                                        commission=commission,
                                        slippage=slippage)
        results_df = engine.run_backtest()

        # 计算绩效指标
        total_return = results_df['cumulative_return'].iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(results_df)) - 1
        sharpe = np.sqrt(252) * results_df['returns'].mean() / results_df['returns'].std()
        win_rate = len([t for t in strategy.trade_log if t['pnl'] > 0]) / len(
            strategy.trade_log) if strategy.trade_log else 0

        results.append({
            'fast_ma': fast,
            'slow_ma': slow,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'max_drawdown': (results_df['cumulative_return'].cummax() - results_df['cumulative_return']).max()
        })

    return pd.DataFrame(results).sort_values(by='sharpe_ratio', ascending=False)


# ==================== 主程序 ====================
if __name__ == "__main__":
    # 生成测试数据
    data = generate_sample_data(days=1000)

    # 运行单次回测
    strategy = EnhancedDualMAStrategy(fast_period=4, slow_period=20)
    engine = EnhancedBacktestEngine(data, strategy,
                                    commission=0.0005,
                                    slippage=0.0003)
    results = engine.run_backtest()
    enhanced_analyze_performance(results, strategy.trade_log)

    # 执行参数优化
    # print("\n正在进行参数优化...")
    # optimization_results = parameter_optimization(data)
    # print("\n最佳参数组合：")
    # print(optimization_results.head(5))