import asyncio
import importlib
from datetime import datetime
from functools import partial

import pandas as pd

from core.utils.time import wait_until_ready
from .candle_manager import CandleFileReader


def calc_by_signal_multi_params(module, factor_cls, df_candle, param_list):
    result_dict = module.signal_multi_params(df_candle, param_list)
    # 创建一个新的 DataFrame，列名为 result_dict 的键
    factor_val_df = pd.DataFrame(result_dict)
    # 给新 DataFrame 的列加上前缀
    factor_val_df = factor_val_df.add_prefix(f'{factor_cls}_')
    return factor_val_df


def calc_by_legacy_signal(module, factor_cls, df_candle, param_list):
    param_col_list = []
    legacy_candle_df = df_candle.copy()  # 如果是老的因子计算逻辑，单独拿出来一份数据
    for param in param_list:
        factor_col_name = f'{factor_cls}_{str(param)}'
        param_col_list.append(factor_col_name)
        legacy_candle_df = module.signal(legacy_candle_df, param, factor_col_name)
    return legacy_candle_df[param_col_list]


# 因子计算封装
class MultiFactorCalculator:

    def __init__(self, factor_cls, package):
        factor_module_path = f'{package}.{factor_cls}'
        module = importlib.import_module(factor_module_path)

        # 如果存在 signal_multi_params ，使用最新的因子加速写法
        if hasattr(module, 'signal_multi_params'):
            self.factor_func = partial(calc_by_signal_multi_params, module=module, factor_cls=factor_cls)
        else:
            self.factor_func = partial(calc_by_legacy_signal, module=module, factor_cls=factor_cls)

    def calc(self, df_candle, param_list):
        return self.factor_func(df_candle=df_candle, param_list=param_list)


# 全市场多标的多因子计算器，适用于截面选币类策略
class BmacMultiFactorCalculator:

    def __init__(self,
                 candle_reader: CandleFileReader,
                 keep_rows: int,
                 package: str = 'factors',
                 bmac_expire_sec: int = 60):
        """
        symbol: 标的名称
        candle_reader: K 线存放目录的 CandleFileReader
        keep_rows: 保留行数
        package: 因子包名，默认为 'factors'
        bmac_expire_sec: BMAC 超时时间(秒)，默认 60 秒
        """
        self.candle_reader = candle_reader
        self.bmac_expire_sec = bmac_expire_sec
        self.package = package
        self.keep_rows = keep_rows

    async def calc_all_factors(self, symbol_factors: dict, run_time: datetime) -> pd.DataFrame:
        """
        run_time: 当前周期时间戳
        
        返回值: 包含给定全市场 run_time 周期所有因子的 DataFrame
        """
        symbols = list(symbol_factors.keys())

        factor_calcs = {
            symbol: [(MultiFactorCalculator(factor_cls, self.package), param_list)
                     for factor_cls, param_list in factor_cfgs] for symbol, factor_cfgs in symbol_factors.items()
        }

        tasks = [wait_until_ready(self.candle_reader, s, run_time, self.bmac_expire_sec) for s in symbols]
        symbol_df = dict()
        for t in asyncio.as_completed(tasks):
            wait_result = await t
            if wait_result is None:
                continue
            candle_reader, symbol, ready_time = wait_result
            df_canle = candle_reader.read_candle(symbol)
            calcs = factor_calcs[symbol]

            all_factor_val_list = []
            for factor_calc, param_list in calcs:
                factor_val_df = factor_calc.calc(df_canle, param_list)
                all_factor_val_list.append(factor_val_df)

            kline_with_factor_df = pd.concat((df_canle, *all_factor_val_list), axis=1).tail(self.keep_rows).copy()
            symbol_df[symbol] = kline_with_factor_df

        return symbol_df
