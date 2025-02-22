from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class BacktestingEngine:
    def __init__(self, data, strategy, initial_cash=100000, fee_rate=0.001, slippage=0.0005):
        self.data = data  # 历史K线数据列表，每个元素为 [timestamp, open, high, low, close, volume]
        self.strategy = strategy  # 策略实例
        self.position = 0  # 持仓数量，正数代表多仓
        self.cash = initial_cash  # 初始资金
        self.fee_rate = fee_rate  # 手续费率（如0.001表示0.1%）
        self.slippage = slippage  # 滑点率（如0.001表示0.1%）
        self.trades = []  # 记录所有单子
        self.equity_curve = []  # 每根K线结束后的账户净值

    def run_backtesting(self):
        print("开始回测...")
        # 通知策略回测引擎已关联
        self.strategy.init_strategy(self)
        # 迭代 DataFrame 行，self.data 为 pandas DataFrame，必须包含 "timestamp", "open", "high", "low", "close", "volume"
        for idx, row in self.data.iterrows():
            self.current_bar_index = idx
            self.current_bar_time = row["timestamp"]
            dt = pd.to_datetime(row["timestamp"], unit="ms")
            # 使用 row.to_dict() 获取所有字段，包括 CSV 中附加的因子字段
            bar_dict = row.to_dict()
            # 更新 datetime 字段为转换后的 datetime 值
            bar_dict["datetime"] = dt
            self.strategy.on_bar(bar_dict)
            current_equity = self.cash + self.position * row["close"]
            self.equity_curve.append(current_equity)

        # 回测结束后调用策略结束回调
        self.strategy.on_backtest_end()

    def execute_order(self, order_type, price, volume):
        """
        模拟订单执行，order_type: 'buy' 或 'sell'
        """
        if order_type == 'buy':
            # 买入时模拟滑点（实际成交价格上浮）
            exec_price = price * (1 + self.slippage)
            cost = exec_price * volume
            fee = cost * self.fee_rate
            total_cost = cost + fee
            if self.cash >= total_cost:
                self.cash -= total_cost
                self.position += volume
                self.trades.append({
                    'type': 'buy',
                    'price': price,
                    'exec_price': exec_price,
                    'volume': volume,
                    'fee': fee,
                    'bar_index': self.current_bar_index,
                    'bar_time': self.current_bar_time
                })
                print(f"以基础价格 {price}，实际成交价格 {exec_price} 买入 {volume}（手续费 {fee}）")
            else:
                print("资金不足，无法买入")
        elif order_type == 'sell':
            # 卖出时模拟滑点（实际成交价格下调）
            exec_price = price * (1 - self.slippage)
            proceeds = exec_price * volume
            fee = proceeds * self.fee_rate
            net_proceeds = proceeds - fee
            self.cash += net_proceeds
            self.position -= volume  # 卖出直接减少仓位，即使结果为负也允许
            self.trades.append({
                'type': 'sell',
                'price': price,
                'exec_price': exec_price,
                'volume': volume,
                'fee': fee,
                'bar_index': self.current_bar_index,
                'bar_time': self.current_bar_time
            })
            print(f"以基础价格 {price}，实际成交价格 {exec_price} 卖出 {volume}（手续费 {fee}）")

    def show_results(self):
        print("回测结果:")
        print(f"最终资金: {self.cash}, 最终持仓: {self.position}")
        if self.data.empty:
            print("数据为空，无法计算最终净值")
        else:
            last_bar = self.data.iloc[-1]
            final_price = last_bar["close"]
            final_nav = self.cash + self.position * final_price
            print(f"最终净值: {final_nav}")
        # 设置中文字体和负号正常显示（请确保系统中有 SimHei 字体，否则请替换为可用的中文字体）
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        # 图表1：标的资产价格及买卖点
        times = pd.to_datetime(self.data["timestamp"], unit="ms")
        asset_prices = self.data["close"]
        plt.figure(figsize=(12, 6))
        plt.plot(times, asset_prices, label="标的资产价格", color="blue")
        # 收集买入和卖出点的时间和对应价格
        buy_times, buy_y = [], []
        sell_times, sell_y = [], []
        for trade in self.trades:
            if trade['type'] == 'buy':
                buy_times.append(pd.to_datetime(trade['bar_time'], unit="ms"))
                buy_y.append(trade['exec_price'])
            elif trade['type'] == 'sell':
                sell_times.append(pd.to_datetime(trade['bar_time'], unit="ms"))
                sell_y.append(trade['exec_price'])
        if buy_times:
            plt.scatter(buy_times, buy_y, marker="^", color="green", s=100, label="买入点")
        if sell_times:
            plt.scatter(sell_times, sell_y, marker="v", color="red", s=100, label="卖出点")
        plt.title("标的资产价格及买卖点")
        plt.xlabel("时间")
        plt.ylabel("价格")
        plt.legend()
        plt.grid(True)

        # 图表2：权益曲线
        times_equity = pd.to_datetime(self.data["timestamp"], unit="ms")
        plt.figure(figsize=(12, 6))
        plt.plot(times_equity, self.equity_curve, label="权益曲线", color="orange")
        plt.title("权益曲线")
        plt.xlabel("时间")
        plt.ylabel("净值")
        plt.legend()
        plt.grid(True)

        # 计算绩效指标
        equity_arr = np.array(self.equity_curve)
        initial_value = equity_arr[0]
        final_value = equity_arr[-1]
        total_return = final_value / initial_value - 1
        
        # 计算年化收益率：利用数据第一根与最后一根bar的时间差来计算年化因子
        start_time = self.data["timestamp"].iloc[0]
        end_time = self.data["timestamp"].iloc[-1]
        diff_years = (end_time - start_time) / (1000 * 3600 * 24 * 365)
        if diff_years == 0:
            diff_years = 1/365
        annual_return = (final_value / initial_value) ** (1 / diff_years) - 1
        
        # 最大回撤的计算：计算运行最高值，然后计算当前回撤幅度，取最大值
        running_max = np.maximum.accumulate(equity_arr)
        drawdowns = (running_max - equity_arr) / running_max
        max_drawdown = drawdowns.max()
        
        # 计算夏普比率：使用等间隔的收益率序列（风险自由利率假设为 0）
        returns = np.diff(equity_arr) / equity_arr[:-1]
        # 计算每根bar的平均时间间隔（单位为毫秒），进而计算每年的bar数量
        avg_bar_period = (self.data["timestamp"].iloc[-1] - self.data["timestamp"].iloc[0]) / (len(self.data) - 1)
        periods_per_year = (1000 * 3600 * 24 * 365) / avg_bar_period
        mean_ret = np.mean(returns)
        std_ret = np.std(returns, ddof=1)
        annual_sharpe = (mean_ret / std_ret) * np.sqrt(periods_per_year) if std_ret != 0 else float('nan')
        
        metric_text = (f"总收益率: {total_return:.2%}\n"
                       f"年化收益率: {annual_return:.2%}\n"
                       f"最大回撤: {max_drawdown:.2%}\n"
                       f"夏普比率: {annual_sharpe:.2f}")
        # 将指标文本以注释形式显示到图中
        plt.gcf().text(0.15, 0.75, metric_text, bbox=dict(facecolor='white', alpha=0.5))

        plt.show()

