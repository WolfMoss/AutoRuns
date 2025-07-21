#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通达信在线30分钟级数据获取脚本（异步处理）
使用 mootdx 库获取数据并保存到 datas 目录
自动获取全部A股股票列表
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from mootdx.quotes import Quotes
import time
import argparse
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor
import threading

def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists('datas'):
        os.makedirs('datas')
        print("创建数据目录: datas")

def get_all_stock_codes(client):
    """获取全部A股股票代码列表"""
    try:
        print("正在获取全部A股股票列表...")
        
        # 获取股票列表
        stock_list = client.stocks(1)

        
        if stock_list is None or len(stock_list) == 0:
            print("警告: 无法获取股票列表，使用默认股票")
            return ['000001', '000002', '600036', '600519', '000858']
        
        # 转换为DataFrame
        df = pd.DataFrame(stock_list)
        
        # 过滤A股股票（排除指数、基金等）
        if 'code' in df.columns:
            # 获取股票代码
            stock_codes = df['code'].tolist()
            
            # 过滤A股代码：000xxx, 002xxx, 300xxx, 600xxx, 601xxx, 603xxx, 688xxx
            a_stock_codes = []
            for code in stock_codes:
                
                if isinstance(code, str) and len(code) == 6:
                    if (str(code).startswith('00') or 
                        str(code).startswith('30')  or 
                        str(code).startswith('60') or 
                        str(code).startswith('688')):
                        a_stock_codes.append(code)
            
            print(f"成功获取 {len(a_stock_codes)} 只A股股票代码")
            return sorted(a_stock_codes)
        else:
            print("警告: 股票列表格式异常，使用默认股票")
            return ['000001', '000002', '600036', '600519', '000858']
            
    except Exception as e:
        print(f"获取股票列表失败: {str(e)}")
        print("使用默认股票列表")
        return ['000001', '000002', '600036', '600519', '000858']

def get_sample_stocks():
    """获取样本股票列表（用于测试）"""
    return [
        '000001', '000002', '000858', '000725',  # 深市主板
        '002415', '002594', '002304',           # 深市中小板  
        '300059', '300750',                     # 创业板
        '600036', '600519', '600276', '600887', # 沪市主板
        '601398', '601988', '601939',           # 沪市大盘股
        '603259', '603288',                     # 沪市新股
        '688981'                                # 科创板
    ]

def get_30min_data_sync(client, stock_code):
    """同步获取指定股票的30分钟数据"""
    try:
        # 获取历史数据
        data = client.bars(symbol=stock_code, frequency=2, offset=8*400)
        
        if data is not None and len(data) > 0:
            # 转换为DataFrame
            df = pd.DataFrame(data)

            
            return df
        else:
            return None
            
    except Exception as e:
        return None

async def get_30min_data_async(client, stock_code, semaphore=None):
    """异步获取指定股票的30分钟数据"""
    if semaphore:
        async with semaphore:
            # 在线程池中执行同步的网络请求
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                df = await loop.run_in_executor(
                    executor, 
                    get_30min_data_sync, 
                    client, 
                    stock_code
                )
            return stock_code, df
    else:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            df = await loop.run_in_executor(
                executor, 
                get_30min_data_sync, 
                client, 
                stock_code
            )
        return stock_code, df

def validate_data(df, stock_code):
    """验证数据的有效性"""
    if df is None or len(df) == 0:
        return False, "数据为空"
    
    # 检查必要的列是否存在
    required_columns = ['datetime']
    price_columns = ['开盘价', '最高价', '最低价', '收盘价', 'open', 'high', 'low', 'close']
    
    has_datetime = any(col in df.columns for col in required_columns)
    has_price = any(col in df.columns for col in price_columns)
    
    if not has_datetime:
        return False, "缺少时间列"
    
    if not has_price:
        return False, "缺少价格数据"
    
    return True, "数据有效"

async def save_to_csv_async(df, stock_code):
    """异步保存数据到CSV文件（直接覆盖）"""
    try:
        # 验证数据
        is_valid, message = validate_data(df, stock_code)
        if not is_valid:
            return False, f"数据验证失败 {stock_code}: {message}"
        
        filename = f"datas/{stock_code}_30min.csv"
        
        # 直接覆盖保存
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return True, f"数据已保存到: {filename} (共{len(df)}条记录)"
        
    except Exception as e:
        return False, f"保存 {stock_code} 数据失败: {str(e)}"

