'''
币安市场数据端点的抽象
此处不需要 API Key

此设计参考了 python-binance 库。(https://github.com/sammchardy/python-binance)
'''

import json
from abc import ABC, abstractmethod
from typing import Tuple

import aiohttp


class BinanceRequestException(Exception):
    '''
    自定义异常类，用于处理币安请求时的异常
    '''

    def __init__(self, message):
        '''
        初始化异常类

        参数:
            message (str): 异常消息
        '''
        self.message = message

    def __str__(self):
        '''
        返回异常的字符串表示

        返回:
            str: 异常的描述信息
        '''
        return 'BinanceRequestException: %s' % self.message


class BinanceAPIException(Exception):
    '''
    自定义异常类，用于处理币安API调用时的异常
    '''

    def __init__(self, response, status_code, text):
        '''
        初始化异常类

        参数:
            response: HTTP响应对象
            status_code (int): HTTP状态码
            text (str): 响应文本
        '''
        self.code = 0  # 初始化错误代码为0
        try:
            json_res = json.loads(text)  # 尝试将响应文本解析为JSON
        except ValueError:
            self.message = 'Invalid JSON error message from Binance: {}'.format(response.text)  # 如果解析失败，设置错误消息
        else:
            self.code = json_res.get('code')  # 从JSON中获取错误代码
            self.message = json_res.get('msg')  # 从JSON中获取错误消息
        self.status_code = status_code  # 设置HTTP状态码
        self.response = response  # 设置响应对象
        self.request = getattr(response, 'request', None)  # 获取请求对象（如果存在）

    def __str__(self):  # pragma: no cover
        '''
        返回API错误的字符串表示

        返回:
            str: API错误的描述信息，包括错误代码和消息
        '''
        return 'APIError(code=%s): %s' % (self.code, self.message)  # 返回API错误的描述信息


class BinanceBaseApi:
    '''
    Binance API 的基类，封装了与币安API交互的通用逻辑。
    '''

    def __init__(self, session: aiohttp.ClientSession, proxy: str) -> None:
        '''
        初始化 BinanceBaseApi 类。

        参数:
            session (aiohttp.ClientSession): 用于发送HTTP请求的会话对象。
            proxy (str): 代理地址，用于请求时通过代理访问。
        '''
        self.session = session  # 保存会话对象
        self.proxy = proxy  # 保存代理地址

    async def _handle_response(self, response: aiohttp.ClientResponse):
        '''
        内部辅助方法，用于处理从币安服务器返回的API响应。
        如果响应状态码不是2xx，抛出 BinanceAPIException 异常；
        否则，尝试将响应解析为JSON并返回。

        参数:
            response (aiohttp.ClientResponse): HTTP响应对象。

        返回:
            dict: 解析后的JSON数据。

        抛出:
            BinanceAPIException: 如果响应状态码不是2xx。
            BinanceRequestException: 如果响应无法解析为JSON。
        '''
        if not str(response.status).startswith('2'):
            # 如果状态码不是2xx，抛出 BinanceAPIException 异常
            raise BinanceAPIException(response, response.status, await response.text())
        try:
            # 尝试将响应解析为JSON
            return await response.json()
        except ValueError:
            # 如果解析失败，抛出 BinanceRequestException 异常
            txt = await response.text()
            raise BinanceRequestException(f'Invalid Response: {txt}')

    async def _aio_get(self, url, params):
        '''
        发送异步GET请求。

        参数:
            url (str): 请求的URL。
            params (dict): 请求参数。

        返回:
            dict: 解析后的JSON数据。
        '''
        if params is None:
            params = {}
        # 发送GET请求并处理响应
        async with self.session.get(url, params=params, proxy=self.proxy) as resp:
            return await self._handle_response(resp)

    async def _aio_post(self, url, params):
        '''
        发送异步POST请求。

        参数:
            url (str): 请求的URL。
            params (dict): 请求参数。

        返回:
            dict: 解析后的JSON数据。
        '''
        # 发送POST请求并处理响应
        async with self.session.post(url, data=params, proxy=self.proxy) as resp:
            return await self._handle_response(resp)


