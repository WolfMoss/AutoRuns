# CTA策略回测系统

基于VNPY框架的加密货币CTA策略回测系统，支持多品种、多策略的量化回测。

## 系统特点

- **结构清晰**：整体采用模块化设计，引擎、策略和工具分离
- **策略扩展性强**：提供统一的策略基类，便于快速开发新策略
- **回测准确性高**：基于VNPY成熟的回测引擎，支持手续费、滑点等真实交易成本模拟
- **全面的性能分析**：提供丰富的绩效统计指标和图表分析
- **参数优化支持**：内置参数优化功能，寻找策略最优参数

## 目录结构

```
CTA回测系统/
├── engine/             # 回测引擎目录
├── strategies/         # 策略目录
├── utils/              # 工具函数
├── config.py           # 配置文件
├── run_backtest.py     # 回测执行入口
└── requirements.txt    # 依赖库
```

## 如何使用

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置回测参数

在 `config.py` 中设置回测参数，包括:
- 交易对
- 回测时间范围
- 手续费率
- 滑点
- 初始资金等

3. 运行回测

```bash
python run_backtest.py
```

## 如何添加新策略

1. 在 `strategies` 目录下创建新的策略文件，例如 `my_strategy.py`
2. 创建一个继承自 `BaseStrategy` 的策略类
3. 实现 `calculate_signals` 方法
4. 在 `strategies/__init__.py` 中导入新策略
5. 在 `config.py` 中为新策略添加默认参数
6. 在 `run_backtest.py` 中使用新策略进行回测

## 例子

```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    # 策略参数
    param1 = 10
    param2 = 20
    
    # 策略变量
    var1 = 0
    
    # 参数列表
    parameters = ["param1", "param2"]
    variables = ["var1"]
    
    def calculate_signals(self, bar):
        # 实现交易信号逻辑
        if self.am.close[-1] > self.am.close[-2]:
            self.buy(bar.close_price, 1)
        elif self.pos > 0:
            self.sell(bar.close_price, self.pos)
```

## 回测结果示例

回测系统会生成详细的回测报告，包括:

- 总收益率
- 年化收益率
- 夏普比率
- 最大回撤
- 交易次数
- 胜率
- 盈亏比
- 月度/年度统计

同时，系统会生成回测结果图表，包括权益曲线、回撤曲线和每日盈亏情况。 