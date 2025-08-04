# DOGE-USDT 强化学习交易示例
# 使用FinRL框架训练交易智能体

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 检查并导入FinRL
try:
    from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
    from finrl.agents.stablebaselines3.models import DRLAgent
    from finrl.meta.preprocessor.preprocessors import FeatureEngineer
    print("✓ FinRL导入成功！")
except ImportError as e:
    print(f"❌ FinRL导入失败: {e}")
    print("请先安装：pip install finrl")

# 导入强化学习算法
try:
    from stable_baselines3 import PPO, A2C, DDPG
    print("✓ Stable-Baselines3导入成功！")
except ImportError:
    print("❌ 请安装：pip install stable-baselines3")

class DOGEDataProcessor:
    """
    DOGE数据处理器
    专门用于处理加密货币数据并转换为FinRL格式
    """
    
    def __init__(self, data_path='datas/DOGE_USDT_1h.csv'):
        self.data_path = data_path
        self.df = None
        
    def load_data(self):
        """加载DOGE数据"""
        try:
            self.df = pd.read_csv(self.data_path)
            print(f"✓ 成功加载数据：{len(self.df)}行")
            print(f"数据列：{list(self.df.columns)}")
            return True
        except Exception as e:
            print(f"❌ 数据加载失败：{e}")
            return False
    
    def preprocess_for_finrl(self):
        """
        将DOGE数据转换为FinRL标准格式
        FinRL需要的列：date, open, high, low, close, volume, tic
        """
        if self.df is None:
            print("❌ 请先加载数据")
            return None
        
        df_processed = self.df.copy()
        
        # 1. 处理时间列
        if 'timestamp' in df_processed.columns:
            df_processed['date'] = pd.to_datetime(df_processed['timestamp'], unit='ms')
        elif 'date' in df_processed.columns:
            df_processed['date'] = pd.to_datetime(df_processed['date'])
        else:
            print("❌ 未找到时间列")
            return None
        
        # 2. 添加交易对标识
        df_processed['tic'] = 'DOGE-USDT'
        
        # 3. 确保必要的价格和成交量列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df_processed.columns:
                print(f"❌ 缺少必要列：{col}")
                return None
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
        
        # 4. 排序并重置索引
        df_processed = df_processed.sort_values('date').reset_index(drop=True)
        
        # 5. 选择FinRL需要的列
        finrl_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'tic']
        df_finrl = df_processed[finrl_columns].copy()
        
        # 6. 删除包含NaN的行
        df_finrl = df_finrl.dropna()
        
        print(f"✓ 数据预处理完成：{len(df_finrl)}行")
        print(f"时间范围：{df_finrl['date'].min()} 到 {df_finrl['date'].max()}")
        
        return df_finrl

class DOGETrainingEnv:
    """
    DOGE交易环境构建器
    用于创建强化学习训练环境
    """
    
    def __init__(self, df_finrl):
        self.df = df_finrl
        self.train_data = None
        self.test_data = None
        
    def split_data(self, train_ratio=0.8):
        """分割训练和测试数据"""
        split_point = int(len(self.df) * train_ratio)
        self.train_data = self.df[:split_point].copy()
        self.test_data = self.df[split_point:].copy()
        
        print(f"✓ 数据分割完成：")
        print(f"  训练数据：{len(self.train_data)}行")
        print(f"  测试数据：{len(self.test_data)}行")
        
        return self.train_data, self.test_data
    
    def add_technical_indicators(self, df):
        """添加技术指标"""
        df_with_indicators = df.copy()
        
        # 简单移动平均
        df_with_indicators['sma_5'] = df['close'].rolling(5).mean()
        df_with_indicators['sma_20'] = df['close'].rolling(20).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df_with_indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df_with_indicators['macd'] = exp1 - exp2
        df_with_indicators['macd_signal'] = df_with_indicators['macd'].ewm(span=9).mean()
        
        # 成交量移动平均
        df_with_indicators['volume_sma'] = df['volume'].rolling(20).mean()
        
        # 删除NaN行
        df_with_indicators = df_with_indicators.dropna().reset_index(drop=True)
        
        print(f"✓ 技术指标计算完成，最终数据：{len(df_with_indicators)}行")
        return df_with_indicators
    
    def create_trading_env(self, df, initial_balance=10000):
        """创建交易环境"""
        # 设置环境参数
        stock_dimension = len(df['tic'].unique())
        state_space = 1 + 2 * stock_dimension + len([col for col in df.columns if col not in ['date', 'tic']])
        
        print(f"环境设置：")
        print(f"  股票维度：{stock_dimension}")
        print(f"  状态空间：{state_space}")
        print(f"  初始资金：${initial_balance}")
        
        # 创建环境
        env_kwargs = {
            "hmax": 100,  # 最大持仓
            "initial_amount": initial_balance,
            "buy_cost_pct": 0.001,  # 买入手续费0.1%
            "sell_cost_pct": 0.001,  # 卖出手续费0.1%
            "state_space": state_space,
            "stock_dim": stock_dimension,
            "tech_indicator_list": [col for col in df.columns if col not in ['date', 'tic', 'open', 'high', 'low', 'close', 'volume']],
            "action_space": stock_dimension,
            "reward_scaling": 1e-4
        }
        
        try:
            env = StockTradingEnv(df=df, **env_kwargs)
            print("✓ 交易环境创建成功！")
            return env
        except Exception as e:
            print(f"❌ 环境创建失败：{e}")
            return None