async def process_stock_batch(client, stock_batch, semaphore, progress_callback=None):
    """异步处理一批股票数据"""
    results = {
        'success': 0,
        'failed': 0,
        'messages': []
    }
    
    # 创建所有异步任务
    tasks = []
    
    for stock_code in stock_batch:
        # 创建异步任务
        task = get_30min_data_async(client, stock_code, semaphore)
        tasks.append(task)
    
    # 并发执行所有任务
    try:
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(completed_tasks):
            stock_code = stock_batch[i]
            
            if isinstance(result, Exception):
                results['failed'] += 1
                results['messages'].append(f"获取 {stock_code} 数据失败: {str(result)}")
                continue
            
            code, df = result
            
            if df is not None and len(df) > 0:
                # 异步保存数据
                success, message = await save_to_csv_async(df, code)
                if success:
                    results['success'] += 1
                    results['messages'].append(f"✅ {code}: {message}")
                else:
                    results['failed'] += 1
                    results['messages'].append(f"❌ {message}")
            else:
                results['failed'] += 1
                results['messages'].append(f"❌ {code}: 没有获取到数据")
            
            # 调用进度回调
            if progress_callback:
                progress_callback(i + 1, len(stock_batch))
    
    except Exception as e:
        results['messages'].append(f"批处理异常: {str(e)}")
    
    return results

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='获取通达信30分钟级股票数据')
    parser.add_argument('--mode', '-m', 
                       choices=['all', 'sample', 'custom'],
                       default=None,
                       help='运行模式：all=全部A股, sample=样本股票, custom=自定义')
    parser.add_argument('--stocks', '-s',
                       nargs='+',
                       help='自定义股票代码，例如: --stocks 000001 600036')
    parser.add_argument('--max-stocks', '-n',
                       type=int,
                       default=None,
                       help='限制最大股票数量，用于测试 (例如: -n 10)')
    parser.add_argument('--interactive', '-i',
                       action='store_true',
                       help='启动交互式菜单模式')
    parser.add_argument('--batch-size', '-b',
                       type=int,
                       default=20,
                       help='异步批处理大小 (默认: 20)')
    parser.add_argument('--max-concurrent', '-c',
                       type=int,
                       default=10,
                       help='最大并发数 (默认: 10)')
    
    return parser.parse_args()

def show_menu():
    """显示交互式菜单"""
    print("\n" + "="*50)
    print("通达信30分钟数据获取工具（异步版本）")
    print("="*50)
    print("请选择操作：")
    print("1. 样本股票数据获取（推荐）")
    print("2. 全部A股数据获取（耗时较长）")  
    print("3. 测试模式（前10只A股）")
    print("4. 自定义股票代码")
    print("0. 退出")
    print("="*50)

def get_user_choice():
    """获取用户选择"""
    while True:
        try:
            choice = input("请输入选择 (0-4): ").strip()
            if choice in ['0', '1', '2', '3', '4']:
                return choice
            else:
                print("无效的选择，请输入0-4之间的数字")
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return '0'
        except Exception:
            print("输入错误，请重新输入")

def get_custom_stocks():
    """获取用户输入的自定义股票代码"""
    while True:
        try:
            stocks_input = input("请输入股票代码，用空格分隔（例如：000001 600036 600519）: ").strip()
            if not stocks_input:
                print("未输入股票代码")
                return None
            
            stocks = stocks_input.split()
            # 简单验证股票代码格式
            valid_stocks = []
            for stock in stocks:
                if len(stock) == 6 and stock.isdigit():
                    valid_stocks.append(stock)
                else:
                    print(f"警告: {stock} 不是有效的股票代码格式")
            
            if valid_stocks:
                return valid_stocks
            else:
                print("没有有效的股票代码")
                return None
                
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return None
        except Exception:
            print("输入错误，请重新输入")

def interactive_mode():
    """交互式模式"""
    while True:
        show_menu()
        choice = get_user_choice()
        
        if choice == '0':
            print("退出程序")
            break
        elif choice == '1':
            print("正在获取样本股票数据...")
            asyncio.run(run_data_collection_async('sample', None, None))
        elif choice == '2':
            print("正在获取全部A股数据，这可能需要很长时间...")
            asyncio.run(run_data_collection_async('all', None, None))

        elif choice == '3':
            print("正在测试模式获取前10只A股数据...")
            asyncio.run(run_data_collection_async('all', None, 10))
        elif choice == '4':
            stocks = get_custom_stocks()
            if stocks:
                print(f"正在获取指定股票数据: {stocks}")
                asyncio.run(run_data_collection_async('custom', stocks, None))
            else:
                continue
        
        print("\n操作完成！")
        print("数据已保存到 datas 目录中")
        print("\n注意：")
        print("- 异步处理大大提高了数据获取效率")
        print("- 样本模式包含主要股票代表，适合日常使用")
        print("- 全A股模式包含所有A股，首次运行较耗时")
        print("- 每次运行都会获取最新的完整数据")
        
        input("\n按回车键继续...")

