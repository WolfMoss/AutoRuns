#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
并发聚合交易数据获取示例程序
演示如何使用异步并发版本的 /api/v3/aggTrades 接口获取历史数据
"""
import traceback
import asyncio
import time
import platform
from datetime import datetime, timedelta
from async_agg_trades_data import AsyncAggTradesDataFetcher

def setup_windows_compatibility():
    """设置Windows兼容性"""
    if platform.system() == 'Windows':
        # Windows下使用SelectorEventLoop而不是ProactorEventLoop
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            print("🔧 已设置Windows异步兼容模式")
        except AttributeError:
            # Python 3.6及以下版本没有WindowsSelectorEventLoopPolicy
            print("⚠️  当前Python版本较老，建议升级到3.7+以获得更好的异步支持")

async def main():
    """主函数 - 演示并发聚合交易数据获取"""
    
    # 配置参数
    symbol = 'TRUMP/USDT'
    cache_dir = "tick_datas"
    # 代理配置 - 包含用户名和密码
    proxy = 'http://axiba:ilikecs123!@wolfmoss.top:8017'  # 格式: http://用户名:密码@主机:端口
    # 如果不需要代理，设为 None
    # 如果代理不需要身份验证，使用: 'http://wolfmoss.top:8016'
    
    print("=== 并发聚合交易数据获取示例 ===")
    print("使用币安 /api/v3/aggTrades 接口 + 异步并发优化")
    print("预期效率提升：3-5倍（相比同步版本）")
    
    # 创建异步获取器
    async_fetcher = AsyncAggTradesDataFetcher(proxy=proxy)
    
    # # 示例1: 异步并发获取数据
    # print(f"\n1. 异步并发获取数据（展示性能优势）...")
    
    # start_time_async = time.time()
    # try:
    #     async_data = await async_fetcher.get_agg_trades_async(
    #         symbol=symbol,
    #         start_time="2025-02-01 00:00:00",  # 字符串格式
    #         end_time="2025-02-05 06:50:00",    # 字符串格式
    #         cache_file=cache_dir
    #     )
        
    #     end_time_async = time.time()
    #     async_duration = end_time_async - start_time_async
        
    #     if not async_data.empty:
    #         print(f"✅ 异步并发获取成功: {len(async_data)} 条记录")
    #         print(f"⏱️  异步获取耗时: {async_duration:.2f} 秒")
    #         print(f"📅 数据时间范围: {async_data['datetime'].min()} 到 {async_data['datetime'].max()}")
            
    #         # 简单数据统计
    #         print(f"💰 价格范围: {async_data['price'].min():.4f} - {async_data['price'].max():.4f}")
    #         print(f"📊 总成交量: {async_data['quantity'].sum():.2f}")
    #         print(f"📈 买单/卖单比例: {len(async_data[async_data['side']=='buy'])}/{len(async_data[async_data['side']=='sell'])}")
    #     else:
    #         print("指定时间段无数据")
            
    # except Exception as e:
    #     print(f"❌ 异步获取失败: {e}")
    

    
    # 示例3: 多品种并发获取（展示真正的并发威力）
    print(f"\n3. 多品种并发获取（并发优势最大化）...")
    
    symbols = ['TRUMP/USDT']
    start_time_multi = time.time()
    
    try:
        # 并发获取多个品种的数据
        tasks = [
            async_fetcher.get_agg_trades_async(
                symbol=sym,
                start_time="2025-08-18 00:00:00",
                end_time="2025-08-18 00:30:00",  # 6小时数据
                cache_file=cache_dir
            )
            for sym in symbols
        ]
        
        print(f"📡 同时发起 {len(symbols)} 个品种的数据获取请求...")
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time_multi = time.time()
        multi_duration = end_time_multi - start_time_multi
        
        print(f"🎯 多品种并发获取完成，总耗时: {multi_duration:.2f} 秒")
        
        total_records = 0
        for i, (symbol_name, result) in enumerate(zip(symbols, results)):
            if isinstance(result, Exception):
                print(f"❌ {symbol_name}: 获取失败 - {result}")
                print(f"错误详情: {type(result).__name__}")
            else:
                total_records += len(result)
                print(f"✅ {symbol_name}: 获取成功 - {len(result)} 条记录")
                if len(result) > 0:
                    print(f"📅 数据时间范围: {result['datetime'].min()} 到 {result['datetime'].max()}")
        
        print(f"📊 总计获取: {total_records} 条记录")
        if len(symbols) > 0:
            print(f"⚡ 平均每品种耗时: {multi_duration/len(symbols):.2f} 秒")
                
    except Exception as e:
        print(f"❌ 多品种并发获取失败: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")

    
    print(f"\n=== 并发示例执行完成 ===")
    print(f"📁 聚合交易数据已保存到目录: {cache_dir}")
    print("\n🚀 并发版本关键优势:")
    print("✅ 时间分片并发处理 - 3-5倍效率提升")
    print("✅ 多品种同时获取 - 大幅节省总时间") 
    print("✅ 智能频率限制管理 - 避免API限制")
    print("✅ 异常隔离处理 - 单个失败不影响整体")
    print("✅ 非阻塞I/O操作 - 更好的资源利用")
    print("✅ 数据完整性保证 - 去重+排序+验证")
    print("✅ 同步接口兼容 - 无缝升级现有代码")
    print("✅ 文件命名格式: {symbol}_agg_trades_async.csv")
    print("\n💡 适用场景:")
    print("🔸 大量历史数据获取")
    print("🔸 多品种数据并行获取") 
    print("🔸 实时数据更新任务")
    print("🔸 数据分析和回测准备")


if __name__ == '__main__':
    # 设置Windows兼容性
    setup_windows_compatibility()
    
    # 运行异步并发主函数
    print("🚀 启动异步并发版本...")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

        print(f"详细错误信息:\n{traceback.format_exc()}")
        
    
    print(f"\n🎉 所有示例程序执行完成！")
    print("💡 建议：日常使用异步版本以获得更好的性能体验") 