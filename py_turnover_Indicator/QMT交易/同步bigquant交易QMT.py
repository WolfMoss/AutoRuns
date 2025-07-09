import os
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
import time, datetime, traceback, sys
from datetime import datetime
import schedule
import sys 
print(sys.path)

# 导入qmt相关的包
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import time 
print('+++++++++++++++++++++++++++++++++++++++++++++++++++++:',datetime.now() ,'导入包完成!')

### 账户、策略id、访问凭证要改成自己的
config= { 
# 资金账号【需要修改的地方-1】（修改成您的实盘资金账号）
'account' : '99080945',
# bigquant.com 的策略模拟交易id【需要修改的地方-2】（在您的“我的策略-特定策略页面上方的链接中最后一个斜杠后面）
'strategy_id' : "eb327fe5-b3a8-4002-b677-7ad36c47305d",
# 获取自己策略信号的access【需要修改的地方-3】（在您的“用户中心-访问凭证”中获得）
'access_key' : "bJ07YdwgkmU5",
# 获取自己策略信号的secret 【需要修改的地方-4】（在您的“用户中心-访问凭证”中获得）
'secret_key' : "dJpkY71nNVJ5sYxP5uQIa1mTdR03PfidmRTNFJib68CG3arP2VLfdIH29HnKhzY3"
}

