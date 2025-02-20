"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import json
import shutil
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
import pytz

from config import backtest_path, backtest_iter_path, strategy_name, utc_offset, data_config
from core.factor import calc_factor_vals
from core.model.rebalance_mode import RebalanceMode
from core.model.strategy_config import StrategyConfig, PosStrategyConfig
from core.model.timing_signal import TimingSignal
from core.utils.log_kit import logger
from core.utils.path_kit import get_folder_path, get_file_path
from core.utils.strategy_hub import StrategyHub


class BacktestConfig:
    data_file_fingerprint: str = ''  # 记录数据文件的指纹

    def __init__(self, name: str, **conf):
        self.name: str = name  # 账户名称，建议用英文，不要带有特殊符号

        # 账户回测交易模拟配置
        self.rebalance_mode: RebalanceMode = RebalanceMode.init(conf.get('rebalance_mode', None))
        self.leverage: int | float = conf.get("leverage", 1)  # 杠杆数。我看哪个赌狗要把这里改成大于1的。高杠杆如梦幻泡影。不要想着一夜暴富，脚踏实地赚自己该赚的钱。

        self.avg_price_col: str = conf.get("avg_price_col", 'avg_price_1m')  # 平均成交价格
        self.initial_usdt: int | float = conf.get("initial_usdt", 10000)  # 初始现金
        self.margin_rate = conf.get('margin_rate', 0.05)  # 维持保证金率，净值低于这个比例会爆仓

        self.swap_c_rate: float = conf.get("swap_c_rate", 6e-4)  # 合约买卖手续费
        self.spot_c_rate: float = conf.get("spot_c_rate", 2e-3)  # 现货买卖手续费

        self.swap_min_order_limit: int | float = conf.get("swap_min_order_limit", 5)  # 合约最小下单量
        self.spot_min_order_limit: int | float = conf.get("spot_min_order_limit", 10)  # 现货最小下单量

        self.unified_time: str = conf.get('unified_time', '2017-01-01')  # 计算 offset，对齐资金曲线的统一时间

        # 策略配置
        # 拉黑名单，永远不会交易。不喜欢的币、异常的币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
        self.black_list: List[str] = conf.get('black_list', []) + self.load_delist()
        # 如果不为空，即只交易这些币，只在这些币当中进行选币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
        self.white_list: List[str] = conf.get('white_list', [])
        self.min_kline_num: int = conf.get('min_kline_num', 168)  # 最少上市多久，不满该K线根数的币剔除，即剔除刚刚上市的新币。168：标识168个小时，即：7*24

        # 根据加载的策略，自动区分多头，空头，多空
        # Long Short Neutral
        self.strategy_type: str = 'Neutral'

        # 再择时配置
        self.timing: Optional[TimingSignal] = None

        self.is_use_spot: bool = False  # 是否包含现货策略
        self.is_day_period: bool = False  # 是否是日盘，否则是小时盘
        self.is_hour_period: bool = False  # 是否是小时盘，否则是日盘
        self.factor_params_dict: Dict[str, set] = {}
        self.factor_col_name_list: List[str] = []
        self.max_hold_period: str = '1H'  # 最大的持仓周期，默认值设置为最小
        self.hold_period_list: List[str] = []  # 持仓周期列表
        self.max_offset_len: int = 0

        # 策略列表，包含每个策略的详细配置
        self.strategy_list: List[StrategyConfig] = []
        self.strategy_name_list: List[str] = []
        self.strategy_list_raw: List[dict] = []

        # 策略评价
        self.report: Optional[pd.DataFrame] = None
        self.reserved_cache: set = conf.get('reserved_cache', set())  # 缓存控制

        # 遍历标记
        self.iter_round: int | str = 0  # 遍历的INDEX，0表示非遍历场景，从1、2、3、4、...开始表示是第几个循环，当然也可以赋值为具体名称

        # 是否含有快照。默认没有快照。
        # 如果存在快照，表示是增量更新
        # 如果不存在快照，表示是全量更新
        self.has_snapshot = False

    def __repr__(self):
        return f"""{'+' * 56}
# {self.name} 配置信息如下：
+ 手续费: 合约{self.swap_c_rate * 100:.2f}%，现货{self.spot_c_rate * 100:.2f}%
+ 杠杆: {self.leverage:.2f}
+ 最小K线数量: {self.min_kline_num}
+ 维持保证金率: {self.margin_rate * 100:.2f}%
+ 拉黑名单: {self.black_list}，只交易名单: {self.white_list}
+ Rebalance 模式: {self.rebalance_mode}
+ 再择时: {self.timing}
{''.join([str(item) for item in self.strategy_list])}
{'+' * 56}
"""

    @staticmethod
    def load_delist() -> list:
        """
        加载delist数据，动态处理黑名单
        """
        delist_path = get_file_path('data', 'delist.json', as_path_type=True)

        if delist_path.exists() is False:
            return []

        try:
            with open(delist_path, 'r') as file:
                de_list = json.load(file)['list']
            return [_ for _ in de_list if _.endswith('USDT')]  # 获取USDT结尾的币种
        except Exception as e:
            print(e)
            return []


    @property
    def hold_period_type(self):
        return 'D' if self.is_day_period else 'H'

    @property
    def is_pure_long(self):
        no_short = all([(stg.short_cap_weight == 0 or stg.short_select_coin_num == 0) for stg in self.strategy_list])
        return self.is_use_spot and no_short

    def info(self):
        # 输出一下配置信息
        logger.debug(self)

    @staticmethod
    def get_kline_num():
        return data_config.get('get_kline_num', 999)

    def get_fullname(self, as_folder_name=False):
        fullname_list = [self.name]
        for stg in self.strategy_list:
            fullname_list.append(f"{stg.get_fullname(as_folder_name)}")

        if self.timing:
            fullname_list.append(f'再择时:{self.timing}')

        fullname = ' '.join(fullname_list)
        return f'{self.name}' if as_folder_name else fullname

    def load_strategy_config(self, strategy_list: list | tuple, re_timing_config=None):
        import config as default_config

        self.strategy_list_raw = strategy_list
        # 所有策略中的权重
        all_cap_weight = sum(item["cap_weight"] for item in strategy_list)

        for index, stg_dict in enumerate(strategy_list):
            # 更新策略权重
            name = stg_dict['strategy']

            strategy = StrategyConfig.init(index, file=StrategyHub.get_by_name(name), **stg_dict)

            offset_list = list(filter(lambda x: x < strategy.period_num, strategy.offset_list))
            if len(offset_list) != len(strategy.offset_list):
                logger.warning(
                    f'策略{strategy.name}的offset_list设置有问题，自动裁剪。原始值：{strategy.offset_list},裁剪后：{offset_list}')
            strategy.offset_list = offset_list
            strategy.cap_weight = strategy.cap_weight / all_cap_weight

            if strategy.is_day_period:
                self.is_day_period = True
            else:
                self.is_hour_period = True

            # 缓存持仓周期的事情
            if strategy.hold_period not in self.hold_period_list:
                self.hold_period_list.append(strategy.hold_period)
                # 更新最大的持仓周期
                if pd.to_timedelta(self.max_hold_period) < pd.to_timedelta(strategy.hold_period):
                    self.max_hold_period = strategy.hold_period

            self.is_use_spot = self.is_use_spot or strategy.is_use_spot
            if self.is_use_spot and self.leverage >= 2:
                logger.error(f'现货策略不支持杠杆大于等于2的情况，请重新配置')
                exit(1)

            if strategy.long_select_coin_num == 0 and (strategy.short_select_coin_num == 0 or
                                                       strategy.short_select_coin_num == 'long_nums'):
                logger.warning('策略中的选币数量都为0，忽略此策略配置')
                continue

            self.strategy_list.append(strategy)
            self.strategy_name_list.append(strategy.name)
            self.factor_col_name_list += strategy.factor_columns

            # 针对当前策略的因子信息，整理之后的列名信息，并且缓存到全局
            for factor_config in strategy.all_factors:
                # 添加到并行计算的缓存中
                if factor_config.name not in self.factor_params_dict:
                    self.factor_params_dict[factor_config.name] = set()
                self.factor_params_dict[factor_config.name].add(factor_config.param)

            if len(strategy.offset_list) > self.max_offset_len:
                self.max_offset_len = len(strategy.offset_list)

        has_long = any(
            stg.long_select_coin_num > 0 and stg.long_cap_weight > 0
            for stg in self.strategy_list
        )
        has_short = any(
            (stg.short_select_coin_num == 'long_nums' or stg.short_select_coin_num > 0) and stg.short_cap_weight > 0
            for stg in self.strategy_list
        )

        if has_long and not has_short:
            self.strategy_type = 'Long'
        elif has_short and not has_long:
            self.strategy_type = 'Short'
        elif has_long and has_short:
            self.strategy_type = 'Neutral'

        self.factor_col_name_list = list(set(self.factor_col_name_list))

        if all((self.is_hour_period, self.is_day_period)):
            logger.critical(f'策略中同时存在小时线和日线的策略融合，请检查配置')
            exit()

        if default_config.is_pure_long:
            if self.is_pure_long and self.is_use_spot:
                logger.debug(f'👌 [{self.name}] 成功启动纯多模式')
            else:
                logger.critical(f'[{self.name}] 包含空头的策略和合约交易，纯多模式下不允许使用含合约的策略，请检查配置')
                exit()

        if re_timing_config:
            self.timing = TimingSignal(**re_timing_config)

    @classmethod
    def init_from_config(cls, load_strategy_list: bool = True) -> "BacktestConfig":
        import config

        backtest_config = cls(
            # ** 策略配置 **
            config.strategy_name,
            rebalance_mode=getattr(config, 'rebalance_mode', None),  # rebalance类型
            leverage=config.leverage,  # 杠杆
            black_list=[item.replace('-', '') for item in config.black_list],  # 拉黑名单
            white_list=[item.replace('-', '') for item in config.white_list],  # 只交易名单
            # ** 数据参数 **
            min_kline_num=config.data_config['min_kline_num'],  # 最小K线数量，k线数量少于这个数字的部分不会计入计算
            reserved_cache=set(config.data_config['reserved_cache']),  # 预留缓存文件类型，可以控制磁盘占用
            # ** 交易配置 **
            initial_usdt=config.simulator_config['initial_usdt'],  # 初始usdt
            margin_rate=config.simulator_config['margin_rate'],  # 维持保证金率
            swap_c_rate=config.simulator_config['swap_c_rate'],  # 合约买入手续费
            spot_c_rate=config.simulator_config['spot_c_rate'],  # 现货买卖手续费
            spot_min_order_limit=config.simulator_config['spot_min_order_limit'],  # 现货最小下单量
            swap_min_order_limit=config.simulator_config['swap_min_order_limit'],  # 合约最小下单量
            avg_price_col=config.simulator_config['avg_price_col'],  # 平均价格列名
            unified_time=config.simulator_config['unified_time'],  # 对齐 offset 和资金曲线的统一时间
        )

        # ** 策略配置 **
        # 初始化策略，默认都是需要初始化的
        if load_strategy_list and hasattr(config, 'strategy_list'):
            re_timing_config = getattr(config, 're_timing', None)  # 从config中读取选币再择时的策略配置
            backtest_config.load_strategy_config(config.strategy_list, re_timing_config)

        return backtest_config

    def set_report(self, report: pd.DataFrame):
        report['param'] = self.get_fullname()
        self.report = report

    def get_result_folder(self) -> Path:
        if self.iter_round == 0:
            return get_folder_path(backtest_path, self.get_fullname(as_folder_name=True), as_path_type=True)
        else:
            config_name = f'策略组_{self.iter_round}' if isinstance(self.iter_round, int) else self.iter_round
            if self.name.startswith(f'S{self.iter_round}'):
                config_name = self.name
            return get_folder_path(backtest_iter_path, strategy_name, config_name, as_path_type=True)

    def get_snapshot_folder(self) -> Path:
        if self.iter_round == 0:
            return get_folder_path('data', 'snapshot', self.get_fullname(as_folder_name=True), as_path_type=True)
        else:
            config_name = f'策略组_{self.iter_round}' if isinstance(self.iter_round, int) else self.iter_round
            if self.name.startswith(f'S{self.iter_round}'):
                config_name = self.name
            return get_folder_path('data', 'snapshot', strategy_name, config_name, as_path_type=True)

    def get_strategy_config_sheet(self, with_factors=True) -> dict:
        factor_dict = {}
        for stg in self.strategy_list:
            for attr_in in ['hold_period', 'is_use_spot', 'offset_list', 'cap_weight']:
                if attr_in not in factor_dict:
                    factor_dict[attr_in] = []
                factor_dict[attr_in].append(getattr(stg, attr_in))

            for factor_config in stg.all_factors:
                _name = f'#FACTOR-{factor_config.name}'
                _val = factor_config.param
                if _name not in factor_dict:
                    factor_dict[_name] = []
                factor_dict[_name].append(_val)
        ret = {
            '策略': self.name,
            'fullname': self.get_fullname(),
        }
        if with_factors:
            ret.update(**{
                k: "_".join(map(str, v)) for k, v in factor_dict.items()
            })

        if self.timing:
            ret['再择时'] = str(self.timing)
        return ret

    def save(self):
        pd.to_pickle(self, self.get_result_folder() / 'config.pkl')

    def delete_cache(self):
        shutil.rmtree(self.get_result_folder())

    def is_reserved(self, item: str) -> bool:
        if 'all' in self.reserved_cache:
            return True
        return item in self.reserved_cache

    def get_final_equity_path(self):
        has_timing_signal = isinstance(self.timing, TimingSignal)
        if has_timing_signal:
            filename = '资金曲线_再择时.csv'
        else:
            filename = '资金曲线.csv'
        final_equity_path = self.get_result_folder() / filename
        return final_equity_path


