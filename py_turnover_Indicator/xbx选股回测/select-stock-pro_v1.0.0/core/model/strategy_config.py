"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import List, Dict, Callable, Union, Tuple

import numpy as np
import pandas as pd

from config import days_listed

ALLOWED_OFFSETS = [
    '2_0', '2_1', '3_0', '3_1', '3_2', '4_0', '4_1', '4_2', '4_3', '5_0', '5_1', '5_2', '5_3', '5_4',
    '10_0', '10_1', '10_2', '10_3', '10_4', '10_5', '10_6', '10_7', '10_8', '10_9',
    'W_0', 'W_1', 'W_2', 'W_3', 'W_4', '2W_0', '2W_1', '3W_0', '3W_1', '3W_2', '4W_0', '4W_1', '4W_2',
    '4W_3', '5W_0', '5W_1', '5W_2', '5W_3', '5W_4', '6W_0', '6W_1', '6W_2', '6W_3', '6W_4', '6W_5',
    'M_0', 'M_-5', 'W53_0'
]


def filter_series_by_range(series, range_str):
    # 提取运算符和数值
    operator = range_str[:2] if range_str[:2] in ['>=', '<=', '==', '!='] else range_str[0]
    value = float(range_str[len(operator):])

    match operator:
        case '>=':
            return series >= value
        case '<=':
            return series <= value
        case '==':
            return series == value
        case '!=':
            return series != value
        case '>':
            return series > value
        case '<':
            return series < value
        case _:
            raise ValueError(f"Unsupported operator: {operator}")


def get_col_name(factor_name, factor_param):
    if isinstance(factor_param,(tuple, list)):
        factor_param_str = '(' + ','.join(map(str, factor_param)) + ')'
    else:
        factor_param_str = str(factor_param)
    return f'{factor_name}_{factor_param_str}'


# 自定义一个类来保持dict的使用方法，并保证其可哈希，且保证顺序
class HashableDict:
    def __init__(self, data: dict):
        # 将字典按键排序并转为tuple，保证顺序并可哈希
        self.data = tuple(sorted(data.items()))

    def __repr__(self):
        # 使其返回一个类似字典的表示方式
        if isinstance(self.data, tuple):
            return "(" + ",".join(f"{k}={v}" for k, v in self.data) + ")"
        return repr(self.data)

    def __eq__(self, other):
        return self.data == other.data

    def __hash__(self):
        return hash(self.data)

    # 支持通过 [] 方式访问
    def __getitem__(self, key):
        if isinstance(self.data, tuple):
            # 将tuple转换回一个dict来支持按键访问
            dict_data = dict(self.data)
            return dict_data[key]
        else:
            raise TypeError(f"Cannot subscript a {type(self.data)} object")


def parse_param(param) -> Union[tuple, HashableDict, str, int, float, bool, None]:
    # param的类型需要转换为hashable的状态
    if isinstance(param, list):
        param = tuple(param)
    elif isinstance(param, dict):
        param = HashableDict(param)
    elif isinstance(param, (str, int, float, tuple, bool)) or param is None:
        pass
    else:
        raise ValueError(f'不支持的参数类型：{type(param)}')
    return param


@dataclass(frozen=True)
class FactorConfig:
    name: str = 'Bias'  # 选股因子名称
    is_sort_asc: bool = True  # 是否正排序
    param: Union[tuple, HashableDict, str, int, float, bool, None] = 3  # 选股因子参数
    weight: float = 1  # 选股因子权重

    @classmethod
    def parse_config_list(cls, config_list: List[tuple]):
        all_long_factor_weight = sum([factor[3] for factor in config_list])
        factor_list = []
        for factor_name, is_sort_asc, param, weight in config_list:
            new_weight = weight / all_long_factor_weight
            # param的类型需要转换为hashable的状态
            param = parse_param(param)
            factor_list.append(cls(name=factor_name, is_sort_asc=is_sort_asc, param=param, weight=new_weight))
        return factor_list

    @cached_property
    def col_name(self):
        return get_col_name(self.name, self.param)

    def __repr__(self):
        return f'{self.col_name}{"↑" if self.is_sort_asc else "↓"}#权重:{self.weight}'

    def to_tuple(self):
        return self.name, self.is_sort_asc, self.param, self.weight


def calc_factor_common(df, factor_list: List[FactorConfig]):
    factor_val = np.zeros(df.shape[0])
    for factor_config in factor_list:
        # 计算单个因子的排名
        _rank = df.groupby('交易日期')[factor_config.col_name].rank(ascending=factor_config.is_sort_asc, method='min')
        # 将因子按照权重累加
        factor_val += _rank * factor_config.weight
    return factor_val


