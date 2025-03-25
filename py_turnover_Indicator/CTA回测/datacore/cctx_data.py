import ccxt
import os           # 用于判断缓存文件是否存在
import csv          # 使用 CSV 模块读写缓存数据
import time
from datetime import datetime   # 新增，用于时间格式转换

class CCTXData:
    def __init__(self, exchange_id, proxy=None):
        self.exchange_id = exchange_id
        self.proxy = proxy

    def get_historical_data(self, symbol, timeframe, since, limit, cache_file=None):
        # 根据传入参数计算缓存文件路径：
        if cache_file:
            if os.path.isdir(cache_file):
                file_path = os.path.join(cache_file, f"{symbol.replace('/', '_')}_{timeframe}.csv")
            else:
                file_path = cache_file
        else:
            cache_folder = "data_cache"
            if not os.path.exists(cache_folder):
                os.makedirs(cache_folder)
            file_path = os.path.join(cache_folder, f"{symbol.replace('/', '_')}_{timeframe}.csv")

        # 如果缓存文件存在，则直接加载数据
        if os.path.exists(file_path):
            print(f"从本地缓存文件 {file_path} 加载历史数据")
            try:
                import pandas as pd
                # 读取CSV文件
                df = pd.read_csv(file_path, encoding="utf-8")
                # 将 datetime 转换为时间戳（毫秒）
                df["timestamp"] = pd.to_datetime(df["datetime"], format="%Y-%m-%d %H:%M:%S").astype('int64') // 10**6
                # 转换必备字段为数值类型
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                return df
            except Exception as ex:
                print("加载缓存失败，准备重新获取数据:", ex)


        #加载在线数据
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
        except AttributeError:
            raise ValueError(f"Exchange {self.exchange_id} 不存在于 CCXT 中")
        config = {
            'enableRateLimit': True,  # 启用请求频率限制
            'timeout': 30000,         # 设置超时为 30 秒（30000 毫秒）
        }
        if self.proxy:
            config['proxies'] = {
                'http': self.proxy,
                'https': self.proxy,
            }
        self.exchange = exchange_class(config)
        self.exchange.enableRateLimit = True  # 启用
        self.exchange.load_markets()  # 加载市场数据，避免 fetch_ohlcv 时出错
        all_ohlcv = []
        while True:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                # 下一次获取数据的起始时间为本次数据最后一个 bar 的时间 + 1 毫秒
                since = ohlcv[-1][0] + 1
                time.sleep(self.exchange.rateLimit / 1000)
                if len(ohlcv) < limit:
                    break
            except Exception as e:
                print("获取数据异常:", e)
                break

        # 获取数据结束后，构造DataFrame并保存到CSV
        import pandas as pd
        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")
        try:
            df[["date","datetime", "open", "high", "low", "close", "volume"]].to_csv(file_path, index=False, encoding="utf-8")
            print(f"历史数据已保存到缓存文件 {file_path}")
        except Exception as e:
            print("保存缓存失败:", e)
        return df

