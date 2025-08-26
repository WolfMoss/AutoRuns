# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
import datetime
import os
import re
import shutil
import sys
import traceback
import warnings
from concurrent.futures import as_completed, ProcessPoolExecutor

import pandas as pd
import requests
from retrying import retry
from tqdm import tqdm


from config import njobs, proxies, fuel_data_path as root_path
from utils.log_kit import get_logger
from utils.simons import DataManager
from utils import compress_kit
from utils.path_kit import get_data_path, get_folder_by_root

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

data_manager = DataManager()

# 初始化日志记录器
logger = get_logger()

def up1(df_, file_name, all_data_path, product):
    # 根据股票代码拼接全量数据路径
    all_data_path_ = os.path.join(all_data_path, file_name + ".csv")
    # 获取路径
    mk_dir = (
        all_data_path_
        if not all_data_path_.endswith("csv")
        else os.path.split(all_data_path_)[0]
    )
    if not os.path.exists(mk_dir):  # 判断路径是否存在
        # 如果路径不存在即创建，并设置全量的数据为空的
        os.makedirs(mk_dir)
        all_df = pd.DataFrame()
    else:
        # 读取数据
        all_df = data_manager.read_file(all_data_path_, product)
    # 把全量数据与增量数据合并
    to_file_df = data_manager.concat_data([all_df, df_], product)
    logger.info(
        f"正在更新{file_name}的{product}数据，数据行数：{df_.shape[0]}行（增）、{all_df.shape[0]}行(全)、{to_file_df.shape[0]}行("
        f"新)，数据列数：{df_.shape[1]}列（增）、{all_df.shape[1]}列(全)、{to_file_df.shape[1]}列(新)"
    )
    # 写出
    if product != "stock-main-index-data":
        to_file_df.columns = pd.MultiIndex.from_tuples(
            zip(
                [
                    "数据由邢不行整理，对数据字段有疑问的，可以直接微信私信邢不行，微信号：xbx297"
                ]
                + [""] * (to_file_df.shape[1] - 1),
                to_file_df.columns,
            )
        )
    # to_file_df.to_csv(all_data_path_, index=False, encoding='gbk')
    temp_file = root_path + f"/data/temp/{product}/{file_name}.csv"
    to_file_df.to_csv(temp_file, index=False, encoding="gbk")
    os.replace(temp_file, all_data_path_)
    return file_name


# 更新数据的主函数，封装为函数便于并行
def up2(new_path, _save_path, all_data_path_, product):
    # print('process...', new_path)

    # 处理文件路径
    _save_path = _save_path.replace("\\", "/")
    new_path = new_path.replace("\\", "/")
    all_data_path_ = os.path.join(
        all_data_path_, re.findall("%s(.*)" % _save_path, new_path)[0][1:]
    )
    if not os.path.exists(all_data_path_):  # 判断文件夹是否存在
        mk_dir = (
            all_data_path_
            if not all_data_path_.endswith("csv")
            else os.path.split(all_data_path_)[0]
        )
        if not os.path.exists(mk_dir):
            os.makedirs(mk_dir)
        logger.info(f"{product}数据复制至{all_data_path_}")
        shutil.move(f"{new_path}", f"{all_data_path_}")
    else:
        # print('read local...')
        all_df = data_manager.read_file(all_data_path_, product)
        # print('read new...')
        new_df = pd.DataFrame(data_manager.read_file(new_path, product))

        # print('merge...')
        df = data_manager.concat_data([all_df, new_df], product)
        logger.info(
            f"正在更新{new_path}的{product}数据，数据行数：{new_df.shape[0]}行（增）、{all_df.shape[0]}行(全)、{df.shape[0]}行("
            f"新)，数据列数：{new_df.shape[1]}列（增）、{all_df.shape[1]}列(全)、{df.shape[1]}列(新)"
        )

        # print('add watermark')
        # 写出
        df.columns = pd.MultiIndex.from_tuples(
            zip(
                [
                    "数据由邢不行整理，对数据字段有疑问的，可以直接微信私信邢不行，微信号：xbx297"
                ]
                + [""] * (df.shape[1] - 1),
                df.columns,
            )
        )
        # df.to_csv(all_data_path_, index=False, encoding='gbk')
        temp_file = (
                root_path + f'/data/temp/{product}/{new_path.split("/")[-1]}'
        )

        # print('save to', temp_file)
        df.to_csv(temp_file, index=False, encoding="gbk")

        # print('move to', all_data_path_)
        os.replace(temp_file, all_data_path_)
    return new_path


