import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import sys
from typing import Optional

import config as bmac_config
from core.utils.log_kit import logger

from .candle_manager import CandleFileManager
from .symbol_filter import BaseSymbolFilter, create_symbol_filter
from .utils.time import convert_interval_to_timedelta


@dataclass
class DataApiCfg:
    # Quantclass Data API 的葫芦 ID (UUID)
    data_api_uuid: str

    # Quantclass Data API 的 apiKey
    data_api_key: str


@dataclass
class DataApiHandle:
    """
    Quantclass Data API 的句柄类，用于管理与 Quantclass 数据源的连接和数据存储
    """

    cfg: DataApiCfg

    # 现货市场重采样周期数据的存储目录路径
    data_api_spot_dir: Path

    # 现货市场重采样周期数据的映射表，键为偏移量 (offset)，值为对应的 CandleFileManager 实例
    spot_mgr_map: dict[str, CandleFileManager]

    # U 本位永续合约市场重采样周期数据的存储目录路径
    data_api_swap_dir: Path

    # U 本位永续合约市场重采样周期数据的映射表，键为偏移量 (offset)，值为对应的 CandleFileManager 实例
    swap_mgr_map: dict[str, CandleFileManager]

    # Data API 的超时时间（单位：秒），如果在时间内 Data API 数据未就绪，则放弃本次请求，默认 30 秒
    data_api_timeout_sec: int = 30

    def get_mgr_map(self, trade_type) -> dict[str, CandleFileManager]:
        """
        根据交易类型获取对应的数据管理器映射表

        Args:
            trade_type (str): 交易类型，支持 "spot"（现货）和 "swap"（U 本位永续合约）

        Returns:
            dict[str, CandleFileManager]: 对应的数据管理器映射表

        Raises:
            ValueError: 如果交易类型不是 "spot" 或 "swap"，则抛出 ValueError
        """
        if trade_type == 'spot':
            return self.spot_mgr_map
        elif trade_type == 'swap':
            return self.swap_mgr_map
        else:
            raise ValueError(f'Unknown trade_type {trade_type}')


@dataclass
class BinanceHandle:
    """
    Binance 市场数据 API 的句柄类，用于管理与 Binance 市场数据的连接和数据存储
    """

    # API 类型，可选值为 spot（现货）、coin_futures（币本位合约）和 usdt_futures（U 本位合约）
    api_type: str

    # Symbol 过滤器，用于筛选每个周期需要的交易对 (symbol)
    symbol_filter: BaseSymbolFilter

    # 基础周期（5m）数据的存储目录
    base_candle_dir: Path

    # 重采样周期（1h）数据的存储目录路径
    resample_dir: Path

    # 重采样周期（1h）数据的映射表，键为偏移量 (offset)，值为对应的 CandleFileManager 实例
    resample_mgr_map: dict[str, CandleFileManager]

    # 每次更新时从 REST API 请求的基础周期 K 线数量，默认值为 99
    once_update_candles: int = 99


@dataclass
class PreprocessHandle:
    """
    预处理数据句柄类，用于管理和存储预处理后的市场数据
    """

    # 预处理数据的存储目录路径
    preprocess_dir: Path

    # 预处理数据的重采样周期（1h）映射表，键为偏移量 (offset)，值为对应的 CandleFileManager 实例
    preprocess_mgr_map: dict[str, CandleFileManager]

    # 预处理数据中近期 K 线的条数，用于仓位管理框架
    num_recent: int

    # 预处理数据中单个 Batch 包含的 symbol 数量
    num_batch: int


@dataclass
class CoinCapHandle:
    cfg: DataApiCfg
    coin_cap_mgr: CandleFileManager


