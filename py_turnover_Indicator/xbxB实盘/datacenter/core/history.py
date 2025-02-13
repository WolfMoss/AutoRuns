import asyncio
import shutil
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from core.candle_manager import CandleFileManager
from core.ts_manager import TSManager
from core.utils.log_kit import divider, logger
from core.utils.time import (async_sleep_until_run_time, convert_interval_to_timedelta, format_time, next_run_time,
                             now_time, now_time_str)
from core.coin_cap import init_coin_cap
from .binance_fetcher_async import BinanceFetcher
from .handle import BinanceHandle, BmacHandle
from .utils.network import create_aiohttp_session


@dataclass
class CandleInfo:
    is_empty: bool
    first_begin_time: Optional[datetime]
    last_begin_time: Optional[datetime]


class Downloader(ABC):

    def __init__(self, handle: BmacHandle, binance_handle: BinanceHandle, fetcher: BinanceFetcher, trade_type: str,
                 run_time: datetime, stage_name: str):
        self.handle = handle
        self.binance_handle = binance_handle
        self.fetcher = fetcher
        self.run_time = run_time
        self.trade_type = trade_type
        self.stage_name = stage_name

    @abstractmethod
    def fetch(self, symbol, info) -> tuple[pd.DataFrame, bool]:
        pass

    @abstractmethod
    def check_finish(self, info):
        pass

    async def run_download(self, candle_infos: dict[str, CandleInfo]):
        fetcher = self.fetcher
        time_start = time.perf_counter()
        num_total_symbols = len(candle_infos)

        # 还未完成补全的交易对
        left_symbols = sorted(candle_infos.keys())

        download_round = 0

        # 每分钟最大权重
        max_minute_weight, once_candles = fetcher.get_api_limits()

        # 循环分批获取每个 symbol 历史数据
        while left_symbols:
            download_round += 1

            # 获取当前的权重和服务器时间。如果已使用的权重超过最大限额的 90%，则 sleep 直至下一分钟
            server_time, weight = await fetcher.get_time_and_weight()
            if weight > max_minute_weight * 0.9:
                await async_sleep_until_run_time(next_run_time('1m'))
                continue

            # 每轮从剩余 symbol 中选择 80 个
            fetch_symbols = left_symbols[:80]

            # 为本轮需要获取的 symbols 创建获取 K 线数据的任务
            tasks = []
            for symbol in fetch_symbols:
                info = candle_infos[symbol]
                tasks.append(self.fetch(symbol, info))

            # 并获取 K 线，预计消耗权重为 160
            results: list[tuple[pd.DataFrame, bool]] = await asyncio.gather(*tasks)

            num_finished_round = 0
            # 更新每个 symbol 的 K线数据
            for symbol, (df_new, not_enough) in zip(fetch_symbols, results):
                symbol_dir = self.binance_handle.base_candle_dir / symbol
                ts_mgr = TSManager(symbol_dir)

                if not df_new.empty:
                    ts_mgr.update(df_new)

                partitions = ts_mgr.list_partitions()

                # K 线数量不足
                if not_enough or not partitions:
                    num_finished_round += 1
                    left_symbols.remove(symbol)
                    del candle_infos[symbol]
                    continue

                first_begin_time = ts_mgr.read_partition(partitions[0])['candle_begin_time'].min()
                last_begin_time = ts_mgr.read_partition(partitions[-1])['candle_begin_time'].max()

                candle_info = CandleInfo(False, first_begin_time, last_begin_time)
                candle_infos[symbol] = candle_info

                # 已经补全了 K 线数据
                if self.check_finish(candle_info):
                    num_finished_round += 1
                    left_symbols.remove(symbol)

            if num_finished_round > 0 or download_round == 1:
                time_elapsed = (time.perf_counter() - time_start) / 60
                num_left = len(left_symbols)
                num_success = num_total_symbols - num_left
                symbol_in_progress = sorted(set(fetch_symbols).intersection(set(left_symbols)))
                num_in_progress = len(symbol_in_progress)

                if num_in_progress > 0:
                    in_progress_str = f', 正在下载: {symbol_in_progress[0]} -- {symbol_in_progress[-1]}'
                else:
                    in_progress_str = ''
                progress = (num_success / num_total_symbols) * 100
                logger.debug(f'{self.trade_type} {self.stage_name}, '
                             f'进度={progress:.1f}%({num_success}/{num_total_symbols}), '
                             f'已耗时={time_elapsed:.1f}分钟, '
                             f'当前时间={now_time_str()}'
                             f'{in_progress_str}')
        return candle_infos


