"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

import os
import time

from core.utils.path_kit import get_folder_path

# ====================================================================================================
# ** 账户及策略配置 **
# 【核心设置区域】设置账户API，策略详细信息，交易的一些特定参数等等
# * 注意，以下功能都是在config.py中实现
# ====================================================================================================

# ------ 框架重要功能 ------
# 支持“纯合约模式”：多头和空头都是合约。
# 支持“现货+合约模式”：多头可以包含现货、合约，空头包含合约。
# 纯多功能：全部仓位只买入策略的多头。不交易空头。
# 统一账户功能：可以在 `传统的非统一账户` 和 `统一账户`模式 之间选择。任何模式下，原有功能都保留
# 分钟偏移功能：支持任意时间开始的小时级别K线
# 多账户功能：一个程序可以同时在多个账户下运行策略。
# 多offset功能

# ------ 策略级别功能 ------
# 多策略融合功能（大杂烩）：一个账户下可以同时运行多个选币策略。例如可以在一个账户下，使用一份资金，运行策略A（参数1）、策略A（参数2）、策略A（参数3）、策略B（参数1）、策略B（参数2）。以此类推。
# 多策略资金配比功能：一个账户运行多个策略时，每个策略可以配置不同的资金比例。
# 多空分离选币：多头和空头可以使用不一样的策略。
# 多空分离过滤（前置）：多头和空头的前置过滤条件可以不同。
# 数据整理支持自定义数据：支持在策略中加入量价数据之外的任意第三方数据

# ------ 其他功能 ------
# 自动rebalance功能。默认开启，可以关闭后手动rebalance
# rebalance时，可以设定最小下单量。例如设置为50u，可以显著降低无效换手。
# 下单时动态拆单功能
# BNB抵扣手续费功能。开启BNB燃烧，抵扣手续费
# 小额资产自动兑换BNB功能。
# 企业微信机器人通知功能。开启企业微信机器人
# 交易黑名单与白名单功能。开启选币黑名单与白名单
# ====================================================================================================

# ++++ 多账户多策略 ++++
# 多账户功能：一个程序可以同时在多个账户下运行策略。同时兼容不同的账户类型。
account_config = {
    "账户1": {
        # 交易所API配置
        'apiKey': '',
        'secret': '',

        # ++++ 策略配置 ++++
        "strategy_list": [
            # === 低价币config_低价缩量组合策略.py中性策略
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_低价币多空策略",
                "offset_list": list(range(0, 24, 1)),  # 只选部分offset[1, 3, 6]；
                "hold_period": "24H",  # 小时级别可选1H到24H；也支持1D交易日级别
                "is_use_spot": False,  # 多头支持交易现货；
                # 资金权重。程序会自动根据这个权重计算你的策略占比
                'cap_weight': 1,
                'long_cap_weight': 1,  # 可以多空比例不同，多空不平衡对策略收益影响大
                'short_cap_weight': 1,
                # 选币数量
                'long_select_coin_num': 0.1,  # 可适当减少选币数量，对策略收益影响大
                'short_select_coin_num': 0.1,  # 四种形式：整数， 小数，'long_nums', 区间选币：(0.1, 0.2), (1, 3)
                # 选币因子信息列表，用于2_选币_单offset.py，3_计算多offset资金曲线.py共用计算资金曲线
                "factor_list": [
                    ('LowPrice', True, 168, 1),  # 多空因子名（和factors文件中相同），排序方式，参数，权重。支持多空分离，多空选币因子不一样；
                ],
                "filter_list": [
                    ('LowPrice', 168, 'rank:>1', False),  # 后置过滤filter_list_post，三种形式：pct, rank, val；支持多空分离，多空过滤因子不一样；
                ],
            },
        ],

        # ++++ 分钟偏移功能 ++++
        # 支持任意时间开始的小时级别K线
        "hour_offset": '0m',  # 分钟偏移设置，可以自由设置时间，配置必须是kline脚本中interval的倍数。默认：0m，表示不偏移。15m，表示每个小时偏移15m下单。

        # ++++ 企业微信机器人功能 ++++
        "wechat_webhook_url": 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=',
        # 创建企业微信机器人 参考帖子: https://bbs.quantclass.cn/thread/10975
        # 配置案例  https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxxxxxxxxxx
    },
}

# ====================================================================================================
# ** 交易所配置 **
# ====================================================================================================
# 如果使用代理 注意替换IP和Port
proxy = {}
# proxy = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}  # 如果你用clash的话
exchange_basic_config = {
    'timeout': 30000,
    'rateLimit': 30,
    'enableRateLimit': False,
    'options': {
        'adjustForTimeDifference': True,
        'recvWindow': 10000,
    },
    'proxies': proxy,
}

# ====================================================================================================
# ** 运行模式及交易细节设置 **
# 设置系统的时差、并行数量，稳定币，特殊币种等等
# ====================================================================================================
# 是否使用数据API服务的开关。默认: False
use_data_api = False

# 个人中心里面的api_key配置。（网址：https://www.quantclass.cn/login）
api_key = ''

# 个人中心里面的葫芦id。（网址：https://www.quantclass.cn/login）
uuid = ''

# debug模式。模拟运行程序，不会去下单
is_debug = True

# 获取当前服务器时区，距离UTC 0点的偏差
utc_offset = int(time.localtime().tm_gmtoff / 60 / 60)  # 如果服务器在上海，那么utc_offset=8

# 现货稳定币名单，不参与交易的币种
stable_symbol = ['BKRW', 'USDC', 'USDP', 'TUSD', 'BUSD', 'FDUSD', 'DAI', 'EUR', 'GBP', 'USBP', 'SUSD', 'PAXG', 'AEUR',
                 'EURI']

# kline下载数据类型。支持:spot , swap, funding
# 如果只需要现货和合约，可以只下载spot和swap，需要资金费数据，配置funding
download_kline_list = ['swap', 'spot', ]

# 特殊现货对应列表。有些币种的现货和合约的交易对不一致，需要手工做映射
special_symbol_dict = {
    'DODO': 'DODOX',  # DODO现货对应DODOX合约
    'LUNA': 'LUNA2',  # LUNA现货对应LUNA2合约
    '1000SATS': '1000SATS',  # 1000SATS现货对应1000SATS合约
}

# 全局报错机器人通知
# - 创建企业微信机器人 参考帖子: https://bbs.quantclass.cn/thread/10975
# - 配置案例  https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxxxxxxxxxx
error_webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key='


# ====================================================================================================
# ** 数据配置 **
# - 配置实盘需要的额外数据
# ====================================================================================================
data_source_dict = {
    # 数据源的标签: ('加载数据的函数名', '数据存储的绝对路径')
    # 说明：数据源的标签,需要与因子文件中的 extra_data_dict 中的 key 保持一致，数据存储的路径需要表达清楚
    "coin-cap": ('load_coin_cap', '/Users/xxxx/Downloads/coin-cap-test',)
}

# ====================================================================================================
# ** 文件系统相关配置 **
# - 获取一些全局路径
# - 自动创建缺失的文件夹们
# ====================================================================================================
root_path = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径

# 获取目录位置，不存在就创建目录
data_path = get_folder_path('data', as_path_type=False)

# 获取目录位置，不存在就创建目录
data_center_path = get_folder_path('data', 'data_center', as_path_type=False)

# 获取目录位置，不存在就创建目录
flag_path = get_folder_path('data', 'flag', as_path_type=False)

# 获取目录位置，不存在就创建目录
order_path = get_folder_path('data', 'order', as_path_type=False)

# 获取目录位置，不存在就创建目录
runtime_folder = get_folder_path('data', 'runtime')
