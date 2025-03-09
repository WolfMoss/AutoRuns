import datetime
from engine import BacktestingEngine
from cctx_data import CCTXData
from strategy.my_strategy import MyStrategy
from strategy.wykoff_strategy import WykoffStrategy


def main():
    # proxy = {
    #     'http': 'http://127.0.0.1:7890',
    #     'https': 'http://127.0.0.1:7890'
    # }
    # url = 'https://api.binance.com/api/v3/exchangeInfo'
    # # 如果要测试不加代理，可以把 proxies 参数去掉
    # response = requests.get(url, proxies=proxy, timeout=30)
    # print(response.text)


    # 设置回测参数
    symbol = 'DOGE/USDT'
    timeframe = '1h'
    # 注意：CCXT 使用的时间戳单位为毫秒
    since = int(datetime.datetime(2023, 1, 1).timestamp() * 1000)
    limit = 1000  # 每次获取的数据量

    # 使用 CCXT 获取历史数据（示例中使用 binance 交易所）
    fetcher = CCTXData('binance', proxy='http://wolfmoss.top:8016')
    print("正在获取历史数据...")
    data = fetcher.get_historical_data(symbol, timeframe, since, limit, cache_file="datas")

    # 初始化策略实例（传入必要参数，如交易对）
    strategy = WykoffStrategy(symbol)

    # 初始化回测引擎，将数据和策略传入
    engine = BacktestingEngine(data=data, strategy=strategy, initial_cash=1)
    engine.run_backtesting()
    engine.show_results()





if __name__ == '__main__':
    main()