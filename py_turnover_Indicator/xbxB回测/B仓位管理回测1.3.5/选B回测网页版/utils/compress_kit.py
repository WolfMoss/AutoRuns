# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
import tarfile
import zipfile

import rarfile
from py7zr import py7zr
from retrying import retry


@retry(stop_max_attempt_number=5)
def zip_uncompress(path, save_path):
    """
    解压zip
    :param path:
    :param save_path:
    :return:
    """
    f = zipfile.ZipFile(path)
    f.extractall(save_path)
    f.close()


@retry(stop_max_attempt_number=5)
def tar_uncompress(path, save_path):
    """
    解压tar格式
    :param path:
    :param save_path:
    :return:
    """
    f = tarfile.open(path)
    f.extractall(save_path)
    f.close()


@retry(stop_max_attempt_number=5)
def rar_uncompress(path, save_path):
    """
    :param path:
    :param save_path:
    :return:
    """
    # rar
    f = rarfile.RarFile(path)  # 待解压文件
    f.extractall(save_path)  # 解压指定文件路径
    f.close()
    pass


@retry(stop_max_attempt_number=5)
def uncompress(path, save_path):
    """
    解压7z
    :param path:
    :param save_path:
    :return:
    """
    # 7z
    f = py7zr.SevenZipFile(path, 'r')
    f.extractall(path=save_path)
    f.close()
    pass
