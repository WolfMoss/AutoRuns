# FinRL 入门教程 - 强化学习在金融交易中的应用
# 作者：为强化学习小白准备的入门指南

"""
FinRL入门教程：从0开始学习金融强化学习

1. 什么是FinRL？
FinRL是一个专门为金融市场设计的强化学习框架，它提供了：
- 预处理的金融数据接口
- 常用的强化学习算法实现
- 金融特定的环境和奖励函数
- 回测和评估工具

2. 安装FinRL
首先需要安装相关依赖包
"""

# 第一步：安装必要的包
# pip install finrl
# pip install stable-baselines3
# pip install yfinance
# pip install pandas numpy matplotlib

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 导入FinRL相关模块
try:
    from finrl import config
    from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
    from finrl.meta.preprocessor.yahoodownloader import YahooDownloader
    from finrl.meta.preprocessor.preprocessors import FeatureEngineer, data_split
    print("FinRL导入成功！")
except ImportError:
    print("FinRL未安装，请先运行：pip install finrl")

# 第三步：基础示例 - 股票交易环境
def create_simple_trading_example():
    """
    创建一个简单的股票交易示例
    这个例子展示了如何：
    1. 下载股票数据
    2. 预处理数据
    3. 创建交易环境
    4. 运行简单的策略
    """
    
    print("=== FinRL基础示例：股票交易 ===")
    
    # 1. 数据下载和预处理
    print("1. 下载股票数据...")
    
    # 设置股票列表和时间范围
    STOCK_LIST = ["AAPL", "MSFT", "GOOGL"]  # 示例股票
    START_DATE = "2020-01-01"
    END_DATE = "2023-01-01"
    
    try:
        # 下载数据
        df = YahooDownloader(start_date=START_DATE,
                           end_date=END_DATE,
                           ticker_list=STOCK_LIST).fetch_data()
        
        print(f"数据下载完成，共{len(df)}行数据")
        print(df.head())
        
    except Exception as e:
        print(f"数据下载失败：{e}")
        print("使用模拟数据进行演示...")
        # 创建模拟数据
        df = create_mock_data(STOCK_LIST, START_DATE, END_DATE)
    
    # 2. 特征工程
    print("\n2. 特征工程...")
    fe = FeatureEngineer(use_technical_indicator=True,
                        tech_indicator_list=config.TECHNICAL_INDICATORS_LIST,
                        use_vix=True,
                        use_turbulence=True,
                        user_defined_feature=False)
    
    processed = fe.preprocess_data(df)
    print(f"特征工程完成，特征数：{len(processed.columns)}")
    
    # 3. 数据分割
    print("\n3. 数据分割...")
    train = data_split(processed, START_DATE, "2022-01-01")
    trade = data_split(processed, "2022-01-01", END_DATE)
    
    print(f"训练数据：{len(train)}行")
    print(f"交易数据：{len(trade)}行")
    
    return train, trade

def create_mock_data(stock_list, start_date, end_date):
    """
    创建模拟股票数据用于演示
    """
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    data = []
    
    for stock in stock_list:
        for date in dates:
            # 生成模拟价格数据
            base_price = 100 + np.random.randn() * 10
            data.append({
                'date': date,
                'tic': stock,
                'open': base_price + np.random.randn(),
                'high': base_price + abs(np.random.randn()),
                'low': base_price - abs(np.random.randn()),
                'close': base_price + np.random.randn() * 0.5,
                'volume': np.random.randint(1000000, 10000000)
            })
    
    return pd.DataFrame(data)

# 第四步：使用您现有的加密货币数据
def use_crypto_data_with_finrl():
    """
    使用您现有的DOGE数据创建FinRL环境
    """
    print("=== 使用您的加密货币数据 ===")
    
    # 读取您的DOGE数据
    try:
        df = pd.read_csv('datas/DOGE_USDT_1h.csv')
        print(f"成功读取DOGE数据，共{len(df)}行")
        print("数据列：", df.columns.tolist())
        print(df.head())
        
        # 数据预处理，转换为FinRL格式
        df_finrl = prepare_crypto_data_for_finrl(df)
        return df_finrl
        
    except Exception as e:
        print(f"读取数据失败：{e}")
        return None

def prepare_crypto_data_for_finrl(df):
    """
    将加密货币数据转换为FinRL格式
    """
    # 假设您的数据包含：timestamp, open, high, low, close, volume
    # 需要转换为FinRL期望的格式
    
    df_copy = df.copy()
    
    # 确保有必要的列
    required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'tic']
    
    # 如果没有date列，从timestamp转换
    if 'timestamp' in df_copy.columns and 'date' not in df_copy.columns:
        df_copy['date'] = pd.to_datetime(df_copy['timestamp'])
    
    # 添加股票代码
    df_copy['tic'] = 'DOGE-USDT'
    
    # 确保数据类型正确
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    
    return df_copy[required_columns]

# 第五步：创建简单的交易策略
class SimpleStrategy:
    """
    简单的交易策略示例
    这是一个基于技术指标的策略，不使用强化学习
    """
    
    def __init__(self, data):
        self.data = data
        self.position = 0  # 0: 无仓位, 1: 做多, -1: 做空
        self.balance = 10000  # 初始资金
        self.trades = []
    
    def calculate_sma(self, window=20):
        """计算简单移动平均"""
        return self.data['close'].rolling(window=window).mean()
    
    def run_strategy(self):
        """运行策略"""
        sma_short = self.calculate_sma(5)
        sma_long = self.calculate_sma(20)
        
        for i in range(20, len(self.data)):
            # 简单策略：短期均线上穿长期均线买入，下穿卖出
            if sma_short.iloc[i] > sma_long.iloc[i] and self.position <= 0:
                # 买入信号
                self.position = 1
                price = self.data['close'].iloc[i]
                self.trades.append({
                    'action': 'BUY',
                    'price': price,
                    'date': self.data.index[i]
                })
                print(f"买入信号: {price:.4f}")
            
            elif sma_short.iloc[i] < sma_long.iloc[i] and self.position >= 0:
                # 卖出信号
                self.position = -1
                price = self.data['close'].iloc[i]
                self.trades.append({
                    'action': 'SELL',
                    'price': price,
                    'date': self.data.index[i]
                })
                print(f"卖出信号: {price:.4f}")
        
        return self.trades

# 主函数：运行示例
def main():
    """
    主函数：演示FinRL的基本使用
    """
    print("欢迎使用FinRL入门教程！")
    print("作为强化学习小白，您将学习：")
    print("1. FinRL的基本概念")
    print("2. 如何处理金融数据")
    print("3. 如何创建交易环境")
    print("4. 如何应用到您的加密货币数据")
    print("\n" + "="*50)
    
    # 尝试使用您的数据
    crypto_data = use_crypto_data_with_finrl()
    
    if crypto_data is not None:
        print("\n使用您的DOGE数据运行简单策略...")
        # 运行简单策略示例
        try:
            strategy = SimpleStrategy(crypto_data)
            trades = strategy.run_strategy()
            print(f"策略执行完成，共产生{len(trades)}个交易信号")
        except Exception as e:
            print(f"策略执行出错：{e}")
    
    print("\n下一步学习建议：")
    print("1. 安装FinRL：pip install finrl")
    print("2. 学习强化学习基础概念")
    print("3. 尝试修改奖励函数")
    print("4. 使用不同的RL算法（PPO, A2C, SAC等）")
    print("5. 在您的DOGE数据上训练模型")

if __name__ == "__main__":
    main() 