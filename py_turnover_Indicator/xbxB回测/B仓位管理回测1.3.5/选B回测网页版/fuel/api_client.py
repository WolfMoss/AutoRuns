# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
from fuel.BaseDataApi import BaseDataApi
from config import api_key, uuid, fuel_data_path

client = BaseDataApi(api_key=api_key, hid=uuid, all_data_path=fuel_data_path, strategy_result_path=fuel_data_path)
