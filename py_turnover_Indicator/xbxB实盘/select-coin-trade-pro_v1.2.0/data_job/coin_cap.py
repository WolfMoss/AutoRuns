"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from config import data_center_path, api_key, uuid, utc_offset, data_source_dict
from core.utils.commons import remedy_until_run_time
from core.utils.log_kit import SimonsLogger
from core.utils.path_kit import get_folder_path, get_file_path

# 获取脚本文件的路径(不需要配置)
script_path = os.path.abspath(__file__)

# 提取文件名(不需要配置)
script_filename = os.path.basename(script_path).split('.')[0]

# 自定义logger(不需要配置)
logger = SimonsLogger(script_filename).logger

# 产品名称(不需要配置)
product = 'coin-cap'

# cmc 原始数据目录 ---->  需要配置
# 如果配置是一个错误的路径，那么只会保存增量更新的数据
raw_data_path = data_source_dict[product][1]

if Path(raw_data_path).exists():
    pass
else:
    logger.debug('需要在`data_job -> coin_cap.py`更新正确的 coin-cap 数据存放路径')
    logger.critical(f'[COIN CAP] {raw_data_path} 路径不存在，数据更新终止')
    exit()

# 临时存放解压目录(不需要配置)
temp_dir = get_folder_path(data_center_path, 'temp')


def download(run_time):
    """
    根据获取数据的情况，自行编写下载数据函数
    :param run_time:    运行时间
    """
    logger.info(f'执行{script_filename}脚本 download 开始')
    # ================================================================
    # 0.调试相关配置区域
    # ================================================================
    if not api_key or not uuid:
        logger.warning(f'当前配置 api_key 或 uuid 为空 ，执行{script_filename}脚本 download 完成')
        return

    # 读取kline完成下载k线时间
    download_time_file = get_file_path(data_center_path, script_filename, 'download-time.txt')
    try:
        with open(download_time_file, 'r') as f:
            kline_download_time = f.read()
    except BaseException as e:
        # 随便取一个比较靠前的时间节点
        kline_download_time = '2021-01-01 00:00:00'

    # 如果当日数据已经下载过，跳过操作
    run_time = run_time - timedelta(hours=utc_offset)  # 转成 utc 时间
    if run_time.date() <= datetime.strptime(kline_download_time, '%Y-%m-%d %H:%M:%S').date():
        logger.warning(f'下载k线时间{kline_download_time}小于1天，执行{script_filename}脚本 download 跳过')
        return

    # 排除提前时间的影响，先sleep到run_time时间
    remedy_until_run_time(run_time)

    _time = datetime.now()  # 获取当前时间

    # ================================================================
    # 1.获取下载地址，下载数据并存储
    # ================================================================
    # 请求接口，拿到下载地址
    download_time = run_time - timedelta(days=1)
    cmc_df = fetch_url_and_download_data(download_time)
    if cmc_df is None:
        return

    # 读取下载的数据并存储
    export_to_csv(cmc_df)

    # ================================================================
    # 2.完成下载时间
    # ================================================================
    with open(download_time_file, 'w') as f:
        f.write(run_time.strftime('%Y-%m-%d %H:%M:%S'))
    logger.ok(f'完成下载{script_filename}时间{download_time_file}完成')

    logger.ok(f'执行{script_filename}脚本 download 完成, 总共耗时：{datetime.now() - _time} s')


def fetch_url_and_download_data(run_time):
    cmc_df = None
    for _ in range(10):
        try:
            # 获取下载地址
            download_url = fetch_download_url_data(run_time)
            if download_url is None:
                logger.warning(f'下载链接为空，执行{script_filename}脚本 download 跳过')
                break

            # 下载并解压数据
            cmc_df = download_and_extract(download_url)
            if cmc_df is None:
                logger.warning(f'下载数据为空，执行{script_filename}脚本 download 跳过')
            break
        except BaseException as e:
            logger.error(str(e))
            logger.info('下载数据失败，等待10秒再尝试···')
            time.sleep(10)
            continue

    return cmc_df


def export_to_csv(df):
    if df.empty:
        return []

    # 调整一下csv的列顺序，方便后续直接追加进去
    df = df[['candle_begin_time', 'symbol', 'id', 'name', 'date_added', 'max_supply', 'circulating_supply',
             'total_supply', 'usd_price', 'max_mcap', 'circulating_mcap', 'total_mcap']]

    success_symbol_list = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        # 遍历每个交易对
        for symbol, symbol_df in df.groupby('symbol'):
            futures.append(executor.submit(save_data, symbol, symbol_df))

        # 获取保存结果
        for future in futures:
            success_symbol_list.append(future.result())
    return success_symbol_list


