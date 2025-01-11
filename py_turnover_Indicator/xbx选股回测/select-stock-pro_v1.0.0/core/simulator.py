"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import numba as nb
import numpy as np
from numba.experimental import jitclass
"""
# 新语法小讲堂
通过操作对象的值而不是更换reference，来保证所有引用的位置都能同步更新。

`self.target_lots[:] = target_lots`
这个写法涉及 Python 中的切片（slice）操作和对象的属性赋值。

`target_lots: nb.int64[:]  # 目标持仓手数`，self.target_lots 是一个列表，`[:]` 是切片操作符，表示对整个列表进行切片。

>>>>>>>>>>>>>>>>>> 10l <<<<<<<<<<<<<<<<<<<<<

### 详细解释：

1. **`self.target_lots[:] = target_lots`**:
   - `self.target_lots` 是对象的一个属性，通常是一个列表（或者其它支持切片操作的可变序列）。
   - `[:]` 是切片操作符，表示对整个列表进行切片。具体来说，`[:]` 是对列表的所有元素进行选择，这种写法可以用于复制列表或对整个列表内容进行替换。

2. **具体操作**：
   - `self.target_lots[:] = target_lots` 不是直接将 `target_lots` 赋值给 `self.target_lots`，而是将 `target_lots` 中的所有元素替换 `self.target_lots` 中的所有元素。
   - 这种做法的一个好处是不会改变 `self.target_lots` 对象的引用，而是修改它的内容。这在有其他对象引用 `self.target_lots` 时非常有用，确保所有引用者看到的列表内容都被更新，而不会因为重新赋值而改变列表的引用。

### 举个例子：

```python
a = [1, 2, 3]
b = a
a[:] = [4, 5, 6]  # 只改变列表内容，不改变引用

print(a)  # 输出: [4, 5, 6]
print(b)  # 输出: [4, 5, 6]，因为 a 和 b 引用的是同一个列表，修改 a 的内容也影响了 b
```

如果直接用 `a = [4, 5, 6]` 替换 `[:]` 操作，那么 `b` 就不会受到影响，因为 `a` 重新指向了一个新的列表对象。
> 10l
"""


