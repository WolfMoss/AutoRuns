# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
import json
import os
import random
import re
import shutil
import time
import traceback
import zipfile
from datetime import datetime, timedelta
from fuel.api_client import client as base_data_api

import requests
from retrying import retry

from config import fuel_data_path
from fuel.preprocess_data2 import preprocess_data
from model.model import ProductInfo
from utils.constant import product_list, product_display_name_dict
from utils.log_kit import get_logger, divider
from utils.path_kit import get_data_path, get_folder_by_root, get_file_path, get_data_file_path

logger = get_logger()


def del_folder(target_folder_path):
    """
    删除当前存在的文件夹.不删除能提高效率,但是会存在文件夹里多手工放入文件的可能性,这样的话会导致未来做md5的时候产生问题(md5是未来可能的需求)
    :param target_folder_path: 目标目录
    :return:
    """
    if os.path.isdir(target_folder_path):
        logger.info(f"准备删除{target_folder_path}")
        shutil.rmtree(target_folder_path)


def unzip(file_name, target_folder_path):
    """
    解压缩
    :param file_name: 解压缩的文件名
    :param target_folder_path: 解压缩目标目录
    :return:
    """
    # 解压缩
    logger.info(f"准备将文件 {file_name} 解压缩至 {target_folder_path}")
    with zipfile.ZipFile(file_name, "r") as zip_ref:
        zip_ref.extractall(target_folder_path)
    logger.info(f"文件 {file_name} 解压缩至 {target_folder_path}完成")


def get_file_in_folder(
        path, file_type, contains=None, contains_list=(), filters=(), drop_type=False
):
    """
    获取指定文件夹下的文件
    :param path: 文件夹路径
    :param file_type: 文件类型
    :param contains: 需要包含的字符串，默认不含
    :param contains_list: 需要包含的字符串，默认不含
    :param filters: 字符串中需要过滤掉的内容
    :param drop_type: 是否要保存文件类型
    :return:
    """
    file_list = os.listdir(path)
    file_list = [file for file in file_list if file_type in file]
    if contains:
        file_list = [file for file in file_list if contains in file]
    if len(contains_list) > 0:
        _file_list = []
        for con in contains_list:
            _file_list += [file for file in file_list if con in file]
        file_list = _file_list
    for con in filters:
        file_list = [file for file in file_list if con not in file]
    if drop_type:
        file_list = [file[: file.rfind(".")] for file in file_list]
    return file_list


def handle_zip_file(full_data_zip_path):
    # 从文件名中,获取目标目录的目录名称,如`D:\量堂工作\数据更新\网页api\data\stock-hk-stock-data-2023-11-14.zip`解压缩的目录是`stock-hk-stock-data`
    match = re.search(r"([^/\\]*?)-\d{4}-\d{2}-\d{2}", full_data_zip_path)
    target_path = get_folder_by_root(fuel_data_path, match.group(1))
    target_path_temp = target_path + "_temp"

    # 如果有temp目录就先删掉
    del_folder(target_path_temp)
    logger.info("正在解压缩文件...")

    # 解压缩文件到目标目录
    unzip(full_data_zip_path, target_path_temp)
    logger.info("数据完成解压.")

    # 删掉原本存文件的目录
    logger.info("清理旧数据并移动文件...")
    del_folder(target_path)

    # 把temp目录改为正确的目录名称
    os.rename(target_path_temp, target_path)
    logger.info("压缩包处理完毕.")

    return target_path


def read_time_in_timestamp(full_data_path):
    """
    从解压缩的文件中，找到timestamp.txt，返回数据日期
    """

    filepath = os.path.join(full_data_path, "timestamp.txt")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            first_line = f.readline().strip()
        content_time_local = first_line.split(",")[0]
        os.remove(filepath)
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if bool(pattern.match(content_time_local)):
            logger.info(
                f"{full_data_path}有timestamp.txt，数据更新时间为 {content_time_local}",
            )
            return content_time_local
    return None


