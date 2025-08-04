#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聚合交易数据获取示例程序
演示如何使用 /api/v3/aggTrades 接口获取历史数据
"""

from datetime import datetime, timedelta
from agg_trades_data import AggTradesDataFetcher

def main():
    """主函数 - 演示聚合交易数据获取"""
    
    # 配置参数
    symbol = 'TRUMP/USDT'
    cache_dir = "tick_datas"
    proxy = 'http://wolfmoss.top:8016'  # 如果不需要代理，设为 None
    
    print("=== 聚合交易数据获取示例 ===")
    print("使用币安 /api/v3/aggTrades 接口，支持时间范围查询")
    
    # 创建获取器
    fetcher = AggTradesDataFetcher(proxy=proxy)
    
    
    # 示例4: 使用字符串时间格式
    print(f"\n4. 使用字符串时间格式获取数据...")
    
    try:
        string_data = fetcher.get_agg_trades(
            symbol=symbol,
            start_time="2025-07-30 03:00:00",  # 字符串格式
            end_time="2025-07-30 06:00:00",    # 字符串格式
            cache_file=cache_dir
        )
        
        if not string_data.empty:
            print(f"使用字符串时间成功获取: {len(string_data)} 条记录")
        else:
            print("指定时间段无数据")
            
    except Exception as e:
        print(f"使用字符串时间失败: {e}")
    
    
    print(f"\n=== 示例执行完成 ===")
    print(f"聚合交易数据已保存到目录: {cache_dir}")
    print("数据格式包含字段: symbol, agg_trade_id, timestamp, datetime, price, quantity, amount_quote, side, is_buyer_maker, first_trade_id, last_trade_id")
    print("\n关键特性:")
    print("✅ 支持时间范围查询（/api/v3/aggTrades的优势）")
    print("✅ 自动分页获取大量数据（突破1000条限制）")
    print("✅ 智能缓存和数据去重")
    print("✅ 多种时间格式支持")
    print("✅ 详细的统计分析")
    print("✅ 数据保存到tick_datas目录（与现有目录结构统一）")
    print("✅ 文件命名格式: {symbol}_agg_trades.csv")

if __name__ == '__main__':
    main() 