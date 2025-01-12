"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import gc
import os.path
import platform
import random
import shutil
import sys
import time
import traceback
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pandas as pd

from config import is_debug, error_webhook_url, utc_offset, data_center_path
from core.account_manager import init_system, get_usable_account_config_dict, get_all_hour_offset_list
from core.model.account_config import AccountConfig
from core.select_coin import calc_factors, select_coins, concat_select_results, process_select_results, \
    save_and_merge_select
from core.utils.commons import sleep_until_run_time, remedy_until_run_time, next_run_time
from core.utils.datatools import load_data, check_data_update_flag
from core.utils.dingding import send_wechat_work_msg
from core.utils.functions import save_select_coin, save_symbol_order, refresh_diff_time, del_insufficient_data
from core.utils.log_kit import logger, divider
from core.utils.misc_kit import mem_save_exe
from core.utils.path_kit import get_file_path, get_folder_path
from core.version import version_prompt

# ====================================================================================================
# ** 脚本运行前配置 **
# 主要是解决各种各样奇怪的问题们
# ====================================================================================================
# region 脚本运行前准备
warnings.filterwarnings('ignore')  # 过滤一下warnings，不要吓到老实人

# pandas相关的显示设置，基础课程都有介绍
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

# 解决pm2在win系统下的乱码问题
os_type = platform.system()
if os_type == 'Windows':  # win执行
    # noinspection PyUnresolvedReferences
    sys.stdout.reconfigure(encoding='utf-8')
    # 若上面sys.stdout = ... 这一行不行，可以试试下一行
    # import io
    # sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
# endregion


# ====================================================================================================
# ** 本脚本的全局变量 **
# ====================================================================================================
# 构建线程池，给统计脚本异步执行
stat_executor = ThreadPoolExecutor()  # 统计脚本真的会跑很久很久

python_exec = sys.executable  # 获取当前环境下的python解释器，也是给统计脚本用的


# ====================================================================================================
# ** 重要的函数区域 **
# 负责我们保温杯系统平顺执行的核心组件
# ====================================================================================================

def load_spot_swap_data(account_config: AccountConfig, run_time):
    all_symbol_list = set()
    for index in list(range(0, account_config.chunk_num, 1)):
        symbol_swap_candle_data = load_data('swap', run_time, account_config, index)
        all_candle_df_list = list(del_insufficient_data(symbol_swap_candle_data).values())
        all_symbol_list = all_symbol_list | set(symbol_swap_candle_data.keys())

        if account_config.use_spot:
            symbol_spot_candle_data = load_data('spot', run_time, account_config, index)
            all_candle_df_list = all_candle_df_list + list(del_insufficient_data(symbol_spot_candle_data).values())
            all_symbol_list = all_symbol_list | set(symbol_spot_candle_data.keys())
            del symbol_spot_candle_data

        pd.to_pickle(all_candle_df_list, get_file_path('data', 'runtime', f'all_candle_df_list_{index}.pkl'))

        del symbol_swap_candle_data
        del all_candle_df_list

    return tuple(all_symbol_list)


def run_statistics_async(run_time):
    divider('运行开始统计', '-')
    os.system(f'{python_exec} {get_file_path("core", "utils", "statistics.py")} {int(run_time.timestamp())}')
    divider('统计运行结束', '-')


# endregion