class RecentDownloader(Downloader):
    '''
    下载直到现在的最新 K线
    '''

    def __init__(self, handle: BmacHandle, binance_handle: BinanceHandle, fetcher: BinanceFetcher, trade_type: str,
                 run_time: datetime):
        super().__init__(handle, binance_handle, fetcher, trade_type, run_time, '阶段 2')

    async def fetch(self, symbol: str, info: CandleInfo):
        not_enough = False
        fetcher = self.fetcher
        max_minute_weight, once_candles = self.fetcher.get_api_limits()

        if info.is_empty:  # 没有已存在的历史 K线, 根据 run_time 获取最近的
            end_ts = int(self.run_time.timestamp()) * 1000
            df_new = await self.fetcher.get_candle(symbol,
                                                   self.handle.base_interval,
                                                   limit=once_candles,
                                                   endTime=end_ts)
            not_enough = df_new.empty
        else:  # 有已存在的历史 K线, 从 last_begin_time 向现在获取
            start_ts = int(info.last_begin_time.timestamp()) * 1000
            df_new = await fetcher.get_candle(symbol, self.handle.base_interval, limit=once_candles, startTime=start_ts)
            not_enough = df_new['candle_begin_time'].max() < self.run_time and len(df_new) < once_candles

        if not_enough:
            return df_new, not_enough

        df_new = df_new[df_new['candle_begin_time'] < self.run_time]
        return df_new, not_enough

    def check_finish(self, info: CandleInfo):
        # 已经补全了 K 线数据
        base_delta = convert_interval_to_timedelta(self.handle.base_interval)
        if info.last_begin_time + base_delta >= self.run_time:
            return True

        return False


class HistoryDownloader(Downloader):
    '''
    下载历史 K线
    '''

    def __init__(self, handle: BmacHandle, binance_handle: BinanceHandle, fetcher: BinanceFetcher, trade_type: str,
                 run_time: datetime):
        super().__init__(handle, binance_handle, fetcher, trade_type, run_time, '阶段 3')

    async def fetch(self, symbol: str, info: CandleInfo):
        fetcher = self.fetcher
        max_minute_weight, once_candles = self.fetcher.get_api_limits()

        # 根据已存在的历史 K线, 从 first_begin_time 向现在获取
        end_ts = int(info.first_begin_time.timestamp()) * 1000
        df_new = await fetcher.get_candle(symbol, self.handle.base_interval, limit=once_candles, endTime=end_ts)
        df_new = df_new[df_new['candle_begin_time'] < self.run_time]

        if len(df_new) < once_candles:
            return df_new, True

        return df_new, False

    def check_finish(self, info: CandleInfo):
        base_delta = convert_interval_to_timedelta(self.handle.base_interval)
        required_first_begin = self.run_time - base_delta * self.handle.num_base_candles

        # 起始 begin_time 已经在期望起始时间之前，则代表补全了 K 线数据
        if info.first_begin_time <= required_first_begin:
            return True

        return False


async def download_enough_history(handle: BmacHandle, trade_type: str, run_time: datetime,
                                  candle_infos: dict[str, CandleInfo]):
    binance_handle = handle.get_binance_handle(trade_type)

    logger.info(f'{trade_type} 初始化历史 K线, 阶段 3, 补全 {handle.base_interval} K线根数, '
                f'交易对数量={len(candle_infos)}, '
                f'当前时间={now_time_str()}')

    t_start = time.perf_counter()

    async with create_aiohttp_session(handle.http_timeout_sec) as session:
        fetcher = BinanceFetcher(binance_handle.api_type, session, handle.proxy)
        downloader = HistoryDownloader(handle, binance_handle, fetcher, trade_type, run_time)
        candle_infos = await downloader.run_download(candle_infos)

    time_elapsed = (time.perf_counter() - t_start) / 60

    logger.ok(f'{trade_type} 初始化历史 K线, 阶段 3 已完成, '
              f'当前时间={now_time_str()}, '
              f'耗时={time_elapsed:.2f}分钟')

    return candle_infos


