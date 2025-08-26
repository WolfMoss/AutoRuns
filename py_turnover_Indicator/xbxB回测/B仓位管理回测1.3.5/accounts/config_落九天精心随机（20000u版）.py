"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
# ====================================================================================================
# ** 实盘账户配置 **
# ‼️‼️‼️账户配置，需要在accounts下的文件中做配置 ‼️‼️‼️
# 此处只是展示配置的结构，具体配置情参考 accounts 文件夹下的 _55mBTC样例.py
# ====================================================================================================
account_config = {
    # ++++ 分钟偏移功能 ++++
    # 支持任意时间开始的小时级别K线
    'hour_offset': '30m',
}  # 实盘账户配置，需要在accounts下的文件中做配置，此处只是结构上的展示

# ====================================================================================================
# ** 策略细节配置 **
# ‼️‼️‼️需要在accounts下的文件中做配置‼️‼️‼️
# 此处只是展示配置的结构，具体配置情参考 accounts 文件夹下的 _55mBTC样例.py
# ====================================================================================================
strategy_name = '随机策略'  # 当前账户运行策略的名称。可以自己任意取
get_kline_num = 3860  # 获取多少根K线。这里跟策略日频和小时频影响。日线策略，代表多少根日线k。小时策略，代表多少根小时k
strategy_config = {
    'name': 'FixedRatioStrategyFill_V2',  
    'hold_period': '1H',  
    'params': {
        'cap_ratios': (0.05, 0.45, 0.0),  # 默认资金分配
        'pos_limit': {
            'monitor_strategy': '无脑做空新币',  # 监控策略名称
            'alt_ratios_0': (0.0, 0.5, 0.0),   # 空仓时的资金分配
            'alt_ratios_1': (0.01, 0.49, 0.0),  # 选1个币时的资金分配
            'alt_ratios_2': (0.02, 0.48, 0.0),  # 选2个币时的资金分配
            'alt_ratios_3': (0.03, 0.47, 0.0),  # 选3个币时的资金分配
            'alt_ratios_4': (0.04, 0.46, 0.0),  # 选4个币时的资金分配
            'alt_ratios_5plus': (0.05, 0.45, 0.0)  # 选5个及以上币时的资金分配
        }
    }
}

