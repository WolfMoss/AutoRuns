# -*- coding: utf-8 -*-
"""
选币策略框架 | 邢不行 | 2024分享会
author: 邢不行
微信: xbx6660
"""
import asyncio
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
import config
from core.utils.dingding import send_wechat_work_msg
from core.utils.log_kit import divider, logger
from core.version import VERSION
from core.binance_update import (fetch_update_binance_candles, update_binance_base_candles, update_binance_meta)
from core.data_api_update import update_data_api_candles
from core.handle import (BmacHandle, create_bmac_handle_from_config, debug_handle)
from core.history import run_download_all_history
from core.preprocess import preprocess_offset_data
from core.resample_candle import resample_history
from core.symbol_match import update_symbol_match
from core.utils.file_system import (copy_data_api_candles, init_dirs)
from core.utils.time import (next_run_time, now_time_str, sleep_until_run_time)
from core.coin_cap import run_coin_cap_update_to_recent

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def update_all(handle: BmacHandle, run_time: datetime):
    if f'{run_time.minute}m' not in handle.enabled_hour_offsets:
        logger.info(f'Runtime={run_time},不在 Offset={handle.enabled_hour_offsets} 中，休息 60s 后，跳过')
        time.sleep(60)  # 必须休息 60s，否则会一直卡在这 1 分钟
        return

    divider(f'Update {handle.base_interval} Runtime={run_time}', with_timestamp=False)

    # 提前 15 秒更新 exchange info
    sleep_until_run_time(run_time - timedelta(seconds=15))

    asyncio.run(update_binance_meta(handle, run_time))

    # 更新现货和永续合约对应关系
    update_symbol_match(handle, run_time)
    logger.ok(f'Exchange Info 与实时资金费获取成功, 本地时间={now_time_str()}')

    # 准点更新 K 线
    sleep_until_run_time(run_time)

    # 用于记录本周期发生的错误，如有错误发送到企业微信
    errs = []

    is_binance_success, is_data_api_success = False, False

    with ProcessPoolExecutor(max_workers=3) as exe:
        # 子进程：从币安 REST API 更新数据, 并且更新 Resample
        task_binance = exe.submit(fetch_update_binance_candles, handle, run_time)
        update_tasks = [task_binance]

        # 子进程：从 QuantClass Data API 更新数据
        if handle.data_api is not None:
            task_data_api = exe.submit(update_data_api_candles, handle, run_time)
            update_tasks.append(task_data_api)

        # 子进程：更新市值数据
        task_coin_cap = None
        if handle.coin_cap_handle is not None:
            task_coin_cap = exe.submit(run_coin_cap_update_to_recent, handle, run_time)

        # 使用 as_completed 等待任意一个任务完成
        task_preprocess = None
        for future in as_completed(update_tasks):
            is_success = False
            if future == task_binance:
                binance_result = task_binance.result()
                if binance_result is not None:
                    is_success = is_binance_success = True
                    spot_dfs, swap_dfs, spot_begin_ts, swap_begin_ts = binance_result
            elif future == task_data_api:
                data_api_result = task_data_api.result()
                if data_api_result is not None:
                    is_success = is_data_api_success = True
                    spot_begin_ts, swap_begin_ts = data_api_result

            # 子进程：预处理数据
            # 只要任何一个数据源成功更新完成，就开始预处理
            if handle.preprocess_handle is not None and task_preprocess is None and is_success:
                task_preprocess = exe.submit(preprocess_offset_data, handle, run_time, spot_begin_ts, swap_begin_ts)

        if task_preprocess is not None:
            task_preprocess.result()

        if task_coin_cap is not None:
            is_coin_cap_success = task_coin_cap.result()
            if not is_coin_cap_success:
                errs.append('获取市值数据失败')

    # 子进程4：更新基础周期(5m) K 线
    if is_binance_success:
        with ProcessPoolExecutor(max_workers=1) as exe:
            task_binance_base = exe.submit(update_binance_base_candles, handle, run_time, spot_dfs, swap_dfs)
            task_binance_base.result()
    else:
        errs.append('获取 Binance API K线失败')

    # Data API 更新失败，复制币安数据
    if handle.data_api is not None and not is_data_api_success:
        # errs.append('获取 Data API K线失败')  # 2025-01-16报错不提示，不然太烦了@SIMONS
        if is_binance_success:
            copy_data_api_candles(handle)

    if errs:
        errs += [f'run_time={run_time}']
        err_msg = '\n'.join(errs)
        send_wechat_work_msg(err_msg, config.error_webhook_url)


def init_history(handle: BmacHandle):
    # 重启，确保数据目录存在，并删除除了币安 base 周期全量数据以外的所有文件
    init_dirs(handle)

    with ProcessPoolExecutor(max_workers=2) as exe:
        # 下载 base 周期历史数据
        download_task = exe.submit(run_download_all_history, handle)
        run_time = download_task.result()

        divider('开始 Resample 历史数据', sep='-')
        resample_spot_task = exe.submit(resample_history, handle, 'spot', run_time)
        resample_swap_task = exe.submit(resample_history, handle, 'swap', run_time)

        resample_swap_task.result()
        resample_spot_task.result()

    if handle.data_api is not None:
        copy_data_api_candles(handle)  # 复制一份给 Quantclass Data API


def main():
    # BMAC 彩虹重制版，版本信息
    divider(f'BMAC 版本: {VERSION}')

    # 阶段1：读取配置, 将配置保存在 BmacHandle 中
    handle = create_bmac_handle_from_config()
    debug_handle(handle)

    while True:
        try:
            # 阶段2: 初始化历史数据
            init_history(handle)

            # 阶段3: 更新数据
            while True:
                run_time = next_run_time(handle.base_interval)
                update_all(handle, run_time)
        except Exception as e:
            import traceback
            from config import error_webhook_url

            ex_str = traceback.format_exc()
            send_wechat_work_msg(f'BMAC 发生错误 {repr(e)}, {ex_str} 1 分钟后重启', error_webhook_url)

            logger.debug(ex_str)
            logger.error(repr(e))

            divider('1 分钟后重启', _logger=logger)
            time.sleep(60)


if __name__ == '__main__':
    main()
