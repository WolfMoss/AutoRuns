from xtquant import xtdata
from xtquant import xtconstant
import pandas as pd
from Config import *

# 官方文档 http://docs.thinktrader.net/vip/pages/198696/#xtquant数据字典

# 查账户资产资金
asset = xt_trader.query_stock_asset(account_putong)
if asset:
    # print('查看有哪些属性字段:', dir(asset))
    print("总资产{}，可用资金{}".format(asset.total_asset, asset.cash))

# 查账户持仓明细
positions = xt_trader.query_stock_positions(account_putong)

def position_to_dict(i):
    return {
        '证券代码': i.stock_code,
        '持仓数量': i.volume,
        '可用数量': i.can_use_volume,
        '平均建仓成本': i.open_price
    }


if len(positions) != 0:
    df_pos = pd.DataFrame(list(map(position_to_dict, positions)))
    print(df_pos)
else:
    print('无持仓信息')


# 查账户的委托明细
orders = xt_trader.query_stock_orders(account_putong, False)


def order_to_dict(i):
    return {
        '证券代码': i.stock_code,
        '委托数量': i.order_volume,
        '委托价格': i.price,
        '订单编号': i.order_id,
        '委托状态':i.order_status
    }

if len(orders) != 0:
    orders_lst = list(map(order_to_dict, orders))
    df_orders = pd.DataFrame(orders_lst)
    print(df_orders)
else:
    print('无委托信息')


# 查询当日最近的成交
trades = xt_trader.query_stock_trades(account_putong)
def trade_to_dict(i):
    return {
        '证券代码': i.stock_code,
        '委托类型': i.order_type,
        '成交时间': i.traded_time,
        '成交均价': i.traded_price,
        '成交数量': i.traded_volume,
        '成交金额': i.traded_amount,
        '订单编号': i.order_id,
        '策略名称': i.strategy_name,
    }
if len(trades) != 0:
    trades_lst = list(map(trade_to_dict, trades))
    df_trades = pd.DataFrame(trades_lst)
    print(df_trades)
else:
    print('无成交信息')
