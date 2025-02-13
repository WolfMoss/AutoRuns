import asyncio
from datetime import datetime, timedelta
import time
from typing import Optional
import pandas as pd

from core.handle import BmacHandle, CoinCapHandle
from core.quantclass_async import QuantclassDataApi
from core.utils.log_kit import logger
from core.utils.network import create_aiohttp_session, async_retry_getter
from core.utils.time import now_time_str


def convert_coin_cap_csv(coin_cap_handle: CoinCapHandle, run_time: datetime):
    coin_cap_mgr = coin_cap_handle.coin_cap_mgr
    base_dir = coin_cap_mgr.base_dir
    csv_files = base_dir.glob('*.csv')
    for csv_file in csv_files:
        df_cap = pd.read_csv(csv_file, skiprows=1, encoding='gbk', parse_dates=['candle_begin_time', 'date_added'])
        symbol = csv_file.stem.replace('-', '')
        df_cap['symbol'] = df_cap['symbol'].str.replace('-', '')

        if coin_cap_mgr.has_symbol(symbol):
            df_old = coin_cap_mgr.read_candle(symbol)
            df_cap = pd.concat([df_old, df_cap], ignore_index=True)
            df_cap.drop_duplicates('candle_begin_time', ignore_index=True, inplace=True)
            df_cap.sort_values('candle_begin_time', inplace=True, ignore_index=True)

        coin_cap_mgr.set_candle(symbol, run_time, df_cap)
        csv_file.unlink()


async def init_coin_cap(handle: BmacHandle, run_time: datetime):
    logger.info(f'开始初始化市值数据, 当前时间={now_time_str()}')
    t_start = time.perf_counter()
    convert_coin_cap_csv(handle.coin_cap_handle, run_time)

    await coin_cap_update_to_recent(handle, run_time)

    time_elapsed = (time.perf_counter() - t_start) / 60
    logger.ok(f'初始化市值数据成功, 当前时间={now_time_str()}, 耗时={time_elapsed:.2f}分钟')


async def coin_cap_update_to_recent(handle: BmacHandle, run_time: datetime):
    coin_cap_mgr = handle.coin_cap_handle.coin_cap_mgr

    symbols = coin_cap_mgr.get_all_symbols()
    if not symbols:
        raise RuntimeError('历史市场数据不存在，请重新上传')

    max_candle_begin_time: datetime = max(coin_cap_mgr.read_candle(s)['candle_begin_time'].max() for s in symbols)

    async with create_aiohttp_session(handle.http_timeout_sec) as session:
        cfg = handle.coin_cap_handle.cfg
        api = QuantclassDataApi(session, cfg.data_api_key, cfg.data_api_uuid)
        df_product = await async_retry_getter(api.aioreq_product_infos)

    last_update_time: datetime = df_product.loc['coin-cap-daily', 'update_time']

    if last_update_time.date() - max_candle_begin_time.date() > timedelta(days=15):
        raise RuntimeError('历史市场数据与最新数据相差超过 15 天，请重新上传')

    range = pd.date_range(max_candle_begin_time.date(), last_update_time.date(), inclusive='neither')
    for dt in range:
        await update_daily_coin_cap(handle, dt, run_time)


async def update_daily_coin_cap(handle: BmacHandle, dt: datetime, run_time: datetime):
    coin_cap_mgr = handle.coin_cap_handle.coin_cap_mgr
    logger.debug(f'更新市场数据, 日期={dt.date()}, 当前时间={now_time_str()}')
    async with create_aiohttp_session(handle.http_timeout_sec) as session:
        cfg = handle.coin_cap_handle.cfg
        api = QuantclassDataApi(session, cfg.data_api_key, cfg.data_api_uuid)
        data_url = await async_retry_getter(api.aioreq_coincap_url, run_time=dt)
        logger.debug(f'url={data_url}')
        df: Optional[pd.DataFrame] = await async_retry_getter(api.aioreq_coincap_df, url=data_url)

    if df is None or df.empty:
        logger.warning(f'日期={dt.date()}, 获取市值数据为空, 跳过该日期')
        return

    for symbol, df_cap in df.groupby('symbol'):
        if coin_cap_mgr.has_symbol(symbol):
            df_old = coin_cap_mgr.read_candle(symbol)
            df_cap = pd.concat([df_old, df_cap], ignore_index=True)
            df_cap.drop_duplicates('candle_begin_time', ignore_index=True, inplace=True)
            df_cap.sort_values('candle_begin_time', inplace=True, ignore_index=True)
        coin_cap_mgr.set_candle(symbol, run_time, df_cap)


def run_coin_cap_update_to_recent(handle: BmacHandle, run_time: datetime):
    logger.info(f'更新市值数据, 当前时间={now_time_str()}')
    t_start = time.perf_counter()

    try:
        asyncio.run(coin_cap_update_to_recent(handle, run_time))
    except:
        logger.exception('更新市值数据发生错误, 跳过本周期')
        return False
    
    time_elapsed = (time.perf_counter() - t_start) / 60
    logger.info(f'市值数据更新成功, 当前时间={now_time_str()}, 耗时={time_elapsed:.2f}分钟')

    return True