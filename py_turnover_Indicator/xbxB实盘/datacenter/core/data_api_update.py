import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pandas as pd

from core.utils.log_kit import logger
from core.resample_candle import update_resample_candle
from core.utils.network import create_aiohttp_session

from .handle import BmacHandle, DataApiHandle
from .quantclass_async import QuantclassDataApi
from .utils.network import async_retry_getter
from .utils.time import (get_offset_from_runtime, now_time, now_time_str)


async def async_fetch_data_api_url(handle: BmacHandle, run_time):
    logger.info(f'开始请求 Data API K 线, 当前时间={now_time_str()}')

    data_api_handle: DataApiHandle = handle.data_api
    timeout_delta = timedelta(seconds=data_api_handle.data_api_timeout_sec)
    expire_time = run_time + timeout_delta

    # Data API 一定为 1h
    offset_str = get_offset_from_runtime(run_time, '1h')

    async with create_aiohttp_session(handle.http_timeout_sec) as session:
        cfg = data_api_handle.cfg
        data_api = QuantclassDataApi(session, cfg.data_api_key, cfg.data_api_uuid)

        # 请求 Data API url
        while True:
            try:
                api_info = await data_api.aioreq_data_api(offset=offset_str)
            except Exception as ex:
                logger.error(f'请求 DataAPI URL 失败, 重试中, 当前时间={now_time_str()}, {repr(ex)}')
                api_info = None

            ts = None
            if api_info is not None:
                ts = api_info['ts']
                if ts == run_time:
                    logger.ok(f"DataAPI URL 就绪, DataAPI 时间戳={api_info['ts']}, 当前时间={now_time_str()}")
                    return api_info

            # 超时
            if now_time() > expire_time:
                break

            await asyncio.sleep(1)

    # 请求 url 超时未就绪，报错
    logger.error(f'DataAPI URL 超时未就绪, now={now_time_str()}')
    return None


async def async_merge_data_api_candles(handle: BmacHandle, run_time, trade_type, url):
    data_api_handle: DataApiHandle = handle.data_api

    # Data API 一定为 1h
    offset_str = get_offset_from_runtime(run_time, '1h')
    resample_delta = timedelta(hours=1)

    # 根据 url 获取 Data API K 线数据

    try:
        symbol_begin_time = dict()
        async with create_aiohttp_session(handle.http_timeout_sec) as session:
            cfg = data_api_handle.cfg
            data_api = QuantclassDataApi(session, cfg.data_api_key, cfg.data_api_uuid)

            # 获取现货 & 永续合约 K 线数据
            df_candle: pd.DataFrame = await async_retry_getter(data_api.aioreq_candle_df, url=url)

        for symbol, df_symbol in df_candle.groupby('symbol'):
            df_symbol = df_symbol.set_index('candle_end_time').drop(columns='symbol')
            candle_mgr = data_api_handle.get_mgr_map(trade_type)[offset_str]
            first_begin_time, last_begin_time = update_resample_candle(candle_mgr, symbol, df_symbol,
                                                                       handle.kline_count_1h, run_time, resample_delta)
            if first_begin_time is not None and last_begin_time is not None:
                symbol_begin_time[symbol] = first_begin_time, last_begin_time
        logger.ok(f'获取并合并 DataAPI 数据 {trade_type} 成功, 当前时间={now_time_str()}')
        return symbol_begin_time

    except Exception as ex:
        logger.exception(f'获取 DataAPI 数据 {trade_type} 失败, 当前时间={now_time_str()}')
        return None


def update_data_api_candles(handle: BmacHandle, run_time):
    # 获取 Data API url
    info = asyncio.run(async_fetch_data_api_url(handle, run_time))

    # 获取 url 失败或缺少 spot/swap url
    if info is None or 'spot' not in info or 'swap' not in info:
        return None

    logger.info(f'data_api_spot={info["spot"]}')
    logger.info(f'data_api_swap={info["swap"]}')

    with ThreadPoolExecutor(max_workers=2) as exe:

        # 下载 spot
        task_spot = exe.submit(asyncio.run, async_merge_data_api_candles(handle, run_time, 'spot', info['spot']))

        # 下载 swap
        task_swap = exe.submit(asyncio.run, async_merge_data_api_candles(handle, run_time, 'swap', info['swap']))

        # 返回是否成功
        symbol_begin_time_spot = task_spot.result()
        symbol_begin_time_swap = task_swap.result()

    if symbol_begin_time_spot is None or symbol_begin_time_swap is None:
        return None

    return symbol_begin_time_spot, symbol_begin_time_swap
