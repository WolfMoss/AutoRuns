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
    def __init__(self, initial_capital=100000, max_positions=10):
        self.initial_capital = initial_capital
        self.max_positions = max_positions

        self.data = {}

        self.trade_records = []  # 新增交易记录列表
    def get_stock_data(self):
        """从MINIQMT获取股票数据"""
        # 获取A股股票列表

        # 获取股票列表
        code_list = xtdata.get_stock_list_in_sector('沪深A股')
        code_list=code_list[:100]

        period = "1d"
        # for i in code_list:
        #     xtdata.download_history_data(i, period, start_time='', end_time='')
        # 读取历史数据
        all_stock_data = xtdata.get_local_data(
            [], code_list, period=period,
            start_time='20200101', end_time='20241230',
            count=-1, dividend_type='front_ratio'
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
                    # 1. 确保索引是datetime类型
                    df.index = pd.to_datetime(df.index)
                    # 计算日MA4
                    df['daily_ma4'] = df['close'].rolling(window=4).mean()

                    # 计算周MA4


                    # 2. 创建周数据
                    # 存储处理后的数据
                    self.data[stock] = self.calculate_m44(df)

                    # 验证数据
                    if df['weekly_ma4'].isnull().all():
                        print(f"警告: {stock} 的weekly_ma4全为空值")
                    else:
                        print(f"成功处理 {stock} 的数据，包含 {len(df)} 行")

            except Exception as e:
                print(f"获取{stock}数据时出错: {str(e)}")

        print("数据获取完成")

    def calculate_m44(self,df):


        # 创建一个新的DataFrame来存储结果
        m44_values = []

        # 获取所有的周五日期
        all_fridays = df[df.index.weekday == 4].index

        # 对每个交易日进行计算
        for date in df.index:
            # 获取当前日期之前的所有周五
            previous_fridays = all_fridays[all_fridays < date]

            if len(previous_fridays) >= 3:
                # 获取最近的3个周五
                last_3_fridays = previous_fridays[-3:]
                # 计算当前日期和前3个周五的close的平均值（共4个值）
                dates_to_average = list(last_3_fridays) + [date]
                m44 = df.loc[dates_to_average, 'close'].mean()
            else:
                m44 = None  # 如果没有足够的历史数据，设置为None

            m44_values.append(m44)

        # 将结果添加到原始DataFrame中
        df['weekly_ma4'] = m44_values

        return df

    def generate_signals(self, df):
        """生成交易信号"""
        # 买入条件
        buy_condition = (
                (df['daily_ma4'] > df['daily_ma4'].shift(1)) &
                (df['weekly_ma4'] > df['weekly_ma4'].shift(1))&
                (df['daily_ma4']>0) &
                (df['weekly_ma4']>0)
        )

        # 卖出条件
        sell_condition = (
                (df['daily_ma4'] <= df['daily_ma4'].shift(1)) &
                (df['daily_ma4']>0) &
                (df['weekly_ma4']>0)
        )

        return buy_condition, sell_condition

    def backtest(self):
        """执行回测"""
        portfolio_results = []

        # 跟踪当前持仓数量和可用资金
        current_positions = 0
        available_cash = self.initial_capital

        # 按时间排序的所有交易信号
        all_signals = []

        # 首先收集所有股票的信号
        for stock, df in self.data.items():
            try:
                buy_signals, sell_signals = self.generate_signals(df)
                df['stock'] = stock
                df['buy_signal'] = buy_signals
                df['sell_signal'] = sell_signals
                all_signals.append(df)
            except Exception as e:
                print(f"生成{stock}信号时出错: {str(e)}")

        # 合并所有信号并按时间排序
        if all_signals:
            combined_signals = pd.concat(all_signals)
            combined_signals.sort_index(inplace=True)

        # 按日期遍历执行交易
        for date in combined_signals.index.unique():
            day_data = combined_signals.loc[date]

            # 处理卖出信号
            if isinstance(day_data, pd.DataFrame):
                sell_stocks = day_data[day_data['sell_signal']]['stock'].unique()
            else:  # 单个股票的情况
                sell_stocks = [day_data['stock']] if day_data['sell_signal'] else []

            for stock in sell_stocks:
                if stock in [trade['symbol'] for trade in self.trade_records if not trade.get('exit_date')]:
                    # 执行卖出操作
                    for trade in self.trade_records:
                        if trade['symbol'] == stock and not trade.get('exit_date'):
                            trade['exit_date'] = date
                            trade['exit_price'] = self.data[stock].loc[date, 'close']
                            trade['pnl'] = (trade['exit_price'] - trade['entry_price']) * trade['size']
                            trade['return'] = trade['pnl'] / (trade['entry_price'] * trade['size'])

                            # 更新可用资金和持仓数量
                            available_cash += trade['exit_price'] * trade['size']
                            current_positions -= 1

            # 处理买入信号
            if isinstance(day_data, pd.DataFrame):
                buy_stocks = day_data[day_data['buy_signal']]['stock'].unique()
            else:
                buy_stocks = [day_data['stock']] if day_data['buy_signal'] else []

            for stock in buy_stocks:
                # 如果当前持仓数已达到最大持仓限制，跳过
                if current_positions >= self.max_positions:
                    break

                # 当前股票价格
                stock_price = self.data[stock].loc[date, 'close']
                # 计算每个位置的最大分配资金
                position_size = available_cash / (self.max_positions - current_positions)

                # 如果分配资金不足以买入至少1股，跳过
                if stock_price <= 0 or position_size < stock_price:
                    continue

                # 计算可买入的股票数量
                shares = int(position_size / stock_price)

                # 确保至少买入1股
                if shares > 0:
                    # 记录买入交易
                    trade_detail = {
                        'symbol': stock,
                        'entry_date': date,
                        'entry_price': stock_price,
                        'size': shares,
                    }
                    self.trade_records.append(trade_detail)

                    # 更新可用资金和持仓数量
                    available_cash -= shares * stock_price
                    current_positions += 1

        # 计算每个股票的最终统计数据
        for stock, df in self.data.items():
            try:
                stock_trades = [trade for trade in self.trade_records if trade['symbol'] == stock]
                if stock_trades:
                    # 计算该股票的统计数据
                    returns = [trade['return'] for trade in stock_trades if 'return' in trade]
                    if returns:
                        stats = {
                            'symbol': stock,
                            'Total Return [%]': sum(returns) * 100,
                            'Max Drawdown [%]': self.calculate_max_drawdown(stock_trades) * 100,
                            'Sharpe Ratio': self.calculate_sharpe_ratio(returns),
                        }
                        portfolio_results.append(stats)
            except Exception as e:
                print(f"计算{stock}统计数据时出错: {str(e)}")

        return pd.DataFrame(portfolio_results)

    def calculate_max_drawdown(self, trades):
        """计算最大回撤"""
        if not trades:
            return 0

        equity_curve = []
        current_equity = 1.0

        for trade in trades:
            if 'return' in trade:
                current_equity *= (1 + trade['return'])
                equity_curve.append(current_equity)

        if not equity_curve:
            return 0

        peak = equity_curve[0]
        max_drawdown = 0

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.02):
        """计算夏普比率"""
        if not returns:
            return 0

        returns = np.array(returns)
        excess_returns = returns - (risk_free_rate / 252)  # 假设252个交易日

        if len(excess_returns) < 2:
            return 0

        return np.mean(excess_returns) / np.std(excess_returns, ddof=1) * np.sqrt(252)
    def visualize_results(self, results):
        """可视化回测结果"""
        # 创建子图，增加一行用于收益/时间折线图
        fig = go.Figure()

        # 添加收益/时间折线图
        # 首先需要整理时间序列数据
        portfolio_values = pd.Series(dtype=float)

        for stock, df in self.data.items():
            try:
                buy_signals, sell_signals = self.generate_signals(df)
                portfolio = vbt.Portfolio.from_signals(
                    close=df['close'],
                    entries=buy_signals,
                    exits=sell_signals,
                    init_cash=self.initial_capital / self.max_positions,
                    freq='1D'
                )

                # 获取该股票的资金曲线
                if portfolio_values.empty:
                    portfolio_values = portfolio.value()
                else:
                    portfolio_values = portfolio_values + portfolio.value()

            except Exception as e:
                print(f"处理{stock}的资金曲线时出错: {str(e)}")

        # 添加收益/时间折线图
        fig.add_trace(
            go.Scatter(
                x=portfolio_values.index,
                y=portfolio_values.values,
                name='总资金曲线',
                line=dict(color='rgb(75, 192, 192)'),
            )
        )

        # 更新布局
        fig.update_layout(
            height=600,  # 设置图表高度
            title_text="累计收益曲线",
            xaxis_title="日期",  # x轴标签
            yaxis_title="账户价值",  # y轴标签
        )

        fig.show()

    def show_trade_details(self):
        """显示交易详情"""
        if not self.trade_records:
            print("没有交易记录")
            return

        trade_df = pd.DataFrame(self.trade_records)
        trade_df['holding_period'] = (trade_df['exit_date'] - trade_df['entry_date']).dt.days

        # 格式化输出
        print("\n=== 交易详情摘要 ===")
        print(f"总交易次数: {len(trade_df)}")
        print(f"盈利交易次数: {len(trade_df[trade_df['pnl'] > 0])}")
        print(f"亏损交易次数: {len(trade_df[trade_df['pnl'] < 0])}")
        print(f"平均持仓天数: {trade_df['holding_period'].mean():.2f}天")
        print(f"平均每笔收益: {trade_df['pnl'].mean():.2f}")
        print("\n=== 具体交易记录 ===")

        # 按照时间排序的详细交易记录
        detailed_trades = trade_df.sort_values('entry_date')[
            ['symbol', 'entry_date', 'exit_date', 'entry_price',
             'exit_price', 'size', 'pnl', 'return', 'holding_period']
        ]
        print(detailed_trades.to_string())

        return detailed_trades
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
        # 显示交易详情
        trade_details = self.show_trade_details()
        # 可视化结果
        self.visualize_results(results)

        end_time = datetime.now()
        print(f"\n回测完成，耗时: {end_time - start_time}")

        return results,trade_details


# 运行回测系统
if __name__ == "__main__":
    backtest_system = BacktestSystem(
        initial_capital=1000000,
        max_positions=10
    )
    results, trade_details = backtest_system.run()
