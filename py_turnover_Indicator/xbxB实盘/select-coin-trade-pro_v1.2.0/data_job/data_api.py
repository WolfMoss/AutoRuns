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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import py7zr
import requests

from config import flag_path, data_center_path, api_key, uuid, use_data_api, utc_offset
from core.account_manager import get_all_hour_offset_list
from core.binance.base_client import BinanceClient
from core.utils.commons import remedy_until_run_time
from core.utils.functions import create_finish_flag
from core.utils.log_kit import SimonsLogger
from core.utils.path_kit import get_file_path, get_folder_path
from data_job.kline import script_filename as kline_script_filename, has_swap, has_spot

# 获取脚本文件的路径
script_path = os.path.abspath(__file__)

# 提取文件名
script_filename = os.path.basename(script_path).split('.')[0]

# 自定义logger
logger = SimonsLogger(script_filename).logger

# 获取交易所对象
cli = BinanceClient.get_dummy_client()

# 获取账户配置的hour_offset分钟偏移
hour_offset_list = get_all_hour_offset_list()

# 获取分钟偏移数据url
api_url = 'https://api.quantclass.cn/api/data/realtime/coin/binance-1h'

# 零食存放解压目录
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
    if not use_data_api:
        logger.ok(f'当前配置use_data_api为 False ')
        return

    if not api_key or not uuid:
        logger.ok(f'当前配置 api_key 或 uuid 为空 ，执行{script_filename}脚本 download 完成')
        return

    # 排除提前时间的影响，先sleep到run_time时间
    remedy_until_run_time(run_time)

    _time = datetime.now()  # 获取当前时间

    # ================================================================
    # 1.调用api接口获取下载数据
    # ================================================================
    # 获取当前的小时偏移
    hour_offset = f'{run_time.minute}m'
    # 只处理配置的小时偏移
    if hour_offset not in hour_offset_list:
        logger.warning(f'非配置的小时偏移：{hour_offset}, 执行{script_filename}脚本 download 完成')
        return

    # 读取kline完成下载k线时间
    kline_download_time_file = get_file_path(data_center_path, kline_script_filename, 'kline-download-time.txt')
    try:
        with open(kline_download_time_file, 'r') as f:
            kline_download_time = f.read()
    except BaseException as e:
        logger.debug(str(e))
        logger.debug(f'当前跳过api下载k线数据，用交易所原始API下载')
        return

    # 如果下载k线时间小于2小时，跳过
    if run_time > datetime.strptime(kline_download_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=1):
        logger.warning(f'下载k线时间{kline_download_time}小于1小时，执行{script_filename}脚本 download 跳过')
        return

    # ================================================================
    # 2.获取下载地址，下载数据并存储
    # ================================================================
    # 请求接口，拿到下载地址
    swap_df, spot_df = fetch_url_and_download_data(hour_offset, run_time)
    if swap_df is None or spot_df is None:
        return

    # 读取下载的数据并存储
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_swap = executor.submit(export_to_csv, swap_df, 'swap', run_time)
        future_spot = executor.submit(export_to_csv, spot_df, 'spot', run_time)

    save_swap_list = future_swap.result()
    save_spot_list = future_spot.result()

    # ================================================================
    # 3.处理容错
    # ================================================================
    # =获取合约交易对的信息
    swap_market_info = cli.get_market_info(symbol_type='swap', require_update=True)
    swap_symbol_list = swap_market_info.get('symbol_list', [])
    # =加载现货交易对信息
    spot_market_info = cli.get_market_info(symbol_type='spot', require_update=True)
    spot_symbol_list = spot_market_info.get('symbol_list', [])

    # 计算数据差集
    diff_swap_list = set(swap_symbol_list) - set(save_swap_list)
    diff_spot_list = set(spot_symbol_list) - set(save_spot_list)

    # 存在数据差集，默认走原始下载逻辑
    if has_swap() and has_spot() and (diff_swap_list or diff_spot_list):
        logger.warning(f'数据差集，执行{script_filename}脚本 download 跳过')
        return
    elif has_swap() and diff_swap_list:
        logger.warning(f'swap 数据差集，执行{script_filename}脚本 download 跳过')
        return
    elif has_spot() and diff_spot_list:
        logger.warning(f'spot 数据差集，执行{script_filename}脚本 download 跳过')
        return
    else:
        logger.ok('没有数据缺失，准备生成完成标志文件···')

    # ================================================================
    # 4.写入kline完成下载k线时间
    # ================================================================
    with open(kline_download_time_file, 'w') as f:
        f.write(run_time.strftime('%Y-%m-%d %H:%M:%S'))
    # 提前生成flag数据，让startup去下单
    create_finish_flag(flag_path, run_time, signal=0)
    logger.ok(f'写入kline完成下载k线时间{kline_download_time_file}完成')

    logger.ok(f'执行{script_filename}脚本 download 完成, 总共耗时：{datetime.now() - _time} s')