@dataclass
class BmacHandle:
    """
    BMAC (Binance Marketdata Async Client) 句柄类，用于管理和配置 BMAC
    """

    # BMAC 数据存储的根目录路径
    base_dir: Path

    # 基础周期，表示原始数据的 K 线间隔，例如 "5m" 表示 5 分钟
    base_interval: str

    # 重采样周期，表示对基础数据进行重采样的间隔，例如 "1h" 表示 1 小时
    resample_interval: str

    # 重采样周期 K 线数量
    kline_count_1h: int

    # 基础周期 K 线的数量
    num_base_candles: int

    # 偏移量数量，表示一个重采样周期内包含多少个基础周期
    num_offsets: int

    # 是否获取资金费率数据
    fetch_funding_rate: bool

    # 资金费率数据的管理器，用于存储和读取资金费率数据
    funding_mgr: Optional[CandleFileManager]

    # 交易所信息(Exchange Info)和其他元数据的管理器，用于存储和读取交易所信息
    exg_mgr: CandleFileManager

    # Quantclass Data API 句柄，用于与 Quantclass 数据源进行交互
    data_api: Optional[DataApiHandle]

    # 币安现货交易市场的句柄，用于与币安现货市场进行交互
    binance_spot: BinanceHandle

    # 币安 U 本位永续合约市场的句柄，用于与币安永续合约市场进行交互
    binance_swap: BinanceHandle

    # 预处理数据句柄，用于生成和管理预处理数据
    preprocess_handle: Optional[PreprocessHandle]

    coin_cap_handle: Optional[CoinCapHandle]

    # 代理设置，用于配置网络请求的代理
    proxy: str

    # 分钟偏移配置，只更新如下分钟偏移（hour_offset）
    enabled_hour_offsets: tuple

    # HTTP 请求的超时时间，单位为秒，默认为 8 秒
    http_timeout_sec: int = 8

    def get_binance_handle(self, trade_type) -> BinanceHandle:
        """
        根据交易类型获取对应的币安市场句柄

        Args:
            trade_type (str): 交易类型，支持 "spot"（现货）和 "swap"（永续合约）

        Returns:
            BinanceHandle: 对应的币安市场句柄

        Raises:
            ValueError: 如果交易类型不是 "spot" 或 "swap"，则抛出 ValueError
        """
        if trade_type == 'spot':
            return self.binance_spot
        elif trade_type == 'swap':
            return self.binance_swap
        else:
            raise ValueError(f'Unknown trade_type {trade_type}')


def create_offset_candle_mgr_map(resample_dir: Path, hour_offsets: tuple[str]) -> dict[str, CandleFileManager]:
    """
    创建偏移量到 CandleFileManager 的映射表，用于管理不同偏移量的重采样周期数据

    Args:
        resample_dir (Path): 重采样周期数据的存储目录路径
        hour_offsets (tuple): 偏移量的数量，表示需要创建的偏移量范围

    Returns:
        dict[str, CandleFileManager]: 偏移量到 CandleFileManager 的映射表，键为偏移量字符串（如 "5m"），
                                     值为对应的 CandleFileManager 实例
    """
    # 计算基础周期的 timedelta
    base_delta: timedelta = convert_interval_to_timedelta(bmac_config.base_interval)

    # 初始化偏移量到 CandleFileManager 的映射表
    candle_mgr_map = dict()

    # 遍历偏移量范围
    for offset_str in hour_offsets:
        # 构建当前偏移量的数据存储目录路径
        offset_candle_dir = os.path.join(resample_dir, offset_str)

        # 创建 CandleFileManager 实例，并将其添加到映射表中
        candle_mgr_map[offset_str] = CandleFileManager(offset_candle_dir, 'pickle')

    # 返回偏移量到 CandleFileManager 的映射表
    return candle_mgr_map


def get_coin_cap_dir():
    storage_path = Path(bmac_config.storage_path)
    coin_cap_dir = storage_path / 'coin_cap'
    return coin_cap_dir


