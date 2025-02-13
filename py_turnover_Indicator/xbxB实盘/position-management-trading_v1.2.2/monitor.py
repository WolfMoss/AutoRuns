"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import time
import traceback
import warnings

import pandas as pd

from config import error_webhook_url
from core.account_manager import init_system, load_multi_accounts
from core.mef_manager import init_mef_system
from core.model.account_config import AccountConfig
from core.model.account_type import AccountType
from core.trade import split_order_twap
from core.utils.dingding import send_wechat_work_msg
from core.utils.path_kit import get_folder_path

warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)

# ===监控间隔(单位: 秒)
monitor_time = 60  # 60：表示每60秒监测一次。注意：检测过于频繁会消耗请求权重
# ===监控合约账户保证金率阈值
stop_equity_pnl = 0.5
# ===监控平仓比例。0.1: 每次达到保证金率阈值，现货和合约的平仓10%，并将剩余的U转入U本位合约账户
stop_rate = 0.1


def run():
    while True:
        for account_profile_file in load_multi_accounts():
            # =====获取账户信息,并且筛选含有现货的账户
            acct_cfg: AccountConfig = init_system(account_profile_file.stem)
            me_conf = init_mef_system(account_profile_file.stem)
            acct_cfg.use_spot = me_conf.use_spot
            acct_cfg.update_account_info()

            for account_info in [acct_cfg]:
                account_name = account_info.name
                # ===前置检查
                if account_info.account_type == AccountType.PORTFOLIO_MARGIN:
                    print(f'{account_name} 账户类型为 【统一账户】不需要进行监控')
                    continue

                # ===获取账号的配置
                spot_position = account_info.spot_position
                swap_position = account_info.swap_position
                swap_equity = account_info.swap_equity
                max_one_order_amount = account_info.max_one_order_amount
                twap_interval = account_info.twap_interval

                # ===判断当前是否有仓位
                if spot_position.empty or swap_position.empty:  # 当前没有仓位直接跳过
                    print('当前没有【现货持仓】 或 【合约持仓】')
                    continue

                # ===计算账户保证金率
                total_equity = swap_equity  # 计算当前账户总净值（含未实现盈亏）
                pos_equity = (swap_position['当前标记价格'] * swap_position['当前持仓量']).abs().sum()  # 计算合约账户持仓价值
                margin_rate = total_equity / pos_equity  # 计算当前账户保证金率
                print(f'当前账户资金: {total_equity}，合约账户持仓价值abs: {pos_equity}，账户保证金率: {margin_rate}')

                # 判断当前账户的保证金率是否达到阈值
                if margin_rate > stop_equity_pnl:
                    print(
                        f'账户保证金率 {margin_rate} 大于 监控阈值 {stop_equity_pnl} , sleep {monitor_time}s 后，继续监控······')
                    continue

                # ===计算下单信息
                swap_position['实际下单量'] = swap_position['当前持仓量'] * stop_rate * -1  # 直接通过当前持仓进行计算，方向要去反
                swap_position['实际下单资金'] = swap_position['实际下单量'] * swap_position[
                    '当前标记价格']  # 计算实际下单资金，用于后续拆单
                swap_position['交易模式'] = '减仓'  # 设置交易模式
                swap_position = swap_position[abs(swap_position['实际下单量']) > 0]  # 保留实际下单量 > 0 的数据
                swap_position.reset_index(inplace=True)
                print('合约下单信息：\n', swap_position)

                # 获取一下现货价格
                spot_position['最新价格'] = None
                if not spot_position.empty:
                    spot_price = account_info.bn.get_spot_ticker_price_series()
                    spot_position['最新价格'] = spot_position.apply(lambda res_row: spot_price[res_row['symbol']], axis=1)

                spot_position['实际下单量'] = spot_position['当前持仓量'] * stop_rate * -1  # 直接通过当前持仓进行计算，方向要去反
                spot_position['实际下单资金'] = spot_position['实际下单量'] * spot_position['最新价格']  # 计算实际下单资金，用于后续拆单
                spot_position['交易模式'] = '减仓'  # 设置交易模式
                spot_position = spot_position[abs(spot_position['实际下单量']) > 0]  # 保留实际下单量 > 0 的数据
                spot_position.reset_index(inplace=True)
                print('现货下单信息：\n', spot_position)

                # 判断是否需要有下单信息
                if swap_position.empty or spot_position.empty:
                    continue

                # 记录一下是否会下单
                is_order = spot_position['实际下单资金'].abs().max() > 10 or swap_position['实际下单资金'].abs().max() > 5

                # ===使用twap算法拆分订单
                swap_orders_df_list = split_order_twap(swap_position, max_one_order_amount)
                spot_orders_df_list = split_order_twap(spot_position, max_one_order_amount)

                # ===遍历下单
                for i in range(len(swap_orders_df_list)):
                    account_info.bn.place_swap_orders_bulk(swap_orders_df_list[i])

                    # 下单间隔
                    print(f'等待 {twap_interval}s 后继续下单')
                    time.sleep(twap_interval)

                # ===现货遍历下单
                for i in range(len(spot_orders_df_list)):
                    account_info.bn.place_spot_orders_bulk(spot_orders_df_list[i])

                    # 下单间隔
                    print(f'等待 {twap_interval}s 后继续下单')
                    time.sleep(twap_interval)

                account_info.update_account_info(is_only_spot_account=True)
                # ===将现货中的U转入的合约账号
                account_info.bn.collect_asset()

                # ===发送信息推送
                if is_order:
                    send_wechat_work_msg(f'成功减仓完毕，已将现货的USDT转入U本位合约账户补充保证金', account_info.wechat_webhook_url)

                # ===休息一会儿
                time.sleep(2)

        # 本次循环结束
        print('-' * 20, '本次监测结束，%f秒后进入下一次监测' % monitor_time, '-' * 20)
        print('\n')
        time.sleep(monitor_time)


if __name__ == '__main__':
    # =====检查监控配置
    # ===检查平仓比例配置
    if stop_rate > 1:
        print('平仓比例配置错误，不支持 1 以上的参数配置')
        exit()
    # ===检查合约账户浮动盈亏阈值配置
    if stop_equity_pnl > 1:
        print('合约账户保证金率阈值配置错误，不支持 1 以上的参数配置')
        exit()

    # ===主程序入口
    while True:
        try:
            run()
        except KeyboardInterrupt:  # 手动终止程序的错误，直接打印'退出'，并退出程序
            print('退出')
            exit()
        except Exception as err:
            msg = '仓位管理monitor脚本出错，10s之后重新运行，出错原因: ' + str(err)
            print(msg)
            print(traceback.format_exc())
            send_wechat_work_msg(msg, error_webhook_url)
            time.sleep(12)