### 模拟交易 Web API封装
log = logging.getLogger("papertradingapi")
class PaperTradingAPI(object):
    """模拟交易 Web API封装"""

    HOST = "https://bigquant.com"
    ACCESS_KEY_HEADER_NAME: str = "X-BigQuant-Access-Key"
    ACCESS_SIGNATURE_HEADER_NAME: str = "X-BigQuant-Signature"
    ACCESS_TIMESTAMP_HEADER_NAME: str = "X-BigQuant-Timestamp"

    def __init__(self, access_key: str, secret_key: str, strategy_id: str):
        self._access_key = access_key
        self._secret_key = secret_key
        self._strategy_id = strategy_id
        self._account_type = ''
        self._account_id = ''
        self.tradingapiserver_host = os.getenv("TRADINGAPISERVER_HOST")
        self.debug = 1

    def query_papertrading_info(self) -> Optional[Dict]:
        """获取模拟交易基本信息
        example data:
        {
            'id': 'aec3e784-0724-4d7d-8917-16461b8c5553', 'created_at': '2023-12-07T17:52:43.232000+08:00', 'updated_at': '2023-12-07T17:53:08.416973+08:00',
            'space_id': '00000000-0000-0000-0000-000000000000', 'creator': '6d0130a2-3d94-4f38-97a2-14e1dc9391a4',
            'strategy_name': 'StockRanker-DAI策略-20231206112622', 'strategy_type': '0', 'status': 1, 'account_id': {'10020': '0'},
            'benchmark_instrument': '000300.SH', 'first_benchmark_index': 3572.36, 'first_trading_day': '2023-12-07', 'frequency': '1d',
            'extension': {}, 'source': 'saas', 'strategy_params': {'volume_limit': 1, 'order_price_field_buy': 'open', 'order_price_field_sell': 'close'
        }
        """
        url = f"{self.tradingapiserver_host}/strategies/{self._strategy_id}"
        params = {'page': 1, 'size': 10}
        if self.tradingapiserver_host:
            url = f"{self.tradingapiserver_host}/strategies/{self._strategy_id}"
            headers = None
        else:
            url, headers = self.signature_headers(self.HOST, f"/bigapis/trading/v1/strategies/{self._strategy_id}", self._access_key, self._secret_key, params=params)
        resp = requests.get(url=url, headers=headers, params=params)
        resp_data = resp.json()
        if self.debug:
            print(f"query_papertrading_info: resp_data={resp_data}")
        if resp_data["code"] != 0:
            raise Exception(resp_data["message"])
        ret = resp_data.get("data")

        account_id_dict = ret["account_id"]
        self._account_type = list(account_id_dict.values())[0]
        self._account_id = list(account_id_dict.keys())[0]
        print(f"query_papertrading_info: got account_id='{self._account_type}',\"{self._account_id}\" by strategy_id={self._strategy_id}")
        return ret

    def query_papertrading_cash(self, trading_day: str) -> Optional[Dict]:
        """获取模拟交易资金信息
        example data:
        {
            'account_type': '0', 'account_id': '10020', 'trading_day': '2023-06-19', 'currency': 'CNY', 'balance': 109016.71000000006,
            'available': 109016.71000000006, 'frozen_cash': 0.0, 'total_margin': 0.0, 'total_market_value': 407791.0, 'portfolio_value': 516807.71,
            'pre_balance': 101875.81000000006, 'positions_pnl': 12350.64, 'capital_changed': 0.0, 'total_capital_changed': 0.0
        }
        """
        constraints = {"account_type": self._account_type, "trading_day__gte": trading_day, "trading_day__lte": trading_day}
        params = {'constraints': json.dumps(constraints), 'page': 1, 'size': 10}
        if self.tradingapiserver_host:
            url, headers = f"{self.tradingapiserver_host}/accounts/{self._account_id}/cash", None
        else:
            url, headers = self.signature_headers(self.HOST, f"/bigapis/trading/v1/accounts/{self._account_id}/cash", self._access_key, self._secret_key, params=params)
        resp = requests.get(url=url, headers=headers, params=params)
        resp_data = resp.json()
        if self.debug:
            print(f"query_papertrading_cash: resp_data={resp_data}")
        if resp_data["code"] != 0:
            raise Exception(resp_data["message"])

        datas = resp_data.get("data").get("items")
        if datas:
            ret = datas[0]
            if "created_at" in ret:
                del ret["created_at"]
            if "id" in ret:
                del ret["id"]
            if "updated_at" in ret:
                del ret["updated_at"]
            return ret
        else:
            return {}

    def query_papertrading_positions(self, trading_day: str) -> List[Dict]:
        """获取模拟交易某日的持仓列表
        example data:
        [{
            'account_type': '0', 'account_id': '10020', 'trading_day': '2023-06-19', 'exchange': 'SZ', 'instrument': '000005.SZ',
            'name': 'ST星源', 'posi_direction': '1', 'current_qty': 17800, 'available_qty': 17800, 'today_qty': 0, 'today_available_qty': 0,
            'cost_price': 1.17, 'last_price': 1.22, 'market_value': 21716.0, 'margin': 0.0, 'position_pnl': 887.92, 'hedge_flag': '1',
            'sum_buy_value': 20826.0, 'sum_sell_value': 0.0, 'commission': 2.08, 'dividend_qty': 0, 'dividend_cash': 0.0,
            'open_date': '2023-06-16', 'open_price': 1.17, 'settlement_price': 0.0, 'hold_days': 2
        }]
        """
        constraints = {"account_type": self._account_type, "trading_day__gte": trading_day, "trading_day__lte": trading_day}
        params = {'constraints': json.dumps(constraints), 'page': 1, 'size': 3000}
        if self.tradingapiserver_host:
            url, headers = f"{self.tradingapiserver_host}/account_positions/{self._account_id}/positions", None
        else:
            url, headers = self.signature_headers(self.HOST, f"/bigapis/trading/v1/account_positions/{self._account_id}/positions", self._access_key, self._secret_key, params=params)
        resp = requests.get(url=url, headers=headers, params=params)
        resp_data = resp.json()
        if resp_data["code"] != 0:
            raise Exception(resp_data["message"])

        list_positions = []
        datas = resp_data.get("data").get("items")
        if datas:
            for pos_data in datas:
                if "created_at" in pos_data:
                    del pos_data["created_at"]
                if "id" in pos_data:
                    del pos_data["id"]
                if "updated_at" in pos_data:
                    del pos_data["updated_at"]
                list_positions.append(pos_data)
            return list_positions
        else:
            return list_positions

    def query_papertrading_planned_orders(self, trading_day: str) -> List[Dict]:
        """获取模拟交易某日的信号列表
        example data:
        [{
            'creator': '6d0130a2-3d94-4f38-97a2-14e1dc9391a4', 'planned_order_id': '145909290', 'strategy_id': 'aec3e784-0724-4d7d-8917-16461b8c5553',
            'account_type': '0', 'account_id': '10020', 'trading_day': '2023-06-19', 'order_dt': '2023-06-19T15:00:00+08:00', 'exchange': 'SH',
            'instrument': '600767.SH', 'name': '*ST运盛', 'direction': '2', 'offset_flag': '1', 'original_order_qty': 251600, 'order_qty': 251600,
            'order_price': 0.42, 'order_type': 'U', 'order_status': 10, 'status_msg': 'Generated', 'order_params': None, 'order_placed_dt': None,
            'order_key': '', 'entrust_no': '', 'algo_order_id': 0, 'stop_loss_price': 0.0, 'stop_profit_price': 0.0
        }]
        """
        constraints = {
            "account_type": self._account_type,
            "account_id": self._account_id,
            "trading_day__gte": trading_day,
            "trading_day__lte": trading_day
        }
        params = {'constraints': json.dumps(constraints), 'page': 1, 'size': 3000}
        if self.tradingapiserver_host:
            url, headers = f"{self.tradingapiserver_host}/planned_order", None
        else:
            url, headers = self.signature_headers(self.HOST, f"/bigapis/trading/v1/planned_order", self._access_key, self._secret_key, params=params)
        resp = requests.get(url=url, headers=headers, params=params)
        resp_data = resp.json()
        if resp_data["code"] != 0:
            raise Exception(resp_data["message"])

        list_planned_orders: List[Dict] = []

        ########
        # For test mock planned orders
        """
        _planned_order = {
            'planned_order_id': '1',
            'strategy_id': self._strategy_id,
            'account_type': '0', 'account_id': '10000',
            'trading_day': trading_day,
            'order_dt': ' '.join([trading_day, "09:31:00"]),
            'exchange': 'SH',
            'instrument': '600900.SH',
            'name': '长江电力',
            'direction': '1',
            'offset_flag': '0',
            'original_order_qty': 600,
            'order_qty': 600,
            'order_price': 23.42,
            'order_type': 'U',
            'order_status': 10,
            'status_msg': 'Generated'
        }
        list_planned_orders.append(_planned_order)
        return list_planned_orders
        """
        ########

        datas = resp_data.get("data").get("items")
        if datas:
            for planned_order in datas:
                if "created_at" in planned_order:
                    del planned_order["created_at"]
                if "id" in planned_order:
                    del planned_order["id"]
                if "updated_at" in planned_order:
                    del planned_order["updated_at"]
                list_planned_orders.append(planned_order)
            return list_planned_orders
        else:
            return list_planned_orders

    def signature_headers(self,
        host: str,
        path: str,
        access_key: str,
        secret_key: str,
        body: bytes = b"",
        headers: dict = {},
        params: dict = None,
    ) -> Tuple[str, dict]:
        """采用aksk给headers添加签名.
    
        Args:
            host (str): host.
            path (str): 路径.
            access_key (str): ak.
            secret_key (str): sk.
            body (bytes): 请求负载.
            headers (dict, optional): 请求头.
    
        Returns:
            Tuple[str, dict]: url, 请求头.
        """
        import hmac
        import httpx
        import time
        from urllib.parse import quote
        url = f"{host}{path}"
        if params:
            url = url + "?" + quote("&".join([f"{k}={v}" for k, v in params.items()]))
        path_encode = path.encode()
        timestamp = int(time.time() * 1000)
        timestamp = str(timestamp)
        # 参与签名的消息
        msg = path_encode + body + timestamp.encode()
        signature = hmac.new(secret_key.encode(), msg=msg, digestmod="SHA256").hexdigest()
        # 给headers这是签名和时间戳
        headers[self.ACCESS_KEY_HEADER_NAME] = access_key
        headers[self.ACCESS_SIGNATURE_HEADER_NAME] = signature
        headers[self.ACCESS_TIMESTAMP_HEADER_NAME] = timestamp
        return url, headers 