def validate_config(base_delta: timedelta, resample_delta: timedelta):
    """
    验证配置的可行性，确保基础周期和重采样周期的设置符合要求

    Args:
        base_delta (timedelta): 基础周期的时间差
        resample_delta (timedelta): 重采样周期的时间差

    Raises:
        ValueError: 如果配置不符合要求，抛出异常并提示具体原因
    """
    # 可行性检查 1: 重采样周期必须是基础周期的倍数
    # 例如，不能使用 3 分钟偏移的 5 分钟线
    if (resample_delta % base_delta).total_seconds() > 1e-6:
        logger.error(f'重采样周期 {bmac_config.resample_interval} 不是基础周期 {bmac_config.base_interval} 的倍数, 请重设')
        sys.exit(-1)

    # 可行性检查 2: Quantclass Data API 仅支持重采样周期为 1h 且基础周期为 5m
    if bmac_config.use_api.get('kline', False):
        if bmac_config.resample_interval.lower() != '1h' or bmac_config.base_interval.lower() != '5m':
            logger.error(f'Quantclass Data API 仅支持 1h 重采样周期和 5m 基础周期, 请重设')
            sys.exit(-1)

    if bmac_config.use_api.get('coin_cap', False):
        coin_cap_dir = get_coin_cap_dir()
        pkl_files = list(coin_cap_dir.glob('*.pkl'))
        csv_files = list(coin_cap_dir.glob('*.csv'))
        if not pkl_files and not csv_files:
            logger.error(f'历史市值数据不存在，请重新上传，目录={coin_cap_dir}')
            sys.exit(-1)


def create_data_api_handle(data_api_cfg: DataApiCfg, hour_offsets: tuple[str]) -> DataApiHandle:
    """
    定义并初始化 Quantclass Data API 的句柄，用于管理现货和 U 本位永续合约的重采样数据

    Args:
        hour_offsets (tuple): 偏移量的数量，表示需要定义的偏移量范围

    Returns:
        DataApiHandle: 初始化后的 Quantclass Data API 句柄，包含现货和 U 本位永续合约的数据管理配置
    """
    # 获取数据存储的基础路径
    storage_path = Path(bmac_config.storage_path)

    # 定义现货市场的重采样数据目录
    data_api_spot_dir = storage_path / 'data_api_spot_1h_resample'
    # 生成现货市场的偏移量到 CandleFileManager 的映射表
    spot_candle_mgr_map = create_offset_candle_mgr_map(data_api_spot_dir, hour_offsets)

    # 定义 U 本位永续合约市场的重采样数据目录
    data_api_swap_dir = storage_path / 'data_api_swap_1h_resample'
    # 生成 U 本位永续合约市场的偏移量到 CandleFileManager 的映射表
    swap_candle_mgr_map = create_offset_candle_mgr_map(data_api_swap_dir, hour_offsets)

    # 初始化 DataApiHandle 实例
    data_api_config = DataApiHandle(
        cfg=data_api_cfg,
        data_api_spot_dir=data_api_spot_dir,
        spot_mgr_map=spot_candle_mgr_map,
        data_api_swap_dir=data_api_swap_dir,
        swap_mgr_map=swap_candle_mgr_map,
    )

    # 返回初始化后的 DataApiHandle 实例
    return data_api_config


def create_binance_spot_handle(hour_offsets: tuple[str]) -> BinanceHandle:
    """
    定义并初始化币安现货市场的句柄，用于管理现货市场的基础周期和重采样周期数据

    Args:
        hour_offsets (str): 偏移量的数量，表示需要定义的偏移量范围

    Returns:
        BinanceHandle: 初始化后的币安现货市场句柄，包含基础周期和重采样周期的数据管理配置
    """
    # 获取数据存储的基础路径，并确保其为 Path 对象
    storage_path = Path(bmac_config.storage_path)

    # 使用币安现货 filter，只保留 USDT 本位现货，并且舍弃稳定币和盘前交易
    spot_filter = create_symbol_filter(filter_name='TradingSpotFilter',
                                       params={
                                           'quote_asset': 'USDT',
                                           'keep_stablecoins': False,
                                           'keep_pre_market': False
                                       })

    # 定义基础周期数据的存储目录
    base_dir = storage_path / f'binance_spot_{bmac_config.base_interval}'

    # 定义重采样周期数据的存储目录
    resample_dir = storage_path / f'binance_spot_{bmac_config.resample_interval}_resample'
    # 生成重采样周期数据的偏移量到 CandleFileManager 的映射表
    resample_mgr_map = create_offset_candle_mgr_map(resample_dir, hour_offsets)

    # 返回初始化后的币安现货市场句柄
    return BinanceHandle(api_type='spot',
                         symbol_filter=spot_filter,
                         base_candle_dir=base_dir,
                         resample_dir=resample_dir,
                         resample_mgr_map=resample_mgr_map)


