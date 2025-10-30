#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance U本位合约 WebSocket 客户端使用示例

支持代理服务器配置，包括用户名和密码身份验证：
- 如果代理服务器需要用户名和密码，请设置 proxy_username 和 proxy_password
- 如果不需要身份验证，保持 proxy_username 和 proxy_password 为 None
"""

import time
import logging
from binance_websocket_client import BinanceFuturesWebSocketClient


def example_3_with_custom_callbacks():
    """示例3：使用自定义回调函数"""
    print("=== 示例3：使用自定义回调函数 ===")
    
    # 自定义数据处理函数
    def handle_trade_message(data):
        """处理接收到的合约交易消息"""
        if 'stream' in data and 'data' in data:
            # 组合流格式
            stream_name = data['stream']
            trade_data = data['data']
            symbol = stream_name.split('@')[0].upper()
            price = float(trade_data.get('p', 0))
            quantity = float(trade_data.get('q', 0))
            
            print(f"🔥 [合约-{symbol}] 价格: {price}, 数量: {quantity}, 金额: {price * quantity:.2f} USDT")
            
        elif 'e' in data and data['e'] == 'aggTrade':
            # 单个流格式
            symbol = data['s']
            price = float(data.get('p', 0))
            quantity = float(data.get('q', 0))
            
            print(f"💰 [合约-{symbol}] 价格: {price}, 数量: {quantity}, 金额: {price * quantity:.2f} USDT")
    
    def handle_error(error):
        """处理错误"""
        print(f"❌ 发生错误: {error}")
    
    def handle_close():
        """处理连接关闭"""
        print("🔌 连接已关闭")
    
    # 创建合约客户端
    client = BinanceFuturesWebSocketClient(
        symbols=['TRUMPUSDT'],
        proxy_host="wolfmoss.top",  # 如果不需要代理，设置为None
        proxy_port=8017,
        proxy_type="http",
        proxy_username="axiba",  # 代理用户名（如果代理需要身份验证）
        proxy_password="ilikecs123!"   # 代理密码（如果代理需要身份验证）
    )
    
    # 设置回调函数
    client.set_message_callback(handle_trade_message)
    client.set_error_callback(handle_error)
    client.set_close_callback(handle_close)
    
    try:
        client.start()
        
        # 监控运行状态
        while True:
            time.sleep(10)
            stats = client.get_stats()
            print(f"📊 状态: 运行中={stats['is_running']}, "
                  f"消息数={stats['message_count']}, "
                  f"重连次数={stats['reconnect_count']}")
            
    except KeyboardInterrupt:
        print("🛑 收到中断信号")
    finally:
        client.stop()


if __name__ == "__main__":

    example_3_with_custom_callbacks()