def fetch_url_and_download_data(hour_offset, run_time):
    swap_df, spot_df = None, None
    for _ in range(3):
        try:
            download_url_data = fetch_download_url_data(hour_offset, run_time)
            if download_url_data is None:
                logger.warning(f'下载数据为空，执行{script_filename}脚本 download 跳过')
                break

            # 获取下载地址
            swap_url = download_url_data['data']['swap'] if has_swap() else None
            spot_url = download_url_data['data']['spot'] if has_spot() else None
            # 下载并解压数据
            swap_df = download_and_extract_7z(swap_url)
            spot_df = download_and_extract_7z(spot_url)
            if swap_df is None or spot_df is None:
                logger.warning(f'下载数据为空，执行{script_filename}脚本 download 跳过')
            break
        except BaseException as e:
            logger.error(str(e))
            logger.info('下载数据失败，等待2秒再尝试···')
            time.sleep(2)
            continue

    return swap_df, spot_df


def export_to_csv(df, symbol_type, run_time):
    if df.empty:
        return []
    # 获取当前的小时偏移
    hour_offset = f'{run_time.minute}m'

    # 获取kline脚本的存储分钟偏移数据的路径
    if not os.path.exists(os.path.join(data_center_path, kline_script_filename, symbol_type, hour_offset)):
        return []
    hour_offset_path = get_folder_path(data_center_path, kline_script_filename, symbol_type, hour_offset)

    # 处理数据
    df['symbol_type'] = symbol_type
    # ======================================
    # !!! API数据暂不提供资金费数据，默认设置为0
    df['fundingRate'] = 0
    # ======================================

    # 调整一下csv的列顺序，方便后续直接追加进去
    df = df[['candle_begin_time', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trade_num',
             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'symbol_type', 'fundingRate', 'tag']]

    success_symbol_list = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        # 遍历每个交易对
        for symbol, symbol_df in df.groupby('symbol'):
            futures.append(executor.submit(save_data, hour_offset_path, symbol, symbol_df))

        # 获取保存结果
        for future in futures:
            success_symbol_list.append(future.result())

    return success_symbol_list


def save_data(hour_offset_path, symbol, df):
    """
    根据获取数据的情况，自行编写保存数据函数
    """
    # 构建存储数据路径
    _hour_offset_file_path = hour_offset_path / f'{symbol}.csv'
    # 保存数据
    if not os.path.exists(_hour_offset_file_path):
        return ''
    else:
        df.to_csv(_hour_offset_file_path, encoding='gbk', index=False, header=False, mode='a')
    return symbol


def download_and_extract_7z(url):
    if url is None:
        return pd.DataFrame()

    # 获取最后一个"/"之后，"?"之前的数据
    file_name = url.split('?', 1)[0].split('/')[-1]
    # 创建解压的目录名称
    csv_filename = file_name.replace('.7z', '.csv')
    try:
        # 下载7z文件
        response = fetch_with_retry(requests.get, url, sleep_time=0.5)
        response.raise_for_status()
        logger.info(F'数据下载完成，准备解压缩文件: {file_name}···')

        # 将下载的二进制数据放入BytesIO对象
        archive_data = BytesIO(response.content)

        # 使用py7zr解压文件到临时目录
        with py7zr.SevenZipFile(archive_data, mode='r') as archive:
            archive.extractall(path=temp_dir)
        logger.info(f'数据解压缩完成，准备读取文件: {csv_filename}···')

        # 构建CSV文件的完整路径
        csv_path = temp_dir / csv_filename
        # 使用pandas读取CSV文件
        df = pd.read_csv(csv_path, encoding='gbk', parse_dates=['candle_begin_time'])
        logger.info(f'文件读取完成，准备清理临时文件: {csv_filename}···')

        # 清理临时文件
        os.remove(csv_path)
        logger.info('清理临时完成')

        logger.ok('下载并解压缩文件完成')
        return df
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        return None
    except py7zr.exceptions.ArchiveError as e:
        logger.error(f"Error extracting archive: {e}")
        return None
    except pd.errors.EmptyDataError as e:
        logger.error(f"Error reading CSV data: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return None


def fetch_download_url_data(hour_offset, run_time):
    logger.info('准备获取下载数据链接···')
    param = {
        'offset': hour_offset,
        'uuid': uuid
    }
    download_url_data = None
    for _ in range(12):
        try:
            download_url_data = fetch_with_retry(requests.get, api_url, param=param)
            download_url_data = download_url_data.json()
            logger.ok(f'获取下载数据链接完成，数据结果:{download_url_data}')
            if download_url_data['data']['ts'] == (run_time + timedelta(hours=(8 - utc_offset))).strftime('%Y%m%d%H%M'):
                break
            else:
                download_url_data = None
                logger.info(f'数据获取时间与run_time不符，等待1.5秒再获取数据')
                time.sleep(1.5)
        except BaseException as e:
            logger.error(f'获取下载数据链接失败：{str(e)}')

    return download_url_data


def fetch_with_retry(func, url, param=None, retries=8, sleep_time: float = 3):
    for i in range(retries):
        try:
            if func.__name__ == 'get':
                response = func(url, params=param, headers={'api-key': api_key}, timeout=10)
            else:
                response = func(url, data=param, headers={'api-key': api_key}, timeout=10)
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


def clean_data():
    """
    根据获取数据的情况，自行编写清理冗余数据函数
    """
    pass


if __name__ == '__main__':
    download(datetime.strptime('2024-09-30 13:00:00', "%Y-%m-%d %H:%M:%S"))
