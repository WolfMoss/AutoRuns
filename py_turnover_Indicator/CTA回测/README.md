# Binance WebSocket U本位合约归集交易订阅客户端

这是一个基于Python的Binance WebSocket客户端，用于订阅U本位合约归集交易数据，支持HTTP代理连接。

## 功能特性

- ✅ 订阅Binance U本位合约归集交易数据 (aggTrade)
- ✅ 支持单个或多个合约交易对同时订阅
- ✅ 支持HTTP、SOCKS4和SOCKS5代理连接
- ✅ 自动重连机制
- ✅ 心跳保活 (PING/PONG)
- ✅ 自定义回调函数
- ✅ 完整的错误处理
- ✅ 连接状态统计
- ✅ 详细的日志记录

## 重要说明

**本客户端现在连接到Binance U本位合约市场，不是现货市场！**

- **API端点**: `wss://fstream.binance.com/ws`
- **市场类型**: USDT保证金合约 (U本位合约)
- **交易对格式**: BTCUSDT, ETHUSDT 等
- **数据类型**: 合约归集交易数据

如果你需要现货数据，请将 `base_url` 改回 `wss://stream.binance.com:443`

## 安装依赖

使用以下命令安装所需的Python包：

```bash
# 使用指定的Python路径
D:\codes\Python\Python312\python.exe -m pip install -r requirements.txt
```

或者手动安装：

```bash
D:\codes\Python\Python312\python.exe -m pip install websocket-client>=1.6.0 pysocks>=1.7.1
```

## 基本使用

### 1. 不使用代理的基本连接

```python
from binance_websocket_client import BinanceFuturesWebSocketClient

# 创建合约客户端
client = BinanceFuturesWebSocketClient(
    symbols=['BTCUSDT']  # 订阅BTC/USDT合约交易对
)

# 启动连接
client.start()

# 保持程序运行
import time
time.sleep(60)  # 运行60秒

# 停止连接
client.stop()
```

### 2. 使用HTTP代理连接

```python
from binance_websocket_client import BinanceFuturesWebSocketClient

# 创建合约客户端（使用HTTP代理）
client = BinanceFuturesWebSocketClient(
    symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],  # 订阅多个合约交易对
    proxy_host="127.0.0.1",    # 代理服务器地址
    proxy_port=7890,           # 代理服务器端口
    proxy_type="http"          # 代理类型: "http" 或 "socks5"
)

# 启动连接
client.start()
```

### 3. 使用自定义回调函数

```python
def handle_trade_message(data):
    """处理合约交易消息的自定义函数"""
    if 'stream' in data and 'data' in data:
        trade_data = data['data']
        symbol = data['stream'].split('@')[0].upper()
        price = float(trade_data.get('p', 0))
        quantity = float(trade_data.get('q', 0))
        print(f"[合约-{symbol}] 价格: {price}, 数量: {quantity}")

# 设置回调函数
client.set_message_callback(handle_trade_message)
```

## 运行示例

程序包含多个使用示例，可以直接运行：

```bash
# 运行示例程序
D:\codes\Python\Python312\python.exe example_usage.py
```

示例包括：
1. 基本使用（不使用代理）
2. 使用HTTP代理连接
3. 使用自定义回调函数
4. 数据收集和存储

## 归集交易数据格式

根据Binance U本位合约API文档，归集交易数据包含以下字段：

```json
{
  "e": "aggTrade",          // 事件类型
  "E": 1672515782136,       // 事件时间
  "s": "BTCUSDT",           // 合约交易对
  "a": 12345,               // 归集交易ID
  "p": "0.001",             // 成交价格
  "q": "100",               // 成交数量
  "f": 100,                 // 被归集的首个交易ID
  "l": 105,                 // 被归集的末个交易ID
  "T": 1672515782136,       // 成交时间
  "m": true                 // 买方是否为maker
}
```

## 配置参数

### BinanceFuturesWebSocketClient 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| symbols | list | ['BTCUSDT'] | 要订阅的合约交易对列表 |
| proxy_host | str | None | 代理服务器地址 |
| proxy_port | int | None | 代理服务器端口 |
| proxy_type | str | "http" | 代理类型 ("http"、"socks4" 或 "socks5") |

### 常用方法

| 方法 | 说明 |
|------|------|
| `start()` | 启动WebSocket连接 |
| `stop()` | 停止WebSocket连接 |
| `set_message_callback(callback)` | 设置消息回调函数 |
| `set_error_callback(callback)` | 设置错误回调函数 |
| `set_close_callback(callback)` | 设置连接关闭回调函数 |
| `get_stats()` | 获取连接统计信息 |

## 注意事项

1. **合约交易**: 本客户端订阅的是U本位合约市场数据，与现货市场不同
2. **代理设置**: 如果不需要代理，将proxy_host设置为None或不传入代理参数
3. **交易对格式**: 合约交易对名称不区分大小写，程序会自动转换为小写
4. **连接限制**: Binance对WebSocket连接有频率限制，请遵循API使用规范
5. **重连机制**: 程序具有自动重连功能，最多重试10次
6. **日志文件**: 程序会生成`binance_futures_ws.log`日志文件，记录运行状态
7. **风险提示**: 合约交易具有高风险，请谨慎使用相关数据

## 常见代理设置

### HTTP代理
```python
proxy_host="127.0.0.1"
proxy_port=7890
proxy_type="http"
```

### SOCKS5代理
```python
proxy_host="127.0.0.1"
proxy_port=1080
proxy_type="socks5"
```

### SOCKS4代理
```python
proxy_host="127.0.0.1"
proxy_port=1080
proxy_type="socks4"
```

## 故障排除

1. **连接失败**: 检查网络连接和代理设置
2. **代理错误**: 确认代理服务器正常运行且配置正确
   - 如果遇到 "Only http, socks4, socks5 proxy protocols are supported" 错误，检查proxy_type参数是否正确
   - 确保代理服务器地址和端口可访问
   - 尝试不同的代理类型（http/socks4/socks5）
3. **依赖问题**: 确保已安装所有必需的Python包
4. **权限错误**: 确保有写入日志文件的权限
5. **WebSocket连接超时**: 检查防火墙设置，确保443端口可访问

## 相关链接

- [Binance WebSocket API文档](https://developers.binance.com/docs/zh-CN/binance-spot-api-docs/web-socket-streams)
- [websocket-client文档](https://websocket-client.readthedocs.io/)

## 许可证

本程序仅供学习和研究使用，使用时请遵循Binance API使用条款。合约交易具有高风险，请谨慎操作。 