# -*-coding:utf-8-*-
import datetime
import time
import pandas as pd
import numpy as np
import schedule
from xtquant import xtdata
from xtquant import xtconstant
from Config import *

pd.set_option('expand_frame_repr', False)
pd.set_option('display.max_rows', 5000)

class SmallCapStrategy:
    def __init__(self):
        self.max_holdings = 10  # 最大持仓数量
        self.max_price = 20.0   # 最大股价限制
        self.position_ratio = 0.1  # 每只股票占总资产的比例
        
    def get_all_stocks(self):
        """获取A股所有股票列表"""
        try:
            # 获取沪深A股股票列表
            stock_list_sh = xtdata.get_stock_list_in_sector('沪深A股')
            if stock_list_sh is None:
                # 如果上面的方法不可用，尝试获取全市场股票
                stock_list_sh = xtdata.get_stock_list_in_sector('全A股')
            
            if stock_list_sh is None:
                # 备用方案：手动构建常见的A股代码范围
                stock_list = []
                # 深交所主板 000001-000999
                for i in range(1, 1000):
                    code = f"{i:06d}.SZ"
                    stock_list.append(code)
                # 深交所中小板 002001-002999  
                for i in range(2001, 3000):
                    code = f"{i:06d}.SZ"
                    stock_list.append(code)
                # 上交所主板 600000-609999
                for i in range(600000, 610000):
                    code = f"{i:06d}.SH"
                    stock_list.append(code)
                return stock_list
            else:
                return stock_list_sh
        except Exception as e:
            print(f"获取股票列表失败：{e}")
            return []
    
    def filter_stocks(self, stock_list):
        """过滤股票：排除ST、科创板、北交所"""
        filtered_stocks = []
        
        for stock in stock_list:
            # 排除科创板（688开头）
            if stock.startswith('688'):
                continue
            # 排除北交所（8开头或43开头）
            if stock.startswith('8') or stock.startswith('43'):
                continue
            # 排除创业板中的特殊情况
            if stock.startswith('30') and stock.endswith('.SZ'):
                # 创业板保留，但后续会检查ST
                pass
            
            # 获取股票基本信息，检查是否为ST股票
            try:
                # 尝试获取股票名称
                instrument_info = xtdata.get_instrument_detail(stock)
                if instrument_info and 'InstrumentName' in instrument_info:
                    stock_name = instrument_info['InstrumentName']
                    # 排除ST股票
                    if 'ST' in stock_name or '*ST' in stock_name:
                        continue
                
                filtered_stocks.append(stock)
            except:
                # 如果获取股票信息失败，跳过该股票
                continue
                
        return filtered_stocks
    
    def get_stock_data(self, stock_list):
        """获取股票的价格和市值数据"""
        stock_data = []
        
        # 分批获取数据，每批处理100只股票
        batch_size = 100
        for i in range(0, len(stock_list), batch_size):
            batch_stocks = stock_list[i:i+batch_size]
            
            try:
                # 获取实时行情数据
                quote_data = xtdata.get_full_tick(batch_stocks)
                
                for stock in batch_stocks:
                    if stock in quote_data:
                        tick_data = quote_data[stock]
                        current_price = tick_data.get('lastPrice', 0)
                        
                        # 过滤股价超过20元的股票
                        if current_price > self.max_price or current_price <= 0:
                            continue
                        
                        # 获取股票基本信息（包含总股本等）
                        try:
                            # 尝试获取财务数据计算市值
                            financial_data = xtdata.get_financial_data([stock], ['TotalShare'], start_time='20231201', end_time='20241201')
                            
                            if financial_data and stock in financial_data:
                                total_shares = financial_data[stock].get('TotalShare', [0])
                                if total_shares and len(total_shares) > 0:
                                    # 市值 = 股价 * 总股本（亿股）
                                    market_cap = current_price * total_shares[-1] * 100000000  # 转换为元
                                else:
                                    # 如果无法获取总股本，使用成交额作为粗略估计
                                    market_cap = tick_data.get('amount', 999999999999)
                            else:
                                # 备用方案：用成交额粗略估计市值
                                market_cap = tick_data.get('amount', 999999999999)
                            
                            stock_data.append({
                                'stock_code': stock,
                                'price': current_price,
                                'market_cap': market_cap
                            })
                            
                        except Exception as e:
                            print(f"获取{stock}财务数据失败：{e}")
                            continue
                            
            except Exception as e:
                print(f"获取行情数据失败：{e}")
                continue
                
        return stock_data
    
    def select_stocks(self):
        """选股：选择市值最小的10只股票"""
        print("开始选股...")
        
        # 获取所有股票
        all_stocks = self.get_all_stocks()
        print(f"获取到{len(all_stocks)}只股票")
        
        # 过滤股票
        filtered_stocks = self.filter_stocks(all_stocks)
        print(f"过滤后剩余{len(filtered_stocks)}只股票")
        
        # 获取股票数据
        stock_data = self.get_stock_data(filtered_stocks)
        print(f"成功获取{len(stock_data)}只股票的数据")
        
        if not stock_data:
            print("没有获取到有效的股票数据")
            return []
        
        # 按市值排序，选择最小的10只
        df = pd.DataFrame(stock_data)
        df = df.sort_values('market_cap')
        selected_stocks = df.head(self.max_holdings)['stock_code'].tolist()
        
        print("选出的股票：")
        for i, row in df.head(self.max_holdings).iterrows():
            print(f"{row['stock_code']}: 价格{row['price']:.2f}, 市值{row['market_cap']:.0f}")
        
        return selected_stocks
    
    def get_current_positions(self):
        """获取当前持仓"""
        try:
            positions = xt_trader.query_stock_positions(account_putong)
            current_holdings = {}
            
            for pos in positions:
                if pos.volume > 0:  # 只考虑有持仓的股票
                    current_holdings[pos.stock_code] = pos.volume
                    
            return current_holdings
        except Exception as e:
            print(f"获取持仓信息失败：{e}")
            return {}
    
    def get_account_asset(self):
        """获取账户总资产"""
        try:
            asset = xt_trader.query_stock_asset(account_putong)
            if asset:
                return asset.total_asset
            return 0
        except Exception as e:
            print(f"获取账户资产失败：{e}")
            return 0
    
    def calculate_buy_volume(self, stock_price, total_asset):
        """计算买入数量"""
        target_amount = total_asset * self.position_ratio  # 目标金额
        buy_volume = int(target_amount / stock_price / 100) * 100  # 向下取整到100股的倍数
        return max(buy_volume, 0)
    
    def execute_trades(self, selected_stocks):
        """执行交易"""
        print("开始执行交易...")
        
        # 获取当前持仓
        current_holdings = self.get_current_positions()
        print(f"当前持仓：{current_holdings}")
        
        # 获取账户总资产
        total_asset = self.get_account_asset()
        print(f"账户总资产：{total_asset}")
        
        if total_asset <= 0:
            print("账户总资产为0，无法执行交易")
            return
        
        # 卖出不在目标股票池中的持仓
        for stock_code, volume in current_holdings.items():
            if stock_code not in selected_stocks:
                print(f"卖出{stock_code}，数量：{volume}")
                try:
                    order_id = xt_trader.order_stock(
                        account_putong, 
                        stock_code, 
                        xtconstant.STOCK_SELL, 
                        volume, 
                        xtconstant.LATEST_PRICE, 
                        -1, 
                        'small_cap_strategy', 
                        f'小市值策略卖出{stock_code}'
                    )
                    print(f"卖出订单号：{order_id}")
                except Exception as e:
                    print(f"卖出{stock_code}失败：{e}")
        
        # 买入目标股票（不在当前持仓中的）
        for stock_code in selected_stocks:
            if stock_code not in current_holdings:
                try:
                    # 获取当前股价
                    quote_data = xtdata.get_full_tick([stock_code])
                    if stock_code in quote_data:
                        current_price = quote_data[stock_code].get('lastPrice', 0)
                        
                        if current_price > 0:
                            # 计算买入数量
                            buy_volume = self.calculate_buy_volume(current_price, total_asset)
                            
                            if buy_volume >= 100:  # 至少买入1手
                                print(f"买入{stock_code}，价格：{current_price}，数量：{buy_volume}")
                                order_id = xt_trader.order_stock(
                                    account_putong,
                                    stock_code,
                                    xtconstant.STOCK_BUY,
                                    buy_volume,
                                    xtconstant.LATEST_PRICE,
                                    -1,
                                    'small_cap_strategy',
                                    f'小市值策略买入{stock_code}'
                                )
                                print(f"买入订单号：{order_id}")
                            else:
                                print(f"{stock_code}计算买入数量不足100股，跳过")
                        else:
                            print(f"{stock_code}获取价格失败，跳过")
                    else:
                        print(f"{stock_code}获取行情失败，跳过")
                        
                except Exception as e:
                    print(f"买入{stock_code}失败：{e}")
    
    def run_strategy(self):
        """运行策略主逻辑"""
        print(f"开始执行小市值策略 - {datetime.datetime.now()}")
        
        try:
            # 选股
            selected_stocks = self.select_stocks()
            
            if not selected_stocks:
                print("没有选出合适的股票，本次不执行交易")
                return
            
            # 执行交易
            self.execute_trades(selected_stocks)
            
            print("策略执行完成")
            
        except Exception as e:
            print(f"策略执行过程中发生错误：{e}")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    strategy = SmallCapStrategy()
    
    # 设置定时任务：每周一14:00执行
    schedule.every().monday.at("14:00").do(strategy.run_strategy)
    
    print("小市值策略已启动，等待每周一14:00执行...")
    print("当前时间：", datetime.datetime.now())
    
    # 可以先手动执行一次测试
    print("是否要立即执行一次测试？(输入y确认)")
    user_input = input()
    if user_input.lower() == 'y':
        strategy.run_strategy()
    
    # 定时循环检查
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    main() 