async def run_data_collection_async(mode, stocks, max_stocks, batch_size=20, max_concurrent=10):
    """异步运行数据收集"""
    # 确保数据目录存在
    ensure_data_dir()
    
    # 创建客户端连接
    try:
        print("正在连接通达信数据源...")
        client = Quotes.factory(market='std', multithread=True, heartbeat=True)
        print("成功连接到通达信数据源")
    except Exception as e:
        print(f"连接数据源失败: {str(e)}")
        print("请检查网络连接或稍后重试")
        return
    
    # 获取股票代码列表
    if stocks:
        stock_codes = stocks
        print(f"使用自定义股票列表: {len(stock_codes)} 只股票")
    elif mode == 'all':
        stock_codes = get_all_stock_codes(client)
        if max_stocks:
            stock_codes = stock_codes[:max_stocks]
            print(f"限制为前 {max_stocks} 只股票进行测试")
    elif mode == 'sample':
        stock_codes = get_sample_stocks()
        print(f"使用样本股票列表: {len(stock_codes)} 只股票")
    else:
        stock_codes = get_sample_stocks()
        print(f"使用默认样本股票列表: {len(stock_codes)} 只股票")
    
    print(f"准备异步获取 {len(stock_codes)} 只股票的30分钟数据")
    print(f"批处理大小: {batch_size}, 最大并发数: {max_concurrent}")
    
    # 创建信号量限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 统计信息
    total_results = {
        'success': 0,
        'failed': 0,
        'messages': []
    }
    
    # 分批处理股票
    total_batches = (len(stock_codes) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(stock_codes), batch_size):
        batch_num = batch_idx // batch_size + 1
        stock_batch = stock_codes[batch_idx:batch_idx + batch_size]
        
        print(f"\n--- 批次 {batch_num}/{total_batches}: 处理 {len(stock_batch)} 只股票 ---")
        
        # 进度回调函数
        def progress_callback(current, total):
            if current % 5 == 0 or current == total:  # 每5个或最后一个显示进度
                print(f"批次进度: {current}/{total}")
        
        # 异步处理当前批次
        batch_results = await process_stock_batch(
            client, stock_batch, semaphore, progress_callback
        )
        
        # 累计统计结果
        total_results['success'] += batch_results['success']
        total_results['failed'] += batch_results['failed']
        total_results['messages'].extend(batch_results['messages'])
        
        print(f"批次完成: 成功 {batch_results['success']}, 失败 {batch_results['failed']}")
        
        # 批次间短暂延迟
        if batch_num < total_batches:
            await asyncio.sleep(0.5)
    
    # 输出最终统计结果
    print("\n" + "="*60)
    print("异步数据获取完成!")
    print(f"总股票数: {len(stock_codes)} 只")
    print(f"成功: {total_results['success']} 只股票")
    print(f"失败: {total_results['failed']} 只股票")
    print(f"数据保存在: datas 目录")
    
    if total_results['success'] > 0:
        print(f"\n✅ 成功处理了 {total_results['success']} 只股票的30分钟数据")
    if total_results['failed'] > 0:
        print(f"⚠️  有 {total_results['failed']} 只股票获取失败，请检查网络连接")
    
    # 显示详细消息（仅显示错误消息）
    error_messages = [msg for msg in total_results['messages'] if msg.startswith('❌')]
    if error_messages and len(error_messages) <= 10:
        print("\n详细错误信息:")
        for msg in error_messages[:10]:
            print(f"  {msg}")
        if len(error_messages) > 10:
            print(f"  ... 还有 {len(error_messages) - 10} 个错误")

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 如果没有任何参数或指定了交互模式，启动交互式菜单
    if (args.mode is None and args.stocks is None and 
        args.max_stocks is None) or args.interactive:
        interactive_mode()
        return
    
    print("开始异步获取通达信30分钟级数据...")
    print("="*60)
    
    # 使用命令行参数模式
    mode = args.mode or 'sample'
    asyncio.run(run_data_collection_async(
        mode, 
        args.stocks, 
        args.max_stocks,
        args.batch_size,
        args.max_concurrent
    ))

if __name__ == "__main__":
    main() 