def _download_file_zip(download_url, temp_path, max_retries=5):
    """
    下载并解压ZIP文件，带重试逻辑

    该函数实现了完整的文件下载和解压流程，包括：
    - 流式下载大文件
    - 自动重试机制
    - 损坏文件清理

    :param download_url: 文件下载链接
    :type download_url: str
    :param temp_path: 临时文件存储路径
    :type temp_path: Path
    :param max_retries: 最大重试次数，默认3次
    :type max_retries: int
    :return: 成功返回True，失败返回False
    :rtype: bool

    note:
        - 使用流式下载避免内存溢出
        - 失败时会自动清理损坏的临时文件
        - 支持断点续传（如果文件已存在则跳过下载）
    """
    for attempt in range(max_retries):
        try:
            # 检查文件是否已存在，避免重复下载
            if not temp_path.exists():
                logger.info(f"开始下载文件: {download_url}")
                # 使用流式下载，避免大文件导致内存溢出
                with requests.get(download_url, stream=True, timeout=60 * 30) as r:
                    r.raise_for_status()
                    with open(temp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                logger.info(f"文件下载完成: {temp_path}")

            return True
        except Exception as e:
            if attempt < max_retries - 1:  # 不是最后一次重试
                # 指数退避策略
                delay = random.uniform(1, 3) * (attempt + 1)
                logger.warning(f"下载失败，第{attempt + 1}次重试，{delay:.2f}秒后重试: {e}")
                time.sleep(delay)
                # 清理可能损坏的临时文件
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
            else:
                logger.error(f"下载失败，已达到最大重试次数{max_retries}: {e}")
                logger.error(traceback.format_exc())

    return False  # 返回False而不是抛出异常，确保调用方能正常处理失败情况


def get_latest_full_data_zip_path(full_data_name):
    # 获取文件夹下所有的zip包
    file_list = get_file_in_folder(get_data_path('temp'),'zip', contains=full_data_name)
    if len(file_list) == 0:
        logger.error(f"{full_data_name}全量更新文件不存在")
        return None

    # 取出最新的文件
    filename = file_list[0]
    full_data_file_path = get_data_file_path('temp', filename)
    logger.info(f"读取到最新文件: {filename}")

    # 读取这个文件的日期
    pattern = r"\b(\d{4}-\d{2}-\d{2})"
    match = re.search(pattern, filename)
    if match:
        filename_dt_str = match.group(1)
        readable_dt = datetime.strptime(filename_dt_str, "%Y-%m-%d")
        logger.info(f"文件名时间戳为: {filename_dt_str}")
    else:
        # 如果文件读到的是一个不带日期的数据，那就获取最近更新的时间并且减去1天
        latest_mod_time = os.path.getmtime(full_data_file_path)
        readable_dt = datetime.fromtimestamp(latest_mod_time)
        logger.info(
            f"文件名并无时间戳，获取zip文件更新时间: {readable_dt}"
        )

    # 往前推2天，留足buffer余地
    full_data_file_date = f"{(readable_dt - timedelta(days=2)).date()}"

    return full_data_file_date


def download_full_file(product_name, url):
    product_info_path = get_file_path(fuel_data_path, f"product_info.json")
    if product_info_path.exists():
        product_info_dict = json.loads(product_info_path.read_text(encoding='utf-8'))
        # 反序列化为ProductInfo对象
        for k, v in product_info_dict.items():
            product_info_dict[k] = ProductInfo.dict_to_product_info(v)
    else:
        product_info_dict = {}

    # 查询当前产品是否存在记录中，不存在返回一个空数据
    product_info = product_info_dict.get(product_name, ProductInfo(product_name=product_name))
    product_info.display_name = product_display_name_dict.get(product_name, None)
    product_info.full_status = 'downloading'

    # 下载状态starting
    filename = url.split("/")[-1].split('?')[0]
    temp_path = get_data_path('temp') / filename
    # 调用下载
    is_success = _download_file_zip(url, temp_path=temp_path)
    # 记录下载状态
    product_info.full_status = 'success' if is_success else 'failed'

    if is_success:
        # 解压文件
        target_path = handle_zip_file(str(temp_path))
        # 获取最新的文件地址以及距离最近的更新时间
        zip_file_date_2days_ago = get_latest_full_data_zip_path(product_name)

        content_time_local = read_time_in_timestamp(target_path)
        if content_time_local is None:
            logger.info(
                f"{target_path}没有timestamp.txt，数据更新时间用zip文件时间近似。倒推2天为：{zip_file_date_2days_ago}",
            )
            content_time_local = zip_file_date_2days_ago
        # 记录下载状态
        product_info.dataContentTime = content_time_local
        product_info.lastUpdateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 保存产品状态
    logger.info(product_info)
    # 保存时转为dict
    product_info_dict[product_name] = product_info.model_dump()
    # 序列化为ProductInfo对象
    for k, v in product_info_dict.items():
        product_info_dict[k] = v.model_dump() if isinstance(v, ProductInfo) else v
    logger.info(product_info_dict)
    product_info_path.write_text(json.dumps(product_info_dict, ensure_ascii=False, indent=2), encoding='utf-8')


@retry(stop_max_attempt_number=5)
def get_product_data_from_url():
    """
    从API获取数据
    :return:
    """
    url = "https://api.quantclass.cn/api/product/data/status/by_category/data-api-products"
    con = requests.get(url, params={"client": 1}, timeout=5)
    data_json = json.loads(con.text)
    return data_json["data"]


@retry(stop_max_attempt_number=5)
def do_date_list_req(product_name, date_str):
    """
    从API获取数据
    :return:
    """
    url = f"https://api.quantclass.cn/api/product/recent-update-record/{product_name}/{date_str}"
    con = requests.get(url, params={"client": 1}, timeout=5)
    data_json = json.loads(con.text)
    return data_json["data"]


def fetch_update_date_list(product_name, local_data_content_time):
    try:
        date_list = do_date_list_req(product_name, local_data_content_time)
    except Exception as e:
        # 如果出现报错，就直接返回空值先
        logger.warning(f"{product_name}获取date list的时候出错了：{e}")
        return []

    if len(date_list) == 0:
        return []

    """
    根据本地时间，筛选日期们
    """
    min_date = min(date_list)
    logger.info(
        f"{product_name}: {', '.join(date_list)}, min: {min_date}, local: {local_data_content_time}"
    )
    if local_data_content_time >= min_date:
        return sorted(
            [
                date_str[:10]
                for date_str in date_list
                if date_str >= local_data_content_time
            ]  # 保留更新时间之后的数据
        )
    else:
        # 没办法补数据了，需要更新全量
        logger.warning(f"{product_name}数据较为陈旧，需要先进行全量更新，增量暂停更新。")
        return []


def do_update(product_name, full_data_name, date_list):
    err_list = []
    sequence = 0
    total_dates = len(date_list)
    success_name = ""

    for date_time in date_list:
        sequence += 1
        logger.ok(f"[{sequence}/{total_dates}] {product_name} {date_time}")
        ret_df = base_data_api.update_single_data(
            product=product_name,
            date_time=date_time,
            full_data_name=full_data_name,
        )
        is_error = ret_df.iloc[0]["error"]
        err_list.append(is_error)

        if is_error:
            logger.error(
                f'{product_name} 数据更新错误 latestDate{ret_df.iloc[0]["date_time"]}更新错误'
            )

            # ‼️当遇到数据报错的时候，直接退出更新，并且最新时间更新的上一个日期的时间戳
            logger.error(
                f"({sequence}/{total_dates}) {product_name} 更新出错，自动推迟该产品延迟6h后更新。如果有需要可手动更新"
            )
            raise Exception(f"({sequence}/{total_dates}) {product_name} 更新出错，自动推迟该产品延迟6h后更新。如果有需要可手动更新")
        else:
            success_name = product_name

    # summery report
    if any(err_list):
        logger.warning(f"{product_name}未执行全部增量更新，部分日期更新错误")
        success_name = ''

    return success_name


def download_daily_file(product_name):
    product_info_path = get_file_path(fuel_data_path, f"product_info.json")
    if product_info_path.exists():
        product_info_dict = json.loads(product_info_path.read_text(encoding='utf-8'))
        # 反序列化为ProductInfo对象
        for k, v in product_info_dict.items():
            product_info_dict[k] = ProductInfo.dict_to_product_info(v)
    else:
        product_info_dict = {}

    # 查询当前产品是否存在记录中，不存在返回一个空数据
    product_info = product_info_dict.get(product_name, ProductInfo(product_name=product_name))
    product_info.display_name = product_display_name_dict.get(product_name, None)
    product_daily_name = product_info.product_daily_name

    # 3. 联网读取在线的信息
    remote_data_json = get_product_data_from_url()
    remote_product_info = remote_data_json.get(product_daily_name, None)

    # 5. 获取服务器时间，并且确定是否需要更新
    remote_data_time = remote_product_info[2]
    local_data_time = product_info.dataContentTime

    if local_data_time != remote_data_time:
        logger.ok(f"服务器有更新。本地：{local_data_time}，服务器：{remote_data_time}")
        date_list = fetch_update_date_list(
            product_daily_name, local_data_time
        )
    else:
        logger.ok(f"服务器无更新。本地：{local_data_time}，服务器：{remote_data_time}")
        date_list = []

    # 6. 根据返回的日期列表，更新指定时间段的数据
    if date_list:
        logger.ok(f"即将更新以下日期数据：{date_list}...")
    else:
        logger.info(f"已是最新({datetime.now().isoformat()})")
    product_info.update_status = 'downloading'

    # 7. 执行更新
    success_name = do_update(
        product_daily_name, product_name, date_list
    )

    if success_name:
        product_info.update_status = 'success'
        product_info.lastUpdateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        product_info.update_status = 'failed'

    product_info.dataContentTime = max(date_list)

    # 保存产品状态
    logger.info(product_info)
    # 保存时转为dict
    product_info_dict[product_name] = product_info.model_dump()
    # 序列化为ProductInfo对象
    for k, v in product_info_dict.items():
        product_info_dict[k] = v.model_dump() if isinstance(v, ProductInfo) else v
    product_info_path.write_text(json.dumps(product_info_dict, ensure_ascii=False, indent=2), encoding='utf-8')


def download_full_and_preprocess_data(product_url_dict):
    result = []
    for product_name, product_url in product_url_dict.items():
        # 下载数据
        try:
            download_full_file(product_name, product_url)
            result.append(product_name)
        except Exception as e:
            logger.error(f'全量更新数据失败: {product_name}')
            logger.error(traceback.format_exc())

        divider(f'{product_name} 处理结束')

    logger.ok(f'全量更新数据完成: {result}')
    # k 线数据更新完成，执行预处理逻辑
    if {'coin-binance-swap-candle-csv-1h', 'coin-binance-candle-csv-1h'}.issubset(set(result)):
        execute_preprocess_data('coin-binance-spot-swap-preprocess-pkl-1h')


def download_daily_and_preprocess_data():
    result = []
    for product_name in product_list:
        try:
            download_daily_file(product_name)
            result.append(product_name)
        except Exception as e:
            logger.error(f'增量更新数据失败: {product_name}')
            logger.error(traceback.format_exc())

        divider(f'{product_name} 处理结束')

    logger.ok(f'增量更新数据完成: {result}')
    # k 线数据更新完成，执行预处理逻辑
    execute_preprocess_data('coin-binance-spot-swap-preprocess-pkl-1h')


def execute_preprocess_data(product_name):
    product_info_path = get_file_path(fuel_data_path, f"product_info.json")
    if product_info_path.exists():
        product_info_dict = json.loads(product_info_path.read_text(encoding='utf-8'))
        # 反序列化为ProductInfo对象
        for k, v in product_info_dict.items():
            product_info_dict[k] = ProductInfo.dict_to_product_info(v)
    else:
        product_info_dict = {}

    # 查询当前产品是否存在记录中，不存在返回一个空数据
    product_info = product_info_dict.get(product_name, ProductInfo(product_name=product_name))
    product_info.display_name = product_display_name_dict.get(product_name, None)

    product_info.full_status = 'processing'
    product_info.update_status = 'processing'

    try:
        preprocess_data()
        product_info.full_status = 'success'
        product_info.update_status = 'success'
    except Exception as e:
        logger.error(traceback.format_exc())
        product_info.full_status = 'failed'
        product_info.update_status = 'failed'

    product_info.dataContentTime = max(product_info_dict['coin-binance-swap-candle-csv-1h'].dataContentTime,
                                       product_info_dict['coin-binance-candle-csv-1h'].dataContentTime)
    product_info.lastUpdateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 保存产品状态
    logger.info(product_info)
    # 保存时转为dict
    product_info_dict[product_name] = product_info.model_dump()
    # 序列化为ProductInfo对象
    for k, v in product_info_dict.items():
        product_info_dict[k] = v.model_dump() if isinstance(v, ProductInfo) else v
    product_info_path.write_text(json.dumps(product_info_dict, ensure_ascii=False, indent=2), encoding='utf-8')

