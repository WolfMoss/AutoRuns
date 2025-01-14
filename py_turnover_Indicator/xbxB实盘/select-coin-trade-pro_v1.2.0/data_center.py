"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import traceback
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

import pandas as pd

from config import *
from core.utils.commons import sleep_until_run_time, remedy_until_run_time
from core.utils.dingding import send_wechat_work_msg
from core.utils.functions import create_finish_flag
from core.utils.log_kit import SimonsLogger, divider

warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

# 获取脚本文件的路径
script_path = os.path.abspath(__file__)

# 提取文件名
script_filename = os.path.basename(script_path).split('.')[0]

# 自定义logger
logger = SimonsLogger(script_filename).logger


def exec_one_job(job_file, method='download', param=''):
    wrong_signal = 0
    # =加载脚本
    cls = __import__('data_job.%s' % job_file, fromlist=('',))

    divider(job_file, sep='-')
    # =执行download方法，下载数据
    try:
        if param:  # 指定有参数的方法
            getattr(cls, method)(param)
        else:  # 指定没有参数的方法
            getattr(cls, method)()
    except KeyboardInterrupt:
        logger.info('退出')
        exit()
    except BaseException as e:
        _msg = f'{job_file}  {method} 任务执行错误：' + str(e)
        logger.error(_msg)
        logger.error(traceback.format_exc())
        send_wechat_work_msg(_msg, error_webhook_url)
        wrong_signal += 1

    return wrong_signal


def exec_jobs(job_files, method='download', param=''):
    """
    执行所有job脚本中指定的函数
    :param job_files: 脚本名
    :param method: 方法名
    :param param: 方法参数
    """
    wrong_signal = 0

    # ===遍历job下所有脚本
    for job_file in job_files:
        if isinstance(job_file, str):
            wrong_signal += exec_one_job(job_file, method, param)
        else:
            with ProcessPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(exec_one_job, job, method, param) for job in job_file]

                for future in as_completed(futures):
                    wrong_signal += future.result()

    return wrong_signal


def run_loop(run_time=None):
    # ====================================================================================================
    # 0. 调试相关配置区域
    # ====================================================================================================
    if is_debug:  # 调试模式，不进行sleep，直接继续往后运行
        run_time = sleep_until_run_time('5m', if_sleep=True, cheat_seconds=0)  # 每小时运行
        # 以下代码可以测试的时候使用(UTC0点 日K才走完，国内时间对应是 早上8点)
        # run_time = datetime.strptime('2024-07-29 10:05:00', "%Y-%m-%d %H:%M:%S")
        # 测试当前小时的代码
        #run_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    else:
        random_time = 0
        run_time = sleep_until_run_time('5m', if_sleep=True, cheat_seconds=random_time)  # 每小时运行

    # =====执行job目录下脚本
    # 按照填写的顺序执行
    job_files = ['funding_fee', ['data_api', 'kline'], 'coin_cap']
    # 执行所有job脚本中的 download 方法
    signal = exec_jobs(job_files, method='download', param=run_time)

    # 定期清理文件中重复数据(目前的配置是：每小时0分钟，分散清理重复的数据)
    if run_time.minute == 0:
        # ===执行所有job脚本中的 clean_data 方法
        exec_jobs(job_files, method='clean_data')

    # 生成指数完成标识文件。如果标记文件过多，会删除7天之前的数据
    create_finish_flag(flag_path, run_time, signal)

    # =====清理数据
    del job_files

    # 本次循环结束
    divider('本次循环结束，%d秒后进入下一次循环' % 23)
    print()
    time.sleep(23)

    return run_time


if __name__ == '__main__':
    if is_debug:
        print('🟠' * 16, '[调试模式]', '🟠' * 16)
    else:
        print('🟢' * 16, '[正式模式]', '🟢' * 16)
    while True:
        try:
            last_run_time = run_loop()

            # 如果返回运行时间，说明本轮执行成功
            if last_run_time:
                # =====补偿当前时间与run_time之间的差值
                remedy_until_run_time(last_run_time)

        except Exception as err:
            msg = '系统出错，10s之后重新运行，出错原因: ' + str(err)
            logger.error(msg)
            logger.debug(traceback.format_exc())
            send_wechat_work_msg(msg, error_webhook_url)
            time.sleep(10)  # 休息十秒钟，再冲