async def download_recent_until_runtime(handle: BmacHandle, trade_type: str, run_time: datetime,
                                        candle_infos: dict[str, CandleInfo]):
    binance_handle = handle.get_binance_handle(trade_type)

    logger.info(f'{trade_type} 初始化历史 K线, 阶段 2, 补全 {handle.base_interval} 最新数据, '
                f'交易对数量={len(candle_infos)}, '
                f'当前时间={now_time_str()}')

    t_start = time.perf_counter()

    async with create_aiohttp_session(handle.http_timeout_sec) as session:
        fetcher = BinanceFetcher(binance_handle.api_type, session, handle.proxy)
        downloader = RecentDownloader(handle, binance_handle, fetcher, trade_type, run_time)
        candle_infos = await downloader.run_download(candle_infos)

    time_elapsed = (time.perf_counter() - t_start) / 60

    logger.ok(f'{trade_type} 初始化历史 K线, 阶段 2 已完成, '
              #   f'需要继续补全的交易对数量={len(candle_infos)}, '
              f'当前时间={now_time_str()}, '
              f'耗时={time_elapsed:.2f}分钟')

    return candle_infos


async def get_type_symbols(handle: BmacHandle, trade_type: str):
    '''
    获取指定 trade_type 的交易对, 按字母序排序
    '''
    binance_handle = handle.get_binance_handle(trade_type)
    async with create_aiohttp_session(handle.http_timeout_sec) as session:
        fetcher = BinanceFetcher(binance_handle.api_type, session, handle.proxy)

        # 异步获取交易所信息
        exginfo = await fetcher.get_exchange_info()

        # 过滤交易对
        symbols_trading = binance_handle.symbol_filter(exginfo)

    # 返回按字母排序的交易对列表
    return sorted(symbols_trading)


def verify_symbol_candle(base_candle_dir: Path, trade_type: str, symbol: str, run_time: datetime,
                         required_first_begin: datetime) -> CandleInfo:
    """
    校验 trade_type 类型 symbol 交易对的历史 K 线
    根据 required_first_begin 和 run_time 过滤过时数据
    symbol -> CandleInfo
    """
    symbol_dir = base_candle_dir / symbol

    empty_candle_info = CandleInfo(True, None, None)
    if not symbol_dir.exists():
        return empty_candle_info

    ts_mgr = TSManager(symbol_dir)
    try:
        # 仅保留期望起始时间 required_first_begin 到当前运行时间 run_time 之间的 K线
        ts_mgr.trim(required_first_begin, run_time)
    except Exception as ex:
        # 修剪数据报错，移除 symbol 目录
        shutil.rmtree(symbol_dir)
        return empty_candle_info

    df = ts_mgr.read_all()
    if not isinstance(df, pd.DataFrame) or df.empty or 'candle_begin_time' not in df.columns:
        shutil.rmtree(symbol_dir)
        return empty_candle_info

    # symbol 缺失数据超过 28 天（一个 monthly partition），认为已经损坏
    if df['candle_begin_time'].diff().max() > timedelta(days=28):
        logger.error(f'{trade_type} {symbol} 数据损坏，缺失数据超过 28 天')
        shutil.rmtree(symbol_dir)
        return empty_candle_info

    candle_info = CandleInfo(False, df['candle_begin_time'].min(), df['candle_begin_time'].max())
    return candle_info


