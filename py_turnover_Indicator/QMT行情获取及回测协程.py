import pandas as pd
from xtquant import xtdata
import pymysql
from datetime import datetime
from MyTT import *
import asyncio
import concurrent.futures
from typing import Dict, List
from functools import partial

# 设定常量
CHUNK_SIZE = 1000  # 可以根据实际情况调整
MAX_WORKERS = 10  # 可以根据CPU核心数调整


async def huice(stock: str, df: pd.DataFrame) -> None:
    try:
        CLOSE = df.close.values
        OPEN = df.open.values
        HIGH = df.high.values
        LOW = df.low.values

        MA5 = MA(CLOSE, 5)
        MA10 = MA(CLOSE, 10)
        MA20 = MA(CLOSE, 20)
        MA250 = MA(CLOSE, 250)

        if not (RET(CLOSE > MA5) and RET(CLOSE > MA10) and RET(CLOSE > MA20)):
            return

        if not LAST(CLOSE < MA250, 140, 20)[-1]:
            return

        if not CLOSE[-2] <= MA250[-2]:
            return

        if not CLOSE[-1] > MA250[-1]:
            return

        print(stock)
    except Exception as e:
        print(f"Error processing {stock}: {str(e)}")


async def process_chunk(chunk: Dict) -> None:
    tasks = []
    for stock, df in chunk.items():
        tasks.append(huice(stock, df))
    await asyncio.gather(*tasks)


def split_dict(data: Dict, chunk_size: int) -> List[Dict]:
    items = list(data.items())
    return [
        dict(items[i:i + chunk_size])
        for i in range(0, len(items), chunk_size)
    ]


async def main(history_data: Dict) -> None:
    # 将数据分块
    chunks = split_dict(history_data, CHUNK_SIZE)

    # 创建任务列表
    tasks = [process_chunk(chunk) for chunk in chunks]

    # 使用 asyncio.gather 并发执行所有任务
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    start_time = datetime.now()
    print('开始时间：', start_time)

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

    # 运行主程序
    try:
        asyncio.run(main(history_data))
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
    finally:
        end_time = datetime.now()
        print('结束时间：', end_time)
        print('总耗时：', end_time - start_time)