def get_papertrading_info(access_key, secret_key, strategy_id, trading_day):
    """
    获取当天模拟交易持仓信息
    """
    import pandas as pd
    paper_api = PaperTradingAPI(access_key=access_key, secret_key=secret_key, strategy_id=strategy_id)

    paper_info = paper_api.query_papertrading_info()
    print(f"策略相关信息: {paper_info}")

    paper_positions = paper_api.query_papertrading_positions(trading_day)
    position_df = []
    for i, paper_position in enumerate(paper_positions):
        position_df.append(paper_position)

    order_df = []
    planned_orders = paper_api.query_papertrading_planned_orders(trading_day)
    for i, planned_order in enumerate(planned_orders):
        order_df.append(planned_order)
    return pd.DataFrame(position_df), pd.DataFrame(order_df)


### ================================这个目录要改成自己的qmt终端的目录的userdata_mini目录=======================================================
path = r'E:\迅投极速策略交易系统交易终端 大同证券QMT实盘\userdata_mini'
session_id = int(time.time())
xt_trader = XtQuantTrader(path, session_id)
account =  config['account']
acc = StockAccount(account, 'STOCK')
xt_trader.start()
# 建立交易连接，返回0表示连接成功
connect_result = xt_trader.connect()
print('建立交易连接，返回0表示连接成功', connect_result)

