"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import os

# 获取脚本文件的路径
script_path = os.path.abspath(__file__)

# 提取文件名
script_filename = os.path.basename(script_path).split('.')[0]


def download(run_time):
    """
    根据获取数据的情况，自行编写下载数据函数
    :param run_time:    运行时间
    """
    print(f'执行{script_filename}脚本 download 开始')
    print(f'执行{script_filename}脚本 download 完成')


def clean_data():
    """
    根据获取数据的情况，自行编写清理冗余数据函数
    """
    print(f'执行{script_filename}脚本 clear_duplicates 开始')
    print(f'执行{script_filename}脚本 clear_duplicates 完成')