class BacktestConfigFactory:
    """
    遍历参数的时候，动态生成配置
    """
    STRATEGY_FACTOR_ATTR = [
        'factor_list',
        'long_factor_list',
        'short_factor_list',
        'filter_list',
        'long_filter_list',
        'short_filter_list',
        'filter_list_post',
        'long_filter_list_post',
        'short_filter_list_post',
    ]

    def __init__(self, **conf):
        # ====================================================================================================
        # ** 参数遍历配置 **
        # 可以指定因子遍历的参数范围
        # ====================================================================================================
        self.factor_param_range_dict: dict = conf.get("factor_param_range_dict", {})
        self.strategy_param_range_dict: dict = conf.get("strategy_param_range_dict", {})
        self.default_param_range = conf.get("default_param_range", [])
        self.backtest_name = conf.get("backtest_name", strategy_name)

        if not self.backtest_name:
            self.backtest_name = f'默认策略-{datetime.now().strftime("%Y%m%dT%H%M%S")}'

        # 缓存全局配置
        self.is_use_spot = conf.get("is_use_spot", False)
        self.black_list = conf.get("black_list", set())

        # 存储生成好的config list和strategy list
        self.config_list: List[BacktestConfig] = []
        logger.debug(f'ℹ️ 名称：{self.backtest_name}')
        logger.debug(f'🗺️ 子策略结果：{self.result_folder}')

    @classmethod
    def init(cls, **conf):
        return cls(
            factor_param_range_dict=conf.get("factor_param_range_dict", {}),
            strategy_param_range_dict=conf.get("strategy_param_range_dict", {}),
            default_param_range=conf.get("default_param_range", []),
            backtest_name=conf.get("backtest_name", strategy_name),
        )

    @property
    def result_folder(self) -> Path:
        return get_folder_path(backtest_iter_path, self.backtest_name, as_path_type=True)

    def update_meta_by_config(self, config: BacktestConfig):
        """
        # 缓存是否使用现货等状态
        :param config: 生成的配置信息
        :return: None
        """
        self.is_use_spot = self.is_use_spot or config.is_use_spot
        self.black_list = self.black_list | set(config.black_list)

    def get_candidates_by_factors(self, strategy_dict, param_name, target_factors, val_index) -> List[tuple]:
        """
        根据指定的因子，获取所有的排列组合
        :param strategy_dict:
        :param param_name:
        :param target_factors:
        :param val_index:
        :return:
        """
        if param_name in ('factor_list', 'filter_list', 'filter_list_post'):
            if f'long_{param_name}' in strategy_dict or f'short_{param_name}' in strategy_dict:
                # 如果设置过的话，默认单边是挂空挡
                legacy_strategy = None
            else:
                legacy_strategy = StrategyHub.get_by_name(strategy_dict['strategy'])
        else:
            legacy_strategy = StrategyHub.get_by_name(strategy_dict['strategy'])

        factor_tuple_list = strategy_dict.get(param_name,
                                              getattr(legacy_strategy, param_name, []) if legacy_strategy else [])
        """
        Step4: 构建选币因子的范围
        """
        factor_param_range = {}

        for factor_tuple in factor_tuple_list:
            factor_name = factor_tuple[0]

            if target_factors is None or factor_name in target_factors:
                factor_param_range[factor_name] = []
                for factor_val in self.factor_param_range_dict.get(factor_name, self.default_param_range):
                    factor_param = factor_tuple[:val_index] + (factor_val,) + factor_tuple[val_index + 1:]
                    factor_param_range[factor_name].append(factor_param)
            else:
                factor_param_range[factor_name] = [factor_tuple]
        if factor_param_range:
            return list(product(*factor_param_range.values()))
        else:
            return []

    def generate_combinations_by_strategy(self, strategy_dict: dict, target_factors: List[str] = None) -> List[dict]:
        """
        根据策略配置，和范围配置，生成指定策略的所有可能性
        :param strategy_dict: 策略配置
        :param target_factors: 指定的目标因子
        :return: 策略的所有可能性
        """
        """
        Step1: 把默认配置转成一个参数范围，范围内只有1个默认值。所有可能性只有1个，即原策略
        """
        strategy_param_range = {
            **{
                k: [v] for k, v in strategy_dict.items() if k != 'strategy'
            },  # 默认config转成list
        }
        """
        Step2: 构建选币因子的范围
        """
        for factor_attr in self.STRATEGY_FACTOR_ATTR:
            val_index = 1 if 'filter' in factor_attr else 2  # 格式不行一样
            candidates = self.get_candidates_by_factors(strategy_dict, factor_attr, target_factors, val_index)
            if candidates:
                strategy_param_range[factor_attr] = candidates
        """
        Step3: 更新默认配置
        - 情况1: 如果设置了 `target_factor`，我们只会循环遍历该因子。其余配置使用默认配置
        - 情况2: 如果没有设置，即需要循环所有可能性。所以我们会用策略配置好的范围，覆盖默认的范围（单参数模式）
        """
        """
        Step4: 根据策略的 strategy_param_range，生成所有的可能的配置
        """
        strategy_combinations = [
            dict(zip(strategy_param_range.keys(), combination), strategy=strategy_dict['strategy'])
            for combination in product(*strategy_param_range.values())
        ]
        return strategy_combinations

    def generate_configs(self, target_factors: list | tuple = None) -> List[BacktestConfig]:
        """
        根据配置的dict和默认的参数列表，自动生成所有的遍历参数组合
        :param target_factors: 可选变量，如果填写了的话，可以只针对这个变量遍历。其他的因子参数都使用策略默认值
        :return: BacktestConfig 的列表
        """
        """
        # Step1: 针对配置中每一个子策略，都生成所有的可能性，并且存档在 strategy_combinations_list 中
        """
        import config
        # 我们启用了大杂烩的支持，因此需要考虑多个子策略的情况
        strategy_combinations_list = []

        # 循环大杂烩中所有的子策略
        for strategy_dict in getattr(config, 'strategy_list', []):
            # 根据参数，生成单子策略的所有的组合
            strategy_combinations = self.generate_combinations_by_strategy(strategy_dict, target_factors)
            strategy_combinations_list.append(strategy_combinations)
        """
        # Step2: 把 strategy_combinations_list 转换为 我们要的策略组合模式
        把一个这样的数据结构
        `[[策略1的组合1, 策略1的组合2], [策略2的组合1, 策略2的组合2, 策略2的组合3]]`
        生成如下结果:
        [
          [策略1的组合1, 策略2的组合1], [策略1的组合1, 策略2的组合2], [策略1的组合1, 策略2的组合3],
          [策略1的组合2, 策略2的组合1], [策略1的组合2, 策略2的组合2], [策略1的组合2, 策略2的组合3]
        ]
        也就是 [strategy_list可能性1, strategy_list可能性2, ...]
        """
        strategy_list_combinations = list(product(*strategy_combinations_list))
        """
        # Step3: 根据所有可能的strategy list，生成所有的backtest_config
        """
        config_list: List[BacktestConfig] = []
        for index, strategy_list in enumerate(strategy_list_combinations):
            # 加载默认配置
            backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
            backtest_config.iter_round = index + 1
            # 使用指定的 strategy list 配置进行策略初始化
            backtest_config.load_strategy_config(strategy_list)
            if len(backtest_config.strategy_list) == 0:
                logger.critical('没有合法的策略，无法启动回测，跳过')
                continue

            self.update_meta_by_config(backtest_config)

            config_list.append(backtest_config)

        self.config_list = config_list

        return self.config_list

    def generate_long_and_short_configs(self) -> List[BacktestConfig]:
        """
        纯多/纯空的配置，用于多空曲线的计算
        :return:
        """
        import config

        long_short_strategy_list = []
        pure_long_strategy_list = []
        pure_short_strategy_list = []
        for strategy_dict in getattr(config, 'strategy_list', []):
            strategy_cfg = strategy_dict.copy()
            long_strategy_cfg = {**strategy_dict, **{'long_cap_weight': 1, 'short_cap_weight': 0}}
            short_strategy_cfg = {**strategy_dict, **{'long_cap_weight': 0, 'short_cap_weight': 1}}

            long_short_strategy_list.append(strategy_cfg)
            pure_long_strategy_list.append(long_strategy_cfg)
            pure_short_strategy_list.append(short_strategy_cfg)

        config_list: List[BacktestConfig] = []
        for stg, suffix in zip([long_short_strategy_list, pure_long_strategy_list, pure_short_strategy_list],
                               ['多空模拟', '纯多模拟', '纯空模拟']):
            backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
            backtest_config.load_strategy_config(stg)
            if len(backtest_config.strategy_list) == 0:
                logger.critical(f'【{suffix}场景】没有生成有效的子策略回测回测，可能所有选币都被重置为0，跳过')
                continue
            backtest_config.name = self.backtest_name
            backtest_config.iter_round = suffix

            self.update_meta_by_config(backtest_config)

            config_list.append(backtest_config)

        self.config_list = config_list

        return self.config_list

    def generate_configs_by_factor(self, *target_factors) -> List[BacktestConfig]:
        """
        生成单因子的配置，用于参数平原计算
        :param target_factors: 因子的名称
        :return:
        """
        return self.generate_configs(target_factors)

    def generate_all_factor_config(self):
        backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
        strategy_list = []
        for conf in self.config_list:
            strategy_list.extend(conf.strategy_list_raw)
        backtest_config.load_strategy_config(strategy_list)
        return backtest_config

    def get_name_params_sheet(self) -> pd.DataFrame:
        rows = []
        for config in self.config_list:
            rows.append(config.get_strategy_config_sheet())

        sheet = pd.DataFrame(rows)
        sheet.to_excel(self.config_list[-1].get_result_folder().parent / '策略回测参数总表.xlsx', index=False)
        return sheet

    def generate_configs_by_strategies(self, strategies, re_timing_strategies=None) -> List[BacktestConfig]:
        config_list = []
        iter_round = 0

        if not re_timing_strategies:
            re_timing_strategies = [None]

        for strategy_list, re_timing_config in product(strategies, re_timing_strategies):
            iter_round += 1
            backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
            if self.backtest_name:
                backtest_config.name = self.backtest_name
            backtest_config.load_strategy_config(strategy_list, re_timing_config)
            backtest_config.iter_round = iter_round

            self.update_meta_by_config(backtest_config)

            config_list.append(backtest_config)

        self.config_list = config_list

        return config_list

    def generate_configs_by_strategies_with_timing(self, strategies: List[dict]) -> List[BacktestConfig]:
        config_list = []
        iter_round = 0

        for strategy in strategies:
            iter_round += 1
            backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
            if 'name' in strategy:
                backtest_config.name = f"S{iter_round}-{strategy['name']}"
            else:
                backtest_config.name = f"S{iter_round}-{self.backtest_name}"
            # 再择时的功能是可选的，并不是所有的选币策略都要配套
            backtest_config.load_strategy_config(strategy['strategy_list'], strategy.get('re_timing', None))
            backtest_config.iter_round = iter_round

            self.update_meta_by_config(backtest_config)

            config_list.append(backtest_config)

        self.config_list = config_list

        return config_list