log = logging.getLogger("papertradingapi")

global access_key,secret_key,strategy_id
access_key = config['access_key']
secret_key = config['secret_key']
strategy_id = config['strategy_id']


def send_order(exec_time):

    ### ================================这个目录要改成自己的qmt终端的目录的userdata_mini目录====================================================
    path = r'E:\迅投极速策略交易系统交易终端 大同证券QMT实盘\userdata_mini'
    session_id = int(time.time())
    xt_trader = XtQuantTrader(path, session_id)
    account =  config['account']
    acc = StockAccount(account, 'STOCK')
    xt_trader.start()
    # 建立交易连接，返回0表示连接成功
    connect_result = xt_trader.connect()
    print('建立交易连接，返回0表示连接成功', connect_result)
    # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
    subscribe_result = xt_trader.subscribe(acc)
    print('对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功', subscribe_result)

    #xt_trader为XtQuant API实例对象，获取可用金额属性
    cash = xt_trader.query_stock_asset(acc).cash
    total_asset = xt_trader.query_stock_asset(acc).total_asset
    print('资金:',cash)

    positions = xt_trader.query_stock_positions(acc)
    pos_dict = {}
    for pos in positions:
        pos_dict[pos.stock_code] = pos.volume
    print("position===:", pos_dict)
    
    # 获取今天的日期
    today = datetime.today() # 计划交易日期
    trading_day = today.strftime('%Y-%m-%d')
    
    # 获取今日信号
    position_df, order_df = get_papertrading_info(access_key, secret_key, strategy_id, trading_day)

    def judge_time(x):
        if '09:30' in x:
            return 'morning'
        elif '15:00' in x:
            return 'afternoon'
        else:
            pass

    order_df['exec_time'] = order_df['order_dt'].apply(judge_time)
    order_df = order_df[order_df['exec_time'] == exec_time]

    ######################################### 开始使用qmt下单 #########################################
    print("start")
    print('计划交易:', len(order_df), order_df) 
    if len(order_df) == 0:
        return 

    buy_signal = order_df[order_df['direction']=='1']['instrument'].tolist()
    sell_signal = order_df[order_df['direction']=='2']['instrument'].tolist()
    
    buy_signal = [i for i in buy_signal if i != '']
    sell_signal = [i for i in sell_signal if i != '']
    
    print('买入信号:', buy_signal, '卖出信号:', sell_signal)
    
         
    for ins in sell_signal:
        volume = order_df[order_df['instrument'] == ins]['order_qty'].iloc[0]
        volume = min(volume, pos_dict[ins]) # 预计卖出量和实际持仓量的较小值 
        price = order_df[order_df['instrument'] == ins]['order_price'].iloc[0] * 0.95
        price = round(price,2)
        now = datetime.now()
        try:
            async_seq = xt_trader.order_stock(acc, ins, xtconstant.STOCK_SELL,
                volume, xtconstant.FIX_PRICE, price,  '您的策略备注', '您的订单备注111')
            print(f"{now} 最新价 卖出 {ins} {volume}股")   
        except Exception as e:
            print('sell order error', ins, e)
            continue    
    
    for ins in buy_signal:
        now = datetime.now()
        volume = order_df[order_df['instrument'] == ins]['order_qty'].iloc[0]
        price = order_df[order_df['instrument'] == ins]['order_price'].iloc[0] * 1.05 
        price = round(price,2)
        
        try:
            async_seq = xt_trader.order_stock(acc, ins, xtconstant.STOCK_BUY,
                                              volume, xtconstant.FIX_PRICE, price, '您的策略备注', '您的订单备注222')
            print(f"{now} 最新价 买入 {ins} {volume}股")
        except Exception as e :
            print('buy order error', ins, e)
            continue 

# 设置每天早上运行 my_daily_task
#schedule.every().day.at("09:16").do(send_order,exec_time='morning')
schedule.every().day.at("14:30").do(send_order,exec_time='afternoon')

print("定时任务已启动，等待每天执行...")

# 无限循环，持续检查任务
while True:
    schedule.run_pending()  # 运行待执行的任务
    time.sleep(30)  # 每 60 秒检查一次（避免 CPU 占用过高）