@dataclass(frozen=True)
class FilterMethod:
    how: str = ''  # 过滤方式
    range: str = ''  # 过滤值

    def __repr__(self):
        match self.how:
            case 'rank':
                name = '排名'
            case 'pct':
                name = '排名百分比'
            case 'val':
                name = '数值'
            case _:
                raise ValueError(f'不支持的过滤方式：`{self.how}`')

        return f'{name}:{self.range}'

    def to_val(self):
        return f'{self.how}:{self.range}'


@dataclass(frozen=True)
class FilterFactorConfig:
    name: str = 'Bias'  # 选股因子名称
    param: Union[tuple, HashableDict, str, int, float, bool, None] = 3  # 选股因子参数
    method: FilterMethod = None  # 过滤方式
    is_sort_asc: bool = True  # 是否正排序

    def __repr__(self):
        _repr = self.col_name
        if self.method:
            _repr += f'{"↑" if self.is_sort_asc else "↓"}#{self.method}'
        return _repr

    @cached_property
    def col_name(self):
        return get_col_name(self.name, self.param)

    @classmethod
    def init(cls, filter_factor: tuple):
        # 仔细看，结合class的默认值，这个和默认策略中使用的过滤是一模一样的
        config = dict(name=filter_factor[0], param=parse_param(filter_factor[1]))
        if len(filter_factor) > 2:
            # 可以自定义过滤方式
            _how, _range = re.sub(r'\s+', '', filter_factor[2]).split(':')
            config['method'] = FilterMethod(how=_how, range=_range)
        if len(filter_factor) > 3:
            # 可以自定义排序
            config['is_sort_asc'] = filter_factor[3]
        return cls(**config)

    def to_tuple(self, full_mode=False):
        if full_mode:
            return self.name, self.param, self.method.to_val(), self.is_sort_asc
        else:
            return self.name, self.param


def filter_common(df, filter_list):
    condition = pd.Series(True, index=df.index)

    for filter_config in filter_list:
        col_name = f'{filter_config.name}_{str(filter_config.param)}'
        match filter_config.method.how:
            case 'rank':
                rank = df.groupby('交易日期')[col_name].rank(ascending=filter_config.is_sort_asc, pct=False)
                condition = condition & filter_series_by_range(rank, filter_config.method.range)
            case 'pct':
                rank = df.groupby('交易日期')[col_name].rank(ascending=filter_config.is_sort_asc, pct=True)
                condition = condition & filter_series_by_range(rank, filter_config.method.range)
            case 'val':
                condition = condition & filter_series_by_range(df[col_name], filter_config.method.range)
            case _:
                raise ValueError(f'不支持的过滤方式：{filter_config.method.how}')

    return condition


