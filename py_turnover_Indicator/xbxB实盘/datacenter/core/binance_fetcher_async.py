import asyncio
from decimal import Decimal

import pandas as pd

from .binance_market_async import create_binance_market_api
from .utils.network import async_retry_getter
from .utils.time import convert_interval_to_timedelta


def _get_from_filters(filters, filter_type, field_name):
    """
    从交易对的过滤器列表中提取指定类型的字段值。

    :param filters: 交易对的过滤器列表，通常包含价格、数量等限制条件。
    :param filter_type: 过滤器的类型，例如 'PRICE_FILTER'、'LOT_SIZE' 等。
    :param field_name: 需要提取的字段名称，例如 'tickSize'、'stepSize' 等。
    :return: 返回指定过滤器类型中对应字段的值。如果未找到，则返回 None。
    """
    for f in filters:  # 遍历过滤器列表
        if f['filterType'] == filter_type:  # 检查过滤器类型是否匹配
            return f[field_name]  # 返回指定字段的值
    return None  # 如果未找到匹配的过滤器类型，返回 None


def _check_from_permission_sets(permission_sets, permission_name):
    """
    检查交易对的权限集中是否包含指定的权限。

    :param permission_sets: 交易对的权限集列表，通常包含交易对的权限信息。
    :param permission_name: 需要检查的权限名称，例如 'PRE_MARKET'。
    :return: 如果权限集中包含指定权限，则返回 True；否则返回 False。
    """
    for permission_set in permission_sets:  # 遍历权限集列表
        if permission_name in permission_set:  # 检查权限名称是否存在于当前权限集中
            return True  # 如果存在，返回 True
    return False  # 如果遍历完所有权限集仍未找到，返回 False


def _parse_usdt_futures_syminfo(info):
    """
    解析 USDT 永续合约交易对的交易规则信息。
    
    :param info: 包含交易对信息的字典，通常从币安 API 获取。
    :return: 返回一个包含解析后交易规则的字典。
    """
    filters = info['filters']  # 获取交易对的过滤器信息
    return {
        'symbol': info['symbol'],  # 交易对名称
        'contract_type': info['contractType'],  # 合约类型
        'status': info['status'],  # 交易对状态
        'base_asset': info['baseAsset'],  # 基础资产
        'quote_asset': info['quoteAsset'],  # 计价资产
        'margin_asset': info['marginAsset'],  # 保证金资产
        'price_tick': Decimal(_get_from_filters(filters, 'PRICE_FILTER', 'tickSize')),  # 价格最小变动单位
        'lot_size': Decimal(_get_from_filters(filters, 'LOT_SIZE', 'stepSize')),  # 最小交易量
        'min_notional_value': Decimal(_get_from_filters(filters, 'MIN_NOTIONAL', 'notional')),  # 最小名义价值
    }


def _parse_coin_futures_syminfo(info):
    """
    解析币本位合约交易对的交易规则信息。
    
    :param info: 包含交易对信息的字典，通常从币安 API 获取。
    :return: 返回一个包含解析后交易规则的字典。
    """
    filters = info['filters']  # 获取交易对的过滤器信息
    return {
        'symbol': info['symbol'],  # 交易对名称
        'contract_type': info['contractType'],  # 合约类型
        'status': info['contractStatus'],  # 合约状态
        'base_asset': info['baseAsset'],  # 基础资产
        'quote_asset': info['quoteAsset'],  # 计价资产
        'margin_asset': info['marginAsset'],  # 保证金资产
        'price_tick': Decimal(_get_from_filters(filters, 'PRICE_FILTER', 'tickSize')),  # 价格最小变动单位
        'lot_size': Decimal(info['contractSize']),  # 一手合约价值(美元)
    }


