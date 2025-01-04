import numpy as np
import pandas as pd
import vectorbt as vbt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from xtquant import xtdata
import warnings

warnings.filterwarnings('ignore')


class BacktestSystem:
    def __init__(self, start_date='2021-01-01', end_date='2024-12-30', initial_capital=100000, max_positions=10):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.max_positions = max_positions

        self.data = {}

    def get_stock_data(self):
        """从MINIQMT获取股票数据"""
        # 获取A股股票列表
        # 获取股票列表
        code_list = xtdata.get_stock_list_in_sector('沪深A股')

        period = "1d"
        # for i in code_list:
        #     xtdata.download_history_data(i, period, start_time='', end_time='')
        # 读取历史数据
        all_stock_data = xtdata.get_local_data(
            [], ['001322.SZ'], period=period,
            start_time='20240101', end_time='20241230',
            count=300, dividend_type='front'
        )
        print('行情加载完成')

        for stock,daily_data in all_stock_data.items():
            try:

                if daily_data is not None and len(daily_data) > 0:
                    # 创建DataFrame
                    df = pd.DataFrame(daily_data)

                    # 正确处理日期格式
                    df['date'] = pd.to_datetime(df.index, format='%Y%m%d')
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    df.set_index('date', inplace=True)

                    # 计算日MA4
                    df['daily_ma4'] = df['close'].rolling(window=4).mean()

                    # 计算周MA4
                    # 1. 确保索引是datetime类型
                    df.index = pd.to_datetime(df.index)

                    # 2. 创建周数据
                    weekly_df = df.resample('W')['close'].last().to_frame()

                    # 3. 计算周MA4
                    weekly_df['weekly_ma4'] = weekly_df['close'].rolling(window=4).mean()

                    # 4. 将周MA4对齐到日数据
                    # 使用前向填充确保每个交易日都有值
                    df['weekly_ma4'] = weekly_df['weekly_ma4'].reindex(df.index, method='ffill')

                    # 存储处理后的数据
                    self.data[stock] = df

                    # 验证数据
                    if df['weekly_ma4'].isnull().all():
                        print(f"警告: {stock} 的weekly_ma4全为空值")
                    else:
                        print(f"成功处理 {stock} 的数据，包含 {len(df)} 行")

            except Exception as e:
                print(f"获取{stock}数据时出错: {str(e)}")

        print("数据获取完成")

    def generate_signals(self, df):
        """生成交易信号"""
        # 买入条件
        buy_condition = (
                (df['daily_ma4'] > df['daily_ma4'].shift(1)) &
                (df['weekly_ma4'] > df['weekly_ma4'].shift(1))
        )

        # 卖出条件
        sell_condition = (df['daily_ma4'] <= df['daily_ma4'].shift(1))

        return buy_condition, sell_condition

    def backtest(self):
        """执行回测"""
        portfolio_results = []

        for stock, df in self.data.items():
            try:
                buy_signals, sell_signals = self.generate_signals(df)

                # 使用vectorbt进行回测
                portfolio = vbt.Portfolio.from_signals(
                    close=df['close'],
                    entries=buy_signals,
                    exits=sell_signals,
                    init_cash=self.initial_capital / self.max_positions,
                    freq='1D'
                )

                # 保存回测结果
                stats = portfolio.stats()
                stats['symbol'] = stock
                portfolio_results.append(stats)

            except Exception as e:
                print(f"回测{stock}时出错: {str(e)}")

        return pd.DataFrame(portfolio_results)

    def visualize_results(self, results):
        """可视化回测结果"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('收益分布', '每股收益率', '累计收益', '回撤分析')
        )

        # 收益分布
        fig.add_trace(
            go.Histogram(x=results['Total Return [%]'], name='收益分布'),
            row=1, col=1
        )

        # 每股收益率
        fig.add_trace(
            go.Bar(x=results['symbol'], y=results['Total Return [%]'], name='每股收益率'),
            row=1, col=2
        )

        # 累计收益
        total_equity = results['Total Return [%]'].cumsum()
        fig.add_trace(
            go.Scatter(x=results['symbol'], y=total_equity, name='累计收益'),
            row=2, col=1
        )

        # 回撤分析
        fig.add_trace(
            go.Scatter(x=results['symbol'], y=results['Max Drawdown [%]'], name='最大回撤'),
            row=2, col=2
        )

        fig.update_layout(height=800, title_text="回测结果分析")
        fig.show()

    def run(self):
        """运行完整的回测流程"""
        print("开始回测...")
        start_time = datetime.now()

        # 获取数据
        self.get_stock_data()

        # 执行回测
        results = self.backtest()

        # 显示回测统计
        print("\n回测统计:")
        print(f"总收益率: {results['Total Return [%]'].mean():.2f}%")
        print(f"平均最大回撤: {results['Max Drawdown [%]'].mean():.2f}%")
        print(f"夏普比率: {results['Sharpe Ratio'].mean():.2f}")

        # 可视化结果
        self.visualize_results(results)

        end_time = datetime.now()
        print(f"\n回测完成，耗时: {end_time - start_time}")

        return results


# 运行回测系统
if __name__ == "__main__":
    backtest_system = BacktestSystem(
        start_date='2024-01-01',
        end_date='2024-12-30',
        initial_capital=100000,
        max_positions=10
    )
    results = backtest_system.run()