def create_binance_swap_handle(hour_offsets: tuple[str]) -> BinanceHandle:
    """
    定义并初始化币安 U 本位永续合约市场的句柄，用于管理永续合约市场的基础周期和重采样周期数据

    Args:
        hour_offsets (str): 偏移量的数量，表示需要定义的偏移量范围

    Returns:
        BinanceHandle: 初始化后的币安 U 本位永续合约市场句柄，包含基础周期和重采样周期的数据管理配置
    """
    # 获取数据存储的基础路径，并确保其为 Path 对象
    storage_path = Path(bmac_config.storage_path)

    # 使用币安 U 本位合约 filter，只保留 USDT 本位永续合约（U 本位合约包含 USDT 和 USDC 永续及交割合约）
    swap_filter = create_symbol_filter(filter_name='TradingUsdtFuturesFilter',
                                       params={
                                           'quote_asset': 'USDT',
                                           'types': ['PERPETUAL']
                                       })

    # 定义基础周期数据的存储目录
    base_dir = storage_path / f'binance_swap_{bmac_config.base_interval}'

    # 定义重采样周期数据的存储目录
    resample_dir = storage_path / f'binance_swap_{bmac_config.resample_interval}_resample'
    # 生成重采样周期数据的偏移量到 CandleFileManager 的映射表
    resample_mgr_map = create_offset_candle_mgr_map(resample_dir, hour_offsets)

    # 返回初始化后的币安 U 本位永续合约市场句柄
    return BinanceHandle(api_type='usdt_futures',
                         symbol_filter=swap_filter,
                         base_candle_dir=base_dir,
                         resample_dir=resample_dir,
                         resample_mgr_map=resample_mgr_map)


