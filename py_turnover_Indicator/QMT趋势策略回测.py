import pandas as pd
import numpy as np
import backtrader as bt
import plotly.graph_objects as go
from xtquant import xtdata

# 1. 获取行情数据
def get_stock_data():
    """从 xtquant 获取全部 A 股数据"""
    # 获取股票列表
    code_list = xtdata.get_stock_list_in_sector('沪深A股')
    period = "1d"

    # 读取历史数据
    all_stock_data = xtdata.get_local_data(
        [], code_list, period=period,
        start_time='2021-01-01', end_time='2024-12-30',
        count=-1, dividend_type='front'
    )
    print('行情加载完成')
    return all_stock_data

# 2. 数据预处理
def prepare_data(stock_data, stock_code):
    """将单只股票的数据转换为 Backtrader 所需的格式"""
    df = pd.DataFrame(stock_data)
    df['datetime'] = pd.to_datetime(df['time'])
    df.set_index('datetime', inplace=True)
    df['openinterest'] = 0  # Backtrader 需要该字段
    return df

# 3. 编写交易策略
class MultiStockStrategy(bt.Strategy):
    params = (
        ('max_stocks', 10),  # 最多持有 10 只股票
        ('ma_period', 4),    # MA4
    )

    def __init__(self):
        # 为每只股票计算日级别的 MA4
        self.daily_ma = {}
        for data in self.datas:
            self.daily_ma[data._name] = bt.ind.SMA(data.close, period=self.params.ma_period)

    def next(self):
        # 检查当前持有的股票数量
        current_positions = len([d for d in self.datas if self.getposition(d).size > 0])

        # 遍历每只股票
        for data in self.datas:
            # 获取当前和上一周期的 MA4 值
            daily_ma_current = self.daily_ma[data._name][0]
            daily_ma_prev = self.daily_ma[data._name][-1]

            # 买入条件
            if daily_ma_current > daily_ma_prev:
                if current_positions < self.params.max_stocks and not self.getposition(data):
                    self.buy(data=data, size=100)  # 假设每次买入 100 股

            # 卖出条件
            if self.getposition(data):
                if daily_ma_current <= daily_ma_prev:
                    self.sell(data=data, size=self.getposition(data).size)

    def notify_trade(self, trade):
        """打印交易信息"""
        if trade.isclosed:
            print(
                f"交易股票: {trade.data._name}, "
                f"方向: {'买入' if trade.size > 0 else '卖出'}, "
                f"价格: {trade.price:.2f}, "
                f"数量: {abs(trade.size)}, "
                f"手续费: {trade.commission:.2f}, "
                f"利润: {trade.pnl:.2f}"
            )

# 4. 回测引擎
def run_backtest(all_stock_data):
    """运行回测"""
    # 初始化 Backtrader 引擎
    cerebro = bt.Cerebro()

    # 设置初始资金
    cerebro.broker.set_cash(100000)

    # 设置手续费
    cerebro.broker.setcommission(
        commission=0.000095,  # 买入手续费比例
        stamp_duty=0,         # 印花税（卖出时收取，A 股为 0.001，这里单独设置卖出手续费）
        commission_short=0.0006,  # 卖出手续费比例
        margin=1.0,           # 保证金比例（默认为 1.0，表示全额交易）
        mult=1.0,             # 合约乘数（默认为 1.0）
        name='A股手续费'
    )

    # 添加策略
    cerebro.addstrategy(MultiStockStrategy)

    # 添加数据
    for stock_code, data in all_stock_data.items():
        data_feed = bt.feeds.PandasData(dataname=data, timeframe=bt.TimeFrame.Days)
        cerebro.adddata(data_feed, name=stock_code)

    # 运行回测
    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    return cerebro

# 5. 绩效分析
def analyze_performance(cerebro):
    """计算绩效指标"""
    portfolio_value = cerebro.broker.getvalue()
    returns = cerebro.broker.get_return()

    # 计算年化收益率
    annual_return = (portfolio_value[-1] / portfolio_value[0]) ** (252 / len(portfolio_value)) - 1

    # 计算最大回撤
    max_drawdown = (np.maximum.accumulate(portfolio_value) - portfolio_value).max()

    # 计算夏普比率
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)

    print(f"Annual Return: {annual_return:.2%}")
    print(f"Max Drawdown: {max_drawdown:.2f}")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")

# 6. 可视化结果
def plot_results(cerebro):
    """使用 Plotly 可视化回测结果"""
    portfolio_value = cerebro.broker.getvalue()

    # 创建 Plotly 图表
    fig = go.Figure()

    # 添加投资组合价值曲线
    fig.add_trace(go.Scatter(
        x=list(range(len(portfolio_value))),
        y=portfolio_value,
        mode='lines',
        name='Portfolio Value'
    ))

    # 添加布局
    fig.update_layout(
        title="Portfolio Value Over Time",
        xaxis_title="Time",
        yaxis_title="Portfolio Value (CNY)",
        template="plotly_dark"
    )

    # 显示图表
    fig.show()

# 主函数
def main():
    # 获取行情数据
    all_stock_data = get_stock_data()

    # 数据预处理
    prepared_data = {}
    for stock_code, data in all_stock_data.items():
        prepared_data[stock_code] = prepare_data(data, stock_code)

    # 运行回测
    cerebro = run_backtest(prepared_data)

    # 绩效分析
    analyze_performance(cerebro)

    # 可视化结果
    plot_results(cerebro)

if __name__ == "__main__":
    main()