# ====================================================================================================
# ** 实盘账户配置 **
# ‼️‼️‼️账户配置，需要在accounts下的文件中做配置 ‼️‼️‼️
# 此处只是展示配置的结构，具体配置情参考 accounts 文件夹下的 account1.py
# 文件名就是账户名，比如 `15m大学生.py` 或者 `55mBTC.py`
# ====================================================================================================
account_config = {
    # 交易所API配置
    'account_type': '统一账户',
    'apiKey': 'miAsEL6QtoCQJneQOsRDMtijqV4cBt88IDBCL5IsAqa9bZGIokJHyRAThx2gsjjw',
    'secret': 'MLbVKHzxe3Wqx5w7Q8DF334FlSLBPN4QUMqunAVVm4hZGTS68WhKnrJshcMFL99H',
    # ++++ 分钟偏移功能 ++++
    # 支持任意时间开始的小时级别K线
    "hour_offset": '25m',  # 分钟偏移设置，可以自由设置时间，配置必须是kline脚本中interval的倍数。默认：0m，表示不偏移。15m，表示每个小时偏移15m下单。
    # ++++ 企业微信机器人功能 ++++
    "wechat_webhook_url": 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b9312317-19d6-4f2a-b2c6-a8b27a4c19e3',
    # ++++ BNB抵扣手续费功能 ++++
    "if_use_bnb_burn": True,  # 是否开启BNB燃烧，抵扣手续费
    "buy_bnb_value": 11,  # 买多少U的bnb来抵扣手续费。建议最低11U，现货最小下单量限制10U
}  # 实盘账户配置，需要在accounts下的文件中做配置，此处只是结构上的展示
# ====================================================================================================
# ** 策略细节配置 **
# ‼️‼️‼️需要在accounts下的文件中做配置‼️‼️‼️
# 此处只是展示配置的结构，具体配置情参考 accounts 文件夹下的 account1.py
# ====================================================================================================
strategy_name = '大学生选币策略-择时覆盖'  # 当前账户运行策略的名称。可以自己任意取
get_kline_num = 3004  # 获取多少根K线。这里跟策略日频和小时频影响。日线策略，代表多少根日线k。小时策略，代表多少根小时k
strategy_config = {  # 策略配置
    'name': 'FixedRatioStrategy',  # *必填。使用什么策略，这里是轮动策略
    'hold_period': '1H',  # *必填。聚合后策略持仓周期。目前回测支持日线级别、小时级别。例：1H，6H，3D，7D......
    'params': {
        'cap_ratios': [
            6 / 10,4 / 10,
        ],  # *必填。资金分配比例。2个策略，每个策略资金占比1/2
    }
}
strategy_pool = [  # 策略池
    dict(
        name='大学生选币策略-Bias-168',
        strategy_list=[
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [12],
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
                "filter_list_post": [
                    ('zjfundingfiter', 1, 'val:>=-0.019', False),
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
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 1536, 'pct:<0.8')
                ],
                "filter_list_post": [
                    ('zjfundingfiter', 1, 'val:>=-0.019', False),
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
        ],
        # 配置再择时之后，可以使用 re_timing.py 进行再择时的资金曲线模拟
        re_timing={'name': 'Bias', 'params': [168]},  # 可选，配置再择时策略
        #re_timing = {'name': 'Bolling1', 'params': [240]}  # 可选，配置再择时策略
    ),
    dict(
        name='黄果树-Bolling1',
        strategy_list=[{
                "strategy": "Strategy_bollinger空头",
                "offset_list": range(0, 24, 1),
                "hold_period": '24H',
                "is_use_spot": False,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.2,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "long_factor_list": [],
                "long_filter_list": [],
                "short_factor_list": [
                    ('Cci', False, 10 * 24, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "short_filter_list": [
                    ('Bias_signal', (10 * 24, -0.15), 'val:==1', False),
                    ('QuoteVolumeMean', 10 * 24, 'pct:<0.2', False),

                ],
                "filter_list_post": [
                    ('ZfAbsMean', 10 * 24, 'val:<0.5'),
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            }
        ],
        # # 配置再择时之后，可以使用 re_timing.py 进行再择时的资金曲线模拟
        re_timing={'name': 'Bolling1', 'params': [240]}  # 可选，配置再择时策略
    ),
]



leverage = 1  # 杠杆数。我看哪个赌狗要把这里改成大于1的。高杠杆如梦幻泡影。不要想着一夜暴富，脚踏实地赚自己该赚的钱。
black_list = ['BTCUSDT', 'ETHUSDT','AAVEUSDT','LINKUSDT','ENAUSDT','TRXUSDT','ONDOUSDT','UNIUSDT','POLUSDT','XRPUSDT','SOLUSDT','ADAUSDT','LTCUSDT','TRUMPUSDT']  # 拉黑名单，永远不会交易。不喜欢的币、异常的币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
white_list = []  # 如果不为空，即只交易这些币，只在这些币当中进行选币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
# rebalance_mode =
is_pure_long = False  # 纯多设置(https://bbs.quantclass.cn/thread/36230)
