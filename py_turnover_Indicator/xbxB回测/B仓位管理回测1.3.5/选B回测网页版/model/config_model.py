# -*- coding: utf-8 -*-
"""
配置数据模型 - 定义config.py文件的数据结构

回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""

import dataclasses
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import fuel_data_path


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy: str
    offset_list: List[int]
    hold_period: str
    market: str = 'mix_swap'
    cap_weight: float = 1
    long_cap_weight: float = 0
    short_cap_weight: float = 1
    long_select_coin_num: int | tuple = 999
    short_select_coin_num: int | str | tuple = 999
    filter_list: Optional[List[tuple]] = None
    long_filter_list: Optional[List[tuple]] = None
    short_filter_list: Optional[List[tuple]] = None
    factor_list: List[tuple] = None
    long_factor_list: Optional[List[tuple]] = None
    short_factor_list: Optional[List[tuple]] = None
    filter_list_post: Optional[List[tuple]] = None
    long_filter_list_post: Optional[List[tuple]] = None
    short_filter_list_post: Optional[List[tuple]] = None
    use_custom_func: bool = False

    def validate(self) -> List[str]:
        """验证策略配置的有效性"""
        errors = []

        # 验证必填字段
        if not self.strategy:
            errors.append("策略名称(strategy)不能为空")

        if not self.offset_list:
            errors.append("偏移列表(offset_list)不能为空")
        elif not isinstance(self.offset_list, list):
            errors.append("偏移列表(offset_list)必须是列表类型")
        elif not all(isinstance(x, int) for x in self.offset_list):
            errors.append("偏移列表(offset_list)必须包含整数")

        if not self.hold_period:
            errors.append("持有周期(hold_period)不能为空")

        # 验证数值范围
        if self.cap_weight < 0:
            errors.append("资金权重(cap_weight)不能为负数")

        if self.long_cap_weight < 0:
            errors.append("多头资金权重(long_cap_weight)不能为负数")

        if self.short_cap_weight < 0:
            errors.append("空头资金权重(short_cap_weight)不能为负数")

        return errors


@dataclass
class BacktestConfig:
    """完整的回测配置数据模型"""

    # 文件名（不包含.py扩展名）
    name: str

    # ====================================================================================================
    # ** 数据配置 **
    # ====================================================================================================
    pre_data_path: str
    data_source_dict: Dict[str, tuple] = field(default_factory=dict)

    # ====================================================================================================
    # ** 回测策略细节配置 **
    # ====================================================================================================
    start_date: str = '2021-01-01'
    end_date: str = '2025-04-01 23:00:00'

    # ====================================================================================================
    # ** 策略配置 **
    # ====================================================================================================
    backtest_name: str = '策略回测'
    strategy_list: List[StrategyConfig] = field(default_factory=list)

    re_timing: Optional[Dict[str, Any]] = None
    rebalance_mode: Optional[Dict[str, Any]] = None
    min_kline_num: int = 0
    black_list: List[str] = field(default_factory=list)
    white_list: List[str] = field(default_factory=list)

    # ====================================================================================================
    # ** 回测模拟下单配置 **
    # ====================================================================================================
    account_type: str = '普通账户'
    initial_usdt: float = 10000
    leverage: int = 1
    margin_rate: float = 0.05

    swap_c_rate: float = 6 / 10000
    spot_c_rate: float = 1 / 1000

    swap_min_order_limit: int = 5
    spot_min_order_limit: int = 10

    avg_price_col: str = 'avg_price_1m'

    # ====================================================================================================
    # ** 回测全局设置 **
    # ====================================================================================================
    job_num: Optional[int] = None  # 如果为None，将使用 max(os.cpu_count() - 1, 1)
    factor_col_limit: int = 64

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，排除name字段"""
        result = {}
        for key, value in self.__dict__.items():
            if key != 'name':  # 排除name字段，因为它不是config.py的变量
                if key == 'strategy_list':
                    # 将StrategyConfig对象转换为字典
                    result[key] = [strategy_to_dict(strategy) for strategy in value]
                else:
                    result[key] = value
        return result

    def validate(self) -> List[str]:
        """验证配置数据的有效性，返回错误信息列表"""
        errors = []

        # 验证必填字段
        if not self.name:
            errors.append("配置名称(name)不能为空")

        if not self.pre_data_path:
            errors.append("数据路径(pre_data_path)不能为空")

        if not self.backtest_name:
            errors.append("回测名称(backtest_name)不能为空")

        # 验证数值范围
        if self.leverage <= 0:
            errors.append("杠杆(leverage)必须大于0")

        if self.margin_rate <= 0 or self.margin_rate >= 1:
            errors.append("保证金率(margin_rate)必须在0到1之间")

        if self.initial_usdt <= 0:
            errors.append("初始资金(initial_usdt)必须大于0")

        if self.swap_min_order_limit < 5:
            errors.append("合约最小下单量(swap_min_order_limit)不能小于5")

        if self.spot_min_order_limit < 10:
            errors.append("现货最小下单量(spot_min_order_limit)不能小于10")

        if self.factor_col_limit <= 0:
            errors.append("因子列限制(factor_col_limit)必须大于0")

            # 验证策略列表
        if not self.strategy_list:
            errors.append("策略列表(strategy_list)不能为空")

        for i, strategy in enumerate(self.strategy_list):
            if not isinstance(strategy, StrategyConfig):
                errors.append(f"策略列表第{i + 1}项类型错误，应为StrategyConfig")
                continue

            # 验证StrategyConfig对象本身
            strategy_errors = strategy.validate()
            for error in strategy_errors:
                errors.append(f"策略列表第{i + 1}项: {error}")

        return errors


