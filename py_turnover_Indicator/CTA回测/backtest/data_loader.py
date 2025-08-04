#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据加载器
用于加载datas目录中的CSV数据到backtrader
"""

import os
import pandas as pd
import backtrader as bt
from datetime import datetime

class CSVDataLoader:
    """CSV数据加载器"""
    
    def __init__(self, data_dir="../datas"):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        
    def list_available_data(self):
        """列出可用的数据文件"""
        files = []
        if os.path.exists(self.data_dir):
            for file in os.listdir(self.data_dir):
                if file.endswith('.csv'):
                    files.append(file)
        return sorted(files)
    
    def load_data(self, filename, start_date=None, end_date=None):
        """
        加载CSV数据并转换为backtrader格式
        
        Args:
            filename: CSV文件名
            start_date: 开始日期（格式：'2025-01-01'）
            end_date: 结束日期（格式：'2025-01-31'）
            
        Returns:
            backtrader数据对象
        """
        file_path = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
        
        # 读取CSV文件
        print(f"正在加载数据文件: {file_path}")
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 检查必要的列
        required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"数据文件缺少必要列: {missing_columns}")
        
        # 转换数据类型
        df['datetime'] = pd.to_datetime(df['datetime'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 删除包含NaN的行
        df = df.dropna()
        
        # 设置datetime为索引
        df.set_index('datetime', inplace=True)
        
        # 按日期过滤
        if start_date:
            start_date = pd.to_datetime(start_date)
            df = df[df.index >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            df = df[df.index <= end_date]
        
        if df.empty:
            raise ValueError("过滤后的数据为空，请检查日期范围")
        
        print(f"数据加载完成:")
        print(f"  - 总记录数: {len(df)}")
        print(f"  - 时间范围: {df.index.min()} 至 {df.index.max()}")
        print(f"  - 价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
        
        # 创建backtrader数据对象
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # 使用索引作为datetime
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=None
        )
        
        return data
    
    def preview_data(self, filename, rows=10):
        """
        预览数据文件内容
        
        Args:
            filename: CSV文件名
            rows: 显示的行数
        """
        file_path = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            print(f"\n=== {filename} 数据预览 ===")
            print(f"总行数: {len(df)}")
            print(f"列名: {list(df.columns)}")
            print(f"\n前{rows}行数据:")
            print(df.head(rows))
            
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                print(f"\n时间范围: {df['datetime'].min()} 至 {df['datetime'].max()}")
            
            if 'close' in df.columns:
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                print(f"收盘价范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
                
        except Exception as e:
            print(f"预览数据失败: {e}")


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_ohlcv_data(df):
        """
        验证OHLCV数据的有效性
        
        Args:
            df: pandas DataFrame
            
        Returns:
            dict: 验证结果
        """
        results = {
            'is_valid': True,
            'issues': [],
            'statistics': {}
        }
        
        # 检查必要列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            results['is_valid'] = False
            results['issues'].append(f"缺少必要列: {missing_columns}")
            return results
        
        # 转换数据类型
        for col in required_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 检查NaN值
        nan_counts = df[required_columns].isnull().sum()
        for col, count in nan_counts.items():
            if count > 0:
                results['issues'].append(f"{col}列包含{count}个NaN值")
        
        # 检查OHLC逻辑
        ohlc_issues = []
        
        # High应该是最高价
        high_issues = df[df['high'] < df[['open', 'close']].max(axis=1)]
        if not high_issues.empty:
            ohlc_issues.append(f"{len(high_issues)}行的high价格低于open或close")
        
        # Low应该是最低价
        low_issues = df[df['low'] > df[['open', 'close']].min(axis=1)]
        if not low_issues.empty:
            ohlc_issues.append(f"{len(low_issues)}行的low价格高于open或close")
        
        # 价格不能为负
        negative_prices = df[(df[['open', 'high', 'low', 'close']] <= 0).any(axis=1)]
        if not negative_prices.empty:
            ohlc_issues.append(f"{len(negative_prices)}行包含非正价格")
        
        # 成交量不能为负
        negative_volume = df[df['volume'] < 0]
        if not negative_volume.empty:
            ohlc_issues.append(f"{len(negative_volume)}行包含负成交量")
        
        results['issues'].extend(ohlc_issues)
        
        if ohlc_issues:
            results['is_valid'] = False
        
        # 统计信息
        if df[required_columns].notna().all().all():
            results['statistics'] = {
                'total_rows': len(df),
                'price_range': {
                    'min': df['close'].min(),
                    'max': df['close'].max(),
                    'mean': df['close'].mean()
                },
                'volume_stats': {
                    'min': df['volume'].min(),
                    'max': df['volume'].max(),
                    'mean': df['volume'].mean()
                }
            }
        
        return results 