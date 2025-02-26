"""
邢不行｜策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import os
from pathlib import Path

from core.utils.path_kit import get_folder_path

# ====================================================================================================
# ** 回测配置 **
# ====================================================================================================
# region 回测策略细节配置
start_date = '2022-01-01 00:00:00'  # 回测开始时间
end_date = '2025-01-07'  # 回测结束时间

# ====================================================================================================
# ** 数据配置 **
# ====================================================================================================
# 数据存储路径，填写绝对路径
# 使用官方准备的预处理数据，专门用于本框架回测使用，大幅提高速度
# 现货和合约1小时预处理数据（pkl格式）：https://www.quantclass.cn/data/coin/coin-binance-spot-swap-preprocess-pkl-1h
pre_data_path = r'E:\quantclass\treadedatas\coin-binance-spot-swap-preprocess-pkl-1h'
min_kline_num = 168  # 最少上市多久，不满该K线根数的币剔除，即剔除刚刚上市的新币。168：标识168个小时，即：7*24
reserved_cache = ('select',)  # 用于缓存控制：['select']表示只缓存选币结果，不缓存其他数据，['all']表示缓存所有数据。
# 目前支持选项：
# - select: 选币结果pkl
# - strategy: 大杂烩中策略选币pkl
# - ratio: 最终模拟持仓的各个币种资金占比
# - all: 无视上述配置细节，包含 `all` 就代表我全要
# 缓存东西越多，硬盘消耗越大，对于参数比较多硬盘没那么大的童鞋，可以在这边设置

# ====================================================================================================
# ** 策略细节配置 **
# 案例策略，需要自己探索，不保证可用
# ====================================================================================================
backtest_name = '大学生选币策略-择时覆盖'  # 回测的策略组合的名称。可以自己任意取。一般建议，一个回测组，就是实盘中的一个账户。

strategy_config = {
    'name': 'FixedRatioStrategy',  # *必填。使用什么策略，这里是轮动策略
    'hold_period': '1H',  # *必填。聚合后策略持仓周期。目前回测支持日线级别、小时级别。例：1H，6H，3D，7D......
    'params': {
        'cap_ratios': [
            2 / 4,2 / 4,
            #10 / 10,
        ]
    }
}

# 全部策略混合
strategy_pool = [  # 策略池
    dict(
        name='大学生选币策略-Bolling1-240',
        strategy_list=[
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [8],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 3,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 36, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [1],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 3,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 2496, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            *({
                "strategy": "Strategy_空头",
                "offset_list": range(0, 1, 1),
                "hold_period": '1H',
                "is_use_spot": False,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    # ('QuoteVolume', True, 1, 1),
                    ('Cci', False, x, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('QuoteVolumeMean', x, 'pct:<0.2', False),
                    # ('Ma', [168,50], 'val:==1'),
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            } for x in [168, 432, 600])
        ],
        # 配置再择时之后，可以使用 re_timing.py 进行再择时的资金曲线模拟
        re_timing={'name': 'Bolling1', 'params': [240]}  # 可选，配置再择时策略
    ),
    dict(
        name='大学生选币策略-Bolling1-408',
        strategy_list=[
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [17],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 3,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 16, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            {
                # 策略名称。与strategy目录中的策略文件名保持一致。
                "strategy": "Strategy_大学生",
                "offset_list": [21],
                "hold_period": "24H",
                "is_use_spot": True,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 3,
                'long_cap_weight': 1,
                'short_cap_weight': 0,
                'long_select_coin_num': 0.1,
                'short_select_coin_num': 0,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    ('CirculatingMcap', True, 1, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('ZfStd', 2112, 'pct:<0.8')
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            },
            *({
                "strategy": "Strategy_空头",
                "offset_list": range(0, 1, 1),
                "hold_period": '1H',
                "is_use_spot": False,
                # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
                'cap_weight': 1,
                'long_cap_weight': 0,
                'short_cap_weight': 1,
                'long_select_coin_num': 0,
                'short_select_coin_num': 0.5,
                # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
                "factor_list": [
                    # ('QuoteVolume', True, 1, 1),
                    ('Cci', False, x, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
                ],
                "filter_list": [
                    ('QuoteVolumeMean', x, 'pct:<0.2', False),
                    # ('Ma', [168,50], 'val:==1'),
                ],
                "use_custom_func": False  # 使用系统内置因子计算、过滤函数
            } for x in [168, 432, 600])
        ],
        # 配置再择时之后，可以使用 re_timing.py 进行再择时的资金曲线模拟
       # re_timing={'name': 'Bolling1', 'params': [408]}  # 可选，配置再择时策略
        re_timing={'name': 'Bias', 'params': [120]}  # 可选，配置再择时策略
    ),
    # dict(
    #     name='CCI选币空头策略',
    #     strategy_list=[
    #         {
    #             "strategy": "Strategy_空头",
    #             "offset_list": range(0, 1, 1),
    #             "hold_period": '1H',
    #             "is_use_spot": False,
    #             # 资金权重。程序会自动根据这个权重计算你的策略占比，具体可以看1.8的直播讲解
    #             'cap_weight': 1,
    #             'long_cap_weight': 0,
    #             'short_cap_weight': 1,
    #             'long_select_coin_num': 0,
    #             'short_select_coin_num': 0.5,
    #             # 选币因子信息列表，用于`2_选币_单offset.py`，`3_计算多offset资金曲线.py`共用计算资金曲线
    #             "factor_list": [
    #                 #('QuoteVolume', True, 1, 1),
    #                 ('Cci', False, x, 1),  # 多头因子名（和factors文件中相同），排序方式，参数，权重。
    #             ],
    #             "filter_list": [
    #                 ('QuoteVolumeMean', x, 'pct:<0.2', False),
    #                 #('Ma', [168,50], 'val:==1'),
    #             ],
    #             "use_custom_func": False  # 使用系统内置因子计算、过滤函数
    #         } for x in [168, 432, 600]
    #     ],
    #     # # 配置再择时之后，可以使用 re_timing.py 进行再择时的资金曲线模拟
    #     re_timing={'name': 'Bolling1', 'params': [240]}  # 可选，配置再择时策略
    # ),
]


leverage = 1  # 杠杆数。我看哪个赌狗要把这里改成大于1的。高杠杆如梦幻泡影。不要想着一夜暴富，脚踏实地赚自己该赚的钱。
black_list = []  # 拉黑名单，永远不会交易。不喜欢的币、异常的币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
white_list = []  # 如果不为空，即只交易这些币，只在这些币当中进行选币。例：LUNA-USDT, 这里与实盘不太一样，需要有'-'
# rebalance_mode =
is_pure_long = False  # 纯多设置(https://bbs.quantclass.cn/thread/36230)

# ====================================================================================================
# ** 模拟器细节配置 **
# 也就是如何模拟的细节，帮你按照你策略指令，计算资金曲线
# ====================================================================================================
simulator_config = dict(
    # 模拟下单回测设置
    account_type='普通账户',  # '统一账户'或者'普通账户'
    initial_usdt=1_0000,  # 初始资金
    margin_rate=0.05,  # 维持保证金率，净值低于这个比例会爆仓
    swap_c_rate=5 / 10000,  # 合约手续费(包含滑点)
    spot_c_rate=1 / 1000,  # 现货手续费(包含滑点)
    swap_min_order_limit=5,  # 合约最小下单量。最小不能低于5
    spot_min_order_limit=10,  # 现货最小下单量。最小不能低于10
    avg_price_col='avg_price_1m',  # 用于模拟计算的平均价，预处理数据使用的是1m，'avg_price_1m'表示1分钟的均价, 'avg_price_5m'表示5分钟的均价。
    # 用于对齐 非24约数持仓周期(`strategy_config -> hold_period`)的资金曲线。
    # 以下配置不需要调整：1H,2H,3H,4H,6H,8H,12H
    # 其他持仓周期，可以根据回测与实盘的情况，调整一致
    unified_time='2017-01-01',
)

# ====================================================================================================
# ** 数据配置 **
# - 配置需要的额外数据
# ====================================================================================================
data_source_dict = {
    # 数据源的标签,需要与因子文件中的 extra_data_dict 中的 key 保持一致
    "coin-cap": ('load_coin_cap', r'E:\quantclass\treadedatas\coin-coinmarketcap',)
}

# ====================================================================================================
# ** 全局设置及自动化 **
# 这些设置是客观事实，基本不会影响到回测的细节，正常不用去改动
# ====================================================================================================
job_num = max(os.cpu_count() - 1, 1)  # 回测并行数量
#job_num = 1  # 回测并行数量

# ==== factor_col_limit 介绍 ====
factor_col_limit = 64  # 内存优化选项，一次性计算多少列因子。64是 16GB内存 电脑的典型值
# - 数字越大，计算速度越快，但同时内存占用也会增加。
# - 该数字是在 "因子数量 * 参数数量" 的基础上进行优化的。
#   - 例如，当你遍历 200 个因子，每个因子有 10 个参数，总共生成 2000 列因子。
#   - 如果 `factor_col_limit` 设置为 64，则计算会拆分为 ceil(2000 / 64) = 32 个批次，每次最多处理 64 列因子。
# - 对于16GB内存的电脑，在跑含现货的策略时，64是一个合适的设置。
# - 如果是在16GB内存下跑纯合约策略，则可以考虑将其提升到 128，毕竟数值越高计算速度越快。
# - 以上数据仅供参考，具体值会根据机器配置、策略复杂性、回测周期等有所不同。建议大家根据实际情况，逐步测试自己机器的性能极限，找到适合的最优值。

# 路径处理
raw_data_path = Path(pre_data_path)  # 预处理数据路径
spot_path = raw_data_path / 'spot_dict.pkl'  # 现货数据路径
swap_path = raw_data_path / 'swap_dict.pkl'  # 合约数据路径

# 回测结果数据路径。用于发帖脚本使用
backtest_path = Path(get_folder_path('data', '仓位管理回测结果'))
backtest_iter_path = Path(get_folder_path('data', '子策略回测结果'))

# 稳定币信息，不参与交易的币种
stable_symbol = ['BKRW', 'USDC', 'USDP', 'TUSD', 'BUSD', 'FDUSD', 'DAI', 'EUR', 'GBP', 'USBP', 'SUSD', 'PAXG', 'AEUR',
                 'EURI']

if spot_path.exists() is False or swap_path.exists() is False:
    print('⚠️ 请先准确配置预处理数据的位置（pre_data_path）。建议直接复制绝对路径，并且粘贴给 pre_data_path')
    exit()
