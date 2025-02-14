"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path
from types import ModuleType
from typing import Optional, List, Union

import pandas as pd

from config import runtime_data_path
from core.market_essentials import import_index_data
from core.model.rebalance_mode import RebalanceMode
from core.model.strategy_config import StrategyConfig, FactorConfig
from core.utils.factor_hub import FactorHub
from core.utils.log_kit import logger
from core.utils.path_kit import get_folder_path
from core.utils.strategy_hub import get_strategy_by_name


class BacktestConfig:
    def __init__(self, **config_dict: dict):
        self.name: str = config_dict.get('backtest_name', '默认策略回测')  # 账户名称，建议用英文，不要带有特殊符号

        self.start_date: Optional[str] = config_dict.get('start_date', None)  # 回测开始时间
        self.end_date: Optional[str] = config_dict.get('end_date',
                                                       None)  # 日期，为None时，代表使用到最新的数据，也可以指定日期，例如'2022-11-01'，但是指定日期

        # 策略列表，包含每个策略的详细配置
        self.strategy_list: List[StrategyConfig] = []
        self.strategy_name_list: List[str] = []
        self.strategy_list_raw: List[dict] = []

        self.initial_cash: float = config_dict.get('initial_cash', 100_0000)  # 初始资金默认100万
        self.c_rate: float = config_dict.get('c_rate', 1.2 / 10000)  # 手续费，默认为0.002，表示万分之二
        self.t_rate: float = config_dict.get('t_rate', 1 / 1000)  # 印花税，默认为0.001

        # 根据输入，进行一下重要中间变量的处理
        self.data_center_path: Path = Path(str(config_dict['data_center_path']))
        # Rebalance 模式
        self.rebalance_mode: RebalanceMode = RebalanceMode.init(config_dict.get('rebalance_mode', None))
        # 整体资金使用率
        self.total_cap_usage: float = config_dict.get('total_cap_usage', 1)

        # 如果你要diy的话，在这里设置你的数据中心路径
        # 股票日线数据，全量数据下载链接：https://www.quantclass.cn/data/stock/stock-trading-data
        self.stock_data_path: Path = self.data_center_path / 'stock-trading-data-pro'
        # 指数数据路径，全量数据下载链接：https://www.quantclass.cn/data/stock/stock-main-index-data
        self.index_data_path: Path = self.data_center_path / 'stock-main-index-data'
        # 其他的数据，全量数据下载链接：https://www.quantclass.cn/data/stock/stock-fin-data-xbx
        self.fin_data_path: Path = self.data_center_path / 'stock-fin-data-xbx'

        self.has_fin_data: bool = self.fin_data_path.exists()  # 是否使用财务数据

        self.factor_params_dict: dict = {}  # 缓存因子参数，用于后续的因子聚合
        self.factor_col_name_list: List[str] = []
        self.hold_period_name_list: List[str] = []  # 持仓周期列表

        self.fin_cols: list = []  # 缓存财务因子列
        self.ov_cols: list = []  # 缓存全息数据的额外字段
        self.extra_data: dict = {}  # 缓存额外数据

        self.agg_rules = {}  # 缓存聚合规则
        self.report: pd.DataFrame = pd.DataFrame()  # 回测报告

        # 遍历标记
        self.iter_round: Union[int, str] = 0  # 遍历的INDEX，0表示非遍历场景，从1、2、3、4、...开始表示是第几个循环，当然也可以赋值为具体名称

        self.period_offset_path = self.data_center_path / 'period_offset.csv'

        if all((self.stock_data_path.exists(), self.fin_data_path.exists(), self.index_data_path.exists(),
                self.period_offset_path.exists())):
            pass  # 数据检查通过
        else:
            logger.critical(f'''必要数据有缺失，请检查:
1. {self.stock_data_path}
2. {self.fin_data_path}
3. {self.index_data_path}
4. {self.period_offset_path}''')
            exit()

    def info(self):
        info_list = [
            '=' * 82,
            f"""🔵 {self.name}
→ 回测周期：{self.start_date} -> {self.end_date}
→ 初始资金：￥{self.initial_cash:,.2f}
→ 费率设置：手续费{self.c_rate * 100:,.2f}%, 印花税{self.t_rate * 100:,.2f}%
→ 数据设置:
  - 财务数据: {self.fin_cols if self.fin_cols else '∅ 否'}
  - 全息数据: {self.ov_cols if self.ov_cols else '∅ 否'}
  - 外部数据: {list(self.extra_data.keys()) if self.extra_data else '∅ 否'}
→ 数据中心路径："{self.data_center_path}"
→ 回测结果路径："{self.get_result_folder()}"
→ 包含子策略：{'、'.join(self.strategy_name_list)}"""]

        for strategy in self.strategy_list:
            info_list.append(f'  {strategy}')

        info_list.append('=' * 82 + '\n')

        return '\n'.join(info_list)

    def save(self):
        pd.to_pickle(self, self.get_result_folder() / 'config.pkl')

    # noinspection PyUnusedLocal
    def load_strategy_config(self, strategy_list: Union[list, tuple], timing_config=None):
        self.strategy_list_raw = strategy_list
        # 所有策略中的权重，当且仅当超过1的时候，才会做归一化处理
        all_cap_weight = max(sum(item.get('cap_weight', 1) for item in strategy_list), 1)
        merged_dict = defaultdict(list)  # 合并额外数据引用

        for index, stg_dict in enumerate(strategy_list):
            strategy_name = stg_dict['name']
            stg_dict['funcs'] = get_strategy_by_name(strategy_name)
            strategy = StrategyConfig.init(index, **stg_dict)
            strategy.cap_weight = strategy.cap_weight / all_cap_weight  # 加权平均策略权重

            # 缓存持仓周期的事情
            self.hold_period_name_list += strategy.hold_period_name_list

            self.strategy_list.append(strategy)
            self.strategy_name_list.append(strategy_name)
            self.factor_col_name_list += strategy.factor_columns

            # 针对当前策略的因子信息，整理之后的列名信息，并且缓存到全局
            for factor_config in strategy.all_factors:
                # 添加到并行计算的缓存中
                if factor_config.name not in self.factor_params_dict:
                    self.factor_params_dict[factor_config.name] = set()
                self.factor_params_dict[factor_config.name].add(factor_config.param)

                factor = FactorHub.get_by_name(factor_config.name)

                # 1. 合并财务因子
                self.fin_cols += getattr(factor, 'fin_cols', [])
                # 2. 合并全息数据的额外字段
                self.ov_cols += getattr(factor, 'ov_cols', [])
                # 3. 合并额外数据
                for k, v in getattr(factor, 'extra_data', {}).items():
                    merged_dict[k].extend(v)

        # 对列名进行去重
        self.fin_cols = list(set(self.fin_cols))
        self.ov_cols = list(set(self.ov_cols))
        self.extra_data = {key: list(set(value)) for key, value in merged_dict.items()}
        self.hold_period_name_list = list(set(self.hold_period_name_list))
        self.factor_col_name_list = list(set(self.factor_col_name_list))

        # if timing_config:
        #     self.timing = TimingSignal(**timing_config)
        # 缓存交易日偏移，按照策略自动裁切

    def load_period_offset(self) -> pd.DataFrame:
        if self.hold_period_name_list:
            return pd.read_csv(self.period_offset_path, encoding='gbk', parse_dates=['交易日期'], skiprows=1,
                               usecols=['交易日期'] + self.hold_period_name_list)
        else:
            return pd.read_csv(self.period_offset_path, encoding='gbk', parse_dates=['交易日期'], skiprows=1)

    def load_index_data(self):
        """
        加载指数数据

        参数:
        index_data (DataFrame): 指数数据
        prg_data_folder (str): 程序数据文件夹路径

        返回:
        index_data (DataFrame): 合并后的指数数据
        """
        # 获取今天的日期
        return import_index_data(self.index_data_path / 'sh000001.csv', [self.start_date, self.end_date])

    def read_trading_dates(self, first_date, last_date):
        period_offset = self.load_period_offset()
        trading_dates = period_offset['交易日期']

        trading_dates = trading_dates[(trading_dates >= first_date) & (trading_dates <= last_date)]
        return trading_dates

    def get_result_folder(self) -> Path:
        if self.iter_round == 0:
            return get_folder_path(runtime_data_path, '回测结果', self.name)
        else:
            config_name = f'策略组_{self.iter_round}' if isinstance(self.iter_round, int) else self.iter_round
            if self.name.startswith(f'S{self.iter_round}'):
                config_name = self.name
            return get_folder_path(runtime_data_path, '遍历结果', config_name)

    @staticmethod
    def get_analysis_folder() -> Path:
        return get_folder_path(runtime_data_path, '分析结果')

    def get_fullname(self, as_folder_name=False):
        fullname_list = [self.name]
        for stg in self.strategy_list:
            fullname_list.append(str(stg))

        fullname = ' '.join(fullname_list) + f'，初始资金￥{self.initial_cash * self.total_cap_usage:,.2f}'
        return f'{self.name}' if as_folder_name else fullname

    def set_report(self, report: pd.DataFrame):
        report['param'] = self.get_fullname()
        self.report = report

    def get_strategy_config_sheet(self, with_factors=True, sep_filter=False) -> dict:
        factor_dict = {'持仓周期': [], '选股数量': []}
        for stg in self.strategy_list:
            factor_dict['持仓周期'].append(stg.hold_period_name_list)
            factor_dict['选股数量'].append(stg.select_num)

            for factor_config in stg.all_factors:
                if sep_filter:
                    factor_type = '因子' if isinstance(factor_config, FactorConfig) else '过滤'
                    _name = f'#{factor_type}-{factor_config.name}'
                else:
                    _name = f'#因子-{factor_config.name}'
                _val = factor_config.param
                if _name not in factor_dict:
                    factor_dict[_name] = []
                factor_dict[_name].append(_val)
        ret = {
            '策略': self.name,
            '策略详情': self.get_fullname(),
        }
        if with_factors:
            ret.update(**{
                k: "，".join(map(str, v)) for k, v in factor_dict.items()
            })

        # if self.timing:
        #     ret['再择时'] = str(self.timing)
        return ret

    @classmethod
    def init_from_config(cls, load_strategy_list=True):
        import config
        # 提取自定义变量
        config_dict = {
            key: value
            for key, value in vars(config).items()
            if not key.startswith('__') and not isinstance(value, ModuleType)
        }
        conf = cls(**config_dict)
        if load_strategy_list:
            conf.load_strategy_config(config.strategy_list, )
        return conf


