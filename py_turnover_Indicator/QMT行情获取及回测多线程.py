import pandas as pd
from xtquant import xtdata
from datetime import datetime
from MyTT import *
import asyncio
import concurrent.futures
from typing import Dict, List
from functools import partial
import multiprocessing as mp
import os

# 设定常量
CHUNK_SIZE = 1000  # 可以根据实际情况调整
CPU_COUNT = mp.cpu_count()
PROCESS_COUNT = max(1, CPU_COUNT - 1)  # 预留一个CPU核心
MAX_WORKERS = 10  # 异步任务的最大并发数


def calculate_indicators(df: pd.DataFrame) -> tuple:
    """计算技术指标"""
    CLOSE = df.close.values
    MA5 = MA(CLOSE, 5)
    MA10 = MA(CLOSE, 10)
    MA20 = MA(CLOSE, 20)
    MA250 = MA(CLOSE, 250)
    return CLOSE, MA5, MA10, MA20, MA250


def check_conditions(CLOSE, MA5, MA10, MA20, MA250) -> bool:
    """检查交易条件"""
    if not (RET(CLOSE > MA5) and RET(CLOSE > MA10) and RET(CLOSE > MA20)):
        return False
    if not LAST(CLOSE < MA250, 140, 20)[-1]:
        return False
    if not CLOSE[-2] <= MA250[-2]:
        return False
    if not CLOSE[-1] > MA250[-1]:
        return False
    return True


async def huice(stock: str, df: pd.DataFrame) -> str:
    """回测单个股票"""
    try:
        CLOSE, MA5, MA10, MA20, MA250 = calculate_indicators(df)

        if check_conditions(CLOSE, MA5, MA10, MA20, MA250):
            return stock
        return ""
    except Exception as e:
        print(f"Error processing {stock}: {str(e)}")
        return ""


async def process_chunk(chunk: Dict) -> List[str]:
    """处理数据块"""
    results = []
    for stock, df in chunk.items():
        result = await huice(stock, df)
        if result:
            results.append(result)
    return results


def process_chunk_in_process(chunk: Dict) -> List[str]:
    """在进程中处理数据块"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        results = loop.run_until_complete(process_chunk(chunk))
        return results
    finally:
        loop.close()


def split_dict(data: Dict, chunk_size: int) -> List[Dict]:
    """将字典分割成小块"""
    items = list(data.items())
    return [
        dict(items[i:i + chunk_size])
        for i in range(0, len(items), chunk_size)
    ]


def main(history_data: Dict) -> List[str]:
    """主函数"""
    # 将数据分块
    chunks = split_dict(history_data, CHUNK_SIZE)

    results = []
    # 使用进程池处理数据块
    with concurrent.futures.ProcessPoolExecutor(max_workers=PROCESS_COUNT) as executor:
        futures = [executor.submit(process_chunk_in_process, chunk)
                   for chunk in chunks]

        # 收集结果
        for future in concurrent.futures.as_completed(futures):
            try:
                chunk_results = future.result()
                results.extend(chunk_results)
            except Exception as e:
                print(f"Error in process: {str(e)}")

    return results


if __name__ == "__main__":
    start_time = datetime.now()
    print('开始时间：', start_time)
    print(f'使用进程数：{PROCESS_COUNT}')

    # 获取股票列表
    code_list = xtdata.get_stock_list_in_sector('沪深A股')
    period = "1d"

    # 读取历史数据
    history_data = xtdata.get_local_data(
        [], code_list, period=period,
        start_time='', end_time='',
        count=-1, dividend_type='front'
    )
    print('行情加载完成')
    print(f'总数据量：{len(history_data)}')

    try:
        # 运行主程序
        matching_stocks = main(history_data)

        # 输出结果
        print("\n符合条件的股票：")
        for stock in matching_stocks:
            print(stock)
        print(f"共找到 {len(matching_stocks)} 只符合条件的股票")

    except Exception as e:
        print(f"Error in main execution: {str(e)}")
    finally:
        end_time = datetime.now()
        print('结束时间：', end_time)
        print('总耗时：', end_time - start_time)