# ====================================================================================================
# ** 流程函数 **
# 主进程 -> run_loop -> run_by_account
# 调度逻辑在 run_loop 函数中
# 核心逻辑在 run_by_account 函数中
# 程序的主要逻辑会在这边写一下，可以试用异步的方案调用，充分释放执行过程中的内存
# ====================================================================================================
def run_by_account(account_name: str, acct_conf: AccountConfig, run_time: datetime):
    """
    针对当前账户，进行选币、下单操作
    :param account_name: 账户的别名
    :param acct_conf: config中账户配置的信息
    :param run_time:  运行时间
    :return:
    """
    divider(account_name, '-')  # 画一个华丽的分割线，账户启动
    # 记录一下时间戳
    r_time = time.time()

    # ====================================================================================================
    # 1. 准备工作
    # ====================================================================================================
    # 和交易所对一下表
    refresh_diff_time()

    # 清理一下运行过程中的缓存数据
    runtime_cache_path = get_folder_path('data', 'runtime')
    shutil.rmtree(runtime_cache_path, ignore_errors=True)

    # 根据配置的hour offset控制本轮是否下单
    if run_time.minute != acct_conf.hour_offset_minute:
        logger.warning(f'账号：{account_name}，当前不是需要下单的时间，跳过···')
        return

    # 判断当前策略持仓是否是日线
    # 如果是日线持仓则需要判断下单时间，小时级别持仓不需要判断下单时间
    if acct_conf.is_day_period and run_time.hour != utc_offset % 24:  # 只有当前小时是utc0点的时候，才会下单
        logger.warning(f'账号：{account_name}，当前不是需要下单的时间，跳过···')
        return

    # 更新一下交易所的行情数据，获取最新币种信息，放置在缓存中
    acct_conf.bn.fetch_market_info('swap')
    if acct_conf.use_spot:
        acct_conf.bn.fetch_market_info('spot')

    # 撤销所有币种挂单
    if is_debug:
        logger.debug(f'🐞 调试模式 - 跳过撤单')
    else:
        acct_conf.bn.cancel_all_swap_orders()  # 合约撤单
        acct_conf.bn.cancel_all_spot_orders()  # 现货撤单
    logger.ok('完成账户准备')

    # ====================================================================================================
    # 2. 读取实盘所需数据，并做简单的预处理
    # ====================================================================================================
    divider('读取数据', sep='-')
    s_time = time.time()
    mem_save_exe(load_spot_swap_data, acct_conf, run_time)
    logger.ok(f'完成读取数据中心数据，花费时间：{time.time() - s_time:.3f}秒')

    # ====================================================================================================
    # 3. 计算因子
    # ====================================================================================================
    divider('因子计算', sep='-')
    s_time = time.time()
    # 为了充分释放循环中的内存，我们会使用多进程来执行函数
    mem_save_exe(calc_factors, acct_conf, run_time)
    logger.ok(f'完成计算因子，花费时间：{time.time() - s_time:.3f}秒，累计时间：{(time.time() - r_time):.3f}秒')

    # ====================================================================================================
    # 4. 选币
    # - 注意：选完之后，每一个策略的选币结果会被保存到硬盘
    # ====================================================================================================
    divider('选币', sep='-')
    s_time = time.time()
    mem_save_exe(select_coins, acct_conf)


    # ====================================================================================================
    # 5. 整理选币结果
    # - 把每一个策略的选币结果聚合成一个df
    # ====================================================================================================
    # 为了充分释放循环中的内存，我们会使用多进程来执行函数
    mem_save_exe(concat_select_results, acct_conf)

    select_results = process_select_results(acct_conf)

    logger.debug(
        f'💾 选币结果df大小：{select_results.memory_usage(deep=True).sum() / 1024 / 1024:.4f} M\n'
        f'🚀 选币结果：\n{select_results}',
    )
    logger.ok(f'完成选币数据整理 & 选币，花费时间：{(time.time() - s_time):.2f}s')

    # ====================================================================================================
    # 6. 保存并合并本地选币文件
    # ====================================================================================================
    divider('开始计算目标仓位', sep='-')
    s_time = time.time()
    spot_position = acct_conf.spot_position
    swap_position = acct_conf.swap_position

    if select_results.empty and spot_position.empty and swap_position.empty:
        return
    select_results = save_and_merge_select(acct_conf, select_results, run_time)
    logger.ok(f'完成计算目标仓位，花费时间： {time.time() - s_time:.3f}秒')

    # ====================================================================================================
    # 7. 计算下单信息
    # ====================================================================================================
    divider('计算下单信息', sep='-')

    symbol_order = acct_conf.calc_order_amount(select_results)
    logger.info(f'下单信息：{symbol_order}\n')

    logger.ok(f'{account_name}策略计算总消耗时间：{time.time() - r_time:.2f}s，准备下单...')
    # 调试模式，打印下单信息之后即可退出程序
    if is_debug:
        return

    # ====================================================================================================
    # 8. 下单
    # ====================================================================================================
    acct_conf.proceed_spot_order(symbol_order, select_results, is_only_sell=True)
    acct_conf.proceed_swap_order(symbol_order)
    acct_conf.proceed_spot_order(symbol_order, select_results, is_only_sell=False)

    # ====================================================================================================
    # 9. 资金归集
    # ====================================================================================================
    acct_conf.bn.collect_asset()

    # ====================================================================================================
    # 10. 记录下单数据
    # ====================================================================================================
    # ===保存选币数据
    save_select_coin(select_results, run_time, account_name)

    # ===保存下单数据
    save_symbol_order(symbol_order, run_time, account_name)


