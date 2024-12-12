# -*-coding:utf-8-*-
import pandas as pd
pd.set_option('expand_frame_repr', False)  # 当列太多时显示完整
pd.set_option('display.max_rows', 5000)  # 最多显示数据的行数

from xtquant import xtdata

# 获取股票全推实时行情
quote_dict = xtdata.get_full_tick(code_list=['000001.SZ', '600519.SH'])
df = pd.DataFrame(quote_dict)
df = df.T
df.reset_index(inplace=True)
rename_dict = {'index': '证券代码', 'timetag': '时间', 'lastPrice': '最新价', 'open': '开盘价', 'high': '最高价', 'low': '最低价',
               'lastClose': '昨收价',
               'amount': '成交额', 'volume': '成交量', 'pvolume': '原始成交总量',
               'settlementPrice': '今结算', 'lastSettlementPrice': '前结算', 'askPrice': '五档卖价', 'bidPrice': '五档买价',
               'askVol': '五档卖量', 'bidVol': '五档买量'}
df.rename(columns=rename_dict, inplace=True)
# print(df.columns)
df = df[['证券代码', '时间', '最新价', '开盘价', '最高价', '最低价', '昨收价', '成交额', '成交量', '五档卖价', '五档买价', '五档卖量', '五档买量']]
print(df)

# 获取板块列表
block_lst = xtdata.get_sector_list()
print(block_lst)

# 获取板块成份股
chengfengu = xtdata.get_stock_list_in_sector(sector_name='SW1传媒加权')
print(chengfengu)