class DOGETrainer:
    """
    DOGE强化学习训练器
    """
    
    def __init__(self, env_train):
        self.env_train = env_train
        self.model = None
        
    def train_ppo_agent(self, total_timesteps=10000):
        """使用PPO算法训练智能体"""
        print("开始使用PPO算法训练...")
        
        try:
            # 创建PPO智能体
            agent = DRLAgent(env=self.env_train)
            model_ppo = agent.get_model("ppo")
            
            # 训练模型
            trained_ppo = agent.train_model(
                model=model_ppo,
                tb_log_name='ppo',
                total_timesteps=total_timesteps
            )
            
            self.model = trained_ppo
            print(f"✓ PPO训练完成！总步数：{total_timesteps}")
            return trained_ppo
            
        except Exception as e:
            print(f"❌ 训练失败：{e}")
            return None
    
    def save_model(self, path="models/doge_ppo_model"):
        """保存训练好的模型"""
        if self.model is None:
            print("❌ 没有可保存的模型")
            return False
        
        try:
            self.model.save(path)
            print(f"✓ 模型已保存到：{path}")
            return True
        except Exception as e:
            print(f"❌ 模型保存失败：{e}")
            return False

def run_doge_backtest(model, env_test):
    """运行回测"""
    print("开始回测...")
    
    try:
        # 重置测试环境
        obs = env_test.reset()
        
        # 记录交易历史
        account_memory = []
        actions_memory = []
        
        # 运行回测
        done = False
        while not done:
            action, _states = model.predict(obs)
            obs, rewards, done, info = env_test.step(action)
            
            # 记录状态
            account_memory.append(env_test.asset_memory[-1])
            actions_memory.append(action)
        
        print(f"✓ 回测完成！")
        print(f"最终资产：${account_memory[-1]:.2f}")
        print(f"收益率：{(account_memory[-1]/account_memory[0] - 1)*100:.2f}%")
        
        return account_memory, actions_memory
        
    except Exception as e:
        print(f"❌ 回测失败：{e}")
        return None, None

def main():
    """主函数：完整的DOGE强化学习交易流程"""
    print("🚀 DOGE-USDT 强化学习交易系统")
    print("=" * 50)
    
    # 1. 数据加载和预处理
    print("\n📊 步骤1：数据处理")
    processor = DOGEDataProcessor()
    
    if not processor.load_data():
        return
    
    df_finrl = processor.preprocess_for_finrl()
    if df_finrl is None:
        return
    
    # 2. 创建训练环境
    print("\n🏋️ 步骤2：创建训练环境")
    env_builder = DOGETrainingEnv(df_finrl)
    train_data, test_data = env_builder.split_data()
    
    # 添加技术指标
    train_data_with_tech = env_builder.add_technical_indicators(train_data)
    test_data_with_tech = env_builder.add_technical_indicators(test_data)
    
    # 创建环境
    env_train = env_builder.create_trading_env(train_data_with_tech)
    env_test = env_builder.create_trading_env(test_data_with_tech)
    
    if env_train is None or env_test is None:
        return
    
    # 3. 训练模型
    print("\n🤖 步骤3：强化学习训练")
    trainer = DOGETrainer(env_train)
    model = trainer.train_ppo_agent(total_timesteps=5000)  # 较小的步数用于快速测试
    
    if model is None:
        return
    
    # 保存模型
    trainer.save_model()
    
    # 4. 回测
    print("\n📈 步骤4：策略回测")
    account_memory, actions_memory = run_doge_backtest(model, env_test)
    
    if account_memory is not None:
        # 绘制收益曲线
        plt.figure(figsize=(12, 6))
        plt.plot(account_memory)
        plt.title('DOGE-USDT 强化学习策略回测结果')
        plt.xlabel('时间步')
        plt.ylabel('账户价值 ($)')
        plt.grid(True)
        plt.savefig('doge_rl_backtest.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("\n🎉 FinRL入门成功完成！")
        print("下一步建议：")
        print("1. 调整超参数优化性能")
        print("2. 尝试不同的RL算法（A2C, DDPG, SAC）")
        print("3. 添加更多技术指标")
        print("4. 实现更复杂的奖励函数")

if __name__ == "__main__":
    main() 