# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
import json
import os
import random
from datetime import datetime, timedelta

import pandas as pd

from utils.log_kit import logger
from utils.path_kit import get_file_path

DEFAULT_CACHE_PATH = get_file_path('data', 'up_data_info.json')


def request_data(method, url):
    import requests
    return requests.request(method, url)


class DataManager:
    def __init__(self, cache_path=DEFAULT_CACHE_PATH):
        self.cache_path = cache_path
        self.up_data_info = self.load_or_update_data()

    def load_or_update_data(self):
        if self._should_update():
            print("🌊 Updating data...", flush=True)
            data = request_data(
                "GET", "https://api.quantclass.cn/api/data/get-data-info"
            ).json()
            self._save_to_cache(data)
            return data
        else:
            return self._load_from_cache()

    def _should_update(self):
        """判断是否需要更新"""
        if not os.path.exists(self.cache_path):
            return True
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            last_update_str = cached.get("_last_update")
            if not last_update_str:
                return True
            last_update = datetime.fromisoformat(last_update_str)
            # 如果不是今天的，就更新
            return datetime.now() - last_update > timedelta(
                hours=random.uniform(23, 24),
                minutes=random.uniform(3, 59),
                seconds=random.uniform(0, 60)
            )
        except Exception as e:
            print(f"读取缓存失败: {e}")
            return True

    def _save_to_cache(self, data):
        data["_last_update"] = datetime.now().isoformat()
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_from_cache(self):
        with open(self.cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        cached.pop("_last_update", None)
        return cached

    def get_data_info(self, product):
        return self.up_data_info.get(product, {
            "duplicate_removal_column": ["交易日期"],
            "fun": "update_by_group",
            "group": "文件名",
            "keep": "last",
            "parse_dates": ["交易日期"]
        })

    def read_file(self, path, product):
        """
        读取数据返回一个df
        :param path:
        :param product:
        :return:
        """
        # 获取文件类型，即.后面所有的字段
        file_type = path.split(".")[-1]
        all_df = pd.DataFrame()
        data_info = self.get_data_info(product)
        # 判断文件是否存在
        if os.path.exists(path):
            if file_type == "csv":
                try:
                    all_df = pd.read_csv(
                        path,
                        encoding="gbk",
                        skiprows=1,
                        parse_dates=data_info["parse_dates"],
                    )
                except Exception as e:
                    # record_log(f"正常逻辑，不是报错：{e}, {path}", is_print="warning")
                    all_df = pd.read_csv(
                        path,
                        encoding="gbk",
                        parse_dates=data_info["parse_dates"],
                    )

            elif file_type == "pkl":
                all_df = pd.read_pickle(path)
            else:
                logger.warning("未匹配到读取代码")

        return all_df

    def concat_data(self, df_list, product):
        """
        把增量数据和全量数据合并
        :param df_list:
        :param product:
        :return:
        """
        # 把多个数据合并
        df = pd.concat(df_list, ignore_index=True)
        data_info = self.get_data_info(product)

        # 根据配置去重
        df.drop_duplicates(
            data_info["duplicate_removal_column"],
            inplace=True,
            keep=data_info["keep"],
        )
        # 排序
        df.sort_values(
            by=data_info["duplicate_removal_column"], inplace=True
        )
        # 重新设置index
        df.reset_index(inplace=True, drop=True)

        return df


if __name__ == "__main__":
    manager = DataManager()
    print(manager.load_or_update_data())