class BinanceBaseMarketApi(ABC, BinanceBaseApi):
    '''
    Binance 市场数据API的基类，继承自 BinanceBaseApi。
    这是一个抽象基类，定义了市场数据API的通用接口。
    '''

    WEIGHT_EFFICIENT_ONCE_CANDLES = 1000  # 高效获取K线数据的权重值
    MAX_MINUTE_WEIGHT = 6000  # 每分钟的最大权重限制

    @abstractmethod
    async def aioreq_time_and_weight(self) -> Tuple[int, int]:
        '''
        抽象方法：获取当前时间和权重信息。

        返回:
            Tuple[int, int]: 包含时间戳和权重值的元组。
        '''
        pass

    @abstractmethod
    async def aioreq_klines(self, **kwargs) -> list:
        '''
        抽象方法: 获取K线数据。

        参数:
            **kwargs: 可变参数，用于传递K线请求的参数。

        返回:
            list: K线数据列表。
        '''
        pass

    @abstractmethod
    async def aioreq_exchange_info(self) -> dict:
        '''
        抽象方法：获取交易所信息。

        返回:
            dict: 交易所信息。
        '''
        pass

    async def aioreq_premium_index(self, **kwargs) -> list:
        '''
        获取 Premium Index (默认未实现)

        参数:
            **kwargs: 可变参数，用于传递请求参数。

        抛出:
            NotImplementedError: 如果子类未实现该方法。
        '''
        raise NotImplementedError


class BinanceMarketUMFapi(BinanceBaseMarketApi):
    """
    币安 USDⓈ-M 期货 Fapi 市场端点的抽象实现。
    用于访问币安 USDⓈ-M 期货市场的 API 接口。
    """

    # USDⓈ-M 期货 API 的基础 URL
    PREFIX = 'https://fapi.binance.com/fapi'

    # 高效获取 K 线数据的权重值
    WEIGHT_EFFICIENT_ONCE_CANDLES = 499

    # 每分钟的最大权重限制
    MAX_MINUTE_WEIGHT = 2400

    async def aioreq_time_and_weight(self) -> Tuple[int, int]:
        """
        获取当前服务器时间和已消耗的权重。

        返回:
            Tuple[int, int]: 包含服务器时间戳和已消耗权重的元组。
        """
        url = f'{self.PREFIX}/v1/time'
        async with self.session.get(url, proxy=self.proxy) as resp:
            weight = int(resp.headers['X-MBX-USED-WEIGHT-1M'])
            timestamp = (await resp.json())['serverTime']
        return timestamp, weight

    async def aioreq_klines(self, **kwargs) -> list:
        """
        获取指定交易对的 K 线/蜡烛图数据。
        K 线通过其开盘时间唯一标识。

        参数:
            **kwargs: 可变参数，用于传递 K 线请求的参数（如 symbol、interval 等）。

        返回:
            list: K 线数据列表。
        """
        url = f'{self.PREFIX}/v1/klines'
        return await self._aio_get(url, kwargs)

    async def aioreq_exchange_info(self) -> dict:
        """
        获取当前交易所的交易规则和交易对信息。

        返回:
            dict: 包含交易所规则和交易对信息的字典。
        """
        url = f'{self.PREFIX}/v1/exchangeInfo'
        return await self._aio_get(url, None)

    async def aioreq_premium_index(self, **kwargs) -> list:
        """
        获取标记价格和资金费率。

        参数:
            **kwargs: 可变参数，用于传递请求参数 (如 symbol)。

        返回:
            list: 包含标记价格和资金费率信息的列表。
        """
        url = f'{self.PREFIX}/v1/premiumIndex'
        return await self._aio_get(url, kwargs)

    async def aioreq_funding_rate(self, **kwargs):
        """
        获取资金费率历史记录。

        参数:
            **kwargs: 可变参数，用于传递请求参数（如 symbol、startTime、endTime 等）。

        返回:
            list: 包含资金费率历史记录的列表。
        """
        url = f'{self.PREFIX}/v1/fundingRate'
        return await self._aio_get(url, kwargs)

    async def aioreq_book_ticker(self, **kwargs):
        """
        获取指定交易对的最优买卖价格和数量。

        参数:
            **kwargs: 可变参数，用于传递请求参数 (如 symbol)。

        返回:
            dict: 包含最优买卖价格和数量的字典。
        """
        url = f'{self.PREFIX}/v1/ticker/bookTicker'
        return await self._aio_get(url, kwargs)


