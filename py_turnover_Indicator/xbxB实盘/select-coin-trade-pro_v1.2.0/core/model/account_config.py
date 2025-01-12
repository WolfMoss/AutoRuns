"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import json
import random
import time
from typing import Optional, List

import numpy as np
import pandas as pd

from config import data_path, is_debug
from core.binance.base_client import BinanceClient
from core.binance.standard_client import StandardClient
from core.binance.portfolio_margin_client import PortfolioMarginClient
from core.model.account_type import AccountType
from core.model.strategy_config import StrategyConfig
from core.trade import split_order_twap
from core.utils.dingding import send_wechat_work_msg
from core.utils.log_kit import logger as default_logger, logger
from core.utils.path_kit import get_file_path
from core.utils.strategy_hub import StrategyHub


class AccountConfig:
    def __init__(self, name: str, **config):
        """
        初始化AccountConfig类

        参数:
        config (dict): 包含账户配置信息的字典

        配置示例:
        config = {
            "strategy_list": [  # 实盘前先回测一下，不要无脑跑案例策略，没人能保证案例策略能赚钱
                # ===========================================================
                # 以下配置非官方提供的案例策略，这里只是举例如何配置，具体配置请自行处理
                # ===========================================================
                {
                    "strategy": "Strategy_Spot_80",  # 策略名称。与strategy目录中的策略文件名保持一致。
                    "offset_list": [0],  # 根据自己回测来决定。offset_list 配置错误，会影响选币和下单金额
                    "cap_weight": 1,  # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                    "is_use_spot": True,  # 是否使用现货交易
                },
                {
                    "strategy": "Strategy_Spot_100",  # 策略名称。与strategy目录中的策略文件名保持一致。
                    "offset_list": [0],  # 根据自己回测来决定。offset_list 配置错误，会影响选币和下单金额
                    "cap_weight": 1,  # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                    "is_use_spot": True,  # 是否使用现货交易
                },
                {
                    "strategy": "Strategy_Spot_151",  # 策略名称。与strategy目录中的策略文件名保持一致。
                    "offset_list": [0],  # 根据自己回测来决定。offset_list 配置错误，会影响选币和下单金额
                    "cap_weight": 1,  # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                    "is_use_spot": True,  # 是否使用现货交易
                },
                {
                    "strategy": "Strategy_Spot_168",  # 策略名称。与strategy目录中的策略文件名保持一致。
                    "offset_list": [0],  # 根据自己回测来决定。offset_list 配置错误，会影响选币和下单金额
                    "cap_weight": 1,  # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                    "is_use_spot": True,  # 是否使用现货交易
                },
                {
                    "strategy": "Strategy_Spot_320",  # 策略名称。与strategy目录中的策略文件名保持一致。
                    "offset_list": [0],  # 根据自己回测来决定。offset_list 配置错误，会影响选币和下单金额
                    "cap_weight": 1,  # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                    "is_use_spot": True,  # 是否使用现货交易
                },
            ],
            # 全局配置改成账户策略配置
            "if_use_bnb_burn": True,  # 是否开启BNB燃烧，抵扣手续费
            "buy_bnb_value": 11,  # 买多少U的bnb来抵扣手续费。建议最低11U，现货最小下单量限制10U
            "if_transfer_bnb": False,  # 是否开启小额资产兑换BNB功能。仅现货模式下生效
            "black_list": ['BTCUSDT', 'ETHUSDT', 'BTSUSDT'],  # 黑名单。不参与交易的币种
            "white_list": [],  # 白名单。只参与交易的币种
            "leverage": 1,  # 杠杆。现货模式下：最大杠杆限制1.3倍。合约模式不做限制。
            "get_kline_num": 999,  # 获取多少根K线。这里跟策略日频和小时频影响。日线策略，代表999根日线k。小时策略，代表999根小时k
            "min_kline_size": 168,  # 最低要求b中有多少小时的k线。这里与回测一致。168：表示168小时
            "max_one_order_amount": 100,  # 最大拆单金额。
            "is_pure_long": True,  # 纯多设置(https://bbs.quantclass.cn/thread/36230)
            "twap_interval": 2,  # 下单间隔
            "if_rebalance": True,  # 是否开启rebalance模式，默认True，表示开启，False表示不开启。
            "hour_offset": '0m',  # 分钟偏移设置，可以自由设置时间，配置必须是kline脚本中interval的倍数。默认：0m，表示不偏移。15m，表示每个小时偏移15m下单。
            # 创建企业微信机器人 参考帖子: https://bbs.quantclass.cn/thread/10975
            # 配置案例  https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxxxxxxxxxx
            "wechat_webhook_url": 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=',
            # 现货下单最小金额限制，适当增加可以减少部分reb。默认10，不建议小于10，这会让你的下单报错，10是交易所的限制。
            'order_spot_money_limit': order_spot_money_limit,
            # 合约下单最小金额限制，适当增加可以减少部分reb。默认5，不建议小于5，这会让你的下单报错，5是交易所的限制。
            'order_swap_money_limit': order_swap_money_limit
        }
        """
        self.name: str = name  # 账户名称，建议用英文，不要带有特殊符号

        # 交易所API
        self.api_key: str = config.get("apiKey", "")
        self.secret: str = config.get("secret", "")

        # 策略列表，包含每个策略的详细配置
        self.strategy_list: List[StrategyConfig] = []

        # 是否开启BNB燃烧，抵扣手续费
        self.if_use_bnb_burn: bool = config.get("if_use_bnb_burn", False)

        # 买多少U的bnb来抵扣手续费。建议最低11U，现货最小下单量限制10U
        self.buy_bnb_value: int = config.get("buy_bnb_value", 11)

        # 是否开启小额资产兑换BNB功能，仅现货模式下生效
        self.if_transfer_bnb: bool = config.get("if_transfer_bnb", False)

        # 黑名单，不参与交易的币种
        self.black_list: list = config.get("black_list", [])

        # 下架公告里面的名单
        self.de_list: list = self.load_delist()

        # 白名单，只参与交易的币种
        self.white_list: list = config.get("white_list", [])

        # 杠杆，现货模式下最大杠杆限制1.3倍，合约模式不做限制
        self.leverage: int = config.get("leverage", 1)

        # 获取多少根K线，这里跟策略日频和小时频影响。日线策略，代表999根日线k。小时策略，代表999根小时k
        self.get_kline_num: int = config.get("get_kline_num", 999)

        # 最低要求b中有多少小时的K线，这里与回测一致。168：表示168小时
        self.min_kline_size: int = config.get("min_kline_size", 168)

        # 最大拆单金额
        self.max_one_order_amount: int | float = config.get("max_one_order_amount", 100) * (
                1 + random.uniform(-0.2, 0.2))

        # 纯多设置
        self.is_pure_long: bool = config.get("is_pure_long", False)

        # 下单间隔
        self.twap_interval: int = config.get("twap_interval", 2)

        # 是否开启重新平衡模式，默认True表示开启，False表示不开启
        self.if_rebalance: bool = config.get("if_rebalance", True)

        # 分钟偏移设置，可以自由设置时间，配置必须是kline脚本中interval的倍数。默认：0m表示不偏移，15m表示每个小时偏移15m下单
        self.hour_offset: str = config.get("hour_offset", '0m')

        # 企业微信机器人Webhook URL
        self.wechat_webhook_url: str = config.get("wechat_webhook_url", '')

        # 现货下单最小金额限制，适当增加可以减少部分reb。默认10，不建议小于10，这会让你的下单报错，10是交易所的限制
        self.order_spot_money_limit: int = config.get("order_spot_money_limit", 10)

        # 合约下单最小金额限制，适当增加可以减少部分reb。默认5，不建议小于5，这会让你的下单报错，5是交易所的限制
        self.order_swap_money_limit: int = config.get("order_swap_money_limit", 5)

        self.use_spot: bool = False  # 2024-09-05 开始，自动从子策略的load中更新

        self.logger = config.get("logger", default_logger)

        # 套利的底仓币种
        self.seed_coins: Optional[list] = config.get("seed_coins", [])

        # 联合保证金币种价值配置
        self.coin_margin: Optional[dict[str, dict[str, float]]] = config.get("coin_margin", {})

        # 账户类型
        self.account_type: AccountType = AccountType.translate(config.get("account_type", '普通账户'))

        if (
                self.account_type == AccountType.PORTFOLIO_MARGIN
                and len(set(self.coin_margin.keys()) & set(self.seed_coins)) > 0
        ):
            self.logger.warning(
                '检测到【seed_coins】与【coin_margin】有重复币种，建议联系助教了解清楚逻辑之后修改配置，当前程序自动退出。')
            exit()

        # 大数据拆分份数
        # 对于大参数的策略而言，一次性读取太多数据会导致内存溢出
        # 现在可以根据你的内存限制，设置拆分份数
        # 拆分份数越大，数据读取会越慢，但是内存占用会减小（轻量服务器）
        # 拆分份数越小，数据读取会越快，但是内存占用会增大（高配服务器）
        self.chunk_num: int = config.get("chunk_num", 1)

        # 通知频率。默认单位：h。默认每小时发送一次
        # 如果设置为0，则不进行通知
        # 如果设置为1，则每小时发送一次
        # 如果设置为2，则每2小时发送一次
        self.notify_freq: int = config.get('notify_freq', 1)

        # 下架公告名单作用范围
        # 默认：对合约和现货都生效。
        # 配置项：['spot', 'swap']
        self.de_list_radius: List[str] = config.get('de_list_radius', ['swap', 'spot'])

        if not self.if_rebalance:
            self.logger.warning(f'[{self.name}] 未开启if_rebalance再平衡模式，建议开启')
            exit()

        if self.seed_coins:
            self.logger.warning('检测到您配置了底仓币种【seed_coins】，系统自动拉黑这些币，避免策略选中影响底仓。')
            self.black_list = list(set(self.black_list + self.seed_coins))

        # 配置之外的一些变量，后续会从strategy中初始化
        self.period: str = ''
        self.is_day_period: bool = False  # 是否是天周期
        self.is_hour_period: bool = False  # 是否是小时周期
        self.max_offset_len: int = 0  # 计算最大的offset长度
        self.max_hold_period: str = '1H'  # 最大的持仓周期，默认值设置为最小
        self.hold_period_list: List[str] = []  # 持仓周期列表

        # 初始化变量
        self.bn: Optional[BinanceClient] = BinanceClient()

        self.strategy_name_list: list = []  # 策略名称列表
        self.factor_col_name_list: list = []  # 因子列列名的列表
        self.factor_params_dict: dict = {}  # 因子参数字典

        self.swap_position: Optional[pd.DataFrame] = pd.DataFrame(columns=['symbol', 'symbol_type', '当前持仓量'])
        self.swap_equity: float = 0
        self.spot_position: Optional[pd.DataFrame] = pd.DataFrame(columns=['symbol', 'symbol_type', '当前持仓量'])
        self.spot_equity: float = 0
        self.spot_usdt: float = 0

        self.is_usable: bool = False  # 会在update account 的时候，判断当前账户是否可用

    def __repr__(self):
        # 打印配置信息，方便调试
        return f"""{'-' * 48}
# {self.name} 配置信息如下：
- 账户类型: {self.account_type}
- 策略数量: {len(self.strategy_list)}
- 燃烧BNB做手续费: {self.if_use_bnb_burn}
- 自动购买BNB阈值(USDT): {self.buy_bnb_value}
- 自动划转BNB: {self.if_transfer_bnb}
- 黑名单设置: {self.black_list}
- 白名单设置: {self.white_list}
- 底仓设置: {self.seed_coins}
- 联合保证金设置: {self.coin_margin}
- 杠杆设置: {self.leverage}
- 获取行情k线数量: {self.get_kline_num}
- 产生信号最小K线数量: {self.min_kline_size}
- 单次下单最大金额(USDT): {self.max_one_order_amount}
- 是否纯多: {self.is_pure_long}
- 拆单间隔(秒): {self.twap_interval}
- 是否Rebalance: {self.if_rebalance}
- Hour Offset: {self.hour_offset}
- 微信推送URL: {self.wechat_webhook_url}
{'-' * 64}"""

    @staticmethod
    def load_delist():
        """
        加载delist数据，动态处理黑名单
        """
        try:
            de_list_path = get_file_path(data_path, 'delist.json')
            if not de_list_path.exists():
                return []
            with open(de_list_path, 'r') as file:
                de_list = json.load(file)['list']
            return [_ for _ in de_list if _.endswith('USDT')]  # 获取USDT结尾的币种
        except Exception as e:
            print(e)
            return []

    def load_strategy_config(self, strategy_list: list):
        # 所有策略中的权重
        all_cap_weight = sum(item["cap_weight"] for item in strategy_list)

        for index, stg_dict in enumerate(strategy_list):
            # 更新策略权重
            strategy_name = stg_dict['strategy']

            stg_cfg = StrategyConfig.init(index, file=StrategyHub.get_by_name(strategy_name), **stg_dict)
            stg_cfg.cap_weight = stg_cfg.cap_weight / all_cap_weight

            # 缓存策略配置中H和D周期的信息
            if stg_cfg.is_day_period:
                self.is_day_period = True
            else:
                self.is_hour_period = True

            # 判断是否有自策略正在使用现货
            self.use_spot = self.use_spot or stg_cfg.is_use_spot
            if self.use_spot and self.leverage >= 2:
                self.logger.error(f'现货策略不支持杠杆大于等于2的情况，请重新配置')
                exit(1)

            # 判断策略中的选股数量，不允许同时为0
            if stg_cfg.long_select_coin_num == 0 and (stg_cfg.short_select_coin_num == 0 or
                                                      stg_cfg.short_select_coin_num == 'long_nums'):
                self.logger.warning('策略中的选股数量都为0，忽略此策略配置')
                continue

            # 缓存持仓周期的事情
            if stg_cfg.hold_period not in self.hold_period_list:
                self.hold_period_list.append(stg_cfg.hold_period)
                # 更新最大的持仓周期
                if pd.to_timedelta(self.max_hold_period) < pd.to_timedelta(stg_cfg.hold_period):
                    self.max_hold_period = stg_cfg.hold_period

            self.strategy_list.append(stg_cfg)
            self.strategy_name_list.append(stg_cfg.name)
            self.factor_col_name_list += stg_cfg.factor_columns

            # 针对当前策略的因子信息，整理之后的列名信息，并且缓存到全局
            for factor_config in stg_cfg.all_factors:
                # 添加到并行计算的缓存中
                if factor_config.name not in self.factor_params_dict:
                    self.factor_params_dict[factor_config.name] = set()
                self.factor_params_dict[factor_config.name].add(factor_config.param)

            if len(stg_cfg.offset_list) > self.max_offset_len:
                self.max_offset_len = len(stg_cfg.offset_list)

            # 打印策略详情
            self.logger.debug(stg_cfg)

        self.factor_col_name_list = list(set(self.factor_col_name_list))

        if self.is_pure_long and any(not stg_cfg.is_use_spot for stg_cfg in self.strategy_list):
            self.logger.error('【is_pure_long】纯现货纯多模式不支持 strategy_list 中配置的合约策略，请检查配置')
            exit(1)

        if (
                self.seed_coins
                and self.account_type == AccountType.PORTFOLIO_MARGIN
                and any(stg_cfg.is_use_spot for stg_cfg in self.strategy_list)
        ):
            # !!! 开发者修改提示
            # 框架是支持统一账户现货交易，但是需要账户有USDT余额
            # 为了避免普通同学错误配置，会强制自动切换为合约模式
            # 需要的话可以自行注释下面的三行代码，并自行承担风险（可能开不了仓）
            self.logger.error('统一账户带底仓的模式下不支持使用现货，请检查配置')
            exit(1)

        if self.coin_margin and self.use_spot:
            self.logger.error('现货模式下不支持配置【coin_margin】，请检查配置')
            exit(1)

        # 判断策略中是否存在小时线和日线的策略融合
        if all((self.is_hour_period, self.is_day_period)):
            self.logger.error(f'策略中同时存在小时线和日线的策略融合，请检查配置')
            exit(1)

        self.logger.debug(self)

    def init_exchange(self, exchange_basic_config):
        if self.api_key and self.secret:
            exchange_basic_config['apiKey'] = self.api_key
            exchange_basic_config['secret'] = self.secret
            # 在Exchange增加纯多标记(https://bbs.quantclass.cn/thread/36230)
            exchange_basic_config['is_pure_long'] = self.is_pure_long

            config_params = dict(
                exchange_config=exchange_basic_config,
                spot_order_money_limit=self.order_spot_money_limit,
                swap_order_money_limit=self.order_swap_money_limit,
                logger=self.logger,
                wechat_webhook_url=self.wechat_webhook_url,
                coin_margin=self.coin_margin,
            )
            match self.account_type:
                case AccountType.STANDARD:
                    client_type = StandardClient
                    config_params['is_pure_long'] = self.is_pure_long
                case AccountType.PORTFOLIO_MARGIN:
                    client_type = PortfolioMarginClient
                    config_params['seed_coins'] = self.seed_coins
                case _:
                    raise Exception("不支持的账户类型：{}".format(self.account_type))
            self.bn = client_type(**config_params)
        else:
            raise Exception("请先配置账号API信息")

    @property
    def hour_offset_minute(self) -> int:
        return int(self.hour_offset[:-1])

    def update_account_info(self, is_only_spot_account: bool = False, is_operate: bool = False):
        self.is_usable = False
        is_simulation = False
        if is_debug:
            logger.debug(f'🐞[DEBUG] - {self.name}不更新账户信息')
            is_simulation = True
        elif not self.is_api_ok():
            logger.debug(f'🚨{self.name}没有配置账号API信息，不更新账户信息')
            is_simulation = True

        if is_simulation:
            print('🎲 模拟下单持仓，账户余额模拟为：现货1000USDT，合约0USDT')
            self.spot_equity = 1000
            self.swap_equity = 0
            return False

        # ===先做一下资金归集，防止手误划转错资金
        self.bn.collect_asset(asset='USDT')

        # 是否只保留现货账户
        if is_only_spot_account and not self.use_spot:  # 如果只保留有现货交易的账户，非现货交易账户被删除
            return False

        # ===加载合约和现货的数据
        account_overview = self.bn.get_account_overview()
        # =获取U本位合约持仓
        swap_position = account_overview.get('swap_assets', {}).get('swap_position_df', pd.DataFrame())
        # =获取U本位合约账户净值(不包含未实现盈亏)
        swap_equity = account_overview.get('swap_assets', {}).get('equity', 0)

        # ===加载现货交易对的信息
        # =获取现货持仓净值(包含实现盈亏，这是现货自带的)
        dust_spot = account_overview.get('spot_assets', {}).get('dust_spot_df', pd.DataFrame())
        spot_usdt = account_overview.get('spot_assets', {}).get('usdt', 0)
        spot_equity = account_overview.get('spot_assets', {}).get('equity', 0)
        spot_position = pd.DataFrame()
        # 判断是否使用现货实盘
        if self.use_spot:  # 如果使用现货实盘，需要读取现货交易对信息和持仓信息
            spot_position = account_overview.get('spot_assets', {}).get('spot_position_df', pd.DataFrame())
            # =小额资产转换
            if self.if_transfer_bnb:
                self.bn.transfer_bnb_for_dust_spot(dust_spot)
        elif self.account_type == AccountType.STANDARD:  # 不使用现货实盘，设置现货价值为默认值0
            spot_equity = 0
            spot_usdt = 0

        self.logger.info(f'合约净值(不含浮动盈亏): {swap_equity}\t现货净值: {spot_equity}\t现货的USDT:{spot_usdt}')

        # 判断当前账号是否有资金
        if swap_equity + spot_equity <= 0:
            return None

        # 判断是否需要进行账户的调整（划转，买BNB，调整页面杠杆）
        if is_operate:
            # ===设置一下页面最大杠杆
            self.bn.reset_max_leverage(max_leverage=5)

            # ===将现货中的U转到合约账户（仅普通账户的时候需要）
            if (
                    (self.account_type == AccountType.STANDARD)
                    and (spot_usdt > self.buy_bnb_value * 2)
                    and (not self.is_pure_long)
            ):
                self.bn.transfer_u_from_spot_to_swap(round(spot_usdt - self.buy_bnb_value * 2 - 1, 1))
                spot_equity -= round(spot_usdt - self.buy_bnb_value * 2 - 1, 1)  # 现货总净值扣除掉划走USDT
                swap_equity += round(spot_usdt - self.buy_bnb_value * 2 - 1, 1)  # 合约总净值加上掉划走USDT

            # ===补充BNB操作(用于抵扣手续费)
            if self.if_use_bnb_burn:  # 判断是否开启BNB燃烧
                # 购买bnb用于抵扣手续费燃烧
                all_buy_bnb_value = self.bn.replenish_bnb(self.buy_bnb_value, self.use_spot)
                if all_buy_bnb_value > 0:
                    # 发送信息给机器人
                    send_wechat_work_msg(
                        f'补充BNB抵扣手续费操作完成，补充金额：{all_buy_bnb_value:.4f} U',
                        self.wechat_webhook_url
                    )
        self.swap_position = swap_position
        self.swap_equity = swap_equity
        self.spot_position = spot_position
        self.spot_equity = spot_equity - self.buy_bnb_value * 2
        self.spot_usdt = spot_usdt

        self.is_usable = True
        return dict(
            swap_position=swap_position,
            swap_equity=swap_equity,
            spot_position=spot_position,
            spot_equity=self.spot_equity,
        )

    def calc_order_amount(self, select_coin) -> pd.DataFrame:
        """
        计算实际下单量

        :param select_coin:             选币结果
        :return:

                   当前持仓量   目标持仓量  目标下单份数   实际下单量 交易模式
        AUDIOUSDT         0.0 -2891.524948          -3.0 -2891.524948     建仓
        BANDUSDT        241.1     0.000000           NaN  -241.100000     清仓
        C98USDT        -583.0     0.000000           NaN   583.000000     清仓
        ENJUSDT           0.0  1335.871133           3.0  1335.871133     建仓
        WAVESUSDT        68.4     0.000000           NaN   -68.400000     清仓
        KAVAUSDT       -181.8     0.000000           NaN   181.800000     清仓

        """
        # 更新合约持仓数据
        swap_position = self.swap_position
        swap_position.reset_index(inplace=True)
        swap_position['symbol_type'] = 'swap'

        # 更新现货持仓数据
        if self.use_spot:
            spot_position = self.spot_position
            spot_position.reset_index(inplace=True)
            spot_position['symbol_type'] = 'spot'
            current_position = pd.concat([swap_position, spot_position], ignore_index=True)
        else:
            current_position = swap_position

        # ===创建symbol_order，用来记录要下单的币种的信息
        # =创建一个空的symbol_order，里面有select_coin（选中的币）、all_position（当前持仓）中的币种
        order_df = pd.concat([
            select_coin[['symbol', 'symbol_type']],
            current_position[['symbol', 'symbol_type']]
        ], ignore_index=True)
        order_df.drop_duplicates(subset=['symbol', 'symbol_type'], inplace=True)

        order_df.set_index(['symbol', 'symbol_type'], inplace=True)
        current_position.set_index(['symbol', 'symbol_type'], inplace=True)

        # =symbol_order中更新当前持仓量
        order_df['当前持仓量'] = current_position['当前持仓量']
        order_df['当前持仓量'].fillna(value=0, inplace=True)

        # =目前持仓量当中，可能可以多空合并
        if select_coin.empty:
            order_df['目标持仓量'] = 0
        else:
            order_df['目标持仓量'] = select_coin.groupby(['symbol', 'symbol_type'])[['目标持仓量']].sum()
            order_df['目标持仓量'].fillna(value=0, inplace=True)

        # ===计算实际下单量和实际下单资金
        order_df['实际下单量'] = order_df['目标持仓量'] - order_df['当前持仓量']

        # ===计算下单的模式，清仓、建仓、调仓等
        order_df = order_df[order_df['实际下单量'] != 0]  # 过滤掉实际下当量为0的数据
        order_df.loc[order_df['目标持仓量'] == 0, '交易模式'] = '清仓'
        order_df.loc[order_df['当前持仓量'] == 0, '交易模式'] = '建仓'
        order_df['交易模式'].fillna(value='调仓', inplace=True)  # 增加或者减少原有的持仓，不会降为0

        if select_coin.empty:
            order_df['实际下单资金'] = np.nan
        else:
            select_coin.sort_values('candle_begin_time', inplace=True)
            order_df['close'] = select_coin.groupby(['symbol', 'symbol_type'])[['close']].last()
            order_df['实际下单资金'] = order_df['实际下单量'] * order_df['close']
            del order_df['close']
        order_df.reset_index(inplace=True)

        # 补全历史持仓的最新价格信息
        if order_df['实际下单资金'].isnull().any():
            symbol_swap_price = self.bn.get_swap_ticker_price_series()  # 获取合约的最新价格
            symbol_spot_price = self.bn.get_spot_ticker_price_series()  # 获取现货的最新价格

            # 获取合约中实际下单资金为nan的数据
            swap_nan = order_df.loc[(order_df['实际下单资金'].isnull()) & (order_df['symbol_type'] == 'swap')]
            if not swap_nan.empty:
                # 补充一下合约中实际下单资金为nan的币种数据，方便后续进行拆单
                for _index in swap_nan.index:
                    order_df.loc[_index, '实际下单资金'] = (
                            order_df.loc[_index, '实际下单量'] * symbol_swap_price[swap_nan.loc[_index, 'symbol']]
                    )

            # 获取现货中实际下单资金为nan的数据
            # 有些spot不存在价格，无法直接乘，eg：ethw
            spot_nan = order_df.loc[(order_df['实际下单资金'].isnull()) & (order_df['symbol_type'] == 'spot')]
            if not spot_nan.empty:
                has_price_spot = list(set(spot_nan['symbol'].to_list()) & set(symbol_spot_price.index))  # 筛选有USDT报价的现货
                spot_nan = spot_nan[spot_nan['symbol'].isin(has_price_spot)]  # 过滤掉没有USDT报价的现货，没有报价也表示卖不出去
                if not spot_nan.empty:  # 对含有报价的现货，补充 实际下单资金 数据
                    # 补充一下现货中实际下单资金为nan的币种数据，方便后续进行拆单
                    for _index in spot_nan.index:
                        order_df.loc[_index, '实际下单资金'] = (
                                order_df.loc[_index, '实际下单量'] * symbol_spot_price[spot_nan.loc[_index, 'symbol']]
                        )
                else:  # 对没有报价的现货，设置 实际下单资金 为1，进行容错
                    order_df.loc[spot_nan.index, '实际下单资金'] = 1

        return order_df

    def calc_spot_need_usdt_amount(self, select_coin, spot_order):
        """
        计算现货账号需要划转多少usdt过去
        """
        # 获取需要计算的数据
        if self.account_type == AccountType.PORTFOLIO_MARGIN:
            return -1  # 统一账户不需要进行划转操作，这里直接返回-1。方便跳过后面操作

        # 现货下单总资金
        spot_strategy_equity = 0 if select_coin.empty else spot_order[spot_order['实际下单资金'] > 0][
            '实际下单资金'].sum()

        # 计算现货下单总资金 与 当前现货的资金差值，需要补充（这里是多加2%的滑点）
        diff_equity = spot_strategy_equity * 1.02

        # 获取合约账户中可以划转的USDT数量
        swap_assets = self.bn.get_swap_account()  # 获取账户净值
        swap_assets = pd.DataFrame(swap_assets['assets'])
        swap_max_withdraw_amount = float(
            swap_assets[swap_assets['asset'] == 'USDT']['maxWithdrawAmount'])  # 获取可划转USDT数量
        swap_max_withdraw_amount = swap_max_withdraw_amount * 0.99  # 出于安全考虑，给合约账户预留1%的保证金

        # 计算可以划转的USDT数量
        transfer_amount = min(diff_equity, swap_max_withdraw_amount)
        # 现货需要的USDT比可划转金额要大，这里发送信息警告(前提：非纯多现货模式下)
        if not self.is_pure_long and diff_equity > swap_max_withdraw_amount:
            msg = '======警告======\n\n'
            msg += f'现货所需金额:{diff_equity:.2f}\n'
            msg += f'合约可划转金额:{swap_max_withdraw_amount:.2f}\n'
            msg += '划转资金不足，可能会造成现货下单失败！！！'
            # 重复发送五次
            for i in range(0, 5, 1):
                send_wechat_work_msg(msg, self.wechat_webhook_url)
                time.sleep(3)

        return transfer_amount

    def proceed_swap_order(self, orders_df: pd.DataFrame):
        """
        处理合约下单
        :param orders_df:    下单数据
        """
        # ===使用twap算法拆分订单
        swap_order = orders_df[orders_df['symbol_type'] == 'swap']
        orders_df_list = split_order_twap(swap_order, self.max_one_order_amount)

        # ===遍历下单
        for i in range(len(orders_df_list)):
            # 逐批下单
            self.bn.place_swap_orders_bulk(orders_df_list[i])
            # 下单间隔
            self.logger.info(f'等待 {self.twap_interval}s 后继续下单')
            time.sleep(self.twap_interval)

    def proceed_spot_order(self, orders_df, select_coin, is_only_sell=False):
        """
        处理现货下单
        :param orders_df:    下单数据
        :param select_coin:     选币数据
        :param is_only_sell:    是否仅仅进行卖单交易
        """
        # ===现货处理
        spot_order_df = orders_df[orders_df['symbol_type'] == 'spot']

        # 判断是否需要现货下单
        if spot_order_df.empty:  # 如果使用了现货数据实盘，则进行现货下单
            return

        # =使用twap算法拆分订单
        short_order = spot_order_df[spot_order_df['实际下单资金'] <= 0]
        long_order = spot_order_df[spot_order_df['实际下单资金'] > 0]
        # 判断是否只卖现货
        if is_only_sell:  # 如果是仅仅交易卖单，只进行拆单
            orders_df_list = split_order_twap(short_order, self.max_one_order_amount)
        else:  # 如果是仅仅交易买单，拆单，划转资金去现货账户
            orders_df_list = split_order_twap(long_order, self.max_one_order_amount)

            # 计算现货所需USDT，从合约账户转U到现货账户
            time.sleep(5)
            transfer_amount = self.calc_spot_need_usdt_amount(select_coin, spot_order_df)
            self.logger.info(f'transfer_amount {transfer_amount}')
            if transfer_amount > 0:
                # 转资金到现货账户
                self.bn.transfer_u_from_swap_to_spot(round(transfer_amount - 1, 1))  # 避免四舍五入的问题

        # =现货遍历下单
        for i in range(len(orders_df_list)):
            # 逐批下单
            self.bn.place_spot_orders_bulk(orders_df_list[i])

            # 下单间隔
            self.logger.info(f'等待 {self.twap_interval}s 后继续下单')
            time.sleep(self.twap_interval)

        # 资金归集
        self.bn.collect_asset()

    def is_api_ok(self):
        # 判断是否配置了api
        return self.api_key and self.secret