class BaseDataApi(object):
    def __init__(
            self, hid: str, api_key: str, all_data_path: str, strategy_result_path: str
    ):
        """
        构建函数，实例化对象的时候传入的参数
        """
        self.url = "https://api.quantclass.cn/api/data"  # 获取数据的url
        self.api_key = api_key  # 个人中心生成的apikey
        self.hid = hid  # 个人中心的hid
        # 如果传入路径为空，默认保存在当前目录下
        if not all_data_path:
            all_data_path = "./数据更新"
        self.all_data_path = all_data_path  # 全量数据保存的路径
        # 如果传入路径为空，默认保存在当前目录下
        if not strategy_result_path:
            strategy_result_path = "./策略结果"
        self.strategy_result_path = strategy_result_path  # 最新策略结果保存路径

        # 定义请求头
        self.headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/100.0.4896.127 Safari/537.36",
            "content-type": "application/json",
            "api-key": self.api_key,
        }

        # 定义error的数据
        self.last_error_df = pd.DataFrame(columns=["product", "date_time", "error"])
        # 定义error的保存路径
        self.error_path = os.path.join(root_path, "error.csv")
        if os.path.exists(self.error_path):  # 判断error路径是否存在
            # 如果存在直接读取数据
            self.last_error_df = pd.read_csv(
                self.error_path, encoding="gbk"
            ).drop_duplicates(subset=["product", "date_time"])

    @retry(stop_max_attempt_number=8)
    def request_data(self, method, url, **kwargs) -> requests.models.Response:
        """
        请求数据
        :param method: 请求方法
        :param url: 请求的url
        :return:
        """
        if "params" in kwargs:
            kwargs["params"]["client"] = 1
        else:
            kwargs["params"] = {"client": 1}
        res = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            proxies=proxies,
            timeout=5,
            **kwargs,
        )
        if res.status_code == 200:
            return res
        elif res.status_code == 404:
            if "upyun" in url:
                # ===================  记录日志  ===================
                logger.warning(f"数据链接不存在{url}")
                # ===================  记录日志  ===================
                print("数据链接不存在", flush=True)
            else:
                # ===================  记录日志  ===================
                logger.warning(f"请求参数错误{url}")
                # ===================  记录日志  ===================
                print("参数错误", flush=True)
        elif res.status_code == 403:
            # ===================  记录日志  ===================
            logger.warning("无下载权限，请检查自己的下载次数与api-key")
            # ===================  记录日志  ===================
            print("无下载权限，请检查自己的下载次数与api-key", flush=True)
        elif res.status_code == 401:
            # ===================  记录日志  ===================
            logger.warning("超出当日下载次数")
            # ===================  记录日志  ===================
            print("超出当日下载次数", flush=True)
        elif res.status_code == 400:
            # ===================  记录日志  ===================
            logger.warning("下载时间超出限制")
            # ===================  记录日志  ===================
            print("下载时间超出限制", flush=True)
        elif res.status_code == 500:
            # ===================  记录日志  ===================
            logger.warning(f"服务器内部出现问题，请稍后尝试，{res.text}")
            # ===================  记录日志  ===================
            print("服务器内部出现问题，请稍后尝试", flush=True)
        else:
            # ===================  记录日志  ===================
            logger.warning("获取数据失败")
            # ===================  记录日志  ===================
            print("获取数据失败", flush=True)
        return res

    # region 文件交互
    @staticmethod
    def get_code_list_in_one_dir(path: str, end_with: str = "csv") -> list:
        """
        从指定文件夹下，导入所有数据
        :param path:
        :param end_with:
        :return:
        """
        symbol_list = []

        # 系统自带函数os.walk，用于遍历文件夹中的所有文件
        for root, dirs, files in os.walk(path):
            if files:  # 当files不为空的时候
                for f in files:
                    if f.endswith(end_with):
                        symbol_list.append(os.path.join(root, f))

        return sorted(symbol_list)

    def get_download_link(self, product, date_time):
        """
        根据指定的产品ID与时间构建下载链接
        :param product: 产品ID
        :param date_time: 数据时间
        :return:
        """
        return self.request_data(
            method="GET",
            url=self.url + f"/get-download-link/{product}/{date_time}?uuid={self.hid}",
        )

    def get_hist_download_link(self, full_data_name):
        """
        根据指定的产品ID与时间构建下载链接
        :param full_data_name: 产品ID
        :return:
        """
        return self.request_data(
            method="GET",
            url=self.url + f"/get-hist-download-link/{full_data_name}?uuid={self.hid}",
        )

    def get_latest_data_time(self, product):
        """
        根据产品ID构建数据最新的日期的链接
        :param product:
        :return:
        """
        res = self.request_data(
            method="GET",
            url=self.url + f"/fetch/{product}-daily/latest?uuid={self.hid}",
        ).text
        if "HTML" in res:
            logger.warning("获取最新数据日期出错，请检查配置")
            return []
        return res.split(",")

    def save_file(self, file_download_url, file_name, tmp_folder, output_path):
        """
        通过数据链接下载数据
        :param file_download_url: 下载连接
        :param file_name: 数据的文件名名
        :param tmp_folder: 放置增量的zip
        :param output_path: 解压缩之后的路径
        :return:
        """
        try:
            # -- 记录开始下载
            logger.info(f"开始下载文件: {file_name}")
            logger.info(f"下载 URL: {file_download_url}")

            # 请求数据
            res = self.request_data(method="GET", url=file_download_url, stream=True)
            if res.status_code != 200:
                logger.error(f"下载请求失败 - 状态码: {res.status_code}, 响应: {res.text}")
                return False

            # 构建数据保存路径
            file_path: str = f"{os.path.join(tmp_folder, file_name)}"
            logger.info(f"临时文件保存路径: {file_path}")

            # -- 检查目录是否存在
            if not os.path.exists(tmp_folder):
                logger.info(f"创建临时目录: {tmp_folder}")
                os.makedirs(tmp_folder)

            # 分块保存，避免某个文件太大导致内存溢出
            try:
                with open(file_path, mode="wb") as f:
                    total_size = 0
                    for chunk in res.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)
                logger.info(f"文件下载完成，大小: {total_size / 1024:.2f}KB")
            except Exception as e:
                logger.error(f"文件写入失败: {str(e)}\n{traceback.format_exc()}")
                return False

            # 判断文件类型进行不同的操作
            try:
                if file_name.endswith(".csv"):
                    logger.info(
                        f"复制 CSV 文件到输出目录: {output_path}"
                    )
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                    shutil.copy(file_path, f"{os.path.join(output_path, file_name)}")
                elif file_name.endswith(".zip"):
                    logger.info(
                        f"解压 ZIP 文件到输出目录: {output_path}"
                    )
                    compress_kit.zip_uncompress(file_path, output_path)

                # -- 验证文件是否成功保存
                output_file = os.path.join(output_path, file_name)
                if os.path.exists(output_file):
                    logger.info(f"文件成功保存到: {output_file}")
                else:
                    logger.warning(f"警告：输出文件未找到: {output_file}")

                return True

            except Exception as e:
                logger.error(f"文件处理失败: {str(e)}\n{traceback.format_exc()}")
                return False

        except Exception as e:
            logger.error(f"save_file 执行失败: {str(e)}\n{traceback.format_exc()}")
            return False

    # noinspection PyUnusedLocal
    @staticmethod
    def update_by_group(file_path, all_data_path, product, **kwargs):
        """
        遍历数据的每个group进行处理
        :param file_path:
        :param all_data_path:
        :param product:
        :return:
        """

        # 更新数据的主函数，封装为函数便于并行

        if not os.path.exists(root_path + "/data/temp/"):
            os.makedirs(root_path + "/data/temp/")
        if os.path.exists(root_path + f"/data/temp/{product}/"):
            shutil.rmtree(root_path + f"/data/temp/{product}/")

        os.makedirs(root_path + f"/data/temp/{product}/")

        get_data_path("temp", product)

        # 因为数据为一个csv，所以需要先读取逐行处理
        df = data_manager.read_file(file_path, product)
        data_info = data_manager.get_data_info(product)
        group = df.groupby(data_info["group"])

        # 开始并行或者串行读取所有增量数据
        is_update_success = True
        with ProcessPoolExecutor(max_workers=njobs) as executor:
            futures = [
                executor.submit(up1, df.loc[i].copy(), df.loc[i[0], data_info["group"]], all_data_path, product) for
                i in group.groups.values()
            ]

            for future in tqdm(as_completed(futures), total=len(futures), desc="合并增量", file=sys.stdout,
                               mininterval=2):
                try:
                    future.result()
                except Exception as e:
                    # 你可以加日志或打印错误
                    print(f"处理失败: {e}")
                    is_update_success = False

        return is_update_success

    def update_by_file(self, all_data_path, product, **kwargs):
        """
        遍历文件内的数据，每一个文件的处理
        :param all_data_path:
        :param product:
        :param kwargs:
        :return:
        """

        if not os.path.exists(root_path + "/data/temp/"):
            os.makedirs(root_path + "/data/temp/")
        if os.path.exists(root_path + f"/data/temp/{product}/"):
            shutil.rmtree(root_path + f"/data/temp/{product}/")
        os.makedirs(root_path + f"/data/temp/{product}/")
        # 获取所有增量数据
        save_path = kwargs["save_path"]
        file_path_list = self.get_code_list_in_one_dir(save_path)

        is_update_success = True
        with ProcessPoolExecutor(max_workers=njobs) as executor:
            futures = [
                executor.submit(up2, file_path, save_path, all_data_path, product)
                for file_path in file_path_list
            ]

            for future in tqdm(as_completed(futures), total=len(futures), desc="合并增量", file=sys.stdout,
                               mininterval=2):
                try:
                    future.result()
                except Exception as e:
                    # 你可以加日志或打印错误
                    print(f"处理失败: {e}")
                    is_update_success = False

        return is_update_success

    @staticmethod
    def on_api_error(product_name, error_resp):
        """
        当API遇到报错的时候都会调用
        """
        logger.warning(f"{product_name}获取下载链接失败，返回状态码：{error_resp.status_code}")
        logger.warning(error_resp.text)  # 存储状态

        print(
            f"{product_name}获取下载链接失败，返回状态码：{error_resp.status_code}",
            flush=True,
        )
        print(error_resp.text, flush=True)  # 输出详细的报错

        if error_resp.status_code == 401:
            try:
                err_path = get_folder_by_root(root_path, "data", "err")

                open(
                    os.path.join(
                        err_path, datetime.datetime.now().strftime("%Y-%m-%d") + ".txt"
                    ),
                    "w",
                ).close()
            except Exception as e:
                print(e, flush=True)

    def save_data_by_download_url(self, product_name, download_url, full_data_name):
        try:
            file_name = re.findall(f"%s.*?/(.*?)\?" % product_name, download_url)[0]

            # 添加日志记录文件名和路径信息
            logger.info(f"准备下载文件: {file_name}")

            tmp_folder = get_folder_by_root(self.all_data_path, "temp", product_name)
            save_path = get_folder_by_root(
                self.all_data_path, "xbx_temporary_data", product_name
            )

            logger.info(f"临时文件夹: {tmp_folder}")
            logger.info(f"保存路径: {save_path}")

            # 保存文件
            judge = self.save_file(
                file_download_url=download_url,
                file_name=file_name,
                tmp_folder=tmp_folder,
                output_path=save_path,
            )

            if not judge:
                logger.warning(f"{product_name}保存失败")
                print(f"{product_name}保存失败，请检查下载链接", flush=True)
                return False

            logger.info(f"保存成功 {download_url}")

            # 调用指定的代码对增量数据进行处理
            data_info = data_manager.get_data_info(full_data_name)
            all_data_path = get_folder_by_root(self.all_data_path, full_data_name)

            # 添加数据处理前的检查
            logger.info(f"开始处理数据，使用方法: {data_info['fun']}")

            try:
                is_update_success = getattr(self, data_info['fun'])(
                    all_data_path=all_data_path,
                    product=full_data_name,
                    file_path=os.path.join(save_path, file_name),
                    save_path=save_path,
                )
            except Exception as e:
                logger.error(f"数据处理失败: {str(e)}\n{traceback.format_exc()}")
                return False

            shutil.rmtree(save_path)
            self.delete_history_data(tmp_folder)
            return is_update_success

        except Exception as e:
            logger.error(f"save_data_by_download_url 执行失败: {str(e)}\n{traceback.format_exc()}")
            return False

    @staticmethod
    def delete_history_data(path):
        """
        只保留7天内的数据，如果数据日期超过七天就进行删除
        :param path:
        :return:
        """
        now_time = datetime.datetime.now()
        file_list = os.listdir(path)
        for file in file_list:
            file_time = pd.to_datetime(file.split(".")[0])
            if file_time < now_time - datetime.timedelta(days=7):
                os.remove(os.path.join(path, file))

    # noinspection PyUnusedLocal
    def update_single_data(
            self, product, date_time, full_data_name=None, **kwargs
    ) -> pd.DataFrame:
        """
        数据更新类主函数
        :param product: 产品ID
        :param date_time: 获取时间，如果是空自动获取最新的日期
        :param full_data_name: 是否并行
        :return:
        """
        ret_dict = {
            "product": [product],
            "date_time": [date_time],
            "error": [False],
        }  # 为了构造df

        # ===================  记录日志  ===================
        logger.info(f"开始下载{product}的{date_time}增量")
        # ===================  记录日志  ===================

        get_file_url_res = self.get_download_link(product=product, date_time=date_time)

        if get_file_url_res.status_code != 200:
            self.on_api_error(product, get_file_url_res)
            ret_dict["error"] = [True]
            return pd.DataFrame(ret_dict)

        # 数据没有什么问题
        file_download_url = get_file_url_res.text

        # ===================  记录日志  ===================
        logger.info(f"开始保存{product}数据")
        # ===================  记录日志  ===================

        # 有些数据太大了，不能直接并行，2024-05-30
        multi_process = product not in ("stock-xueqiu-hot-stock-daily",)

        is_success = self.save_data_by_download_url(product, file_download_url, full_data_name)

        if not is_success:
            logger.error(f"{product} 合并到本地数据出错 {file_download_url}")
            ret_dict["error"] = [True]
        # ===================  记录日志  ===================
        logger.ok(f"{product}({date_time})更新完成")
        # ===================  记录日志  ===================

        return pd.DataFrame(ret_dict)

    def get_strategy_result(self, strategy, period, select_count):
        """
        获取策略结果
        :param strategy: 策略名称
        :param period: 策略持仓时间，选股策略填'周'、'月'、'自然月'，事件策略填'x天'，与我们网页的参数贴合
        :param select_count:选股数量，若选择所有股票，填入0，与我们网页的参数贴合
        :return:
        """

        def up(_strategy, _strategy_df, _period, _select_count):
            period_dict = {"周": "week", "月": "month", "自然月": "natural_month"}
            if "天" in _period:
                period_type = _period.replace("天", "")
            else:
                period_type = period_dict[_period]
            to_path = f"{self.strategy_result_path}"
            if not os.path.exists(to_path):  # 判断文件夹是否存在
                os.makedirs(to_path)  # 不存在则创建
            to_file_path = os.path.join(
                to_path,
                f'{_strategy.replace("-", "_")}_{period_type}_{select_count}.csv',
            )

            if os.path.exists(to_file_path):
                old_df = pd.read_csv(to_file_path, encoding="gbk")
                _strategy_df = pd.concat([old_df, _strategy_df])
                _strategy_df.drop_duplicates(
                    subset=["交易日期", "股票代码"], inplace=True
                )
            _strategy_df.to_csv(to_file_path, encoding="gbk", index=False)

        url = self.url + "/stock-result/service/%s" % strategy

        params = {
            "uuid": self.hid,
            "period_type": period,
            "select_stock_max_num": select_count,
        }
        res = self.request_data("GET", url, params=params)
        if res.status_code != 200:
            return None
        res_json = res.json()
        code = res_json["code"]
        if code == 200:
            df = pd.DataFrame(res_json["result"]).rename(
                columns={"name": "股票名称", "symbol": "股票代码"}
            )
            df["交易日期"] = res_json["select_time"]
            df["选股排名"] = 1
            df = df[["交易日期", "股票代码", "股票名称", "选股排名"]]
            up(strategy, df, period, select_count)
            return res_json
        elif code == 1003:
            print(f"{strategy}策略无获取权限")
            logger.warning(f"{strategy}策略无获取权限")
        elif code == 1004:
            print(f"{strategy}策略不存在")
            logger.warning(f"{strategy}策略不存在")
        elif code == 1005:
            print(f"{strategy}策略无数据")
            logger.warning(f"{strategy}策略无数据")
        elif code == 1006:
            print(f"{strategy}策略获取数据参数错误")
            logger.warning(f"{strategy}策略获取数据参数错误")
        return None
