# 交易策略回测系统

基于 Backtrader 框架的专业级交易策略回测系统，适合新手学习和专业使用。

## 🎯 系统特性

- **📚 新手友好**: 清晰的代码结构和详细注释，易于理解
- **🔧 专业可靠**: 基于知名的 Backtrader 框架，确保回测可靠性
- **📊 完整分析**: 提供详细的性能指标和风险分析
- **⚡ 参数优化**: 内置参数优化功能，寻找最优策略参数
- **📈 可视化**: 支持回测结果图表展示
- **🔌 易扩展**: 模块化设计，方便添加自定义策略

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## 📁 文件结构

```
backtest/
├── simple_strategy.py      # 策略实现（MA策略、RSI策略）
├── data_loader.py          # 数据加载器
├── backtest_engine.py      # 回测引擎和性能分析
├── run_backtest.py         # 主入口程序
├── requirements.txt        # 依赖文件
└── README.md              # 使用说明
```

## 🚀 快速开始

### 0. 环境检查（推荐第一步）

```bash
cd backtest
python check_setup.py
```

这个脚本会检查：
- Python版本和依赖包
- 目录结构和数据文件
- 模块导入是否正常

### 1. 基本回测

```bash
cd backtest
python run_backtest.py
```

选择模式 1 进行完整回测，系统将：
- 自动加载 `datas` 目录中的 CSV 数据
- 运行移动平均线策略
- 生成详细的性能报告
- 可选择进行参数优化

### 2. 快速示例

```bash
python run_backtest.py
```

选择模式 2 进行快速回测演示。

## 📊 策略介绍

### 移动平均线策略 (SimpleMAStrategy)

**原理**: 
- 金叉买入：短期均线上穿长期均线时买入
- 死叉卖出：短期均线下穿长期均线时卖出

**参数**:
- `ma_short`: 短期均线周期（默认10）
- `ma_long`: 长期均线周期（默认30）

### RSI策略 (RSIStrategy)

**原理**:
- 超卖买入：RSI < 30 时买入
- 超买卖出：RSI > 70 时卖出

**参数**:
- `rsi_period`: RSI计算周期（默认14）
- `rsi_upper`: 超买阈值（默认70）
- `rsi_lower`: 超卖阈值（默认30）

## 🔧 自定义使用

### 创建自定义策略

```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (
        ('param1', 10),
        ('param2', 20),
    )
    
    def __init__(self):
        # 初始化指标
        self.sma = bt.indicators.SimpleMovingAverage(period=self.params.param1)
        
    def next(self):
        # 策略逻辑
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()
        else:
            if self.data.close[0] < self.sma[0]:
                self.sell()
```

### 使用自定义策略

```python
from backtest_engine import BacktestEngine
from data_loader import CSVDataLoader

# 加载数据
loader = CSVDataLoader()
data = loader.load_data('your_data.csv')

# 运行回测
engine = BacktestEngine(initial_cash=100000)
engine.setup_cerebro()
engine.add_data(data)
engine.add_strategy(MyStrategy, param1=15, param2=25)
engine.run_backtest()
engine.print_performance_report()
```

## 📈 性能指标说明

### 基本信息
- **初始资金**: 回测开始时的资金
- **最终资金**: 回测结束时的资金
- **总收益**: 总收益率百分比
- **手续费率**: 交易手续费率

### 收益指标
- **年化收益率**: 按年计算的平均收益率
- **夏普比率**: 风险调整后的收益率，越高越好
- **SQN评分**: 系统质量数字，衡量策略稳定性

### 风险指标
- **最大回撤**: 资金从峰值下跌的最大幅度
- **最大回撤期间**: 最大回撤持续的时间
- **平均回撤**: 所有回撤的平均值

### 交易统计
- **总交易次数**: 完成的交易总数
- **胜率**: 盈利交易占总交易的比例
- **盈亏比**: 平均盈利与平均亏损的比值

## 🎛️ 参数优化

系统支持自动参数优化，寻找最优的策略参数组合：

```python
from backtest_engine import ParameterOptimizer

optimizer = ParameterOptimizer(MyStrategy, data)
results = optimizer.optimize_parameters(
    param_ranges={
        'ma_short': range(5, 20, 2),
        'ma_long': range(20, 50, 5)
    },
    optimization_target='sharpe'  # 'return', 'sharpe', 'sqn'
)
```

## 💡 使用建议

### 新手指南
1. **从简单策略开始**: 先理解移动平均线策略的逻辑
2. **观察性能指标**: 重点关注总收益、最大回撤、夏普比率
3. **多种数据测试**: 在不同的数据上测试策略稳健性
4. **参数敏感性**: 测试参数变化对策略表现的影响

### 进阶使用
1. **样本外测试**: 将数据分为训练集和测试集
2. **组合策略**: 结合多个策略或多个品种
3. **风险管理**: 添加止损、止盈机制
4. **实时监控**: 实现策略的实时运行监控

## ⚠️ 注意事项

1. **回测偏差**: 回测结果不等于实际交易结果
2. **数据质量**: 确保使用高质量、完整的历史数据
3. **过度拟合**: 避免过度优化参数导致策略失效
4. **交易成本**: 考虑实际的手续费、滑点等成本
5. **市场变化**: 策略在不同市场环境下可能表现不同

## 🔗 扩展学习

- [Backtrader 官方文档](https://www.backtrader.com/)
- [量化交易策略](https://github.com/topics/quantitative-trading)
- [技术指标说明](https://www.investopedia.com/technical-analysis-4689657)

## 📞 支持

如果在使用过程中遇到问题，请检查：
1. 数据文件格式是否正确
2. 依赖库是否安装完整
3. 策略逻辑是否符合预期

## 🛠️ 故障排除

### 常见问题

**1. "没有找到数据文件"错误**
- 确保 `datas` 目录在项目根目录下
- 确保 datas 目录中有 CSV 文件
- 运行 `python check_setup.py` 检查路径

**2. 模块导入错误**
- 确保在 `backtest` 目录中运行脚本
- 检查所有必要的 .py 文件是否存在

**3. 依赖包缺失**
```bash
pip install -r requirements.txt
```

**4. 数据格式错误**
- CSV文件必须包含：datetime, open, high, low, close, volume 列
- datetime列格式：'YYYY-MM-DD HH:MM:SS'

### 目录结构要求

```
项目根目录/
├── backtest/           # 回测系统目录
│   ├── *.py           # 回测相关脚本
│   └── requirements.txt
├── datas/             # 数据目录（必需）
│   ├── *.csv         # OHLCV数据文件
└── 其他目录...
```

### 使用步骤

1. **环境检查**: `python check_setup.py`
2. **安装依赖**: `pip install -r requirements.txt`
3. **运行回测**: `python run_backtest.py` 