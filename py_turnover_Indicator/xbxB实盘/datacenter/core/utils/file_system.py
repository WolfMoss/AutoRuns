import os
import shutil

from core.utils.log_kit import logger
from core.handle import BmacHandle


def init_offset_dirs(offset_candle_mgr_map: dict):
    for offset_mgr in offset_candle_mgr_map.values():
        offset_mgr.clear_all()


def ensure_dir(dir_path, remove_exist=True):
    if os.path.exists(dir_path):
        if remove_exist:
            shutil.rmtree(dir_path)
        else:
            return

    os.makedirs(dir_path)


def init_dirs(handle: BmacHandle):
    # 确保创建 exginfo 目录
    ensure_dir(handle.exg_mgr.base_dir)

    # 确保创建币安 base(5m) 周期目录，不删除旧数据
    ensure_dir(handle.binance_spot.base_candle_dir, remove_exist=False)
    ensure_dir(handle.binance_swap.base_candle_dir, remove_exist=False)

    if handle.fetch_funding_rate:
        ensure_dir(handle.funding_mgr.base_dir, remove_exist=False)

    # 确保创建币安 resample(1h) 周期目录
    ensure_dir(handle.binance_spot.resample_dir)
    init_offset_dirs(handle.binance_spot.resample_mgr_map)
    ensure_dir(handle.binance_swap.resample_dir)
    init_offset_dirs(handle.binance_swap.resample_mgr_map)

    # 确保创建币安 resample(1h) 周期目录
    if handle.data_api is not None:
        ensure_dir(handle.data_api.data_api_spot_dir)
        init_offset_dirs(handle.data_api.spot_mgr_map)
        ensure_dir(handle.data_api.data_api_swap_dir)
        init_offset_dirs(handle.data_api.swap_mgr_map)

    # 确保创建预处理数据 dir
    if handle.preprocess_handle is not None:
        ensure_dir(handle.preprocess_handle.preprocess_dir)
        init_offset_dirs(handle.preprocess_handle.preprocess_mgr_map)

    if handle.coin_cap_handle is not None:
        ensure_dir(handle.coin_cap_handle.coin_cap_mgr.base_dir, remove_exist=False)


def only_ready_files(directory, files):
    # 忽略不以 .ready 结尾的文件
    return [f for f in files if not f.endswith('.ready')]


def copy_data_api_type_candles(binance_resample_dir, data_api_resample_dir):
    offset_strs = os.listdir(binance_resample_dir)
    ignore_ready = shutil.ignore_patterns('*.ready')

    for offset_str in offset_strs:
        binance_offset_dir = os.path.join(binance_resample_dir, offset_str)
        data_api_offset_dir = os.path.join(data_api_resample_dir, offset_str)
        ensure_dir(data_api_offset_dir)

        shutil.copytree(binance_offset_dir, data_api_offset_dir, ignore=ignore_ready, dirs_exist_ok=True)
        shutil.copytree(binance_offset_dir, data_api_offset_dir, ignore=only_ready_files, dirs_exist_ok=True)


def copy_data_api_candles(handle: BmacHandle):
    copy_data_api_type_candles(handle.binance_spot.resample_dir, handle.data_api.data_api_spot_dir)
    copy_data_api_type_candles(handle.binance_swap.resample_dir, handle.data_api.data_api_swap_dir)
    logger.ok(f'Binance {handle.resample_interval} 复制到 Data API 成功')
