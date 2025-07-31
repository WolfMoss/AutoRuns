import concurrent.futures
import datetime
from cctx_data import CCTXData

#独立获取行情程序

def fetch_symbol(symbol, timeframe, since, limit, proxy, cache_dir):
    # 为每个品种单独实例化数据获取对象
    fetcher = CCTXData('binance', proxy=proxy)
    print(f"正在获取 {symbol} 的历史数据...")
    data = fetcher.get_historical_data(symbol, timeframe, since, limit, cache_file=cache_dir)
    print(f"{symbol} 获取到数据条数: {len(data)}")
    return symbol, data

def main():
    # 设置多个品种，例如 BTC/USDT、ETH/USDT、BNB/USDT
    symbols = ['TRUMP/USDT',]
    timeframe = '30m'
    # 注意：时间戳单位为毫秒
    since = int(datetime.datetime(2025, 1, 19).timestamp() * 1000)
    limit = 1000  # 每次获取的数据量
    # 指定缓存目录，如果传入的是目录，则会在目录下生成按照品种和时间周期命名的 csv 文件
    cache_dir = "datas"
    # 代理设置（如果不需要代理可以将 proxy 设为 None）
    proxy = 'http://wolfmoss.top:8016'
    
    results = {}
    # 使用线程池并发获取多个品种的数据，每个品种单独使用一个线程
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(symbols)) as executor:
        future_to_symbol = {
            executor.submit(fetch_symbol, symbol, timeframe, since, limit, proxy, cache_dir): symbol
            for symbol in symbols
        }
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol, data = future.result()
            results[symbol] = data
            # 输出每个品种前 3 条数据
            print(f"{symbol} 前 3 条数据:")
            for row in data[:3]:
                print(row)

if __name__ == '__main__':
    main() 