#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立计算因子程序：
    从输入CSV中读取历史数据（要求必须包含表头及至少字段：datetime, open, high, low, close, volume），
    计算因子后，生成新的CSV文件，原有字段与新计算因子字段均保留。
"""

import csv
import argparse
import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd

def calculate_factors(df):
    """
    计算因子：
        1. ma10: 基于收盘价的10期移动平均值
        2. momentum10: 当前收盘价与10期前的差值
    """
    # 确保 close 列为数值类型
    df["close"] = pd.to_numeric(df["close"], errors="coerce")

    # 计算ma
    for i in [4,16,24]:
        df[f"ma{i}"] = df["close"].rolling(window=i, min_periods=i).mean()


    return df

def process_file(input_file):
    output_file = input_file  # 直接覆盖原始CSV文件
    if not os.path.exists(input_file):
        print(f"输入文件 {input_file} 不存在")
        return
    df = pd.read_csv(input_file, encoding="utf-8")
    if df.empty:
        print(f"文件 {input_file} 内没有数据")
        return
    print(f"读取 {input_file} 的数据：{len(df)} 行, 正在计算因子...")
    df = calculate_factors(df)
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"{input_file} 的因子计算完成，结果已保存。")

def main():
    import pandas as pd
    # 直接配置需要处理的多个标的CSV文件路径
    file_list = [
        "datas/BTC_USDT_1h.csv",
        "datas/ETH_USDT_1h.csv",
        "datas/BNB_USDT_1h.csv",
        "datas/DOGE_USDT_1h.csv"
    ]
    for file_path in file_list:
        process_file(file_path)

if __name__ == '__main__':
    main() 