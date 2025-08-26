# -*- coding: utf-8 -*-
"""
# 预处理数据
1. relist: 将原始的k线数据进行检查。遇到relist的情况，直接拆分，并且记录date_range。output到一个独立的folder
2. mapping: 将split之后的数据和symbol按照has_swap的映射关系进行映射
3. 合成并且预处理数据

回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from config import njobs
from utils.log_kit import get_logger
from utils.path_kit import get_data_path, get_data_file_path

logger = get_logger()

# 现货数据路径
spot_path = get_data_path("coin-binance-candle-csv-1h")
# 合约数据路径
swap_path = get_data_path("coin-binance-swap-candle-csv-1h")

# 特殊现货对应列表
special_symbol_dict = {
    "DODO": "DODOX",  # DODO现货对应DODOX合约
    "LUNA": "LUNA2",  # LUNA现货对应LUNA2合约
    "1000SATS": "1000SATS",  # 1000SATS现货对应1000SATS合约
}
# TODO: 遇到现货更名的复杂情况还得迭代
SWAP_SPLIT_MAP = {
    "LUNA-USDT": ["LUNA-USDT", "LUNA2-USDT"],
    "DODO-USDT": ["DODO-USDT", "DODOX-USDT"],
}
# 稳定币信息，不参与交易的币种
stable_symbol = [
    "BKRW",
    "USDC",
    "USDP",
    "TUSD",
    "BUSD",
    "FDUSD",
    "DAI",
    "EUR",
    "GBP",
    "USBP",
    "SUSD",
    "PAXG",
    "AEUR",
]

data_path = get_data_path("coin-binance-spot-swap-preprocess-pkl-1h", "output")
output_path = get_data_path("coin-binance-spot-swap-preprocess-pkl-1h")


def is_trade_symbol(symbol, black_list) -> bool:
    """
    过滤掉不能用于交易的币种，比如稳定币、非USDT交易对，以及一些杠杆币
    :param symbol: 交易对
    :param black_list: 黑名单
    :return: 是否可以进入交易，True可以参与选币，False不参与
    """
    # 稳定币和黑名单币不参与
    if not symbol or not symbol.endswith("USDT") or symbol in black_list:
        return False

    # 筛选杠杆币
    base_symbol = symbol.upper().replace("-USDT", "USDT")[:-4]
    if (
            base_symbol.endswith(("UP", "DOWN", "BEAR", "BULL"))
            and base_symbol != "JUP"
            and base_symbol != "SYRUP"
            or base_symbol in stable_symbol
    ):
        return False
    else:
        return True


def preprocess_kline(df: pd.DataFrame) -> pd.DataFrame:
    """
    预处理k线数据
    :param df:  k线数据
    :return:
    """
    candle_data_dict = {}
    is_swap = "fundingRate" in df.columns

    # 定义一个开始的基准时间，避免周期转换出现问题
    first_candle_time = df["candle_begin_time"].min()
    last_candle_time = df["candle_begin_time"].max()

    benchmark_epoch = first_candle_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    benchmark = pd.DataFrame(
        pd.date_range(start=benchmark_epoch, end=last_candle_time, freq="1h")
    )  # 创建0点至数据末尾
    benchmark.rename(columns={0: "candle_begin_time"}, inplace=True)

    # ===与benchmark合并
    df = pd.merge(
        left=benchmark,
        right=df,
        on="candle_begin_time",
        how="left",
        sort=True,
        indicator=True,
    )
    # 按照惯例排序并去重，防止原始数据有问题
    df.sort_values(by="candle_begin_time", inplace=True)
    df.drop_duplicates(subset=["candle_begin_time"], inplace=True, keep="last")

    # 空数据预处理
    df["close"] = df["close"].ffill()
    df["open"] = df["open"].fillna(df["close"])

    # 数据填充
    candle_data_dict["candle_begin_time"] = df["candle_begin_time"]
    candle_data_dict["symbol"] = pd.Categorical(df["symbol"].ffill())

    candle_data_dict["open"] = df["open"]
    candle_data_dict["high"] = df["high"].fillna(df["close"])
    candle_data_dict["close"] = df["close"]
    candle_data_dict["low"] = df["low"].fillna(df["close"])

    candle_data_dict["volume"] = df["volume"].fillna(0)
    candle_data_dict["quote_volume"] = df["quote_volume"].fillna(0)
    candle_data_dict["trade_num"] = df["trade_num"].fillna(0)
    candle_data_dict["taker_buy_base_asset_volume"] = df[
        "taker_buy_base_asset_volume"
    ].fillna(0)
    candle_data_dict["taker_buy_quote_asset_volume"] = df[
        "taker_buy_quote_asset_volume"
    ].fillna(0)
    candle_data_dict["funding_fee"] = (
        df["fundingRate"].fillna(value=0) if is_swap else 0
    )
    candle_data_dict["avg_price_1m"] = df["avg_price_1m"].fillna(df["open"])
    candle_data_dict["avg_price_5m"] = df["avg_price_5m"].fillna(df["open"])

    # 计算需要的数据
    # candle_data_dict['avg_price'] = candle_data_dict['avg_price_1m']  # 假设资金量很大，可以使用5m均价作为开仓均价
    # candle_data_dict['avg_price'].fillna(value=candle_data_dict['open'], inplace=True)  # 若均价空缺，使用open填充
    # candle_data_dict['下个周期_avg_price'] = candle_data_dict['avg_price'].shift(-1)  # 用于后面计算当周期涨跌幅

    # 存在成交量的数据，标识可交易状态。一个币种1h之内没有一笔交易，去除。但如果将来处理分钟数据，此处要改。
    candle_data_dict["是否交易"] = np.where(df["volume"] > 0, 1, 0).astype(np.int8)

    candle_data_dict["first_candle_time"] = pd.Series([first_candle_time] * len(df))
    candle_data_dict["last_candle_time"] = pd.Series([last_candle_time] * len(df))

    # 初始化spot和swap symbol
    candle_data_dict["symbol_spot"] = (
        [""] * len(df) if is_swap else df["symbol"].ffill()
    )
    candle_data_dict["symbol_swap"] = (
        [""] * len(df) if not is_swap else df["symbol"].ffill()
    )

    # 币种类型
    candle_data_dict["is_spot"] = np.int8(0) if is_swap else np.int8(1)

    return pd.DataFrame(candle_data_dict).reset_index(drop=True)


def get_date_range(df: pd.DataFrame, symbol_type: str) -> dict:
    date_range_dict = {}

    # 针对每一个币种进行处理
    post_fix = symbol_type.upper()[:2]
    for symbol, grp in tqdm(
            df.groupby("symbol"), desc=f"生成{symbol_type}的date_range", file=sys.stdout, mininterval=2
    ):
        symbol = f"{symbol}"
        # 针对每一个交易对进行处理
        base_symbol = symbol.split("-USDT")[0]

        # 循环添加周期信息
        date_range_list = []
        _begin = None
        for _, row in grp.iterrows():
            date_range = (
                f"{base_symbol}_{post_fix}{len(date_range_list)}-USDT",
                _begin,
                row["prev_candle_begin_time"],
            )
            _begin = row["candle_begin_time"]
            date_range_list.append(date_range)

        # 最后补上最后一个周期
        date_range_list.append((symbol, _begin, None))

        # 和币种绑定
        date_range_dict[symbol] = date_range_list

    return date_range_dict


def relist_check(filename):
    # 文件预检查
    symbol = filename.stem
    df = pd.read_csv(
        filename,
        # 注意：这里 mac arm 下需要使用 utf-8 编码，否则会出现乱码问题
        # encoding="utf-8",
        encoding="gbk",
        parse_dates=["candle_begin_time"],
        skiprows=1,
    )
    is_spot = 1 if ("fundingRate" not in df.columns) else 0

    # 整理数据，确保数据按照顺序排列
    df.sort_values(by="candle_begin_time", inplace=True)

    # 计算candle_begin_time行与行之间的时间差。
    # - 如果是一份正经的1H数据，time_diff每一行都应该是1H，
    # - 第一行为空
    df["time_diff"] = df["candle_begin_time"].diff()
    regular_gap = df[
        "time_diff"
    ].min()  # 这边也可以写 pd.to_timedelta('1h')，但是为了兼容更多的情况，我们用min

    # 裁切那些不正经的数据，也就是命名是1H的数据，但是时间差不是1H的数据
    non_regular_row_index_list = df[df["time_diff"] > regular_gap].index

    gaps = []
    for idx in non_regular_row_index_list:
        # 获取时间差异常的前后两行
        non_regular_gap_rows = df.loc[:idx].tail(2)

        # 获取时间和时间差详情
        prev_candle_begin_time = non_regular_gap_rows.iloc[0]["candle_begin_time"]
        candle_begin_time = non_regular_gap_rows.iloc[1]["candle_begin_time"]
        time_delta = candle_begin_time - prev_candle_begin_time

        # 计算一下上收盘价和当前开盘价之间的delta，一般太大说明有问题的
        price_change = (
                non_regular_gap_rows.iloc[1]["open"] / non_regular_gap_rows.iloc[0]["close"]
                - 1
        )
        gaps.append(
            (
                symbol,
                prev_candle_begin_time,
                candle_begin_time,
                time_delta,
                price_change,
                np.int8(is_spot),
            )
        )

    return gaps


def split_raw_data(filename: Path, split_info) -> Dict[str, pd.DataFrame]:
    symbol = filename.stem
    content = pd.read_csv(
        filename, encoding="gbk", parse_dates=["candle_begin_time"], skiprows=1
    )
    split_content = dict()
    if split_info:
        for dest_symbol_name, start_date, stop_date in split_info:
            condition = True
            content["symbol"] = dest_symbol_name
            if start_date:
                condition = condition & (content["candle_begin_time"] >= start_date)
            if stop_date:
                condition = condition & (content["candle_begin_time"] <= stop_date)

            split_content[dest_symbol_name] = preprocess_kline(content.loc[condition])
    else:
        split_content[symbol] = preprocess_kline(content)

    return split_content


def process_relist(spot_file_list, swap_file_list):
    # ======================================================================================
    # 1. 读取原始文件信息，并且排除掉一些不希望进入后续选币的币种
    # ======================================================================================
    file_list = spot_file_list + swap_file_list

    # ======================================================================================
    # 2. 进行relist检查，找到所有的中间空缺区间信息
    # ======================================================================================
    all_gaps = []
    with ThreadPoolExecutor(max_workers=njobs) as executor:
        # 映射任务到进程池
        results = list(
            tqdm(
                executor.map(relist_check, file_list),
                total=len(file_list),
                desc="检查空缺k线",
                file=sys.stdout,
                mininterval=2
            )
        )
        # 汇总所有结果
        for result in results:
            all_gaps.extend(result)
    candle_gaps = pd.DataFrame(
        all_gaps,
        columns=[
            "symbol",
            "prev_candle_begin_time",
            "candle_begin_time",
            "time_delta",
            "price_change",
            "is_spot",
        ],
    )

    candle_gaps.to_excel(data_path / "relist.xlsx", index=False)

    # ======================================================================================
    # 3. 对空缺数据进行过滤
    # 过滤掉时间差超过2天的数据，或者涨跌幅超过1%的数据
    # ======================================================================================
    # 过滤掉时间差超过2天的数据
    gap_threshold = pd.to_timedelta("1days")
    change_threshold = 0.01

    # 过滤掉时间差超过2天的数据，或者涨跌幅超过1%的数据
    problem_candle_gaps = candle_gaps[
        (candle_gaps["time_delta"] > gap_threshold)
        & (candle_gaps["price_change"].abs() >= change_threshold)
        ].copy()

    problem_candle_gaps.sort_values(by=["symbol", "candle_begin_time"], inplace=True)
    problem_candle_gaps.reset_index(drop=True, inplace=True)

    problem_candle_gaps.to_csv(data_path / "relist.csv", index=False)

    # ======================================================================================
    # 5. 生成币种切割信息json
    # ======================================================================================
    split_info = dict()
    # 线处理spot数据
    spot_gaps = problem_candle_gaps[problem_candle_gaps["is_spot"] == 1]
    split_info["spot"] = get_date_range(spot_gaps, "spot")

    # 线处理swap数据
    swap_gaps = problem_candle_gaps[problem_candle_gaps["is_spot"] == 0]
    split_info["swap"] = get_date_range(swap_gaps, "swap")

    pd.to_pickle(split_info, data_path / "split_info.pkl")

    return split_info


def map_spot_swap(
        spot_file_list, swap_file_list
) -> List[
    Union[Tuple[str, str], Tuple[str, None], Tuple[None, str], Tuple[None, None]]
]:
    # 读取原始文件信息，并且排除掉一些不希望进入后续选币的币种
    spot_symbol_list = [file.stem for file in spot_file_list]
    swap_symbol_list = [file.stem for file in swap_file_list]

    # ====================================================================================================
    # 3. ** 合并spot和swap数据 **
    # - 结果为 [('BTCUSDT', 'BTCUSDT'), (None, '1000SATSUSDT'), ...]
    # ====================================================================================================
    print("合并计算交易对...")
    same_symbols = set(spot_symbol_list) & set(swap_symbol_list)  # join，取交集
    all_symbols = set(spot_symbol_list) | set(swap_symbol_list)  # union，取并集

    problem_symbols = _ = [
        symbol for sublist in SWAP_SPLIT_MAP.values() for symbol in sublist
    ]

    # 3.0 预处理一下special symbol，加上usdt的尾缀，原始配置只有币种名称
    special_symbol_with_usdt_dict = {
        f"{_spot}-USDT".upper(): f"{_special_swap}-USDT".upper()
        for _spot, _special_swap in special_symbol_dict.items()
    }

    # 3.1 组合相同币种，
    # - 比如 spot是 BTCUSDT，swap是BTCUSDT，
    # - 结果为 (BTCUSDT. BTCUSDT)
    symbol_pair_list1 = [(_spot, _spot) for _spot in same_symbols]

    # 3.2 组合config中special_symbol_dict配置的特殊币种，
    # - 比如 spot是 DODOUSDT，swap是DODOXUSDT，
    # - 结果为 (DODOUSDT. DODOXUSDT)
    # symbol_pair_list2 = [(_spot, _swap) for _spot, _swap in special_symbol_with_usdt_dict.items()]
    symbol_pair_list2 = []

    # 3.3 组合swap相比于spot前面多了1000的币种，
    # - 比如 spot是 FLOKIUSDT，swap列表中存在1000FLOKIUSDT，但是swap不存在 FLOKIUSDT
    # - 结果为 (FLOKIUSDT. 1000FLOKIUSDT)
    symbol_pair_list3 = []
    for _spot in spot_symbol_list:
        _special_swap = f"1000{_spot}"
        if _special_swap in swap_symbol_list:
            symbol_pair_list3.append((_spot, _special_swap))
            special_symbol_with_usdt_dict[
                _spot
            ] = _special_swap  # 缓存到special中，为了简化3.4

    # 3.4 组合剩下的币种，这些要么只有spot或者只有swap，
    # - 比如 spot是 AMPUSDT，没有swap，结果就是 (AMPUSDT, None)
    # - 又比如 swap是 BSVUSDT，没有spot，结果就是 (None, BSVUSDT)
    symbol_pair_list4 = [
        (None, _symbol)
        if _symbol in swap_symbol_list
        else (_symbol, special_symbol_with_usdt_dict.get(_symbol, None))
        for _symbol in all_symbols
        if
        # 去掉 3.1、3.2、3.3还有problems
        _symbol
        not in {
            *same_symbols,
            *special_symbol_with_usdt_dict.keys(),
            *special_symbol_with_usdt_dict.values(),
            *problem_symbols,
        }
    ]
    symbol_pair_list = (
            symbol_pair_list1 + symbol_pair_list2 + symbol_pair_list3 + symbol_pair_list4
    )

    return symbol_pair_list


def read_and_process_data(spot_symbol, swap_symbol, spot_split_info, swap_split_info):
    # 1. 处理swap数据先
    swap_result = dict()
    if swap_symbol is not None:
        swap_result = split_raw_data(swap_path / f"{swap_symbol}.csv", swap_split_info)

    # 2. 处理spot数据
    spot_result = dict()
    if spot_symbol is not None:
        spot_result = split_raw_data(spot_path / f"{spot_symbol}.csv", spot_split_info)
        for exclusive_swap in [
            symbol
            for symbol in SWAP_SPLIT_MAP.get(spot_symbol, [])
            if symbol not in swap_result
        ]:
            swap_result.update(
                split_raw_data(swap_path / f"{exclusive_swap}.csv", swap_split_info)
            )

    # 3. 结合两边的数据进行交叉检查
    for symbol_spot, spot_candle_df in spot_result.items():
        for symbol_swap, swap_candle_df in swap_result.items():
            symbol_swap_df = pd.merge(
                spot_candle_df[["candle_begin_time", "symbol"]],
                swap_candle_df[["candle_begin_time", "symbol"]],
                on="candle_begin_time",
                suffixes=("", "_swap"),
                how="left",
            ).dropna(subset=["symbol_swap"])

            spot_candle_df.loc[symbol_swap_df.index, "symbol_swap"] = symbol_swap

            symbol_spot_df = pd.merge(
                swap_candle_df[["candle_begin_time", "symbol"]],
                spot_candle_df[["candle_begin_time", "symbol"]],
                on="candle_begin_time",
                suffixes=("", "_spot"),
                how="left",
            ).dropna(subset=["symbol_spot"])

            swap_candle_df.loc[symbol_spot_df.index, "symbol_spot"] = symbol_spot

            spot_candle_df["symbol_spot"] = pd.Categorical(
                spot_candle_df["symbol_spot"]
            )
            swap_candle_df["symbol_swap"] = pd.Categorical(
                swap_candle_df["symbol_swap"]
            )

    # tmp output
    for k, v in spot_result.items():
        v.to_csv(
            get_data_file_path(
                "coin-binance-spot-swap-preprocess-pkl-1h", "split", "spot", f"{k}.csv"
            ),
            index=False,
        )

    # tmp output
    for k, v in swap_result.items():
        v.to_csv(
            get_data_file_path(
                "coin-binance-spot-swap-preprocess-pkl-1h", "split", "swap", f"{k}.csv"
            ),
            index=False,
        )
    return spot_result, swap_result


def make_market_pivot(market_dict, market_type="spot"):
    cols = [
        "candle_begin_time",
        "symbol",
        "open",
        "close",
        "funding_fee",
        "avg_price_1m",
    ]
    df_list = [df.loc[:, cols].dropna(subset="symbol") for df in market_dict.values()]
    df_all_market = pd.concat(df_list, ignore_index=True)
    df_all_market["symbol"] = pd.Categorical(df_all_market["symbol"])
    df_open = df_all_market.pivot(
        values="open", index="candle_begin_time", columns="symbol"
    )
    df_close = df_all_market.pivot(
        values="close", index="candle_begin_time", columns="symbol"
    )
    df_vwap1m = df_all_market.pivot(
        values="avg_price_1m", index="candle_begin_time", columns="symbol"
    )
    if market_type == "swap":
        df_rate = df_all_market.pivot(
            values="funding_fee", index="candle_begin_time", columns="symbol"
        )
        df_rate.fillna(value=0, inplace=True)
        return {
            "open": df_open,
            "close": df_close,
            "funding_rate": df_rate,
            "vwap1m": df_vwap1m,
        }
    else:
        return {"open": df_open, "close": df_close, "vwap1m": df_vwap1m}


def generate_data(
        symbol_pair_list: List[
            Union[Tuple[str, str], Tuple[str, None], Tuple[None, str], Tuple[None, None]]
        ],
        split_info: dict,
):
    spot_dict = dict()
    swap_dict = dict()

    with ThreadPoolExecutor(max_workers=njobs) as executor:
        futures = []

        # 提交任务到进程池，保存每个任务的 Future 对象
        for spot_symbol, swap_symbol in symbol_pair_list:
            spot_split_info = split_info["spot"].get(spot_symbol)
            swap_split_info = split_info["swap"].get(swap_symbol)
            future = executor.submit(
                read_and_process_data,
                spot_symbol,
                swap_symbol,
                spot_split_info,
                swap_split_info,
            )
            futures.append(future)

        # 使用 as_completed 函数监控任务完成情况
        for future in tqdm(as_completed(futures), total=len(futures), file=sys.stdout, mininterval=2):
            try:
                spot_result, swap_result = future.result()
                spot_dict.update(spot_result)
                swap_dict.update(swap_result)
            except Exception as e:
                # 捕获和处理任何可能的异常
                logger.error(
                    f"Exception occurred for pair ({spot_symbol}, {swap_symbol}): {e}",
                )

    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)

    pd.to_pickle(spot_dict, output_path / "spot_dict.pkl")
    pd.to_pickle(swap_dict, output_path / "swap_dict.pkl")

    s = time.time()
    logger.info("加载 spot 数据...")
    market_pivot_spot = make_market_pivot(spot_dict, market_type="spot")
    logger.info("加载 swap 数据...")
    market_pivot_swap = make_market_pivot(swap_dict, market_type="swap")
    logger.ok("加载数据完成.({:.2f}s)".format(time.time() - s))

    pd.to_pickle(market_pivot_spot, output_path / "market_pivot_spot.pkl")
    pd.to_pickle(market_pivot_swap, output_path / "market_pivot_swap.pkl")

    logger.ok("数据生成完成，spot_dict 和 swap_dict 已保存。")
    logger.ok(f"保存位置: {output_path}")

    return spot_dict, swap_dict


def preprocess_data():
    logger.info("开始预处理数据...")

    # 读取原始文件信息，并且排除掉一些不希望进入后续选币的币种
    spot_file_list = [
        file
        for file in spot_path.rglob("*-USDT.csv")
        if not file.stem.startswith(".") and is_trade_symbol(file.stem, [])
    ]
    swap_file_list = [
        file
        for file in swap_path.rglob("*-USDT.csv")
        if not file.stem.startswith(".") and is_trade_symbol(file.stem, [])
    ]
    # 从原始数据，结合配置，完成 spot 和 swap 的数据映射
    generate_data(
        map_spot_swap(spot_file_list, swap_file_list),
        process_relist(spot_file_list, swap_file_list),
    )

    logger.ok("数据预处理完成")


if __name__ == "__main__":
    preprocess_data()
