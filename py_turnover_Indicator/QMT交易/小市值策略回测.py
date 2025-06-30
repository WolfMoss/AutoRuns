# -*-coding:utf-8-*-
import datetime
import pandas as pd
import numpy as np
from xtquant import xtdata
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class SmallCapBacktest:
    def __init__(self, start_date='20230101', end_date='20241201', initial_capital=100000):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital  # 初始资金
        self.max_holdings = 10
        self.max_price = 20.0
        self.position_ratio = 0.1
        self.commission_rate = 0.0003  # 手续费率
        self.stamp_tax = 0.001  # 印花税（卖出时）
        
        # 回测结果存储
        self.portfolio_value = []
        self.dates = []
        self.positions = {}
        self.trades = []
        self.returns = []
        
    def get_trading_dates(self):
        """获取交易日期（每周一）"""
        start = pd.to_datetime(self.start_date)
        end = pd.to_datetime(self.end_date)
        
        # 生成所有周一的日期
        trading_dates = []
        current_date = start
        
        while current_date <= end:
            # 找到当周的周一
            days_since_monday = current_date.weekday()
            monday = current_date - pd.Timedelta(days=days_since_monday)
            
            if monday >= start and monday <= end:
                trading_dates.append(monday.strftime('%Y%m%d'))
            
            # 移动到下一周
            current_date += pd.Timedelta(days=7)
        
        return sorted(list(set(trading_dates)))
    
    def get_stock_universe(self, date):
        """获取指定日期的股票池（模拟过滤逻辑）"""
        try:
            # 获取所有A股股票代码
            all_stocks = []
            
            # 深交所主板和中小板
            for i in range(1, 1000):
                all_stocks.append(f"{i:06d}.SZ")
            for i in range(2001, 3000):
                all_stocks.append(f"{i:06d}.SZ")
            
            # 上交所主板
            for i in range(600000, 610000):
                all_stocks.append(f"{i:06d}.SH")
            
            # 过滤掉科创板和北交所
            filtered_stocks = []
            for stock in all_stocks:
                if not stock.startswith('688') and not stock.startswith('8') and not stock.startswith('43'):
                    filtered_stocks.append(stock)
            
            return filtered_stocks[:500]  # 限制数量以提高回测速度
            
        except Exception as e:
            print(f"获取股票池失败：{e}")
            return []
    
    def get_stock_data_for_date(self, stock_list, date):
        """获取指定日期的股票数据"""
        stock_data = []
        
        try:
            # 获取历史行情数据
            end_date = pd.to_datetime(date).strftime('%Y%m%d')
            start_date = (pd.to_datetime(date) - pd.Timedelta(days=5)).strftime('%Y%m%d')
            
            for stock in stock_list:
                try:
                    # 获取股票价格数据
                    price_data = xtdata.get_market_data(
                        stock_list=[stock],
                        period='1d',
                        start_time=start_date,
                        end_time=end_date,
                        field_list=['close', 'volume', 'amount']
                    )
                    
                    if price_data and stock in price_data:
                        df = price_data[stock]
                        if not df.empty:
                            latest_data = df.iloc[-1]
                            close_price = latest_data['close']
                            volume = latest_data['volume']
                            amount = latest_data['amount']
                            
                            # 过滤股价和成交量
                            if close_price <= self.max_price and close_price > 0 and volume > 0:
                                # 简单市值估算：用成交额作为市值代理
                                estimated_market_cap = amount * 100  # 粗略估算
                                
                                stock_data.append({
                                    'stock_code': stock,
                                    'price': close_price,
                                    'market_cap': estimated_market_cap,
                                    'volume': volume,
                                    'amount': amount
                                })
                                
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"获取{date}股票数据失败：{e}")
        
        return stock_data
    
    def select_stocks_for_date(self, date):
        """为指定日期选择小市值股票"""
        print(f"选股日期：{date}")
        
        # 获取股票池
        stock_universe = self.get_stock_universe(date)
        print(f"股票池大小：{len(stock_universe)}")
        
        # 获取股票数据
        stock_data = self.get_stock_data_for_date(stock_universe, date)
        print(f"获取到有效数据的股票数量：{len(stock_data)}")
        
        if not stock_data:
            return []
        
        # 按市值排序选择
        df = pd.DataFrame(stock_data)
        df = df.sort_values('market_cap')
        selected_stocks = df.head(self.max_holdings)
        
        result = []
        for _, row in selected_stocks.iterrows():
            result.append({
                'stock_code': row['stock_code'],
                'price': row['price'],
                'market_cap': row['market_cap']
            })
        
        print(f"选出股票数量：{len(result)}")
        return result
    
    def calculate_transaction_cost(self, amount, is_sell=False):
        """计算交易成本"""
        commission = amount * self.commission_rate
        commission = max(commission, 5)  # 最低5元
        
        stamp_tax = amount * self.stamp_tax if is_sell else 0
        
        return commission + stamp_tax
    
    def execute_rebalance(self, date, selected_stocks, current_portfolio_value):
        """执行组合调仓"""
        current_positions = self.positions.copy()
        new_positions = {}
        
        # 计算目标持仓
        target_positions = {}
        for stock_info in selected_stocks:
            stock_code = stock_info['stock_code']
            price = stock_info['price']
            target_value = current_portfolio_value * self.position_ratio
            target_shares = int(target_value / price / 100) * 100  # 向下取整到100的倍数
            
            if target_shares >= 100:
                target_positions[stock_code] = {
                    'shares': target_shares,
                    'price': price
                }
        
        # 卖出不在目标组合中的股票
        total_sell_value = 0
        for stock_code, position in current_positions.items():
            if stock_code not in target_positions:
                # 获取当前价格
                sell_price = self.get_stock_price_for_date(stock_code, date)
                if sell_price > 0:
                    sell_value = position['shares'] * sell_price
                    transaction_cost = self.calculate_transaction_cost(sell_value, is_sell=True)
                    net_sell_value = sell_value - transaction_cost
                    total_sell_value += net_sell_value
                    
                    self.trades.append({
                        'date': date,
                        'stock_code': stock_code,
                        'action': 'sell',
                        'shares': position['shares'],
                        'price': sell_price,
                        'value': sell_value,
                        'cost': transaction_cost
                    })
                    
                    print(f"卖出 {stock_code}: {position['shares']}股 @ {sell_price:.2f}")
        
        # 买入目标股票
        available_cash = total_sell_value
        for stock_code, target_pos in target_positions.items():
            if stock_code not in current_positions:
                buy_value = target_pos['shares'] * target_pos['price']
                transaction_cost = self.calculate_transaction_cost(buy_value)
                total_cost = buy_value + transaction_cost
                
                if total_cost <= available_cash:
                    available_cash -= total_cost
                    new_positions[stock_code] = target_pos
                    
                    self.trades.append({
                        'date': date,
                        'stock_code': stock_code,
                        'action': 'buy',
                        'shares': target_pos['shares'],
                        'price': target_pos['price'],
                        'value': buy_value,
                        'cost': transaction_cost
                    })
                    
                    print(f"买入 {stock_code}: {target_pos['shares']}股 @ {target_pos['price']:.2f}")
            else:
                # 保持现有持仓
                new_positions[stock_code] = current_positions[stock_code]
        
        self.positions = new_positions
        return available_cash
    
    def get_stock_price_for_date(self, stock_code, date):
        """获取指定日期的股票价格"""
        try:
            end_date = pd.to_datetime(date).strftime('%Y%m%d')
            start_date = (pd.to_datetime(date) - pd.Timedelta(days=5)).strftime('%Y%m%d')
            
            price_data = xtdata.get_market_data(
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=end_date,
                field_list=['close']
            )
            
            if price_data and stock_code in price_data:
                df = price_data[stock_code]
                if not df.empty:
                    return df.iloc[-1]['close']
            
            return 0
        except:
            return 0
    
    def calculate_portfolio_value(self, date):
        """计算组合总价值"""
        total_value = 0
        
        for stock_code, position in self.positions.items():
            current_price = self.get_stock_price_for_date(stock_code, date)
            if current_price > 0:
                stock_value = position['shares'] * current_price
                total_value += stock_value
        
        return total_value
    
    def run_backtest(self):
        """运行回测"""
        print("开始回测...")
        print(f"回测期间：{self.start_date} - {self.end_date}")
        print(f"初始资金：{self.initial_capital:,.0f}元")
        
        trading_dates = self.get_trading_dates()
        print(f"交易日期数量：{len(trading_dates)}")
        
        current_cash = self.initial_capital
        
        for i, date in enumerate(trading_dates):
            print(f"\n{'='*50}")
            print(f"交易日期：{date} ({i+1}/{len(trading_dates)})")
            
            # 选股
            selected_stocks = self.select_stocks_for_date(date)
            
            if not selected_stocks:
                print("未选出股票，跳过本期")
                portfolio_value = self.calculate_portfolio_value(date) + current_cash
            else:
                # 计算当前组合价值
                holdings_value = self.calculate_portfolio_value(date)
                portfolio_value = holdings_value + current_cash
                
                # 执行调仓
                remaining_cash = self.execute_rebalance(date, selected_stocks, portfolio_value)
                current_cash = remaining_cash
                
                # 重新计算组合价值
                portfolio_value = self.calculate_portfolio_value(date) + current_cash
            
            # 记录结果
            self.portfolio_value.append(portfolio_value)
            self.dates.append(pd.to_datetime(date))
            
            # 计算收益率
            if i == 0:
                period_return = 0
            else:
                period_return = (portfolio_value - self.portfolio_value[i-1]) / self.portfolio_value[i-1]
            
            self.returns.append(period_return)
            
            print(f"组合价值：{portfolio_value:,.0f}元")
            print(f"期间收益：{period_return:.2%}")
            print(f"累计收益：{(portfolio_value/self.initial_capital-1):.2%}")
        
        print("\n回测完成！")
        self.analyze_results()
    
    def analyze_results(self):
        """分析回测结果"""
        if not self.portfolio_value:
            print("没有回测数据")
            return
        
        df_results = pd.DataFrame({
            'date': self.dates,
            'portfolio_value': self.portfolio_value,
            'returns': self.returns
        })
        
        # 计算关键指标
        total_return = (self.portfolio_value[-1] / self.initial_capital - 1)
        annual_return = (1 + total_return) ** (252 / len(self.returns)) - 1
        volatility = np.std(self.returns) * np.sqrt(52)  # 周频数据年化
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        max_drawdown = 0
        peak = self.portfolio_value[0]
        for value in self.portfolio_value:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        print("\n" + "="*60)
        print("回测结果分析")
        print("="*60)
        print(f"总收益率：{total_return:.2%}")
        print(f"年化收益率：{annual_return:.2%}")
        print(f"年化波动率：{volatility:.2%}")
        print(f"夏普比率：{sharpe_ratio:.2f}")
        print(f"最大回撤：{max_drawdown:.2%}")
        print(f"交易次数：{len(self.trades)}")
        
        # 胜率统计
        profitable_trades = sum(1 for ret in self.returns if ret > 0)
        win_rate = profitable_trades / len(self.returns) if self.returns else 0
        print(f"胜率：{win_rate:.2%}")
        
        # 绘制净值曲线
        self.plot_results(df_results)
        
        # 保存详细结果
        self.save_results(df_results)
    
    def plot_results(self, df_results):
        """绘制回测结果图表"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 净值曲线
        ax1.plot(df_results['date'], df_results['portfolio_value'], 'b-', linewidth=2)
        ax1.set_title('组合净值曲线', fontsize=14)
        ax1.set_ylabel('组合价值（元）')
        ax1.grid(True, alpha=0.3)
        ax1.ticklabel_format(style='plain', axis='y')
        
        # 收益率分布
        ax2.hist(df_results['returns'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.set_title('收益率分布', fontsize=14)
        ax2.set_xlabel('收益率')
        ax2.set_ylabel('频次')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('小市值策略回测结果.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def save_results(self, df_results):
        """保存回测结果"""
        # 保存净值数据
        df_results.to_csv('小市值策略回测净值.csv', index=False, encoding='utf-8-sig')
        
        # 保存交易记录
        if self.trades:
            df_trades = pd.DataFrame(self.trades)
            df_trades.to_csv('小市值策略交易记录.csv', index=False, encoding='utf-8-sig')
        
        print("\n结果已保存到文件：")
        print("- 小市值策略回测净值.csv")
        print("- 小市值策略交易记录.csv")
        print("- 小市值策略回测结果.png")

def main():
    """主函数"""
    print("小市值策略回测系统")
    print("="*50)
    
    # 设置回测参数
    start_date = input("请输入开始日期(YYYYMMDD，默认20230101)：") or "20240401"
    end_date = input("请输入结束日期(YYYYMMDD，默认20241201)：") or "20250627"
    initial_capital = float(input("请输入初始资金(默认100000)：") or "20000")
    
    # 创建回测实例
    backtest = SmallCapBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    # 运行回测
    backtest.run_backtest()

if __name__ == "__main__":
    main() 