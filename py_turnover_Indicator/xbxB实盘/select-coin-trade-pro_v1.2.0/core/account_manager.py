"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import importlib
import json
import os
from typing import Optional

import config
from core.model.account_config import AccountConfig
from core.utils.functions import ignore_error
from core.utils.log_kit import logger
from core.utils.path_kit import get_file_path

account_config_dict = {}


# ====================================================================================================
# ** 系统config初始化相关 **
# ===================================================================================================
def get_account_config(is_reload=False) -> dict:
    global account_config_dict

    if is_reload:
        account_config_dict = {}
        importlib.reload(config)

    if not is_reload and account_config_dict:
        return account_config_dict

    config_json_path = get_file_path('account_config.json')
    if os.path.exists(config_json_path):
        # 读取JSON配置文件
        try:
            with open(config_json_path, 'r') as file:
                config_json = json.load(file)
            if config_json:
                account_config_dict = config_json
                return config_json
            else:
                logger.info('读取JSON配置文件配置为空，进入config.py模式')
        except Exception as e:
            ignore_error(e)
            logger.info('读取JSON配置文件失败，进入config.py模式')

    account_config_dict = config.account_config

    return account_config_dict


def init_system() -> dict[str, AccountConfig]:
    # 遍历账户配置，将所有账户的交易所配置，全部创建出来
    account_name_list = list(get_account_config(is_reload=True).keys())
    valid_config_dict = {}

    for account_name in account_name_list:
        # 初始化config对象
        cfg = init_config(account_name)

        # 把成功初始化的对象放入到返回结果
        if cfg:
            valid_config_dict[account_name] = cfg

    return valid_config_dict


def init_config(account_name=None) -> Optional[AccountConfig]:
    if account_name is None:
        account_name = list(get_account_config().keys())[0]

    _config_dict = get_account_config()[account_name]
    cfg: AccountConfig = AccountConfig(account_name, **_config_dict)
    # 自动加载、解析策略配置
    cfg.load_strategy_config(_config_dict['strategy_list'])

    if cfg.is_api_ok():
        # 更新交易所基础配置
        config.exchange_basic_config['apiKey'], config.exchange_basic_config['secret'] = cfg.api_key, cfg.secret

        # 初始化交易所相关接口
        cfg.init_exchange(config.exchange_basic_config)

        print()

    # 把成功初始化的对象放入到返回结果
    return cfg


def get_usable_account_config_dict() -> dict[str, AccountConfig]:
    from core.utils.functions import update_accounts_info

    configs = init_system()
    config_dict = update_accounts_info(configs)

    # 判断是否没能成功读取任一账户
    if not len(config_dict.keys()):  # 如果update_account_info数据为空，表示更新账户信息失败
        logger.warning(f'所有账户更新信息失败')

    return config_dict


def get_all_hour_offset_list() -> set[str]:
    return {cfg['hour_offset'] for cfg in get_account_config().values()}


def get_max_kline_num() -> int:
    return max([cfg.get('get_kline_num', 1500) for cfg in get_account_config().values()])
