"""
加密货币回测主程序
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Exchange, Interval
from vnpy_ctastrategy import CtaStrategyApp
from vnpy_ctabacktester import CtaBacktesterApp
from vnpy_ctabacktester.engine import BacktestingEngine, OptimizationSetting
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import webbrowser

# 打印可用的交易所枚举值
# print("可用的交易所枚举值:")
# for ex in Exchange:
#     print(f"{ex.name}: {ex.value}")
    
# 导入自定义模块
from config.backtest_config import SETTINGS, SYMBOL_CONFIG, STRATEGY_CONFIG, DATA_CONFIG
from utils.data_loader import load_csv_data
from strategies import MaStrategy, BollStrategy

def create_interactive_chart(engine, strategy_name, symbol):
    """
    创建交互式HTML图表
    """
    # 获取回测结果数据
    df = engine.calculate_result()
    trades = engine.get_all_trades()
    
    # 打印DataFrame的列，以便调试
    print(f"回测结果DataFrame的列: {df.columns.tolist()}")
    
    # 确定资金曲线的列名（不同版本可能不同）
    balance_column = None
    for possible_name in ["balance", "net_pnl", "equity", "net_value"]:
        if possible_name in df.columns:
            balance_column = possible_name
            break
    
    if not balance_column:
        print("警告: 无法找到资金曲线数据列")
        # 使用第一个数值列作为替代
        for col in df.columns:
            if df[col].dtype in [float, int]:
                balance_column = col
                print(f"使用 {col} 作为资金曲线")
                break
                
    # 确定持仓列名
    pos_column = "pos" if "pos" in df.columns else None
    if not pos_column:
        for col in ["position", "holding", "position_size"]:
            if col in df.columns:
                pos_column = col
                break
                
    # 创建带有子图的图表布局
    fig = make_subplots(
        rows=4, 
        cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=("价格", "交易量", "持仓", "资金曲线")
    )
    
    # 添加K线图
    klines = engine.history_data
    dates = [bar.datetime for bar in klines]
    
    candle = go.Candlestick(
        x=dates,
        open=[bar.open_price for bar in klines],
        high=[bar.high_price for bar in klines],
        low=[bar.low_price for bar in klines],
        close=[bar.close_price for bar in klines],
        name="K线"
    )
    fig.add_trace(candle, row=1, col=1)
    
    # 添加调试代码，查看交易方向
    print(f"总交易记录数: {len(trades)}")
    if trades:
        print(f"交易记录示例: {trades[0].__dict__}")
        print(f"交易方向值: {[trade.direction for trade in trades[:5]]}")

    # 添加成交记录
    long_trades_x = []
    long_trades_y = []
    short_trades_x = []
    short_trades_y = []
    exit_trades_x = []
    exit_trades_y = []
    
    for trade in trades:
        # 更灵活的方向匹配
        direction = str(trade.direction).upper()
        if "多" in direction or "LONG" in direction or "BUY" in direction:
            long_trades_x.append(trade.datetime)
            long_trades_y.append(trade.price)
            print(f"添加多头交易: {trade.datetime}, {trade.price}")
        elif "空" in direction or "SHORT" in direction or "SELL" in direction:
            if trade.offset and ("平" in str(trade.offset).upper() or "CLOSE" in str(trade.offset).upper()):
                # 这是平仓
                exit_trades_x.append(trade.datetime)
                exit_trades_y.append(trade.price)
                print(f"添加平仓交易: {trade.datetime}, {trade.price}")
            else:
                # 这是开空
                short_trades_x.append(trade.datetime)
                short_trades_y.append(trade.price)
                print(f"添加空头交易: {trade.datetime}, {trade.price}")
        elif trade.offset and ("平" in str(trade.offset).upper() or "CLOSE" in str(trade.offset).upper()):
            # 其他类型的平仓
            exit_trades_x.append(trade.datetime)
            exit_trades_y.append(trade.price)
            print(f"添加平仓交易: {trade.datetime}, {trade.price}")
    
    # 添加开多标记
    fig.add_trace(
        go.Scatter(
            x=long_trades_x, 
            y=long_trades_y,
            mode="markers",
            marker=dict(size=10, color="red", symbol="triangle-up"),
            name="做多"
        ),
        row=1, col=1
    )
    
    # 添加开空标记
    fig.add_trace(
        go.Scatter(
            x=short_trades_x, 
            y=short_trades_y,
            mode="markers",
            marker=dict(size=10, color="green", symbol="triangle-down"),
            name="做空"
        ),
        row=1, col=1
    )
    
    # 添加平仓标记
    fig.add_trace(
        go.Scatter(
            x=exit_trades_x, 
            y=exit_trades_y,
            mode="markers",
            marker=dict(size=8, color="black", symbol="circle"),
            name="平仓"
        ),
        row=1, col=1
    )
    
    # 添加交易量图
    volume = go.Bar(
        x=dates,
        y=[bar.volume for bar in klines],
        name="成交量"
    )
    fig.add_trace(volume, row=2, col=1)
    
    # 添加持仓图（如果有持仓数据）
    if pos_column:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[pos_column],
                fill="tozeroy",
                name="持仓"
            ),
            row=3, col=1
        )
    
    # 添加净值曲线（如果有资金数据）
    if balance_column:
        # 原始资金曲线
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[balance_column],
                name="资金曲线"
            ),
            row=4, col=1
        )
        
        # 添加策略净值曲线（相对收益）
        # 计算初始资金
        init_capital = SETTINGS["init_capital"]
        # 计算净值曲线（相对收益比例）
        equity_curve = (df[balance_column] + init_capital) / init_capital
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=equity_curve,
                name="策略净值",
                line=dict(color="purple", width=2)
            ),
            row=4, col=1
        )
    
    # 更新布局
    fig.update_layout(
        title=f"{strategy_name} - {symbol} 回测结果",
        xaxis_rangeslider_visible=False,
        height=900,
        width=1200,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    # 为不同类型的图表分别设置悬停信息
    fig.update_traces(
        hoverinfo="all",
        selector=dict(type='candlestick')
    )
    
    fig.update_traces(
        hovertemplate="时间: %{x}<br>价格: %{y:.6f}<extra></extra>",
        selector=dict(type='scatter')
    )
    
    fig.update_traces(
        hovertemplate="时间: %{x}<br>成交量: %{y}<extra></extra>",
        selector=dict(type='bar')
    )
    
    # 为净值曲线设置特殊的悬停模板
    fig.update_traces(
        hovertemplate="时间: %{x}<br>净值: %{y:.4f}<extra></extra>",
        selector=dict(name="策略净值")
    )
    
    # 保存为HTML文件
    html_path = f"results/{strategy_name}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    os.makedirs("results", exist_ok=True)
    fig.write_html(html_path, auto_open=True)
    
    print(f"交互式图表已保存至: {html_path}")
    return html_path

def run_backtest():
    """
    运行回测
    """
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 获取配置参数
    start_date = SETTINGS["start_date"]
    end_date = SETTINGS["end_date"]
    interval = SETTINGS["interval"]
    symbol = SYMBOL_CONFIG["symbol"]
    currency = SYMBOL_CONFIG["currency"]
    
    # 使用一个有效的交易所枚举值
    # 这里我使用假设的"SSE"作为示例，您需要替换成在步骤1中找到的有效值
    # 例如 exchange = Exchange.SSE 或其他有效的交易所枚举
    try:
        # 尝试几个常见的交易所枚举
        if hasattr(Exchange, "LOCAL"):
            exchange = Exchange.LOCAL
        elif hasattr(Exchange, "SSE"):
            exchange = Exchange.SSE  
        elif hasattr(Exchange, "SMART"):
            exchange = Exchange.SMART
        else:
            # 使用任何可用的交易所枚举
            exchange = list(Exchange)[0]  # 使用第一个可用的交易所枚举
            
        print(f"使用交易所: {exchange.name}")
    except:
        print("无法获取有效的交易所枚举，请检查VNPY安装")
        return
    
    # 设置回测参数
    vt_symbol = f"{symbol}_{currency}.{exchange.value}"
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=Interval(interval),
        start=datetime.strptime(start_date, "%Y-%m-%d"),
        end=datetime.strptime(end_date, "%Y-%m-%d"),
        rate=SETTINGS["commission_rate"],
        slippage=SETTINGS["slippage"],
        size=SETTINGS["contract_multiplier"],
        pricetick=0.00001,  # 价格精度，加密货币通常较小
        capital=SETTINGS["init_capital"]
    )
    
    # 构建CSV文件路径
    data_folder = DATA_CONFIG["data_folder"]
    file_name = f"{symbol}_{currency}_{interval}.csv"
    file_path = os.path.join(data_folder, file_name)
    
    # 加载数据
    bars = load_csv_data(file_path, symbol, exchange, Interval(interval))

    # 尝试各种可能的方法来加载数据
    try:
        # 方法1: 尝试使用add_bars
        if hasattr(engine, "add_bars"):
            engine.add_bars(bars)
        # 方法2: 尝试使用feed_data
        elif hasattr(engine, "feed_data"):
            for bar in bars:
                engine.feed_data([bar])
        # 方法3: 尝试直接设置history_data
        elif hasattr(engine, "history_data"):
            engine.history_data = bars
        else:
            print("无法找到合适的方法加载数据，请查阅VNPY文档")
            return
    except Exception as e:
        print(f"加载数据时出错: {e}")
        return
    
    # 添加策略
    strategy_class_name = STRATEGY_CONFIG["class_name"]
    strategy_class = globals()[strategy_class_name]
    engine.add_strategy(strategy_class, STRATEGY_CONFIG["parameters"])
    
    # 运行回测
    engine.run_backtesting()
    
    # 计算结果
    df = engine.calculate_result()
    
    # 计算统计指标
    stats = engine.calculate_statistics()
    
    # 输出结果
    print("=========================")
    print(f"策略: {STRATEGY_CONFIG['name']}")
    print(f"品种: {symbol}_{currency}")
    print(f"周期: {interval}")
    print(f"起始时间: {start_date}")
    print(f"结束时间: {end_date}")
    print("=========================")
    print("回测结果统计:")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # 创建交互式HTML图表
    try:
        html_path = create_interactive_chart(
            engine, 
            STRATEGY_CONFIG["name"], 
            f"{symbol}_{currency}"
        )
        print(f"交互式图表已保存至: {html_path}")
    except Exception as e:
        print(f"创建交互式图表时出错: {e}")
        print("无法创建交互式图表")

def run_optimization():
    """
    运行参数优化
    """
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 获取配置参数
    start_date = SETTINGS["start_date"]
    end_date = SETTINGS["end_date"]
    interval = SETTINGS["interval"]
    symbol = SYMBOL_CONFIG["symbol"]
    currency = SYMBOL_CONFIG["currency"]
    exchange_str = SYMBOL_CONFIG["exchange"]
    exchange = Exchange(exchange_str)
    
    # 设置回测参数
    vt_symbol = f"{symbol}_{currency}.{exchange_str}"
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=Interval(interval),
        start=datetime.strptime(start_date, "%Y-%m-%d"),
        end=datetime.strptime(end_date, "%Y-%m-%d"),
        rate=SETTINGS["commission_rate"],
        slippage=SETTINGS["slippage"],
        size=SETTINGS["contract_multiplier"],
        pricetick=0.00001,  # 价格精度，加密货币通常较小
        capital=SETTINGS["init_capital"]
    )
    
    # 构建CSV文件路径
    data_folder = DATA_CONFIG["data_folder"]
    file_name = f"{symbol}_{currency}_{interval}.csv"
    file_path = os.path.join(data_folder, file_name)
    
    # 加载数据
    bars = load_csv_data(file_path, symbol, exchange, Interval(interval))

    # 尝试各种可能的方法来加载数据
    try:
        # 方法1: 尝试使用add_bars
        if hasattr(engine, "add_bars"):
            engine.add_bars(bars)
        # 方法2: 尝试使用feed_data
        elif hasattr(engine, "feed_data"):
            for bar in bars:
                engine.feed_data([bar])
        # 方法3: 尝试直接设置history_data
        elif hasattr(engine, "history_data"):
            engine.history_data = bars
        else:
            print("无法找到合适的方法加载数据，请查阅VNPY文档")
            return
    except Exception as e:
        print(f"加载数据时出错: {e}")
        return
    
    # 设置优化参数
    strategy_class_name = STRATEGY_CONFIG["class_name"]
    strategy_class = globals()[strategy_class_name]
    
    setting = OptimizationSetting()
    
    # 根据不同的策略设置优化参数
    if strategy_class_name == "MaStrategy":
        setting.add_parameter("fast_window", 5, 30, 5)
        setting.add_parameter("slow_window", 20, 60, 10)
        setting.add_parameter("trailing_percent", 0.5, 2.0, 0.5)
    elif strategy_class_name == "BollStrategy":
        setting.add_parameter("boll_window", 10, 40, 5)
        setting.add_parameter("boll_dev", 1.0, 3.0, 0.5)
    
    setting.set_target("sharpe_ratio")  # 以夏普比率为优化目标
    
    # 运行优化
    result = engine.run_optimization(strategy_class, setting)
    
    # 输出结果
    print("=========================")
    print(f"策略优化结果: {strategy_class_name}")
    print("=========================")
    for res in result:
        print(f"参数: {res[0]}, 目标值: {res[1]}")

def main():
    """
    主函数
    """
    print("加密货币回测系统")
    print("1. 运行回测")
    print("2. 运行参数优化")
    
    choice = input("请选择操作: ")
    
    if choice == "1":
        run_backtest()
    elif choice == "2":
        run_optimization()
    else:
        print("无效的选择")

if __name__ == "__main__":
    main() 