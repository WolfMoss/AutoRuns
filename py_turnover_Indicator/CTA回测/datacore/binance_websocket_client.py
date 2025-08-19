#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Binance WebSocket U本位合约归集交易订阅客户端
支持HTTP代理连接
"""

import json
import time
import logging
import threading
from typing import Optional, Dict, Any, Callable
import websocket
import ssl

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('binance_futures_ws.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class BinanceFuturesWebSocketClient:
    """Binance U本位合约WebSocket客户端"""
    
    def __init__(self, 
                 symbols: list = None,
                 proxy_host: str = None,
                 proxy_port: int = None,
                 proxy_type: str = "http"):
        """
        初始化WebSocket客户端
        
        Args:
            symbols: 合约交易对列表，如['BTCUSDT', 'ETHUSDT']
            proxy_host: 代理服务器地址
            proxy_port: 代理服务器端口
            proxy_type: 代理类型，支持'http'、'socks4'或'socks5'
        """
        self.symbols = symbols or ['BTCUSDT']
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_type = proxy_type
        
        # WebSocket相关 - 使用U本位合约端点
        self.ws = None
        self.base_url = "wss://fstream.binance.com/ws"
        self.is_running = False
        self.reconnect_interval = 5  # 重连间隔（秒）
        self.max_reconnect_attempts = 10  # 最大重连次数
        self.reconnect_count = 0
        
        # 回调函数
        self.on_message_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        self.on_close_callback: Optional[Callable] = None
        
        # 数据统计
        self.message_count = 0
        self.last_message_time = None
        
        self.logger = logging.getLogger(__name__)
        
    def set_proxy(self, proxy_host: str, proxy_port: int, proxy_type: str = "http"):
        """设置代理配置"""
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_type = proxy_type
        self.logger.info(f"设置代理: {proxy_type}://{proxy_host}:{proxy_port}")
    
    def set_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置消息回调函数"""
        self.on_message_callback = callback
    
    def set_error_callback(self, callback: Callable[[Exception], None]):
        """设置错误回调函数"""
        self.on_error_callback = callback
    
    def set_close_callback(self, callback: Callable[[], None]):
        """设置连接关闭回调函数"""
        self.on_close_callback = callback
    
    def _get_stream_url(self) -> str:
        """构建WebSocket流URL"""
        if len(self.symbols) == 1:
            # 单个合约交易对
            stream_name = f"{self.symbols[0].lower()}@aggTrade"
            return f"{self.base_url}/{stream_name}"
        else:
            # 多个合约交易对组合流
            streams = [f"{symbol.lower()}@aggTrade" for symbol in self.symbols]
            stream_params = "/".join(streams)
            return f"wss://fstream.binance.com/stream?streams={stream_params}"
    
    def _on_message(self, ws, message):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            self.message_count += 1
            self.last_message_time = time.time()
            
            # 解析归集交易数据
            if 'stream' in data and 'data' in data:
                # 组合流格式
                stream_name = data['stream']
                trade_data = data['data']
                symbol = stream_name.split('@')[0].upper()
                self._process_trade_data(symbol, trade_data)
            elif 'e' in data and data['e'] == 'aggTrade':
                # 单个流格式
                symbol = data['s']
                self._process_trade_data(symbol, data)
            
            # 调用用户自定义回调
            if self.on_message_callback:
                self.on_message_callback(data)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {e}")
        except Exception as e:
            self.logger.error(f"消息处理错误: {e}")
    
    def _process_trade_data(self, symbol: str, data: Dict[str, Any]):
        """处理合约归集交易数据"""
        try:
            trade_info = {
                'symbol': symbol,
                'trade_id': data.get('a'),  # 归集交易ID
                'price': float(data.get('p', 0)),  # 成交价格
                'quantity': float(data.get('q', 0)),  # 成交数量
                'first_trade_id': data.get('f'),  # 被归集的首个交易ID
                'last_trade_id': data.get('l'),  # 被归集的末个交易ID
                'timestamp': data.get('T'),  # 成交时间戳
                'is_buyer_maker': data.get('m', False),  # 买方是否为maker
                'trade_time': time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(data.get('T', 0) / 1000))
            }
            
            # 计算成交金额
            trade_info['amount'] = trade_info['price'] * trade_info['quantity']
            
            # 判断买卖方向
            trade_info['side'] = 'SELL' if trade_info['is_buyer_maker'] else 'BUY'
            
            self.logger.info(
                f"[合约-{trade_info['symbol']}] "
                f"价格: {trade_info['price']:.4f}, "
                f"数量: {trade_info['quantity']:.4f}, "
                f"金额: {trade_info['amount']:.2f} USDT, "
                f"方向: {trade_info['side']}, "
                f"时间: {trade_info['trade_time']}"
            )
            
        except Exception as e:
            self.logger.error(f"合约交易数据处理错误: {e}")
    
    def _on_error(self, ws, error):
        """处理WebSocket错误"""
        self.logger.error(f"WebSocket错误: {error}")
        if self.on_error_callback:
            self.on_error_callback(error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket连接关闭"""
        self.logger.warning(f"WebSocket连接关闭: {close_status_code} - {close_msg}")
        self.is_running = False
        
        if self.on_close_callback:
            self.on_close_callback()
            
        # 自动重连
        if self.reconnect_count < self.max_reconnect_attempts:
            self._schedule_reconnect()
    
    def _on_open(self, ws):
        """WebSocket连接打开"""
        self.logger.info("WebSocket连接已建立")
        self.is_running = True
        self.reconnect_count = 0
        
        # 如果是组合流，需要发送订阅消息
        if len(self.symbols) > 1:
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@aggTrade" for symbol in self.symbols],
                "id": 1
            }
            ws.send(json.dumps(subscribe_message))
            self.logger.info(f"发送订阅消息: {subscribe_message}")
    
    def _on_pong(self, ws, data):
        """处理PONG消息"""
        self.logger.debug("收到PONG响应")
    
    def _schedule_reconnect(self):
        """安排重连"""
        self.reconnect_count += 1
        self.logger.info(f"准备重连 ({self.reconnect_count}/{self.max_reconnect_attempts}) "
                        f"等待 {self.reconnect_interval} 秒...")
        
        def reconnect():
            time.sleep(self.reconnect_interval)
            if not self.is_running:
                self.connect()
        
        threading.Thread(target=reconnect, daemon=True).start()
    
    def connect(self):
        """建立WebSocket连接"""
        try:
            if self.ws:
                self.ws.close()
            
            url = self._get_stream_url()
            self.logger.info(f"连接到: {url}")
            
            # 配置WebSocket
            websocket.enableTrace(False)
            
            # 设置代理
            proxy_config = {}
            if self.proxy_host and self.proxy_port:
                if self.proxy_type.lower() == "http":
                    proxy_config = {
                        "http_proxy_host": self.proxy_host,
                        "http_proxy_port": self.proxy_port,
                        "proxy_type": "http"
                    }
                elif self.proxy_type.lower() == "socks5":
                    proxy_config = {
                        "http_proxy_host": self.proxy_host,
                        "http_proxy_port": self.proxy_port,
                        "proxy_type": "socks5"
                    }
                elif self.proxy_type.lower() == "socks4":
                    proxy_config = {
                        "http_proxy_host": self.proxy_host,
                        "http_proxy_port": self.proxy_port,
                        "proxy_type": "socks4"
                    }
                else:
                    self.logger.warning(f"不支持的代理类型: {self.proxy_type}，将尝试HTTP代理")
                    proxy_config = {
                        "http_proxy_host": self.proxy_host,
                        "http_proxy_port": self.proxy_port,
                        "proxy_type": "http"
                    }
                self.logger.info(f"使用代理: {self.proxy_type}://{self.proxy_host}:{self.proxy_port}")
            
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_pong=self._on_pong
            )
            
            # 启动连接
            run_forever_args = {
                "sslopt": {"cert_reqs": ssl.CERT_NONE},
                "ping_interval": 20,
                "ping_timeout": 10
            }
            
            # 如果有代理配置则添加代理参数
            if proxy_config:
                run_forever_args.update(proxy_config)
            
            self.ws.run_forever(**run_forever_args)
                
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            if self.reconnect_count < self.max_reconnect_attempts:
                self._schedule_reconnect()
    
    def start(self):
        """启动WebSocket客户端"""
        self.logger.info(f"启动Binance U本位合约WebSocket客户端，订阅合约交易对: {self.symbols}")
        
        # 在单独线程中运行
        def run():
            self.connect()
        
        threading.Thread(target=run, daemon=True).start()
    
    def stop(self):
        """停止WebSocket客户端"""
        self.logger.info("停止U本位合约WebSocket客户端")
        self.is_running = False
        self.reconnect_count = self.max_reconnect_attempts  # 阻止重连
        if self.ws:
            self.ws.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            'is_running': self.is_running,
            'message_count': self.message_count,
            'last_message_time': self.last_message_time,
            'reconnect_count': self.reconnect_count,
            'symbols': self.symbols
        }


def main():
    """主函数示例"""
    # 创建客户端实例
    client = BinanceFuturesWebSocketClient(
        symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],  # 订阅的交易对
        proxy_host="127.0.0.1",  # 代理服务器地址
        proxy_port=7890,         # 代理服务器端口
        proxy_type="http"        # 代理类型
    )
    
    # 可选：设置自定义回调函数
    def custom_message_handler(data):
        """自定义消息处理函数"""
        if 'stream' in data:
            # 组合流数据
            pass
        elif 'e' in data and data['e'] == 'aggTrade':
            # 单个交易数据
            pass
    
    def custom_error_handler(error):
        """自定义错误处理函数"""
        logging.error(f"自定义错误处理: {error}")
    
    # client.set_message_callback(custom_message_handler)
    # client.set_error_callback(custom_error_handler)
    
    try:
        # 启动客户端
        client.start()
        
        # 保持程序运行
        while True:
            time.sleep(10)
            stats = client.get_stats()
            if stats['is_running']:
                logging.info(f"运行状态: 已接收 {stats['message_count']} 条消息")
            else:
                logging.warning("连接已断开")
                
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在关闭...")
        client.stop()
    except Exception as e:
        logging.error(f"程序异常: {e}")
        client.stop()


if __name__ == "__main__":
    main() 