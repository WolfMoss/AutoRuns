#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
异步聚合交易数据获取模块
使用币安 /api/v3/aggTrades 接口 + 异步并发优化
功能：
- 支持时间范围查询
- 异步并发获取大量历史数据
- 智能缓存管理
- 数据去重和质量检查
- 保证数据完整性的同时显著提升效率
"""

import asyncio
import aiohttp
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import logging
from concurrent.futures import ThreadPoolExecutor
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncAggTradesDataFetcher:
    """
    异步聚合交易数据获取器
    使用 /api/v3/aggTrades 接口 + 异步并发优化
    """
    
    def __init__(self, proxy: Optional[str] = None, config: Optional[Dict] = None):
        """
        初始化异步聚合交易数据获取器
        
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
        self.rate_limit_delay = 0.1  # 异步环境下可以更短的间隔
        self.max_concurrent_requests = 5  # 最大并发请求数
        
        # Windows兼容性：延迟创建信号量到异步上下文中
        self._semaphore = None
        
        # 币安API端点
        self.base_url = "https://api.binance.com"
        
        # 会话配置
        self.session_timeout = aiohttp.ClientTimeout(total=30)
    
    def _get_semaphore(self):
        """获取信号量，确保在正确的事件循环中创建"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self._semaphore
        
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
                return os.path.join(cache_file, f"{symbol.replace('/', '_')}_agg_trades_async.csv")
            else:
                return cache_file
        else:
            if not os.path.exists(self.default_cache_dir):
                os.makedirs(self.default_cache_dir)
            return os.path.join(self.default_cache_dir, f"{symbol.replace('/', '_')}_agg_trades_async.csv")
    
    async def _fetch_agg_trades_batch_async(self, session: aiohttp.ClientSession, 
                                          symbol: str, start_time: Optional[int] = None, 
                                          end_time: Optional[int] = None, from_id: Optional[int] = None,
                                          limit: int = 1000) -> List[Dict]:
        """
        异步获取单批聚合交易数据
        
        Args:
            session: aiohttp会话
            symbol: 交易对符号
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            from_id: 起始聚合交易ID
            limit: 获取条数
            
        Returns:
            聚合交易数据列表
        """
        async with self._get_semaphore():  # 使用延迟创建的信号量
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
                    logger.debug(f"异步请求参数: {params}")
                    async with session.get(url, params=params) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            logger.debug(f"异步获取到 {len(data)} 条聚合交易数据")
                            return data
                        elif response.status == 429:
                            # 触发频率限制
                            retry_after = int(response.headers.get('Retry-After', 60))
                            logger.warning(f"触发频率限制，等待 {retry_after} 秒后重试")
                            await asyncio.sleep(retry_after)
                            attempts += 1
                            continue
                        else:
                            logger.error(f"API请求失败: {response.status} - {await response.text()}")
                            response.raise_for_status()
                            
                except Exception as e:
                    attempts += 1
                    logger.error(f"异步获取聚合交易数据失败 (尝试 {attempts}/{self.retry_attempts}): {e}")
                    
                    if attempts < self.retry_attempts:
                        logger.info(f"等待 {self.retry_delay} 秒后重试...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        logger.error(f"获取数据最终失败: {symbol}")
                        raise e
                        
            return []
    
    async def _fetch_time_segment_async(self, session: aiohttp.ClientSession, 
                                      symbol: str, start_time: int, end_time: int) -> List[Dict]:
        """
        异步获取单个时间段的所有聚合交易数据
        
        Args:
            session: aiohttp会话
            symbol: 交易对符号
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            该时间段的聚合交易数据列表
        """
        logger.info(f"异步获取时间段: {datetime.fromtimestamp(start_time/1000)} 到 {datetime.fromtimestamp(end_time/1000)}")
        
        # 使用fromId分页获取这个时间段的所有数据
        from_id = None
        batch_trades = []
        
        while True:
            if from_id is not None:
                # 使用fromId分页
                trades = await self._fetch_agg_trades_batch_async(session, symbol, from_id=from_id, limit=self.batch_size)
            else:
                # 使用时间范围
                trades = await self._fetch_agg_trades_batch_async(session, symbol, start_time=start_time, 
                                                                end_time=end_time, limit=self.batch_size)
            
            if not trades:
                break
                
            # 过滤出当前时间范围内的数据
            valid_trades = [trade for trade in trades if start_time <= trade['T'] <= end_time]
            batch_trades.extend(valid_trades)
            
            # 检查是否需要继续分页
            if len(trades) < self.batch_size:
                # 返回的数据少于批次大小，说明没有更多数据
                break
                
            # 更新fromId为最后一个交易的ID + 1
            from_id = trades[-1]['a'] + 1
            
            # 如果最后一个交易的时间超过了当前批次的结束时间，停止
            if trades[-1]['T'] >= end_time:
                break
                
            # 短暂延迟，避免过于频繁的请求
            await asyncio.sleep(self.rate_limit_delay / 2)
            
        logger.info(f"时间段完成，获取到 {len(batch_trades)} 条数据")
        return batch_trades
    
    async def _fetch_agg_trades_time_range_async(self, symbol: str, start_time: int, end_time: int) -> List[Dict]:
        """
        异步获取指定时间范围内的所有聚合交易数据
        
        Args:
            symbol: 交易对符号
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            
        Returns:
            完整的聚合交易数据列表
        """
        logger.info(f"开始异步获取 {symbol} 从 {datetime.fromtimestamp(start_time/1000)} 到 {datetime.fromtimestamp(end_time/1000)} 的聚合交易数据")
        
        # 将时间范围分割为多个较小的段，便于并发处理
        time_segments = []
        current_start = start_time
        segment_duration = 6 * 60 * 60 * 1000  # 6小时为一个段，平衡并发度和数据完整性
        
        while current_start < end_time:
            segment_end = min(current_start + segment_duration, end_time)
            time_segments.append((current_start, segment_end))
            current_start = segment_end + 1
        
        logger.info(f"时间范围分割为 {len(time_segments)} 个段，准备并发获取")
        
        # 配置aiohttp会话 - Windows兼容性优化
        connector = aiohttp.TCPConnector(
            limit=50, 
            limit_per_host=20,
            use_dns_cache=False,  # Windows兼容性：禁用DNS缓存
            ttl_dns_cache=300,
            family=0  # 允许IPv4和IPv6
        )
        
        session_kwargs = {
            'timeout': self.session_timeout,
            'connector': connector
        }
        
        # Windows代理配置优化
        if self.proxy:
            session_kwargs['proxy'] = self.proxy
        
        async with aiohttp.ClientSession(**session_kwargs) as session:
            # 并发获取所有时间段的数据
            tasks = [
                self._fetch_time_segment_async(session, symbol, seg_start, seg_end)
                for seg_start, seg_end in time_segments
            ]
            
            # 等待所有任务完成
            segment_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果和异常
            all_trades = []
            for i, result in enumerate(segment_results):
                if isinstance(result, Exception):
                    logger.error(f"时间段 {i+1} 获取失败: {result}")
                    # 可以选择重试单个失败的段
                    continue
                else:
                    all_trades.extend(result)
                    
        logger.info(f"异步获取完成，总计 {len(all_trades)} 条聚合交易数据")
        return all_trades
    
    def _convert_to_dataframe(self, trades: List[Dict]) -> pd.DataFrame:
        """
        将聚合交易数据转换为DataFrame
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
        
        # 排序和去重 - 关键：保证数据完整性
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
            
            logger.info(f"异步聚合交易数据已保存到: {file_path} ({len(df)} 条记录)")
            
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
    
    async def get_agg_trades_async(self, symbol: str, start_time: Union[str, datetime, int], 
                                 end_time: Union[str, datetime, int], cache_file: Optional[str] = None,
                                 force_refresh: bool = False) -> pd.DataFrame:
        """
        异步获取指定时间范围的聚合交易数据
        
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
                        
        # 获取在线数据（异步）
        try:
            trades = await self._fetch_agg_trades_time_range_async(symbol, start_ts, end_ts)
            
            if not trades:
                logger.warning(f"未获取到任何聚合交易数据: {symbol}")
                return pd.DataFrame()
                
            # 转换为DataFrame
            df = self._convert_to_dataframe(trades)
            
            # 保存到缓存
            self._save_to_cache(df, file_path, symbol)
            
            return df
            
        except Exception as e:
            logger.error(f"异步获取聚合交易数据失败: {symbol} - {e}")
            # 如果在线获取失败，尝试返回缓存数据
            cached_data = self._load_cached_data(file_path)
            if cached_data is not None:
                logger.info("使用缓存数据作为备选")
                return cached_data
            else:
                raise e
    
    def get_agg_trades(self, symbol: str, start_time: Union[str, datetime, int], 
                      end_time: Union[str, datetime, int], cache_file: Optional[str] = None,
                      force_refresh: bool = False) -> pd.DataFrame:
        """
        同步接口：获取指定时间范围的聚合交易数据
        内部使用异步实现，对外提供同步接口保持兼容性
        """
        # Windows兼容性：设置正确的事件循环策略
        import platform
        if platform.system() == 'Windows':
            # Windows下使用SelectorEventLoop而不是ProactorEventLoop
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except AttributeError:
                # Python 3.6及以下版本没有WindowsSelectorEventLoopPolicy
                pass
        
        # 获取或创建事件循环
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 运行异步任务
        return loop.run_until_complete(
            self.get_agg_trades_async(symbol, start_time, end_time, cache_file, force_refresh)
        )
                
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
    
    async def get_recent_agg_trades_async(self, symbol: str, hours: int = 1) -> pd.DataFrame:
        """
        异步获取最近几小时的聚合交易数据
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        return await self.get_agg_trades_async(symbol, start_time, end_time, force_refresh=True)
    
    def get_recent_agg_trades(self, symbol: str, hours: int = 1) -> pd.DataFrame:
        """
        同步接口：获取最近几小时的聚合交易数据
        """
        # Windows兼容性处理
        import platform
        if platform.system() == 'Windows':
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except AttributeError:
                pass
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.get_recent_agg_trades_async(symbol, hours)
        ) 