@dataclass
class StrategyConfig:
    name: str = 'Strategy'

    # 持仓周期。
    hold_period: str = 'W'

    # 持仓周期的参数，比如offset
    offset_list: Tuple[int] = (0,)

    # 策略权重
    cap_weight: float = 1.

    # 原始数据的周期。
    candle_period: str = 'D'

    # 选股数量。1 表示一个股票; 0.1 表示做多10%的股票
    select_num: int or float = 0.1

    # ** 换仓时间 **
    # 选股日换仓的时候，我们可以自定义换仓的时间点
    # - 'close-open'：选股日收盘前卖出，交易日开盘后买入（隔日换仓）；
    # - 'open'：交易日开盘后先卖出，交易日开盘后再买入（日内早盘）；
    # - 'close'：选股日收盘前卖出，选股日收盘前再买入（日内尾盘）；
    # 默认是 'close-open'，表示收盘买，下个开盘买，即隔日换仓
    rebalance_time: str = 'close-open'

    # 因子列名。
    factor_name: str = '复合因子'  # 因子：表示使用复合因子，默认是 factor_list 里面的因子组合。需要修改 calc_factor 函数配合使用

    factor_list: List[FactorConfig] = field(default_factory=list)  # 因子名（和factors文件中相同），排序方式，参数，权重。

    filter_list: List[FilterFactorConfig] = field(default_factory=list)  # 因子名（和factors文件中相同），参数

    # 策略函数
    funcs: Dict[str, Callable] = field(default_factory=dict)

    @cached_property
    def period_type(self) -> str:
        return self.hold_period[-1]

    @cached_property
    def period_num(self) -> int:
        num_str = self.hold_period[:-1]

        if num_str.isnumeric():
            return int(num_str)
        else:
            return 1

    @cached_property
    def hold_period_name_list(self) -> List[str]:
        match self.period_type:
            case 'D':
                period_prefix = f'{self.period_num}_'
            case 'M':
                period_prefix = f'M_'
            case _:
                period_prefix = f'{self.hold_period}_'

        if period_prefix.startswith('1W_'):
            period_prefix = period_prefix.replace('1W_', 'W_')
        return [f'{period_prefix}{offset}' for offset in self.offset_list]

    @cached_property
    def hold_period_name(self) -> str:
        return ','.join(self.hold_period_name_list)

    @cached_property
    def factor_columns(self) -> List[str]:
        factor_columns = set()  # 去重

        # 针对当前策略的因子信息，整理之后的列名信息，并且缓存到全局
        for factor_config in self.factor_list:
            # 策略因子最终在df中的列名
            factor_columns.add(factor_config.col_name)  # 添加到当前策略缓存信息中

        # 针对当前策略的过滤因子信息，整理之后的列名信息，并且缓存到全局
        for filter_factor in self.filter_list:
            # 策略过滤因子最终在df中的列名
            factor_columns.add(filter_factor.col_name)  # 添加到当前策略缓存信息中

        return list(factor_columns)

    @cached_property
    def all_factors(self) -> set:
        all_factors = set()
        for factor_config in self.factor_list:
            all_factors.add(factor_config)
        for filter_factor in self.filter_list:
            all_factors.add(filter_factor)
        return all_factors

    @classmethod
    def init(cls, index: int, **config):
        config['factor_list'] = FactorConfig.parse_config_list(config.get('factor_list', []))
        config['filter_list'] = [FilterFactorConfig.init(filter_config) for filter_config in
                                 config.get('filter_list', [])]
        stg_conf = cls(**config)

        stg_conf.name = f'#{index}.{stg_conf.name}'

        return stg_conf

    def __repr__(self):
        return f"{self.name}，周期{self.hold_period_name}，{self.select_num}个票，因子{self.factor_list}，过滤{self.filter_list}，{self.trade_mode_name()}"

    def trade_mode_name(self):
        match self.rebalance_time:
            case 'close-open':
                return '隔日换仓'
            case 'close':
                return '日内尾盘'
            case 'open':
                return '日内早盘'
            case _:
                sell_time, buy_time = self.rebalance_time.split('-')
                return '自定义换仓({}卖{}买)'.format(sell_time, buy_time)

    def max_int_param(self) -> int:
        max_int = 0
        for factor_config in self.all_factors:
            if isinstance(factor_config.param, int):
                max_int = max(max_int, factor_config.param)
        return max_int

    def filter_before_select(self, period_df):
        if 'filter_stock' in self.funcs:
            return self.funcs['filter_stock'](period_df, self)

        # 通用的filter筛选
        # =删除不能交易的周期数
        # 删除月末为st状态的周期数
        cond1 = ~period_df['股票名称'].str.contains('ST', regex=False)
        # 删除月末为s状态的周期数
        cond2 = ~period_df['股票名称'].str.contains('S', regex=False)
        # 删除月末有退市风险的周期数
        cond3 = ~period_df['股票名称'].str.contains('*', regex=False)
        cond4 = ~period_df['股票名称'].str.contains('退', regex=False)
        # 删除交易天数过少的周期数
        # cond5 = period_df['交易天数'] / period_df['市场交易天数'] >= 0.8

        cond6 = period_df['下日_是否交易'] == 1
        cond7 = period_df['下日_开盘涨停'] != 1
        cond8 = period_df['下日_是否ST'] != 1
        cond9 = period_df['下日_是否退市'] != 1
        cond10 = period_df['上市至今交易天数'] > days_listed

        # common_filter = cond1 & cond2 & cond3 & cond4 & cond5 & cond6 & cond7 & cond8 & cond9 & cond10
        common_filter = cond1 & cond2 & cond3 & cond4 & cond6 & cond7 & cond8 & cond9 & cond10
        period_df = period_df[common_filter]

        filter_condition = filter_common(period_df, self.filter_list)

        return period_df[filter_condition]

    def calc_select_factor(self, period_df):
        if 'calc_select_factor' in self.funcs:
            return self.funcs['calc_select_factor'](period_df, self)
        period_df[self.factor_name] = self.calc_select_factor_default(period_df)
        return period_df

    def calc_select_factor_default(self, period_df):
        return calc_factor_common(period_df, self.factor_list)