class BinanceMarketCMDapi(BinanceBaseMarketApi):
    """
    币安 COIN-M 期货 Dapi 市场端点的抽象实现。
    用于访问币安 COIN-M 期货市场的 API 接口。
    """

    # COIN-M 期货 API 的基础 URL
    PREFIX = 'https://dapi.binance.com/dapi'

    # 高效获取 K 线数据的权重值
    WEIGHT_EFFICIENT_ONCE_CANDLES = 499

    # 每分钟的最大权重限制
    MAX_MINUTE_WEIGHT = 2400

    async def aioreq_time_and_weight(self) -> Tuple[int, int]:
        """
        获取当前服务器时间和已消耗的权重。

        返回:
            Tuple[int, int]: 包含服务器时间戳和已消耗权重的元组。
        """
        url = f'{self.PREFIX}/v1/time'
        async with self.session.get(url, proxy=self.proxy) as resp:
            weight = int(resp.headers['X-MBX-USED-WEIGHT-1M'])
            timestamp = (await resp.json())['serverTime']
        return timestamp, weight

    async def aioreq_klines(self, **kwargs) -> list:
        """
        获取指定交易对的 K 线/蜡烛图数据。
        K 线通过其开盘时间唯一标识。

        参数:
            **kwargs: 可变参数，用于传递 K 线请求的参数（如 symbol、interval 等）。

        返回:
            list: K 线数据列表。
        """
        url = f'{self.PREFIX}/v1/klines'
        return await self._aio_get(url, kwargs)

    async def aioreq_exchange_info(self) -> dict:
        """
        获取当前交易所的交易规则和交易对信息。

        返回:
            dict: 包含交易所规则和交易对信息的字典。
        """
        url = f'{self.PREFIX}/v1/exchangeInfo'
        return await self._aio_get(url, None)

    async def aioreq_premium_index(self, **kwargs) -> list:
        """
        获取标记价格和资金费率。

        参数:
            **kwargs: 可变参数，用于传递请求参数（如 symbol）。

        返回:
            list: 包含标记价格和资金费率信息的列表。
        """
        url = f'{self.PREFIX}/v1/premiumIndex'
        return await self._aio_get(url, kwargs)

    async def aioreq_funding_rate(self, **kwargs):
        """
        获取资金费率历史记录。

        参数:
            **kwargs: 可变参数，用于传递请求参数（如 symbol、startTime、endTime 等）。

        返回:
            list: 包含资金费率历史记录的列表。
        """
        url = f'{self.PREFIX}/v1/fundingRate'
        return await self._aio_get(url, kwargs)


class BinanceMarketSpotApi(BinanceBaseMarketApi):
    """
    币安现货市场 API 端点的抽象实现。
    用于访问币安现货市场的 API 接口。
    """

    # 现货 API 的基础 URL
    PREFIX = 'https://api.binance.com/api'

    # 高效获取 K 线数据的权重值
    WEIGHT_EFFICIENT_ONCE_CANDLES = 1000

    # 每分钟的最大权重限制
    MAX_MINUTE_WEIGHT = 6000

    async def aioreq_time_and_weight(self) -> Tuple[int, int]:
        """
        获取当前服务器时间和已消耗的权重。

        返回:
            Tuple[int, int]: 包含服务器时间戳和已消耗权重的元组。
        """
        url = f'{self.PREFIX}/v3/time'
        async with self.session.get(url, proxy=self.proxy) as resp:
            weight = int(resp.headers['X-MBX-USED-WEIGHT-1M'])
            timestamp = (await resp.json())['serverTime']
        return timestamp, weight

    async def aioreq_klines(self, **kwargs):
        """
        获取指定交易对的 K 线/蜡烛图数据。
        K 线通过其开盘时间唯一标识。

        参数:
            **kwargs: 可变参数，用于传递 K 线请求的参数（如 symbol、interval 等）。

        返回:
            list: K 线数据列表。
        """
        url = f'{self.PREFIX}/v3/klines'
        return await self._aio_get(url, kwargs)

    async def aioreq_exchange_info(self):
        """
        获取当前交易所的交易规则和交易对信息。

        返回:
            dict: 包含交易所规则和交易对信息的字典。
        """
        url = f'{self.PREFIX}/v3/exchangeInfo'
        return await self._aio_get(url, None)


def create_binance_market_api(type_, session, proxy=None) -> BinanceBaseMarketApi:
    """
    根据类型创建币安市场 API 实例。

    参数:
        type_ (str): API 类型，可选值为 'spot'（现货）、'usdt_futures'（USDⓈ-M 期货）、'coin_futures'（COIN-M 期货）。
        session (aiohttp.ClientSession): 用于发送 HTTP 请求的会话对象。
        proxy (str, optional): 代理地址，默认为 None。

    返回:
        BinanceBaseMarketApi: 对应类型的币安市场 API 实例。
    """
    if type_ == 'spot':
        return BinanceMarketSpotApi(session, proxy)
    elif type_ == 'usdt_futures':
        return BinanceMarketUMFapi(session, proxy)
    elif type_ == 'coin_futures':
        return BinanceMarketCMDapi(session, proxy)