strategy_pool = [
    dict(
        name='落九天',
        strategy_list=[
            # 落九天策略实例1
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_落九天",
                "offset_list": [1, 6],
                "hold_period": "8H",
                "is_use_spot": False,
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 999,
                'short_select_coin_num': 999,
                "factor_list": [
                    ('ZfMeanQ', True, 100, 1),
                ],
                "filter_list": [
                    ('新币', 1 ,'val:<415'),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 192, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # 落九天策略实例2
            {
                "strategy": "Strategy_落九天",
                "offset_list": [0, 4],
                "hold_period": "8H",
                "is_use_spot": False,
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 999,
                'short_select_coin_num': 999,
                "factor_list": [
                    ('ZfMeanQ', True, 100, 1),
                ],
                "filter_list": [
                    ('新币', 1 ,'val:<415'),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 72, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # 落九天策略实例3
            {
                "strategy": "Strategy_落九天",
                "offset_list": [0, 2],
                "hold_period": "8H",
                "is_use_spot": False,
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 999,
                'short_select_coin_num': 999,
                "factor_list": [
                    ('ZfMeanQ', True, 100, 1),
                ],
                "filter_list": [
                    ('新币', 1 ,'val:<415'),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 331, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # 落九天策略实例4
            {
                "strategy": "Strategy_落九天",
                "offset_list": [5, 7],
                "hold_period": "8H",
                "is_use_spot": False,
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 999,
                'short_select_coin_num': 999,
                "factor_list": [
                    ('ZfMeanQ', True, 100, 1),
                ],
                "filter_list": [
                    ('新币', 1 ,'val:<415'),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 225, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
        ]
    ),
    dict(
        name='黄果树浪淘沙',
        strategy_list=[
            # ===1.黄果树系列1-1
            {
                "strategy": "Strategy_黄果树系列1",
                "offset_list": [4, 6],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 3/5/6,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('Cci', False, 389, 1),
                ],
                "filter_list": [
                    ('QuoteVolumeMean', 389, 'pct:<0.2', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 389, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===1.黄果树系列1-2
            {
                "strategy": "Strategy_黄果树系列1",
                "offset_list": [13, 20],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 3/5/6,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('BiasQ', False, 363, 1),
                ],
                "filter_list": [
                    ('QuoteVolumeMean', 363, 'pct:<0.2', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 363, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===1.黄果树系列1-3
            {
                "strategy": "Strategy_黄果树系列1",
                "offset_list": [9, 22],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 3/5/6,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('Cci', False, 562, 1),
                ],
                "filter_list": [
                    ('QuoteVolumeMean', 562, 'pct:<0.2', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 562, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===1.黄果树系列1-4
            {
                "strategy": "Strategy_黄果树系列1",
                "offset_list": [5, 16],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 3/5/6,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('BiasQ', False, 405, 1),
                ],
                "filter_list": [
                    ('QuoteVolumeMean', 405, 'pct:<0.2', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 405, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===1.黄果树系列1-5
            {
                "strategy": "Strategy_黄果树系列1",
                "offset_list": [1, 14],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 3/5/6,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('BiasQ', False, 469, 1),
                ],
                "filter_list": [
                    ('QuoteVolumeMean', 469, 'pct:<0.2', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 469, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===1.黄果树系列1-6
            {
                "strategy": "Strategy_黄果树系列1",
                "offset_list": [7, 20],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 3/5/6,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('Cci', False, 414, 1),
                ],
                "filter_list": [
                    ('QuoteVolumeMean', 414, 'pct:<0.2', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 414, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===2.黄果树系列2-1
            {
                "strategy": "Strategy_黄果树系列2",
                "offset_list": [3, 15],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 1/5/2,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('QuoteVolumeMean', True, 180, 1),
                ],
                "filter_list": [
                    ('MinMax', 180, 'pct:<0.2'),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 180, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===2.黄果树系列2-2
            {
                "strategy": "Strategy_黄果树系列2",
                "offset_list": [15, 20],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 1/5/2,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                "factor_list": [
                    ('QuoteVolumeMean', True, 504, 1),
                ],
                "filter_list": [
                    ('BiasQ', 504, 'pct:<0.2'),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 504, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===3.黄果树系列3-1
            {
                "strategy": "Strategy_黄果树系列3",
                "offset_list": [9, 15],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 1/5/2,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 9999,
                "factor_list": [
                    ('QuoteVolumeMean', True, 1, 1),
                ],
                "filter_list": [
                    ('MinMax', 435, 'pct:<0.15'),
                    ('QuoteVolumeMean', 435, 'pct:<0.15', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 435, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
            # ===3.黄果树系列3-2
            {
                "strategy": "Strategy_黄果树系列3",
                "offset_list": [1, 21],
                "hold_period": '24H',
                "is_use_spot": False,
                'cap_weight': 1/5/2,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 9999,
                "factor_list": [
                    ('QuoteVolumeMean', True, 1, 1),
                ],
                "filter_list": [
                    ('BiasQ', 607, 'pct:<0.15'),
                    ('QuoteVolumeMean', 607, 'pct:<0.15', False),
                ],
                "filter_list_post": [
                    ('ZfMeanQ', 607, 'val:<0.5'),
                ],
                "use_custom_func": False
            },
        ]
    ),
    dict(
        name='无脑做空新币',
        strategy_list=[
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_新币做空",
                "offset_list": list(range(0, 1, 1)),
                "hold_period": "1H",
                "is_use_spot": False,
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 999,
                'short_select_coin_num': 999,
                "factor_list": [
                    ('ZfMeanQ', True, 10, 1),
                ],
                "filter_list": [
                    ('新币', 1 ,'val:<415'),
                ],
                "use_custom_func": False
            } 
        ]
    ),
]  # 策略池
leverage = 1  # 杠杆数。我看哪个赌狗要把这里改成大于1的。高杠杆如梦幻泡影。不要想着一夜暴富，脚踏实地赚自己该赚的钱。
black_list = []  # 拉黑名单，永远不会交易。不喜欢的币、异常的币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
white_list = []  # 如果不为空，即只交易这些币，只在这些币当中进行选币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
# rebalance_mode =  # 换仓模式控制
is_pure_long = False  # 纯多设置(https://bbs.quantclass.cn/thread/36230) 