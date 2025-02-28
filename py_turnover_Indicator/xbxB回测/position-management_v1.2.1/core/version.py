"""
邢不行｜策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""

from pandas import show_versions

from core.utils.log_kit import divider, logger

sys_version = '1.2.2'
sys_name = 'position-management'
build_version = f'v{sys_version}.20250228'


def version_prompt():
    show_versions()
    divider('[SYSTEM INFO]', with_timestamp=False)
    logger.debug(f'# VERSION:\t{sys_name}({sys_version})')
    logger.debug(f'# BUILD:\t{build_version}')
    divider('[SYSTEM INFO]', with_timestamp=False)