def _parse_spot_syminfo(info):
    """
    解析现货交易对的交易规则信息。
    
    :param info: 包含交易对信息的字典，通常从币安 API 获取。
    :return: 返回一个包含解析后交易规则的字典。
    """
    filters = info['filters']  # 获取交易对的过滤器信息
    permission_sets = info.get('permissionSets', [])  # 获取交易对的权限集
    return {
        'symbol': info['symbol'],  # 交易对名称
        'status': info['status'],  # 交易对状态
        'base_asset': info['baseAsset'],  # 基础资产
        'quote_asset': info['quoteAsset'],  # 计价资产
        'price_tick': Decimal(_get_from_filters(filters, 'PRICE_FILTER', 'tickSize')),  # 价格最小变动单位
        'lot_size': Decimal(_get_from_filters(filters, 'LOT_SIZE', 'stepSize')),  # 最小交易量
        'min_notional_value': Decimal(_get_from_filters(filters, 'NOTIONAL', 'minNotional')),  # 最小名义价值
        'pre_market': _check_from_permission_sets(permission_sets, 'PRE_MARKET'),  # 是否是盘前交易状态
    }


def pandas_parse_kline(klines):
    """
    将币安的 K 线数据（二维数组）转化为 Pandas DataFrame，并进行数据清洗和格式化。

    :param klines: 币安 K 线数据，通常是一个二维数组，每行代表一根 K 线。
    :return: 返回一个处理后的 Pandas DataFrame，包含格式化后的 K 线数据。
    """
    # 定义 DataFrame 的列名，与币安 K 线数据的字段一一对应
    columns = [
        'candle_begin_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'trade_num',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ]

    # 将 K 线数据转换为 DataFrame，并指定列名
    df = pd.DataFrame(klines, columns=columns)

    # 删除不需要的列（'ignore' 和 'close_time'）
    df.drop(columns=['ignore', 'close_time'], inplace=True)

    # 定义每列的数据类型
    dtypes = {
        'candle_begin_time': int,  # K 线开始时间（时间戳，毫秒）
        'open': float,  # 开盘价
        'high': float,  # 最高价
        'low': float,  # 最低价
        'close': float,  # 收盘价
        'volume': float,  # 成交量
        'quote_volume': float,  # 成交额
        'trade_num': int,  # 成交笔数
        'taker_buy_base_asset_volume': float,  # 主动买入的成交量
        'taker_buy_quote_asset_volume': float  # 主动买入的成交额
    }

    # 将 DataFrame 的列转换为指定的数据类型
    df = df.astype(dtypes)

    # 将 'candle_begin_time' 列的时间戳（毫秒）转换为 UTC 时区的 datetime 类型
    df['candle_begin_time'] = pd.to_datetime(df['candle_begin_time'], unit='ms', utc=True)

    # 基于 'candle_begin_time' 列去除重复的 K 线
    df.drop_duplicates('candle_begin_time', inplace=True)

    # 按 'candle_begin_time' 列对数据进行排序，并重置索引
    df.sort_values('candle_begin_time', inplace=True, ignore_index=True)

    # 返回处理后的 DataFrame
    return df


class BinanceFetcher:

    TYPE_MAP = {
        'usdt_futures': _parse_usdt_futures_syminfo,
        'coin_futures': _parse_coin_futures_syminfo,
        'spot': _parse_spot_syminfo,
    }

    def __init__(self, trade_type, session, proxy=None):
        self.trade_type = trade_type
        self.market_api = create_binance_market_api(trade_type, session, proxy)

        if trade_type in self.TYPE_MAP:
            self.syminfo_parse_func = self.TYPE_MAP[trade_type]
        else:
            raise ValueError(f'Type {trade_type} not supported')

    def get_api_limits(self) -> tuple[int, int]:
        return self.market_api.MAX_MINUTE_WEIGHT, self.market_api.WEIGHT_EFFICIENT_ONCE_CANDLES

    async def get_time_and_weight(self) -> tuple[pd.Timestamp, int]:
        server_timestamp, weight = await async_retry_getter(self.market_api.aioreq_time_and_weight)
        server_timestamp = pd.to_datetime(server_timestamp, unit='ms', utc=True)
        return server_timestamp, weight

    async def get_exchange_info(self) -> dict[str, dict]:
        """
        Parse trading rules from return values of /exchangeinfo API
        """
        exg_info = await async_retry_getter(self.market_api.aioreq_exchange_info)
        results = dict()
        for info in exg_info['symbols']:
            results[info['symbol']] = self.syminfo_parse_func(info)
        return results

    async def get_candle(self, symbol, interval, **kwargs) -> pd.DataFrame:
        """
        异步获取指定交易对的 K 线数据，并将其转换为 Pandas DataFrame。

        :param symbol: 交易对符号，例如 'BTCUSDT'。
        :param interval: K 线的时间间隔，例如 '5m'、'1h'等。
        :param kwargs: 其他可选参数，用于传递给币安 API 的 K 线接口。例如：
                    - startTime: 获取 K 线的起始时间（时间戳，毫秒）。
                    - endTime: 获取 K 线的结束时间（时间戳，毫秒）。
                    - limit: 获取 K 线的数量限制。
        :return: 返回一个包含 K 线数据的 Pandas DataFrame
        """
        # 异步调用币安 API 获取 K 线数据
        data = await async_retry_getter(self.market_api.aioreq_klines, symbol=symbol, interval=interval, **kwargs)

        # 将获取的 K 线数据转换为 Pandas DataFrame
        return pandas_parse_kline(data)

    async def batch_get_candle(self, params_list: list[dict]) -> list[pd.DataFrame]:
        """
        异步批量获取多个交易对的 K 线数据，并将其转换为 Pandas DataFrame 列表。

        :param params_list: 包含多个请求参数的字典列表。每个字典的键值对如下：
                            - symbol: 交易对符号，例如 'BTCUSDT'。
                            - interval: K 线的时间间隔，例如 '5m'、'1h'等。
                            - limit: 获取 K 线的数量限制（可选）。
                            - startTime: 获取 K 线的起始时间（可选，时间戳，毫秒）。
                            - endTime: 获取 K 线的结束时间（可选，时间戳，毫秒）。
                            - 其他可选参数，用于传递给币安 API 的 K 线接口。
        :return: 返回一个列表，每个元素是对应交易对的 K 线数据 DataFrame。列表顺序与 params_list 一致。
        """
        # 创建异步任务列表，每个任务异步调用币安 API 获取 K 线数据
        tasks = [async_retry_getter(self.market_api.aioreq_klines, **params) for params in params_list]

        # 使用 asyncio.gather 并发执行所有任务，获取原始 K 线数据
        raw_data_list = await asyncio.gather(*tasks)

        # 将原始 K 线数据解析为 DataFrame，并存储在列表中
        result = [pandas_parse_kline(raw_data) for raw_data in raw_data_list]
        return result

    async def get_realtime_funding_rate(self) -> pd.DataFrame:
        '''
        Parse realtime funding rates from /premiumIndex
        '''
        if self.trade_type == 'spot':
            raise RuntimeError('Cannot request funding rate for spot')
        data = await async_retry_getter(self.market_api.aioreq_premium_index)
        # 如果 lastFundingRate 不能转换为浮点数，则转换为 nan
        data = [{
            'symbol': d['symbol'],
            'funding_rate': pd.to_numeric(d['lastFundingRate'], errors='coerce'),
            'next_funding_time': pd.to_datetime(d['nextFundingTime'], unit='ms', utc=True)
        } for d in data]
        df = pd.DataFrame.from_records(data)
        return df

    async def get_hist_funding_rate(self, symbol, **kwargs):
        '''
        Parse historical funding rates from /fundingRate
        '''
        if self.trade_type == 'spot':
            raise RuntimeError('Cannot request funding rate for spot')

        # funding rates 接口限制 500/5mins，失败后等待 75 秒
        data = await async_retry_getter(self.market_api.aioreq_funding_rate, symbol=symbol, _sleep_seconds=75, **kwargs)
        data = [{
            'symbol': d['symbol'],
            'funding_rate': pd.to_numeric(d['fundingRate'], errors='coerce'),
            'candle_begin_time': pd.to_datetime(d['fundingTime'], unit='ms', utc=True)
        } for d in data]
        df = pd.DataFrame.from_records(data)
        if df.empty:
            return df
        funding_ts = df['candle_begin_time'].astype(int) // (10**9) / 3600.0
        funding_ts = funding_ts.round().astype(int) * 3600
        df['candle_begin_time'] = pd.to_datetime(funding_ts, unit='s', utc=True)
        df.sort_values('candle_begin_time', inplace=True)
        return df
