import ccxt
import pandas as pd
import time

def main():
    # 创建币安交易所实例
    exchange = ccxt.binance({
        'enableRateLimit': True,  # 启用请求频率限制
        'options': {
            'defaultType': 'spot'  # 选择现货市场
        }
    })

    # 设置交易对和时间框架
    symbol = 'BTC/USDT'
    timeframe = '1h'  # 1小时K线
    since = exchange.parse8601('2023-01-01T00:00:00Z')  # 从2023年1月1日开始
    limit = 100  # 获取100根K线

    try:
        # 获取历史K线数据
        print(f"正在获取 {symbol} 的历史K线数据...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        
        # 将数据转换为DataFrame以便处理
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # 转换时间戳为可读格式
        print(df)

    except Exception as e:
        print(f"获取数据时发生错误: {e}")

if __name__ == '__main__':
    main() 