class MultiEquityBacktestConfig:
    import config as default_config  # 获取config
    pos_ratio_precision = 9  # 仓位比例的精度

    def __init__(
            self,
            name: str = default_config.strategy_name,
            strategy_config: dict = default_config.strategy_config,
            strategies: List[dict] = default_config.strategy_pool
    ):
        # 初始化仓位管理策略
        self.strategy: PosStrategyConfig = PosStrategyConfig(**strategy_config)
        self.strategy.load()  # 加载对应的策略实现

        # 初始化策略工厂
        if self.default_config.is_pure_long:
            logger.debug('🔵 纯多模式: YES')
        else:
            logger.debug('🟡 纯多模式: NO，（多空模式）')
        self.factory: BacktestConfigFactory = BacktestConfigFactory.init(backtest_name=name)
        self.factory.generate_configs_by_strategies_with_timing(strategies)

        # 因为后续我们需要ratio选币，所以要配置一下
        for conf in self.factory.config_list:
            conf.reserved_cache.add('ratio')

        # 运行过程中的中间变量们
        self.equity_dfs = []
        self.ratio_dfs = []
        self.start_time = None
        self.end_time = None

    def transfer_equity_period(self, equity_df: pd.DataFrame, hour_offset: str = '0m',
                               unified_time: str = '2017-01-01') -> pd.DataFrame:
        """
        把资金曲线的周期转换为策略的周期
        :param equity_df: 资金曲线
        :param hour_offset: 实盘配置中的分钟偏移
        :param unified_time: 对齐 offset 和资金曲线的统一时间
        :return: 合成了`open`, `high`, `low`, `close`的策略的资金曲线
        """
        # 填入统一日期数据，对齐回测与实盘
        equity_df.loc[equity_df.shape[0], 'candle_begin_time'] = pd.to_datetime(unified_time).tz_localize('UTC')

        resampled_df = equity_df.resample(self.strategy.hold_period, on='candle_begin_time', offset=hour_offset).agg({
            'equity': ['first', 'max', 'min', 'last']
        })
        resampled_df.columns = ['open', 'high', 'low', 'close']

        # 清理掉数据对齐填入的空值数据
        resampled_df.dropna(subset=resampled_df.columns, how='any', inplace=True)
        # 清理掉对齐数据填入的日期数据
        equity_df = equity_df[equity_df['candle_begin_time'] > pd.to_datetime(unified_time).tz_localize('UTC')]

        if resampled_df.index.min() < equity_df['candle_begin_time'].min():
            resampled_df = resampled_df.iloc[1:]  # 丢弃掉第一个不满周期的数据

        # 去掉最后一个不满周期的数据
        if (
                equity_df['candle_begin_time'].max() - resampled_df.index.max() + pd.to_timedelta('1H')
                != pd.to_timedelta(self.strategy.hold_period)
        ):
            resampled_df = resampled_df.iloc[:-1]

        return resampled_df.reset_index(inplace=False, drop=False)

    def process_equities(self, run_time: datetime, hour_offset: str = '0m'):
        """
        聚合资金曲线结果到系统中
        :param run_time: 运行时间
        :param hour_offset: 实盘配置中的分钟偏移。会影响我们resample资金曲线
        :return:
        """
        equity_dfs = []
        ratio_dfs = []
        configs = self.factory.config_list

        for conf in configs:
            # ====处理资金曲线
            equity_path = conf.get_final_equity_path()
            equity_df = pd.read_csv(equity_path, parse_dates=['candle_begin_time'], index_col=0)

            # 1. 进行周期转换
            equity_df = self.transfer_equity_period(equity_df, hour_offset=hour_offset, unified_time=conf.unified_time)
            # 2. 添加因子(如有需要计算)
            factor_cols = {}
            for factor in self.strategy.factor_list:
                factor_cols.update(calc_factor_vals(equity_df, factor.name, [factor.param]))

            # 3. 添加回测结果并去掉空值，特别提示，这边会造成equity长度缺失，后续会补充0
            equity_df = pd.DataFrame({
                'candle_begin_time': equity_df['candle_begin_time'],
                'open': equity_df['open'].values,
                'high': equity_df['high'].values,
                'low': equity_df['low'].values,
                'close': equity_df['close'].values,
                **factor_cols
            }).ffill().dropna(subset=self.strategy.factor_columns, how='any')
            equity_dfs.append(equity_df)

            start_time = equity_df['candle_begin_time'].min()
            end_time = run_time - pd.Timedelta(hours=utc_offset)
            end_time = end_time.replace(tzinfo=pytz.UTC)

            # 策略的因子参数范围有长短，会造成资金曲线回测的长度有长短，我们选取短的资金曲线
            if self.start_time is None or start_time > self.start_time:
                self.start_time = start_time
            if self.end_time is None or end_time > self.end_time:
                self.end_time = end_time

            # ====处理选币仓位结果
            spot_df = pd.read_pickle(conf.get_snapshot_folder() / f'ratio_spot.pkl')
            swap_df = pd.read_pickle(conf.get_snapshot_folder() / f'ratio_swap.pkl')

            ratio_dfs.append((spot_df, swap_df))

            # 保存到本地
            equity_df.to_pickle(get_file_path(self.factory.result_folder / conf.name / 'equity_df.pkl'))

        # 需要对其所有资金曲线数据的长度
        for idx, df in enumerate(equity_dfs):
            equity_dfs[idx] = df[
                (df['candle_begin_time'] <= self.end_time) & (df['candle_begin_time'] >= self.start_time)]

        self.equity_dfs = equity_dfs
        self.ratio_dfs = ratio_dfs

    def smooth_single_ratio(self, df_ratio):
        """
        Smoothly rebalance a single column of position signals, ensuring stepwise adjustment.

        Args:
        - df (pd.DataFrame): Original position signals with index as candle_begin_time (1 column only).
        - rebalance_cap_step (float): Maximum fraction of total adjustment per step.

        Returns:
        - pd.DataFrame: DataFrame of adjusted rebalance positions.
        """
        rebalance_cap_step = self.strategy.rebalance_cap_step
        if rebalance_cap_step > 0.9999:
            return df_ratio

        rebalance_df = df_ratio.astype(float)  # Copy the original DataFrame
        rebalance_df.iloc[0] = df_ratio.iloc[0]  # Initialize with the first row

        for i in range(1, len(df_ratio)):
            prev_signal = rebalance_df.iloc[i - 1, 0].astype(float)  # Previous adjusted signal
            target_signal = df_ratio.iloc[i, 0].astype(float)  # Target signal for the current row

            # Compute the adjustment needed
            difference = target_signal - prev_signal
            adjustment = max(min(difference, rebalance_cap_step), -rebalance_cap_step)

            # Apply the adjustment
            rebalance_df.iloc[i, 0] = prev_signal + adjustment

        return rebalance_df.round(self.pos_ratio_precision)

    def smooth_ratios(self, df_ratio):
        """
        Generate rebalance positions allowing negatives only if target_signal is negative,
        while keeping total increase and decrease equal to rebalance_cap_step.

        Args:
        - df (pd.DataFrame): Original position signals with index as candle_begin_time.
        - rebalance_cap_step (float): Fixed step for total increase/decrease in positions.

        Returns:
        - pd.DataFrame: DataFrame of adjusted rebalance positions.
        """
        rebalance_cap_step = self.strategy.rebalance_cap_step
        if rebalance_cap_step > 0.9999:
            return df_ratio

        rebalance_df = df_ratio.astype(float)  # Copy the original DataFrame
        rebalance_df.iloc[0] = df_ratio.iloc[0]  # First row matches the initial signal

        for i in range(1, len(df_ratio)):
            prev_signal = rebalance_df.iloc[i - 1]  # Previous adjusted signal
            target_signal = df_ratio.iloc[i]  # Target signal for the current row

            # Difference between target and current signal
            difference = target_signal - prev_signal

            # Allowable increase/decrease ranges
            increase_indices = (difference > 0)
            decrease_indices = (difference < 0)

            # Non-negative constraint: For columns where target_signal >= 0, ensure result >= 0
            non_negative_indices = (target_signal >= 0)
            allowable_decrease = prev_signal[non_negative_indices].clip(lower=0)

            # Calculate total increase and decrease
            total_increase = min(difference[increase_indices].sum(), rebalance_cap_step)
            total_decrease = min(-difference[decrease_indices].sum(), rebalance_cap_step)

            # Scale increases and decreases to meet rebalance_cap_step
            if total_increase > 0:
                scaled_increase = difference[increase_indices] * (total_increase / difference[increase_indices].sum())
            else:
                scaled_increase = pd.Series(0, index=difference.index)

            if total_decrease > 0:
                scaled_decrease = difference[decrease_indices] * (total_decrease / -difference[decrease_indices].sum())
            else:
                scaled_decrease = pd.Series(0, index=difference.index)

            # Apply non-negative constraints
            if non_negative_indices.any():
                scaled_decrease[non_negative_indices] = scaled_decrease[non_negative_indices].clip(
                    lower=-allowable_decrease
                )

            # Apply adjustments
            adjustment = pd.Series(0, index=prev_signal.index)
            adjustment[increase_indices] = scaled_increase
            adjustment[decrease_indices] = scaled_decrease

            # Update rebalance signal
            rebalance_df.iloc[i] = prev_signal + adjustment

            # Normalize to ensure the row sums to 1
            # rebalance_df.iloc[i] = rebalance_df.iloc[i] / rebalance_df.iloc[i].sum()

        return rebalance_df.round(self.pos_ratio_precision)

    def calc_ratios(self):
        logger.info(f'开始计算选币仓位...')
        # 计算选币仓位，这里是按照持仓周期resample之后的index
        ratios = self.strategy.calc_ratios(self.equity_dfs)
        # **特别说明**，
        # 在仓位管理的hold period不等于1H的时候，我们需要额外做转换处理
        # ratios的结构是：
        # ----------------------------------------
        #                      0    1
        # candle_begin_time
        # 2021-01-01 00:00:00  1.0  0.0
        # 2021-01-01 06:00:00  1.0  0.0
        # 2021-01-01 12:00:00  1.0  0.0
        # 2021-01-01 18:00:00  1.0  0.0
        # 2021-01-02 00:00:00  1.0  0.0
        # ...                  ...  ...
        # 2024-07-23 06:00:00  0.0  1.0
        # 2024-07-23 12:00:00  0.0  1.0
        # 2024-07-23 18:00:00  0.0  1.0
        # ---------------------------------------
        # 但是resample之后的资金曲线，是通过`收盘后的equity`来计算的，也就是每个周期的 'close'，
        # candle_begin_time == '2021-01-01 00:00:00' 的选币仓位是给那个周期最后一个1H来使用的。
        # 上述案例中，持仓周期为6H
        # - 00:00:00 ~ 00:04:00: 没有选币仓位
        # - 00:05:00 ~ 00:10:00: 使用candle_begin_time == '2021-01-01 00:00:00' 的选币仓位
        # - 00:11:00 ~ 00:16:00: 使用candle_begin_time == '2021-01-01 06:00:00' 的选币仓位
        # - 00:17:00 ~ 00:22:00: 使用candle_begin_time == '2021-01-01 12:00:00' 的选币仓位
        # - ...
        # 所以，我们需要把时间label进行调整，并且forward fill
        ratios.loc[ratios.index.max() + pd.to_timedelta(self.strategy.hold_period)] = None
        ratios = ratios.shift().fillna(0)  # 把所有动态仓位赋值给下一个周期，并且空出第一个周期

        # 重新自动填充为1H的仓位ratio
        candle_begin_times = pd.date_range(self.start_time, self.end_time, freq='H', inclusive='both')
        df_ratio = ratios.reindex(candle_begin_times, method='ffill')
        df_ratio.fillna(0, inplace=True)

        # 补全数据之后，向上移动1H，并且ffill
        df_ratio = df_ratio.shift(-1).dropna(how='all')

        # 叠加一下再择时的杠杆（如有）
        for idx, conf in enumerate(self.factory.config_list):
            leverage_path = conf.get_result_folder() / '再择时动态杠杆.csv'
            if leverage_path.exists():
                logger.debug(f'⌛️ 加载`{conf.name}`再择时动态杠杆: {leverage_path}')
                leverages = pd.read_csv(leverage_path, index_col='candle_begin_time', encoding='utf-8-sig',
                                        parse_dates=['candle_begin_time'])
                leverages = leverages[leverages.index >= df_ratio.index.min()]
                df_ratio[idx] = df_ratio[idx].mul(leverages['动态杠杆'].astype(float), axis=0)
                logger.debug(f'策略`{conf.name}`，再择时动态杠杆: {leverages.iloc[-1]["动态杠杆"]}')
            logger.debug(f'策略`{conf.name}`，仓位比例: {df_ratio.iloc[-1][idx]}')

        df_ratio.to_csv(self.factory.result_folder / '仓位比例-原始.csv')
        # 根据单次换仓限制，平滑换仓比例
        if len(df_ratio.columns) == 1:
            df_ratio = self.smooth_single_ratio(df_ratio)
        else:
            df_ratio = self.smooth_ratios(df_ratio)
        df_ratio.to_csv(self.factory.result_folder / '仓位比例.csv')
        return df_ratio

    def agg_pos_ratio(self, pos_ratio) -> (pd.DataFrame, pd.DataFrame):
        df_spot_ratio_sum = pd.DataFrame()
        df_swap_ratio_sum = pd.DataFrame()
        for idx, (df_spot_ratio, df_swap_ratio) in enumerate(self.ratio_dfs):
            # 获取仓位管理ratio
            group_ratio = pos_ratio[idx]
            # 裁切对应的资金权重
            spot_ratio = df_spot_ratio.loc[pos_ratio.index, :].mul(group_ratio, axis=0)
            swap_ratio = df_swap_ratio.loc[pos_ratio.index, :].mul(group_ratio, axis=0)
            # 累加
            df_spot_ratio_sum = df_spot_ratio_sum.add(spot_ratio, fill_value=0)
            df_swap_ratio_sum = df_swap_ratio_sum.add(swap_ratio, fill_value=0)

        return df_spot_ratio_sum, df_swap_ratio_sum

    def backtest_strategies(self, run_time):
        from core.backtest import run_backtest_multi
        logger.debug(f'🗄️ 仓位管理策略: {self}')
        return run_backtest_multi(self.factory, run_time)

    def __repr__(self):
        return strategy_name + ' ' + str(self.strategy)

    @property
    def use_spot(self):
        return any([conf.is_use_spot for conf in self.factory.config_list])


if __name__ == '__main__':
    for c in BacktestConfigFactory.init().generate_configs():
        print(c.get_fullname())