def run_loop() -> datetime | None:
    """
    无限循环这个函数♾️
    :return: 成功执行的话，返回本次运行的时间，否则是None
    """
    divider('本次循环开始', '+')

    # ====================================================================================================
    # 0. 调试相关配置区域
    # ====================================================================================================
    if is_debug:  # 调试模式，不进行sleep，直接继续往后运行
        random_time = None
        from config import account_config
        all_names = list(account_config.keys())
        hour_offset_min = int(account_config[all_names[0]].get('hour_offset', '0m')[:-1])
        run_time = next_run_time('1h', 0) - timedelta(hours=1) + timedelta(minutes=hour_offset_min)
        if run_time > datetime.now():
            run_time -= timedelta(hours=1)
    else:
        random_time = random.randint(1 * 60, 2 * 60)  # 不建议使用负数。小时级别提前时间可以设置短一点
        run_time = sleep_until_run_time('5m', if_sleep=True, cheat_seconds=random_time)  # 每五分钟运行一次

    # ====================================================================================================
    # 1. 更新、检查账户信息
    # ====================================================================================================
    # 获取账户信息，并且剔除掉无效账户
    usable_account_config_dict = get_usable_account_config_dict()

    # ====================================================================================================
    # 2. 等待数据中心完成数据更新
    # ====================================================================================================
    logger.info(f'检查数据中心，{run_time}...')
    # 调试模式下，自动下载数据中心数据
    is_data_ready = check_data_update_flag(run_time)
    # 判断数据是否更新好了
    if not is_data_ready:  # 没有更新好，跳过当前下单
        logger.warning(f'数据中心数据未更新，跳过当前，{run_time}，[调试模式]：{is_debug}')
        return
    logger.ok(f'数据中心数据更新完成，准备选币下单，[调试模式]：{is_debug}')

    # ====================================================================================================
    # 3. 针对每一个配置好的可用账户，进行因子计算、选币、下单
    # ====================================================================================================
    """!!! 核心逻辑在这里 !!!"""
    for account_name, account_config in usable_account_config_dict.items():
        # 为了充分释放循环中的内存，我们会使用多进程来执行函数
        # 和 `run_by_account(account_name, account_config, run_time)` 等价
        # with ProcessPoolExecutor() as executor:
        mem_save_exe(run_by_account, account_name, account_config, run_time)
        gc.collect()  # 强制垃圾回收

    # 本次循环结束
    divider('本次循环结束，23秒后进入下一次循环', '+')
    if not is_debug:
        time.sleep(23)

    # ====================================================================================================
    # 4. 运行当前offset的监测脚本
    # ====================================================================================================
    is_send = False
    for account_config in usable_account_config_dict.values():
        # 当前offset，且是需要通知的时候
        if (run_time.minute == account_config.hour_offset_minute
                and run_time.hour % account_config.notify_freq == 0
                and account_config.notify_freq != 0):
            is_send = True
            break
    if is_send and not is_debug:
        time.sleep(random_time if random_time else 120)  # 提前随机多久，就休息多久，默认2分钟
        stat_executor.submit(run_statistics_async, run_time)  # 异步执行

    remedy_until_run_time(run_time)  # 休息休息～～～
    return run_time


def check_accounts():
    account_configs = init_system()
    # 针对所有的账户，进行运行前准备
    for name, account in account_configs.items():
        if not account.is_api_ok():
            logger.debug(f'🚨[{account.name}] 交易所API不可用，跳过自检')
            continue
        logger.debug('%s 检查杠杆、持仓模式、保证金模式...' % name)
        account.bn.reset_max_leverage()  # 检查杠杆
        account.bn.set_single_side_position()  # 检查并且设置持仓模式：单向持仓
        account.bn.set_multi_assets_margin()  # 检查联合保证金模式
        time.sleep(2)  # 多账户之间，停顿一下


if __name__ == '__main__':
    version_prompt()
    if is_debug:
        print('🟠' * 16, '[调试模式]', '🟠' * 16)
    else:
        print('🟢' * 16, '[正式模式]', '🟢' * 16)
    logger.info(f'系统初始化，稍等...')
    time.sleep(1)

    # ====================================================================================================
    # 运行前自检和准备
    # ====================================================================================================
    if is_debug:
        logger.debug('🐞 调试模式 - 跳过账户检查和准备')
    else:
        refresh_diff_time()  # 刷新与交易所的时差
        check_accounts()

    # 针对所有的账户，进行运行前准备
    if is_debug:
        logger.debug('🐞[DEBUG] - 跳过自检')
    else:
        refresh_diff_time()  # 刷新与交易所的时差
        check_accounts()
        print('✅自检完成')

    # ====================================================================================================
    # 实盘主程序，电不停我不停
    # ====================================================================================================
    while True:
        try:
            run_loop()
        except Exception as err:
            msg = '系统出错，10s之后重新运行，出错原因: ' + str(err)
            logger.error(msg)
            logger.debug(traceback.format_exc())
            send_wechat_work_msg(msg, error_webhook_url)
            time.sleep(11)  # 休息十一秒钟，再冲
        finally:
            if is_debug:
                logger.critical('DEBUG模式下，只跑一次')
                break