def verify_exist_history(handle: BmacHandle, trade_type: str, run_time: datetime, symbols: list[str]):
    binance_handle = handle.get_binance_handle(trade_type)
    base_candle_dir = binance_handle.base_candle_dir
    base_delta = convert_interval_to_timedelta(handle.base_interval)

    # 推算 base 周期(5m) K线起始和终止 candle_begin_time
    required_first_begin = run_time - base_delta * handle.num_base_candles

    logger.info(f'{trade_type} 初始化历史 K线, 阶段 1, 校验并清除过时数据, 当前时间={now_time_str()}')

    t_start = time.perf_counter()

    candle_infos = dict()
    for idx, symbol in enumerate(symbols, 1):
        candle_infos[symbol] = verify_symbol_candle(base_candle_dir, trade_type, symbol, run_time, required_first_begin)
        if idx % 40 == 0:
            time_elapsed = (time.perf_counter() - t_start) / 60
            finish_pct = idx / len(symbols) * 100
            logger.debug(f'{trade_type} 已完成 {finish_pct:.1f}%({idx}/{len(symbols)}) 交易对校验, '
                         f'耗时={time_elapsed:.2f}分钟')

    time_elapsed = (time.perf_counter() - t_start) / 60
    logger.ok(f'{trade_type} 初始化历史 K线, 阶段 1 已完成, 耗时={time_elapsed:.2f}分钟')
    return candle_infos


def initialize_history(handle: BmacHandle, trade_type: str, run_time: datetime, symbols: list[str]):
    # 阶段1: 校验已保存的 K线数据，并清除过时的 K线
    candle_infos = verify_exist_history(handle, trade_type, run_time, symbols)

    # 阶段2: 向现在补全最新的 K线, 直到 run_time
    candle_infos = asyncio.run(download_recent_until_runtime(handle, trade_type, run_time, candle_infos))

    # 阶段3: 向过去补全 handle.num_base_candles 根 K线
    asyncio.run(download_enough_history(handle, trade_type, run_time, candle_infos))


async def async_download_funding_rates(handle: BmacHandle, run_time: datetime, symbols: list[str]):
    binance_handle = handle.binance_swap
    funding_mgr = handle.funding_mgr

    logger.info(f'开始获取历史资金费, 当前时间={now_time_str()}')
    t_start = time.perf_counter()

    # 下载历史资金费率
    async with create_aiohttp_session(30) as session:
        fetcher = BinanceFetcher(binance_handle.api_type, session, handle.proxy)
        results = await asyncio.gather(*[fetcher.get_hist_funding_rate(symbol, limit=1000) for symbol in symbols])

    # 保存历史资金费率
    for symbol, df_funding in zip(symbols, results):
        funding_mgr.set_candle(symbol, run_time, df_funding)

    time_elapsed = (time.perf_counter() - t_start) / 60
    logger.ok(f'获取历史资金费率成功, 当前时间={now_time_str()}, 耗时={time_elapsed:.2f}分钟')


def run_download_all_history(handle: BmacHandle):
    while True:
        # 计算历史数据 run_time
        run_time = next_run_time(handle.base_interval) - convert_interval_to_timedelta(handle.base_interval)
        divider(f'开始初始化历史数据, run_time={run_time}', with_timestamp=False)

        spot_symbols = asyncio.run(get_type_symbols(handle, 'spot'))
        swap_symbols = asyncio.run(get_type_symbols(handle, 'swap'))
        logger.info(f'现货交易对数量={len(spot_symbols)}, 永续合约交易对数量={len(swap_symbols)}')

        with ThreadPoolExecutor(max_workers=4) as executor:
            download_spot = executor.submit(initialize_history, handle, 'spot', run_time, spot_symbols)
            download_swap = executor.submit(initialize_history, handle, 'swap', run_time, swap_symbols)
            tasks = [download_spot, download_swap]

            if handle.fetch_funding_rate:
                download_funding = executor.submit(asyncio.run,
                                                   async_download_funding_rates(handle, run_time, swap_symbols))
                tasks.append(download_funding)

            if handle.coin_cap_handle is not None:
                coin_cap = executor.submit(asyncio.run, init_coin_cap(handle, run_time))
                tasks.append(coin_cap)

            for download_task in as_completed(tasks):
                download_task.result()

        if now_time() - run_time < convert_interval_to_timedelta(handle.resample_interval):
            return run_time

        # 如果本期下载时间太长，导致结束时间距离 run_time 大于一个 resample(1h) 周期，则再下载一次