def save_data(symbol, df):
    """
    根据获取数据的情况，自行编写保存数据函数
    """
    # 构建存储数据路径
    file_path = Path(raw_data_path) / f'{symbol}.csv'
    # 保存数据
    if not file_path.exists():
        pd.DataFrame(columns=['数据由邢不行整理，对数据字段有疑问的，可以直接微信私信邢不行，微信号：xbx9585']).to_csv(
            file_path, encoding='gbk', index=False)
        df.to_csv(file_path, encoding='gbk', index=False, mode='a')
    else:
        df.to_csv(file_path, encoding='gbk', index=False, header=False, mode='a')
    return symbol


def download_and_extract(url):
    if url is None:
        return pd.DataFrame()

    # 获取最后一个"/"之后，"?"之前的数据
    file_name = url.split('?', 1)[0].split('/')[-1]
    # 创建解压的目录名称
    csv_filename = file_name.replace('.7z', '.csv')
    # 构建CSV文件的完整路径
    csv_path = temp_dir / csv_filename
    res = fetch_with_retry(requests.get, url, stream=True)
    if res is None:
        return None
    with open(csv_path, mode='wb') as f:
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    logger.info(f'数据下载完成')

    # 使用pandas读取CSV文件
    try:
        df = pd.read_csv(csv_path, encoding='gbk', parse_dates=['candle_begin_time'])
    except:
        df = pd.read_csv(csv_path, encoding='gbk', skiprows=1, parse_dates=['candle_begin_time'])
    logger.info(f'文件读取完成，准备清理临时文件: {csv_filename}···')

    # 清理临时文件
    os.remove(csv_path)
    logger.info('清理临时完成')

    logger.ok('下载并解压缩文件完成')
    return df


def fetch_download_url_data(run_time):
    logger.info('准备获取下载数据链接···')
    # 获取分钟偏移数据url
    url_ = f'https://api.quantclass.cn/api/data/get-download-link/{product}-daily/{run_time.strftime("%Y-%m-%d")}'
    param = {
        'uuid': uuid
    }
    download_url_data = None
    for _ in range(5):
        try:
            resp = fetch_with_retry(requests.get, url_, param=param)
            if resp is not None:
                download_url_data = resp.text
                logger.ok(f'获取下载数据链接完成，数据结果:{download_url_data}')
                break
            else:
                logger.debug('你的UUID和API-KEY可能写错了，没有权限，5s后重试')
                time.sleep(5)
        except BaseException as e:
            logger.error(f'获取下载数据链接失败：{str(e)}')
            time.sleep(5)

    return download_url_data


def fetch_with_retry(func, url, param=None, retries=8, sleep_time: float = 3, **kwargs):
    for i in range(retries):
        try:
            if func.__name__ == 'get':
                response = func(url, params=param, headers={'api-key': api_key}, timeout=10, **kwargs)
            else:
                response = func(url, data=param, headers={'api-key': api_key}, timeout=10, **kwargs)
            # 检查响应状态码是否成功 (200-299)
            if 200 <= response.status_code < 300:
                return response  # 假设我们期望返回JSON数据
            elif 400 <= response.status_code < 500:
                logger.error(f"Request failed with status {response.status_code}, retrying...")
                return None
            else:
                logger.error(f"Request failed with status {response.status_code}, retrying...")
        except BaseException as e:
            import traceback
            logger.error(e)
            logger.error(f"Request failed due to: {traceback.format_exc()}, retrying...")

        # 除了最后一次尝试，其他时候等待一段时间再重试
        if i < retries - 1:
            time.sleep(sleep_time)
    else:
        logger.error("Maximum retries reached, request failed.")
        raise Exception('Maximum retries reached, request failed')


def clear_duplicates(file_path):
    if not file_path.exists():
        return
    df = pd.read_csv(file_path, encoding='gbk', skiprows=1, parse_dates=['candle_begin_time'])
    df.drop_duplicates(subset=['candle_begin_time'], keep='last', inplace=True)
    df.sort_values('candle_begin_time', inplace=True)  # 通过candle_begin_time排序
    # df.to_csv(file_path, encoding='gbk', index=False)
    pd.DataFrame(columns=['数据由邢不行整理，对数据字段有疑问的，可以直接微信私信邢不行，微信号：xbx9585']).to_csv(
        file_path, encoding='gbk', index=False)
    df.to_csv(file_path, encoding='gbk', index=False, mode='a')


def clean_data():
    """
    根据获取数据的情况，自行编写清理冗余数据函数
    """
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(clear_duplicates, _file) for _file in Path(raw_data_path).rglob('*.csv')]

        for future in tqdm(as_completed(futures), total=len(futures), desc='清理冗余数据'):
            try:
                future.result()
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                logger.debug(traceback.format_exc())


if __name__ == '__main__':
    download(datetime.strptime('2025-01-08 09:00:00', "%Y-%m-%d %H:%M:%S"))
    # clean_data()
