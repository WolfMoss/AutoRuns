import datetime
import os
import time
import traceback

from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

# ========== 初始化 ==========
path = r'E:\迅投极速策略交易系统交易终端 大同证券QMT实盘\userdata_mini'  # 极简版QMT的路径
account_id = '2009107197'  # 资金账号

session_id = int(time.time() * 1000)  # session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号（自己随便写）
xt_trader = XtQuantTrader(path, session_id)  # 创建API实例
account_putong = StockAccount(account_id, 'STOCK')  # 创建股票账户
# 启动交易线程
xt_trader.start()
# 建立交易连接，返回0表示连接成功
connect_result = xt_trader.connect()
if connect_result != 0:
    print('连接失败')
else:
    print('连接成功')
# 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
subscribe_result = xt_trader.subscribe(account_putong)
if subscribe_result != 0:
    print('连接失败')
else:
    print('连接成功')