def strategy_to_dict(strategy: StrategyConfig) -> Dict[str, Any]:
    """将StrategyConfig对象转换为字典"""
    return {
        key: value for key, value in strategy.__dict__.items()
        if value is not None  # 排除None值的可选字段
    }


def create_strategy_from_dict(data: Dict[str, Any]) -> StrategyConfig:
    """从字典创建StrategyConfig对象，只保留定义字段"""
    field_names = {f.name for f in dataclasses.fields(StrategyConfig)}
    filtered_data = {}

    # 需要将数组转换为tuple的字段列表
    tuple_fields = {
        'factor_list', 'long_factor_list', 'short_factor_list',
        'filter_list', 'long_filter_list', 'short_filter_list',
        'filter_list_post', 'long_filter_list_post', 'short_filter_list_post'
    }

    for k, v in data.items():
        if k == 'is_use_spot':
            filtered_data['market'] = 'spot_swap' if v else 'swap_swap'

        if k in field_names:
            # 如果是需要转换的字段且值是列表，则将其中的子列表转换为tuple
            if k in tuple_fields and isinstance(v, list):
                filtered_data[k] = [tuple(item) if isinstance(item, list) else item for item in v]
            else:
                filtered_data[k] = v

    return StrategyConfig(**filtered_data)


def create_config_from_dict(data: Dict[str, Any]) -> BacktestConfig:
    """从字典创建配置对象"""
    local_data_path = Path(fuel_data_path)

    # 创建数据副本，避免修改原始数据
    filtered_data = data.copy()
    # 回测数据路径，直接从 config 中获取
    filtered_data['pre_data_path'] = str(local_data_path / 'coin-binance-spot-swap-preprocess-pkl-1h')
    filtered_data['data_source_dict'] = {
        "coin-cap": ('load_coin_cap', str(local_data_path / 'coin-cap'),)
    }

    # 过滤掉不需要保存的字段
    excluded_fields = {'backtest_iter_path', 'backtest_path', 'raw_data_path', 'spot_path', 'swap_path',
                       'stable_symbol'}
    for _field in excluded_fields:
        filtered_data.pop(_field, None)

    # 处理job_num的默认值
    if filtered_data.get('performance_mode') is None:
        if filtered_data.get('job_num') is None:
            filtered_data['job_num'] = max(os.cpu_count() - 1, 1)
    else:
        match filtered_data.get('performance_mode'):
            case 'EQUAL':  # 均衡。使用 1/2 内核
                filtered_data['job_num'] = min(int(os.cpu_count() / 2), 63)
            case 'PERFORMANCE':  # 性能。使用全部内核-1
                filtered_data['job_num'] = min(int(os.cpu_count() - 1), 63)
            case 'ECONOMY':  # 节能。使用 1/3 内核
                filtered_data['job_num'] = min(int(os.cpu_count() / 3), 63)
            case _:
                filtered_data['job_num'] = min(int(os.cpu_count() / 3), 63)
        del filtered_data['performance_mode']

    # 处理strategy_list - 将字典列表转换为StrategyConfig对象列表
    if 'strategy_list' in filtered_data and isinstance(filtered_data['strategy_list'], list):
        strategy_configs = []
        for strategy_dict in filtered_data['strategy_list']:
            if isinstance(strategy_dict, dict):
                strategy_configs.append(create_strategy_from_dict(strategy_dict))
            elif isinstance(strategy_dict, StrategyConfig):
                strategy_configs.append(strategy_dict)
        filtered_data['strategy_list'] = strategy_configs

    # 创建配置对象
    config = BacktestConfig(**filtered_data)

    return config
