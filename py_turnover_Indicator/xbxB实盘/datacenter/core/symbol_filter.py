from abc import ABC, abstractmethod

STABLECOINS = {
    'BKRWUSDT', 'USDCUSDT', 'USDPUSDT', 'TUSDUSDT', 'BUSDUSDT', 'FDUSDUSDT', 'DAIUSDT', 'EURUSDT', 'GBPUSDT',
    'USBPUSDT', 'SUSDUSDT', 'PAXGUSDT', 'AEURUSDT', 'USDSUSDT', 'USDSBUSDT'
}


class BaseSymbolFilter(ABC):

    def __call__(self, exginfo: dict) -> list[str]:
        symbols = [info['symbol'] for info in exginfo.values() if self.is_valid(info)]
        return symbols

    @abstractmethod
    def is_valid(self, x):
        pass


class TradingSpotFilter(BaseSymbolFilter):

    def __init__(self, quote_asset, keep_stablecoins, keep_pre_market):
        self.quote_asset = quote_asset
        self.keep_stablecoins = keep_stablecoins
        self.keep_pre_market = keep_pre_market

    def is_valid(self, x):

        # 如果不是交易状态，则无效
        if x['status'] != 'TRADING':
            return False

        # 如果 quote_asset 不匹配，则无效
        if x['quote_asset'] != self.quote_asset:
            return False

        # 如果是稳定币并且不接受稳定币，则无效
        if x['symbol'] in STABLECOINS and not self.keep_stablecoins:
            return False

        # 如果是盘前交易且不保留盘前交易，则无效
        if x['pre_market'] and not self.keep_pre_market:
            return False

        return True


class TradingUsdtFuturesFilter(BaseSymbolFilter):

    def __init__(self, quote_asset, types):
        self.quote_asset = quote_asset

        self.contract_types = types
        if isinstance(types, str):
            self.contract_types = {types}

    def is_valid(self, x):

        # Not valid if is not trading
        if x['status'] != 'TRADING':
            return False

        # Not valid if quote_asset mismatches
        if x['quote_asset'] != self.quote_asset:
            return False

        # Not valid if contract_type mismatches
        if x['contract_type'] not in self.contract_types:
            return False

        return True


class TradingCoinFuturesFilter(BaseSymbolFilter):
    # quote_asset of Coin margined Futures are always USD

    def __init__(self, types):
        self.contract_types = types
        if isinstance(types, str):
            self.contract_types = {types}

    def is_valid(self, x):

        # Not valid if is not trading
        if x['status'] != 'TRADING':
            return False

        # Not valid if contract_type mismatches
        if x['contract_type'] not in self.contract_types:
            return False

        return True


def create_symbol_filter(filter_name, params) -> BaseSymbolFilter:
    if filter_name not in globals():
        raise ValueError(f'{filter_name} is not supported')
    cls = globals()[filter_name]
    return cls(**params)