def create_bmac_handle_from_config() -> BmacHandle:
    """
    根据配置创建并初始化 BmacHandle 实例

    Returns:
        BmacHandle: 初始化后的 BmacHandle 实例，包含所有必要的配置和数据管理组件
    """
    # 计算基础周期和重采样周期的 timedelta
    base_delta = convert_interval_to_timedelta(bmac_config.base_interval)
    resample_delta = convert_interval_to_timedelta(bmac_config.resample_interval)

    # 验证配置的可行性
    validate_config(base_delta, resample_delta)

    # 计算偏移量数量：重采样周期包含的基础周期数量
    # 例如，如果 base=5m 且 resample=1h，则 num_offsets=12
    num_offsets = resample_delta // base_delta

    # 计算基础周期 K 线数量，比配置要求的重采样周期多 3 个周期，防止数据不足
    num_base_candles = num_offsets * (bmac_config.kline_count_1h + 3)

    data_api_cfg = DataApiCfg(data_api_uuid=bmac_config.data_api_uuid, data_api_key=bmac_config.data_api_key)

    # 如果需要使用 Quantclass Data API，初始化 DataApiHandle
    data_api_handle = None
    if bmac_config.use_api.get('kline', False):
        data_api_handle = create_data_api_handle(data_api_cfg, bmac_config.enabled_hour_offsets)

    # 创建币安现货和 U 本位永续合约的句柄
    binance_spot = create_binance_spot_handle(bmac_config.enabled_hour_offsets)
    binance_swap = create_binance_swap_handle(bmac_config.enabled_hour_offsets)

    # 初始化 Exchange Info 的文件管理器
    storage_path = Path(bmac_config.storage_path)
    exginfo_dir = storage_path / 'exginfo'
    exg_mgr = CandleFileManager(exginfo_dir, 'pickle')

    # 如果需要预处理数据，初始化预处理句柄
    preprocess_handle = None
    if bmac_config.preprocess:
        preprocess_dir = storage_path / 'preprocess_1h_resample'
        preprocess_mgr_map = create_offset_candle_mgr_map(preprocess_dir, bmac_config.enabled_hour_offsets)
        preprocess_handle = PreprocessHandle(preprocess_dir=preprocess_dir,
                                             preprocess_mgr_map=preprocess_mgr_map,
                                             num_recent=bmac_config.preprocess_num_recent,
                                             num_batch=bmac_config.preprocess_num_batch)

    # 如果需要获取资金费率，初始化资金费率文件管理器
    funding_mgr = None
    if bmac_config.funding_rate:
        funding_dir = storage_path / 'funding'
        funding_mgr = CandleFileManager(funding_dir, 'pickle')

    coin_cap_handle = None
    if bmac_config.use_api.get('coin_cap', False):
        coin_cap_dir = get_coin_cap_dir()
        mgr = CandleFileManager(coin_cap_dir, 'pickle')
        coin_cap_handle = CoinCapHandle(cfg=data_api_cfg, coin_cap_mgr=mgr)

    # 返回初始化后的 BmacHandle 实例
    return BmacHandle(
        base_dir=storage_path,
        base_interval=bmac_config.base_interval,
        resample_interval=bmac_config.resample_interval,
        kline_count_1h=bmac_config.kline_count_1h,
        num_base_candles=num_base_candles,
        num_offsets=num_offsets,
        fetch_funding_rate=bmac_config.funding_rate,
        funding_mgr=funding_mgr,
        exg_mgr=exg_mgr,
        data_api=data_api_handle,
        binance_spot=binance_spot,
        binance_swap=binance_swap,
        preprocess_handle=preprocess_handle,
        coin_cap_handle=coin_cap_handle,
        proxy=bmac_config.proxy,
        enabled_hour_offsets=bmac_config.enabled_hour_offsets,
    )


def debug_handle(handle: BmacHandle):
    logger.debug(f'数据目录={handle.base_dir}')
    logger.debug(f'基础周期={handle.base_interval}, Resample 周期={handle.resample_interval}')
    logger.debug((f'{handle.resample_interval} 数量={handle.kline_count_1h:,d}, '
                  f'Offset={handle.enabled_hour_offsets}, '
                  f'{handle.base_interval} 数量={handle.num_base_candles:,d}'))

    logger.debug(f'Exchange Info 目录={handle.exg_mgr.base_dir}')
    logger.debug(f'币安现货, {handle.base_interval} 目录={handle.binance_spot.base_candle_dir}')
    logger.debug(f'币安现货, {handle.resample_interval} 目录={handle.binance_spot.resample_dir}')
    logger.debug(f'币安永续合约, {handle.base_interval} 目录={handle.binance_swap.base_candle_dir}')
    logger.debug(f'币安永续合约, {handle.resample_interval} 目录={handle.binance_swap.resample_dir}')

    if handle.fetch_funding_rate:
        logger.debug(f'资金费目录={handle.funding_mgr.base_dir}')
    else:
        logger.debug(f'不使用资金费率数据')

    if handle.data_api is not None:
        logger.debug(f'DataAPI 现货目录={handle.data_api.data_api_spot_dir}')
        logger.debug(f'DataAPI 永续合约目录={handle.data_api.data_api_swap_dir}')
    else:
        logger.debug(f'不使用 DataAPI')

    if handle.preprocess_handle is not None:
        logger.debug(f'预处理数据目录={handle.preprocess_handle.preprocess_dir}')
    else:
        logger.debug('不使用预处理数据')

    if handle.coin_cap_handle is not None:
        logger.debug(f'市值数据目录={handle.coin_cap_handle.coin_cap_mgr.base_dir}')
    else:
        logger.debug('不使用市值数据数据')