class BacktestConfigFactory:
    """
    遍历参数的时候，动态生成配置
    """

    def __init__(self, **conf):
        # ====================================================================================================
        # ** 参数遍历配置 **
        # 可以指定因子遍历的参数范围
        # ====================================================================================================
        # 存储生成好的config list和strategy list
        self.config_list: List[BacktestConfig] = []
        self.backtest_name = conf.get("backtest_name")

        if not self.backtest_name:
            self.backtest_name = f'默认策略-{datetime.now().strftime("%Y%m%dT%H%M%S")}'

        # 缓存全局配置
        self.is_use_spot = conf.get("is_use_spot", False)
        self.black_list = conf.get("black_list", set())

        # 存储生成好的config list和strategy list
        self.config_list: List[BacktestConfig] = []
        self.strategy_list: List[StrategyConfig] = []

    @property
    def result_folder(self) -> Path:
        return get_folder_path(runtime_data_path, '遍历结果')

    def generate_all_factor_config(self):
        """
        产生一个conf，拥有所有策略的因子，用于因子加速并行计算
        """
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

    def generate_configs_by_strategies(self, strategies, timing_strategies=None) -> List[BacktestConfig]:
        config_list = []
        iter_round = 0

        if not timing_strategies:
            timing_strategies = [None]

        for strategy_list, timing_config in product(strategies, timing_strategies):
            iter_round += 1
            backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
            if self.backtest_name:
                backtest_config.name = f"S{iter_round}-{self.backtest_name}"
            backtest_config.load_strategy_config(strategy_list, timing_config)
            backtest_config.iter_round = iter_round

            # self.update_meta_by_config(backtest_config)

            config_list.append(backtest_config)

        self.config_list = config_list

        return config_list


def load_config() -> BacktestConfig:
    return BacktestConfig.init_from_config()


def create_factory(strategies):
    from config import backtest_name
    factory = BacktestConfigFactory(backtest_name=backtest_name)
    factory.generate_configs_by_strategies(strategies)

    return factory
