from xtquant import xtdata
from xtquant import xtconstant
import pandas as pd
from Config import *
"""
miniqmt业内俗称小QMT，应该是最适合散户量化交易的方式，没有之一！相比于大qmt，他可以直接在pycharm里写策略，同时支持免费查实时和历史行情数据，支持查资金成交持仓委托，以及买卖下单和撤单等。几乎可以满足量化交易的全部基本需求。今天分享，如果快速上手miniqmt，并演示买卖下单！

miniqmt轻松入门：
第一步，你需要联系你所在的券商，申请开通含有极简模式即miniqmt的QMT终端权限。
第二步，本机安装好qmt，记录好安装路径，然后在site-packages下找到xtquant文件夹，复制，然后粘贴到你本机python的site-packages文件夹下。
第三部，在python代码编辑器导入所需的包。这样，就可以直接在python里调用miniqmt的行情和交易接口啦！
"""
# 官方文档 http://docs.thinktrader.net/vip/pages/198696/#xtquant数据字典

# 指定价买入下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
fix_result_order_id = xt_trader.order_stock(account_putong, '300433.SZ', xtconstant.STOCK_BUY, 100, xtconstant.FIX_PRICE, 0.7)
print(fix_result_order_id)

# 按最新价买入下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
fix_result_order_id = xt_trader.order_stock(account_putong, '300433.SZ', xtconstant.STOCK_BUY, 100, xtconstant.MARKET_SZ_FULL_OR_CANCEL, 0)
print(fix_result_order_id)


# 指定价卖出下单示例，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
# sell_order_id = xt_trader.order_stock(account_putong, '159742.SZ', xtconstant.STOCK_SELL, 100, xtconstant.FIX_PRICE, 0.508, 'strategy1', '卖出恒生科技ETF')
# print(sell_order_id)

# 根据委托编号撤单 返回是否成功发出撤单指令，0: 成功, -1: 表示撤单失败
# order_id = 1209008133
# cancel_order_result = xt_trader.cancel_order_stock(account_putong, order_id)
# print(cancel_order_result)