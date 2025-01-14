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
        'apiKey': 'miAsEL6QtoCQJneQOsRDMtijqV4cBt88IDBCL5IsAqa9bZGIokJHyRAThx2gsjjw',
        'secret': 'MLbVKHzxe3Wqx5w7Q8DF334FlSLBPN4QUMqunAVVm4hZGTS68WhKnrJshcMFL99H',

        # ++++ 策略配置 ++++
        "strategy_list": [
            # === 1.大学生纯多策略
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [9],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 32, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [16],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 1824, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [3],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': (0.1, 0.2),
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 92, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [5],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': (0.1, 0.2),
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 500, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
        ],

        # ++++ 分钟偏移功能 ++++
        # 支持任意时间开始的小时级别K线
        "hour_offset": '10m',  # 分钟偏移设置，可以自由设置时间，配置必须是kline脚本中interval的倍数。默认：0m，表示不偏移。15m，表示每个小时偏移15m下单。

        # ++++ 企业微信机器人功能 ++++
        "wechat_webhook_url": 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b9312317-19d6-4f2a-b2c6-a8b27a4c19e3',
        # 创建企业微信机器人 参考帖子: https://bbs.quantclass.cn/thread/10975
        # 配置案例  https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxxxxxxxxxx

        # ++++ 交易黑名单与白名单功能 ++++
        "black_list": ['BTCUSDT', 'ETHUSDT', 'BCHUSDT', 'LTCUSDT', 'ETCUSDT', 'LINKUSDT', 'SOLUSDT', 'AVAXUSDT', 'AAVEUSDT'],  # 黑名单。不参与策略的选币，如果持有黑名单币种，将会自动清仓
        "white_list": [],  # 白名单。只参与策略的选币

        # ++++ 其他账户设置 ++++
        "leverage": 1,  # 实际下单杠杆。现货模式不要超过1，合约模式不要超过2。对于杠杆的一些解释： https://bbs.quantclass.cn/thread/25188
        "get_kline_num": 1924,  # 获取多少根K线。这里跟策略日频和小时频影响。日线策略，代表999根日线k。小时策略，代表999根小时k
        "min_kline_size": 168,  # 最低要求b中有多少小时的k线。这里与回测一致。168：表示168小时

        # 大数据拆分份数
        # 对于大参数的策略而言，一次性读取太多数据会导致内存溢出
        # 现在可以根据你的内存限制，设置拆分份数
        # 拆分份数越大，数据读取会越慢，但是内存占用会减小（轻量服务器）
        # 拆分份数越小，数据读取会越快，但是内存占用会增大（高配服务器）
        "chunk_num": 1,  # 默认：1。表示不对数据进行拆分
        # ++++ BNB抵扣手续费功能 ++++
        "if_use_bnb_burn": True,  # 是否开启BNB燃烧，抵扣手续费
        "buy_bnb_value": 11,  # 买多少U的bnb来抵扣手续费。建议最低11U，现货最小下单量限制10U
        # 支持账户类型：统一账户，普通账户
        'account_type': '统一账户',
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
api_key = '1L9Z9IL0ELWATTBOIPCF2GD5MD4D235T'

# 个人中心里面的葫芦id。（网址：https://www.quantclass.cn/login）
uuid = 'e1388f20d6a43ee4838520e8ab0f61c1'

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
error_webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e51b3705-1073-46e7-805a-3c8228708299'


# ====================================================================================================
# ** 数据配置 **
# - 配置实盘需要的额外数据
# ====================================================================================================
data_source_dict = {
    # 数据源的标签: ('加载数据的函数名', '数据存储的绝对路径')
    # 说明：数据源的标签,需要与因子文件中的 extra_data_dict 中的 key 保持一致，数据存储的路径需要表达清楚
    "coin-cap": ('load_coin_cap', '/home/ubuntu/select-coin-trade-pro_v1.2.0/data/coin-cap',)
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