@jitclass
class Simulator:
    cash: float  # 账户现金余额, 单位人民币元
    pos_values: nb.float64[:]  # 仓位价值，单位人民币元

    commission_rate: float  # 交易佣金费率，表示每次买入或卖出股票时，按交易金额收取的佣金比例
    stamp_tax_rate: float  # 印花税率，仅在卖出股票时收取，按卖出金额的比例计算

    last_prices: nb.float64[:]  # 最新价格

    def __init__(self, init_capital, commission_rate, stamp_tax_rate, init_pos_values):
        """
        初始化模拟器

        :param init_capital: 初始资金，单位人民币元
        :param commission_rate: 交易佣金费率，表示每次买入或卖出股票时，按交易金额收取的佣金比例（例如 0.0003 表示万分之三）
        :param stamp_tax_rate: 印花税率，仅在卖出股票时收取，按卖出金额的比例计算（例如 0.001 表示千分之一）
        :param init_pos_values: 初始仓位价值，表示每个股票的初始持仓价值，单位人民币元
        """
        self.cash = init_capital  # 初始化现金余额为初始资金
        self.commission_rate = commission_rate  # 设置交易佣金费率
        self.stamp_tax_rate = stamp_tax_rate  # 设置印花税率

        n = len(init_pos_values)  # 获取初始仓位价值的数量

        # 初始化仓位价值数组，长度为n，数据类型为float64
        self.pos_values = np.zeros(n, dtype=np.float64)
        self.pos_values[:] = init_pos_values  # 将初始仓位价值赋值给仓位价值数组

        # 初始化最新价格数组，长度为n，数据类型为float64
        self.last_prices = np.zeros(n, dtype=np.float64)

    def deposit(self, cash):
        """
        模拟向账户中存入资金

        :param cash: 入金金额，单位人民币元。必须为非负数。
        """
        # 检查入金金额是否为负数，如果是负数则直接返回，不进行任何操作
        if cash < 0:
            return
        # 将入金金额加到当前现金余额中
        self.cash += cash

    def withdraw(self, cash):
        """
        模拟从账户中提取资金

        :param cash: 出金金额，单位人民币元。必须为非负数。
        :return: 实际提取的金额。如果请求的金额大于当前现金余额，则返回当前全部可用现金。
        """
        # 检查出金金额是否为负数，如果是负数则返回 0，表示未提取任何资金
        if cash < 0:
            return 0

        # 如果请求的出金金额大于当前现金余额，则将出金金额调整为当前现金余额
        if cash > self.cash:
            cash = self.cash

        # 从当前现金余额中扣除出金金额
        self.cash -= cash
        # 返回实际提取的金额
        return cash

    def withdraw_all(self):
        """
        提取账户中全部可用现金

        :return: 账户中全部可用现金的金额，单位人民币元。
        """
        # 调用 withdraw 方法，提取当前全部现金余额
        return self.withdraw(self.cash)

    def fill_last_prices(self, prices):
        """
        更新最新价格数组 `last_prices`，将非 NaN 的价格填充到对应位置

        :param prices: 当前价格数组，可能包含 NaN 值
        """
        # 创建一个布尔掩码，标记 prices 数组中非 NaN 的位置
        mask = np.logical_not(np.isnan(prices))
        # 将 prices 数组中非 NaN 的值更新到 last_prices 数组的对应位置
        self.last_prices[mask] = prices[mask]

    def settle_pos_values(self, prices):
        """
        根据当前价格计算并更新仓位价值 `pos_values`

        :param prices: 当前价格数组，可能包含 NaN 值
        """
        # 创建一个布尔掩码，标记满足以下两个条件的位置：
        # 1. pos_values 大于 1e-6（避免极小值的影响）
        # 2. prices 数组中对应位置的值不是 NaN
        mask = np.logical_and(self.pos_values > 1e-6, np.logical_not(np.isnan(prices)))

        # 根据当前价格和上一次价格的比率，更新仓位价值
        # 公式：pos_values = pos_values * (当前价格 / 上一次价格)
        self.pos_values[mask] *= prices[mask] / self.last_prices[mask]

    def get_pos_value(self):
        """
        计算并返回当前所有仓位的总价值

        :return: 所有仓位的总价值，单位人民币元
        """
        # 使用 numpy 的 sum 函数对 pos_values 数组求和，得到所有仓位的总价值
        return np.sum(self.pos_values)

    def sell_all(self, exec_prices):
        """
        卖出所有持仓，将当前仓位调整为 0，并返回交易印花税和佣金

        :param exec_prices: 卖出价格数组，表示每个股票的卖出价格
        :return: 印花税和佣金，单位人民币元
        """
        # 创建一个全零数组，表示目标仓位为 0（即清空所有持仓）
        target_pos = np.zeros(len(self.pos_values), dtype=np.float64)

        # 调用 adjust_positions 方法，将仓位调整为 0，并返回印花税和佣金
        stamp_tax, commission = self.adjust_positions(exec_prices, target_pos)

        # 返回印花税和佣金
        return stamp_tax, commission

    def adjust_positions(self, exec_prices, target_pos):
        """
        模拟调仓操作，根据目标仓位和调仓价格调整当前仓位，并计算交易成本和更新账户状态

        :param exec_prices: 调仓价格数组，表示每个股票的调仓价格
        :param target_pos: 目标仓位数组，表示每个股票的目标持仓数量
        :return: 交易佣金，单位人民币元
        """
        # 根据调仓价格和上一次的最新价格（开盘价），结算当前仓位价值
        self.settle_pos_values(exec_prices)

        # 初始化目标仓位价值数组，长度与 pos_values 相同，数据类型为 float64
        target_values = np.zeros(len(self.pos_values), dtype=np.float64)

        # 创建一个布尔掩码，标记目标仓位大于 0 的位置
        mask = target_pos > 0
        # 计算目标仓位价值：目标仓位价值 = 调仓价格 * 目标持仓数量
        target_values[mask] = exec_prices[mask] * target_pos[mask]

        # 计算仓位价值的变化量：目标仓位价值 - 当前仓位价值
        delta_values = target_values - self.pos_values

        # 计算买入成交额：所有仓位价值变化量为正的部分之和
        buy_turnover = np.sum(delta_values[delta_values > 0])

        # 计算卖出成交额：所有仓位价值变化量为负的部分之和（取绝对值）
        sell_turnover = -np.sum(delta_values[delta_values < 0])

        # 将当前仓位价值更新为目标仓位价值
        self.pos_values[:] = target_values

        # 计算券商佣金：佣金 = (买入成交额 + 卖出成交额) * 佣金费率
        commission = (buy_turnover + sell_turnover) * self.commission_rate

        # 计算印花税：印花税 = 卖出成交额 * 印花税率
        stamp_tax = sell_turnover * self.stamp_tax_rate

        # 更新账户现金余额：
        # 现金变化 = 卖出成交额 - 买入成交额 - 佣金 - 印花税
        self.cash += sell_turnover - buy_turnover - commission - stamp_tax

        # 更新最新价格为调仓价格
        self.fill_last_prices(exec_prices)

        # 返回交易佣金
        return stamp_tax, commission
