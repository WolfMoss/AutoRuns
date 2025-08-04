#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聚合交易数据获取模块
使用币安 /api/v3/aggTrades 接口
功能：
- 支持时间范围查询
- 自动分页获取大量历史数据
- 智能缓存管理
- 数据去重和质量检查
"""

import requests
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AggTradesDataFetcher:
    """
    聚合交易数据获取器
    使用 /api/v3/aggTrades 接口
    """
    
    def __init__(self, proxy: Optional[str] = None, config: Optional[Dict] = None):
        """
        初始化聚合交易数据获取器
        
        Args:
            proxy: 代理地址
            config: 额外配置参数
        """
        self.proxy = proxy
        self.config = config or {}
        
        # 默认配置
        self.default_cache_dir = "tick_datas"
        self.retry_attempts = 3
        self.retry_delay = 2  # 秒
        self.batch_size = 1000  # 每次获取的记录数（API最大限制）
        self.rate_limit_delay = 0.2  # 请求间隔，避免触发频率限制
        
        # 币安API端点
        self.base_url = "https://api.binance.com"
        
        # 设置requests会话
        self.session = requests.Session()
        if self.proxy:
            self.session.proxies = {
                'http': self.proxy,
                'https': self.proxy,
            }
            
    def _ensure_cache_dir(self, cache_path: str) -> str:
        """确保缓存目录存在"""
        if os.path.isdir(cache_path):
            cache_dir = cache_path
        else:
            cache_dir = os.path.dirname(cache_path)
            
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            logger.info(f"创建缓存目录: {cache_dir}")
            
        return cache_path
        
    def _get_cache_file_path(self, symbol: str, cache_file: Optional[str] = None) -> str:
        """获取缓存文件路径"""
        if cache_file:
            if os.path.isdir(cache_file):
                return os.path.join(cache_file, f"{symbol.replace('/', '_')}_agg_trades.csv")
            else:
                return cache_file
        else:
            if not os.path.exists(self.default_cache_dir):
                os.makedirs(self.default_cache_dir)
            return os.path.join(self.default_cache_dir, f"{symbol.replace('/', '_')}_agg_trades.csv")
            
    def _fetch_agg_trades_batch(self, symbol: str, start_time: Optional[int] = None, 
                               end_time: Optional[int] = None, from_id: Optional[int] = None,
                               limit: int = 1000) -> List[Dict]:
        """
        获取单批聚合交易数据
        
        Args:
            symbol: 交易对符号
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            from_id: 起始聚合交易ID
            limit: 获取条数
            
        Returns:
            聚合交易数据列表
        """
        url = f"{self.base_url}/api/v3/aggTrades"
        
        params = {
            'symbol': symbol.replace('/', ''),  # 移除斜杠
            'limit': min(limit, 1000)  # API最大限制1000
        }
        
        # 添加时间范围或ID参数
        if from_id is not None:
            params['fromId'] = from_id
        else:
            if start_time is not None:
                params['startTime'] = int(start_time)
            if end_time is not None:
                params['endTime'] = int(end_time)
        
        attempts = 0
        while attempts < self.retry_attempts:
            try:
                logger.debug(f"请求参数: {params}")
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"获取到 {len(data)} 条聚合交易数据")
                    return data
                elif response.status_code == 429:
                    # 触发频率限制
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"触发频率限制，等待 {retry_after} 秒后重试")
                    time.sleep(retry_after)
                    attempts += 1
                    continue
                else:
                    logger.error(f"API请求失败: {response.status_code} - {response.text}")
                    response.raise_for_status()
                    
            except Exception as e:
                attempts += 1
                logger.error(f"获取聚合交易数据失败 (尝试 {attempts}/{self.retry_attempts}): {e}")
                
                if attempts < self.retry_attempts:
                    logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"获取数据最终失败: {symbol}")
                    raise e
                    
        return []
        
    def _fetch_agg_trades_time_range(self, symbol: str, start_time: int, end_time: int) -> List[Dict]:
        """
        获取指定时间范围内的所有聚合交易数据
        
        Args:
            symbol: 交易对符号
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            完整的聚合交易数据列表
        """
        logger.info(f"开始获取 {symbol} 从 {datetime.fromtimestamp(start_time/1000)} 到 {datetime.fromtimestamp(end_time/1000)} 的聚合交易数据")
        
        all_trades = []
        current_start = start_time
        
        while current_start < end_time:
            # 计算当前批次的结束时间（最多24小时，避免数据量过大）
            batch_end = min(current_start + 24 * 60 * 60 * 1000, end_time)
            
            logger.info(f"获取时间段: {datetime.fromtimestamp(current_start/1000)} 到 {datetime.fromtimestamp(batch_end/1000)}")
            
            # 使用fromId分页获取这个时间段的所有数据
            from_id = None
            batch_trades = []
            
            while True:
                if from_id is not None:
                    # 使用fromId分页
                    trades = self._fetch_agg_trades_batch(symbol, from_id=from_id, limit=self.batch_size)
                else:
                    # 使用时间范围
                    trades = self._fetch_agg_trades_batch(symbol, start_time=current_start, 
                                                        end_time=batch_end, limit=self.batch_size)
                
                if not trades:
                    break
                    
                # 过滤出当前时间范围内的数据
                valid_trades = [trade for trade in trades if current_start <= trade['T'] <= batch_end]
                batch_trades.extend(valid_trades)
                
                # 检查是否需要继续分页
                if len(trades) < self.batch_size:
                    # 返回的数据少于批次大小，说明没有更多数据
                    break
                    
                # 更新fromId为最后一个交易的ID + 1
                from_id = trades[-1]['a'] + 1
                
                # 如果最后一个交易的时间超过了当前批次的结束时间，停止
                if trades[-1]['T'] >= batch_end:
                    break
                    
                # 遵守频率限制
                time.sleep(self.rate_limit_delay)
                
            all_trades.extend(batch_trades)
            logger.info(f"当前时间段获取到 {len(batch_trades)} 条数据，总计 {len(all_trades)} 条")
            
            # 移动到下一个时间段
            current_start = batch_end + 1
            
            # 遵守频率限制
            time.sleep(self.rate_limit_delay)
            
        logger.info(f"完成数据获取，总计 {len(all_trades)} 条聚合交易数据")
        return all_trades
        
    def _convert_to_dataframe(self, trades: List[Dict]) -> pd.DataFrame:
        """
        将聚合交易数据转换为DataFrame
        
        Args:
            trades: 聚合交易数据列表
            
        Returns:
            包含聚合交易数据的DataFrame
        """
        if not trades:
            return pd.DataFrame()
            
        df = pd.DataFrame(trades)
        
        # 重命名列以符合常用格式
        column_mapping = {
            'a': 'agg_trade_id',      # 聚合交易ID
            'p': 'price',             # 价格
            'q': 'quantity',          # 数量
            'f': 'first_trade_id',    # 第一个交易ID
            'l': 'last_trade_id',     # 最后一个交易ID
            'T': 'timestamp',         # 时间戳
            'm': 'is_buyer_maker',    # 买方是否为挂单方
            'M': 'is_best_match'      # 是否为最优匹配
        }
        
        df = df.rename(columns=column_mapping)
        
        # 转换数据类型
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        
        # 添加datetime列
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # 添加成交额列
        df['amount_quote'] = df['price'] * df['quantity']
        
        # 添加买卖方向列（基于is_buyer_maker）
        df['side'] = df['is_buyer_maker'].apply(lambda x: 'sell' if x else 'buy')
        
        # 排序和去重
        df = df.drop_duplicates(subset=['agg_trade_id']).sort_values('timestamp').reset_index(drop=True)
        
        return df
        
    def _save_to_cache(self, df: pd.DataFrame, file_path: str, symbol: str):
        """保存数据到缓存文件"""
        try:
            if df.empty:
                logger.warning("数据为空，跳过保存")
                return
                
            # 选择要保存的列
            output_columns = ['agg_trade_id', 'timestamp', 'datetime', 'price', 'quantity', 
                            'amount_quote', 'side', 'is_buyer_maker', 'first_trade_id', 'last_trade_id']
            
            # 确保所有列都存在
            for col in output_columns:
                if col not in df.columns:
                    df[col] = None
                    
            # 添加symbol列
            df['symbol'] = symbol
            
            df[['symbol'] + output_columns].to_csv(file_path, index=False, encoding="utf-8")
            
            logger.info(f"聚合交易数据已保存到: {file_path} ({len(df)} 条记录)")
            
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            
    def _load_cached_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """加载缓存数据"""
        if not os.path.exists(file_path):
            return None
            
        try:
            logger.info(f"从缓存文件加载聚合交易数据: {file_path}")
            df = pd.read_csv(file_path, encoding="utf-8")
            
            if df.empty:
                logger.warning(f"缓存文件为空: {file_path}")
                return None
                
            # 数据质量检查
            required_columns = ["timestamp", "price", "quantity"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.warning(f"缓存文件缺少必要列: {missing_columns}")
                return None
                
            logger.info(f"成功加载缓存数据: {len(df)} 条聚合交易记录")
            return df
            
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return None
            
    def get_agg_trades(self, symbol: str, start_time: Union[str, datetime, int], 
                      end_time: Union[str, datetime, int], cache_file: Optional[str] = None,
                      force_refresh: bool = False) -> pd.DataFrame:
        """
        获取指定时间范围的聚合交易数据
        
        Args:
            symbol: 交易对符号 (如: 'BTC/USDT')
            start_time: 开始时间（字符串、datetime对象或时间戳毫秒）
            end_time: 结束时间（字符串、datetime对象或时间戳毫秒）
            cache_file: 缓存文件路径或目录
            force_refresh: 是否强制刷新数据
            
        Returns:
            包含聚合交易数据的DataFrame
        """
        # 转换时间格式
        start_ts = self._convert_to_timestamp(start_time)
        end_ts = self._convert_to_timestamp(end_time)
        
        if start_ts >= end_ts:
            raise ValueError("开始时间必须早于结束时间")
            
        # 获取缓存文件路径
        file_path = self._get_cache_file_path(symbol, cache_file)
        self._ensure_cache_dir(file_path)
        
        # 如果不强制刷新，尝试加载缓存
        if not force_refresh:
            cached_data = self._load_cached_data(file_path)
            if cached_data is not None:
                # 过滤出指定时间范围的数据
                if 'timestamp' in cached_data.columns:
                    mask = (cached_data['timestamp'] >= start_ts) & (cached_data['timestamp'] <= end_ts)
                    filtered_data = cached_data[mask]
                    if not filtered_data.empty:
                        logger.info(f"从缓存返回 {len(filtered_data)} 条记录")
                        return filtered_data
                        
        # 获取在线数据
        try:
            trades = self._fetch_agg_trades_time_range(symbol, start_ts, end_ts)
            
            if not trades:
                logger.warning(f"未获取到任何聚合交易数据: {symbol}")
                return pd.DataFrame()
                
            # 转换为DataFrame
            df = self._convert_to_dataframe(trades)
            
            # 保存到缓存
            self._save_to_cache(df, file_path, symbol)
            
            return df
            
        except Exception as e:
            logger.error(f"获取聚合交易数据失败: {symbol} - {e}")
            # 如果在线获取失败，尝试返回缓存数据
            cached_data = self._load_cached_data(file_path)
            if cached_data is not None:
                logger.info("使用缓存数据作为备选")
                return cached_data
            else:
                raise e
                
    def _convert_to_timestamp(self, time_input: Union[str, datetime, int]) -> int:
        """转换各种时间格式为时间戳（毫秒）"""
        if isinstance(time_input, int):
            # 假设已经是毫秒时间戳
            return time_input
        elif isinstance(time_input, datetime):
            return int(time_input.timestamp() * 1000)
        elif isinstance(time_input, str):
            # 尝试解析字符串
            try:
                dt = pd.to_datetime(time_input)
                return int(dt.timestamp() * 1000)
            except:
                raise ValueError(f"无法解析时间字符串: {time_input}")
        else:
            raise ValueError(f"不支持的时间格式: {type(time_input)}")
            
    def get_recent_agg_trades(self, symbol: str, hours: int = 1) -> pd.DataFrame:
        """
        获取最近几小时的聚合交易数据
        
        Args:
            symbol: 交易对符号
            hours: 小时数
            
        Returns:
            最近的聚合交易数据
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        return self.get_agg_trades(symbol, start_time, end_time, force_refresh=True)
        
    def get_agg_trades_statistics(self, symbol: str, start_time: Union[str, datetime, int], 
                                 end_time: Union[str, datetime, int]) -> Dict[str, Any]:
        """
        获取聚合交易统计信息
        
        Args:
            symbol: 交易对符号
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            统计信息字典
        """
        try:
            df = self.get_agg_trades(symbol, start_time, end_time)
            
            if df.empty:
                return {}
                
            stats = {
                'symbol': symbol,
                'total_trades': len(df),
                'time_range': {
                    'start': df['datetime'].min() if 'datetime' in df.columns else None,
                    'end': df['datetime'].max() if 'datetime' in df.columns else None
                },
                'price_stats': {
                    'min': df['price'].min() if 'price' in df.columns else 0,
                    'max': df['price'].max() if 'price' in df.columns else 0,
                    'avg': df['price'].mean() if 'price' in df.columns else 0,
                    'median': df['price'].median() if 'price' in df.columns else 0
                },
                'volume_stats': {
                    'total_quantity': df['quantity'].sum() if 'quantity' in df.columns else 0,
                    'total_amount': df['amount_quote'].sum() if 'amount_quote' in df.columns else 0,
                    'avg_trade_size': df['quantity'].mean() if 'quantity' in df.columns else 0
                }
            }
            
            # 买卖统计
            if 'side' in df.columns:
                buy_trades = df[df['side'] == 'buy']
                sell_trades = df[df['side'] == 'sell']
                
                stats['trade_direction'] = {
                    'buy_trades': len(buy_trades),
                    'sell_trades': len(sell_trades),
                    'buy_volume': buy_trades['quantity'].sum() if not buy_trades.empty else 0,
                    'sell_volume': sell_trades['quantity'].sum() if not sell_trades.empty else 0,
                    'buy_amount': buy_trades['amount_quote'].sum() if not buy_trades.empty else 0,
                    'sell_amount': sell_trades['amount_quote'].sum() if not sell_trades.empty else 0
                }
                
                if stats['trade_direction']['sell_volume'] > 0:
                    stats['trade_direction']['buy_sell_ratio'] = (
                        stats['trade_direction']['buy_volume'] / stats['trade_direction']['sell_volume']
                    )
                    
            logger.info(f"生成聚合交易统计: {symbol}")
            return stats
            
        except Exception as e:
            logger.error(f"获取聚合交易统计失败: {e}")
            return {} 