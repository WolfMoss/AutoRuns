"""
邢不行｜策略分享会
仓位管理实盘框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import html
import json
import os.path
import pickle
import random
import re
import time
import traceback
import warnings
from datetime import datetime, timedelta

import pandas as pd
from DrissionPage import WebPage, ChromiumOptions

from config import proxy, error_webhook_url
from core.account_manager import init_system, load_multi_accounts
from core.mef_manager import init_mef_system
from core.model.account_type import AccountType
from core.trade import split_order_twap
from core.utils.commons import retry_wrapper
from core.utils.dingding import send_wechat_work_msg
from core.utils.functions import ignore_error
from core.utils.path_kit import get_folder_path, get_file_path

warnings.filterwarnings('ignore')

# 构建浏览器的配置
options = ChromiumOptions()
options.headless(True)
options.set_argument('--no-sandbox')
if proxy:
    options.set_proxy(proxy['http' if 'http' in proxy else 'https'])
# 公告详细的baseurl
baseurl = 'https://www.binance.com/en/support/announcement'
data_path = get_folder_path('data')
order_path = get_folder_path('data', 'order', as_path_type=True)
# 保存下架币种信息的位置
de_list_path = os.path.join(data_path, 'delist.json')
# 监测下架公告时间间隔。默认：60s监测一次，设置太短会被BN封禁
monitor_time = 60
# 获取数据的公共交易所对象
first_account_exchange = init_system(str(load_multi_accounts()[0])).bn.exchange


def get_delist_page(page):
    """
    从公告总页面获取下架币对应的页面链接
    """
    # 访问目标网址
    page.get(baseurl)
    page.wait.ele_displayed('__APP')
    a = page.ele('xpath://a[descendant::h3[contains(text(), "Delisting")]]')
    href_value = a.attr('href')
    if href_value:
        print('delisting page info: ', href_value)
    else:
        raise Exception(f'从{baseurl},未找到delisting匹配的 href 值，币安可能修改了页面文件')
    return href_value


def get_delist_list(page, url):
    time.sleep(random.randint(5, 10))
    page.get(url)
    page.wait.ele_displayed('#__APP_DATA')
    ele = page.ele('#__APP_DATA')
    # 转成json格式
    json_obj = json.loads(ele.raw_text)
    # 解析需要的内容
    # arc_list = json_obj['appState']['loader']['dataByRouteId']['d34e']['catalogDetail']['articles']
    arc_list = []
    routeId = json_obj['appState']['loader']['dataByRouteId']
    for key in routeId:
        if 'catalogDetail' in routeId[key]:
            arc_list.extend(routeId[key]['catalogDetail']['articles'])
            break
    return arc_list


def get_page_info():
    de_list = []
    # ===读取本地下架数据
    try:
        with open(de_list_path, 'r') as file:
            de_list_dict = json.load(file)
            if 'last_id_list' not in de_list_dict:
                de_list_dict['last_id_list'] = []
                del de_list_dict['last_id']
    except Exception as e:
        ignore_error(e)
        de_list_dict = {'last_id_list': [], 'list': []}

    try:
        # 初始化 SessionPage 对象
        page = WebPage(timeout=50, chromium_options=options)
        url = get_delist_page(page)  # 获取下架公告url
        data = get_delist_list(page, url)  # 获取下架公告列表

        id_list = []
        # 遍历最新的公告数据
        for item in data:
            # 判断公告id是否超过最新的id
            if item['id'] in de_list_dict['last_id_list']:
                continue

            # 判断是否是逐仓保证金交易，直接跳过
            if 'Isolated Margin' in item['title']:
                continue
            # 杠杆代币
            if 'Leveraged Tokens' in item['title']:
                continue
            # 质押代币
            if 'Staking' in item['title']:
                continue

            # 标题含有 delist 可以直接解析币种信息
            if 'delist' in item['title'].lower():
                # 匹配正则规则
                matches = re.findall(r'\b[A-Z]+\b', item['title'].replace('/', '').replace('USDⓈ-M', ''))
                print('标题：', matches)
                de_list.extend(matches)
            else:  # 标题不含有 delist，需要通过公告内容解析币种信息
                # 移除非字母数字字符，将空格替换为连字符，并转为小写
                clean_title = re.sub(r'\W+', ' ', item['title']).strip().replace(' ', '-').lower()
                # 构建详情地址
                url = f"{baseurl}/{clean_title}-{item['code']}"
                try:
                    page.get(url)
                    page.wait.ele_displayed('#__APP_DATA')
                    ele = page.ele('#__APP_DATA')
                    # 转成json格式
                    json_obj = json.loads(ele.raw_text)
                    # 解析需要的内容
                    # body = json_obj['appState']['loader']['dataByRouteId']['d969']['articleDetail']['body']
                    routeId = json_obj['appState']['loader']['dataByRouteId']
                    for key in routeId:
                        if 'articleDetail' in routeId[key]:
                            body = routeId[key]['articleDetail']['body']
                            break
                    else:
                        continue
                except Exception as e:
                    print(f'当前url内容无法解析：{e}', url)
                    continue
                # 匹配正则规则
                matches = re.findall(r'\b[A-Z]+\b', body.replace('/', '').replace('USDⓈ-M', ''))
                print('文章解析：', matches)
                de_list.extend(matches)
            time.sleep(random.randint(1, 3))   # 休息一下，被封怕了
            id_list.append(item['id'])
        # 更新最新的下架公告id
        id_list = list(set(id_list) - set(de_list_dict['last_id_list']))
        de_list_dict['last_id_list'].extend(id_list)

        # 退出浏览器
        page.quit(timeout=10)
    except Exception as e:
        print(e)
        print('页面接口解析出错', traceback.format_exc())

    return de_list, de_list_dict


def get_spot_api_info():
    api_de_list = []
    try:
        time.sleep(random.randint(5, 10))  # 为了缓解api权重限制，随机休息5-10s
        res = retry_wrapper(first_account_exchange.sapi_get_spot_delist_schedule, func_name='获取现货下架数据')
        if res is not None and len(res) > 0:
            [api_de_list.extend(_['symbols']) for _ in res]
            print('请求现货下架接口返回：', api_de_list)
    except Exception as e:
        print(traceback.format_exc())
        print('api 获取现货下架数据出错')

    return api_de_list


def get_swap_api_info():
    api_de_list = []
    try:
        time.sleep(random.randint(5, 10))  # 为了缓解api权重限制，随机休息5-10s
        exchange_info = retry_wrapper(first_account_exchange.fapipublic_get_exchangeinfo, func_name='获取BN合约币种规则数据')
        for info in exchange_info['symbols']:
            symbol = info['symbol']  # 交易对信息

            # 过滤掉非报价币对, 非交易币对, 非永续合约
            if info['quoteAsset'] != 'USDT' or info['status'] != 'TRADING' or info['contractType'] != 'PERPETUAL':
                continue

            # 过滤盘前交易币种
            if 'permissionSets' in info and len(info['permissionSets']) > 1 and 'PRE_MARKET' in info['permissionSets'][1]:
                continue

            if datetime.fromtimestamp(int(info['deliveryDate'][:-3])) - timedelta(days=30) < datetime.now():
                api_de_list.append(symbol)

        print('请求合约接口返回：', api_de_list)
    except Exception as e:
        print(traceback.format_exc())
        print('api 获取现货下架数据出错')

    return api_de_list


def timed_task():
    while True:
        try:
            # 获取网页接口数据
            page_de_list, de_list_dict = get_page_info()

            # 获取现货api接口数据
            spot_api_de_list = get_spot_api_info()

            # 获取合约api接口数据
            swap_api_de_list = get_swap_api_info()

            # 整合两个接口的数据
            de_list = page_de_list + spot_api_de_list + swap_api_de_list

            # 数据整理 (这里直接一刀切，有些币种是现货，有些是汇率对，都直接追加USDT，币种名称显示比较奇怪)
            # 这里追加不会有太大问题，我们主要使用USDT交易，所以这是没有问题的
            de_list = [_.replace('USDT', '') + 'USDT' for _ in de_list]  # 去掉USDT，再追加USDT结尾。防止一些公告中币种添加USDT后缀
            # de_list = [_.replace('BUSDUSDT', 'BUSD') for _ in de_list]  # 去掉BUSDUSDT，改成BUSD。24年BN将不支持BUSD

            # 筛选出新增的下架币种
            new_data = list(set(de_list) - set(de_list_dict['list']))

            # ===发现新公告币种下架，执行平仓下架币种功能
            if len(new_data) > 0:
                print(f'下架币种：{new_data}')
                # 卖掉持仓
                try:
                    time.sleep(random.randint(10, 60))  # 随机sleep 10-60s，避免大家一起下单，滑点太大
                    clear_delist_pos(new_data)
                except BaseException as e:
                    print(traceback.format_exc())
                    print('清仓失败', e)

                # 发送下架通知(首次启动会load很多数据，建议首次之后手动打开)
                # send_wechat_work_msg(f'下架币种：{new_data}', error_webhook_url)

                # ===更新数据
                # 追加新下架的币种
                de_list_dict['list'].extend(new_data)

                # ===保存下架数据
                with open(de_list_path, 'w') as file:
                    json.dump(de_list_dict, file)
            else:
                print('没有新公告出现')
        except Exception as e:
            traceback.print_exc()
            print(f'币安下架币种接口报错：{e}')

        print('=' * 20, f'当前循环结束，sleep {monitor_time}s 准备进入下一轮循环', '=' * 20)
        time.sleep(monitor_time)


def clear_delist_pos(delist):
    for account_profile_file in load_multi_accounts():
        account = init_system(account_profile_file.stem)
        # =====获取账户信息,并且筛选含有现货的账户
        me_conf = init_mef_system(account_profile_file.stem)
        account.use_spot = me_conf.use_spot
        account.update_account_info()
        account_config_dict = {
            account.name: account
        }

        # 判断是否有可用账户
        if not len(account_config_dict.keys()):  # 如果update_account_info数据为空，表示更新账户信息失败
            print(f'monitor脚本 所有账户更新信息失败，{monitor_time}后重试······')
            time.sleep(monitor_time)
            return

        # =====遍历所有账号监测
        for account_name, account_config in account_config_dict.items():
            # ===前置检查
            if account_config.account_type == AccountType.PORTFOLIO_MARGIN and not account_config.use_spot:
                print(f'{account_name} 账户类型为 【统一账户】，策略模式为【合约模式】，不需要进行监控')
                continue

            # ===获取账号的配置
            spot_position = account_config.spot_position
            swap_position = account_config.swap_position
            max_one_order_amount = account_config.max_one_order_amount
            twap_interval = account_config.twap_interval

            # ===判断当前是否有仓位
            if spot_position.empty and swap_position.empty:  # 当前没有仓位直接跳过
                print('当前没有任何【持仓】，跳过后续操作')
                continue

            # ===计算下单信息
            if not swap_position.empty:
                swap_position = swap_position[swap_position.index.isin(delist)]
                swap_position['实际下单量'] = swap_position['当前持仓量'] * -1  # 直接通过当前持仓进行计算，方向要去反
                swap_position['实际下单资金'] = swap_position['实际下单量'] * swap_position['当前标记价格']  # 计算实际下单资金，用于后续拆单
                swap_position['交易模式'] = '清仓'  # 设置交易模式
                swap_position = swap_position[abs(swap_position['实际下单量']) > 0]  # 保留实际下单量 > 0 的数据
                swap_position.reset_index(inplace=True)
                swap_position['symbol_type'] = 'swap'
                print('合约下单信息：\n', swap_position)

            # 获取一下现货价格
            if not spot_position.empty:
                spot_position['最新价格'] = None
                if not spot_position.empty:
                    spot_price = account_config.bn.get_spot_ticker_price_series()
                    spot_position['最新价格'] = spot_position.apply(lambda res_row: spot_price[res_row['symbol']], axis=1)

                spot_position = spot_position[spot_position['symbol'].isin(delist)]
                spot_position['实际下单量'] = spot_position['当前持仓量'] * -1  # 直接通过当前持仓进行计算，方向要去反
                spot_position['实际下单资金'] = spot_position['实际下单量'] * spot_position['最新价格']  # 计算实际下单资金，用于后续拆单
                spot_position['交易模式'] = '清仓'  # 设置交易模式
                spot_position = spot_position[abs(spot_position['实际下单量']) > 0]  # 保留实际下单量 > 0 的数据
                spot_position.reset_index(inplace=True)
                swap_position['symbol_type'] = 'spot'
                print('现货下单信息：\n', spot_position)

            # 判断是否需要有下单信息
            if swap_position.empty and spot_position.empty:
                continue

            # ===合约处理
            if not swap_position.empty:
                # ===使用twap算法拆分订单
                swap_orders_df_list = split_order_twap(swap_position, max_one_order_amount)
                # ===遍历下单
                for i in range(len(swap_orders_df_list)):
                    # 获取币种的最新价格
                    account_config.bn.place_swap_orders_bulk(swap_orders_df_list[i], slip_rate=0.03)

                    # 下单间隔
                    print(f'等待 {twap_interval}s 后继续下单')
                    time.sleep(twap_interval)

            # ===现货处理
            if not spot_position.empty:
                # ===使用twap算法拆分订单
                spot_orders_df_list = split_order_twap(spot_position, max_one_order_amount)
                # ===现货遍历下单
                for i in range(len(spot_orders_df_list)):
                    account_config.bn.place_spot_orders_bulk(spot_orders_df_list[i], slip_rate=0.03)

                    # 下单间隔
                    print(f'等待 {twap_interval}s 后继续下单')
                    time.sleep(twap_interval)

                account_config.update_account_info(is_only_spot_account=True)
                # ===将现货中的U转入的合约账号
                account_config.bn.collect_asset()

            # 构建仓位存储选币目录
            file_path = get_folder_path(data_path, f'{account_config.name}')
            file_path = get_file_path(file_path, 'shift_select_coin_result.pkl')
            # 判断是否需要更新本地选币文件
            if os.path.exists(file_path):  # 文件存在，说明需要更新最近的选币文件
                # 读取本地存储的文件
                with open(file_path, 'rb') as f:
                    local_select_result = pickle.load(f)
                # 更新选币
                for factor in list(local_select_result.keys()):  # 因子
                    for key in list(local_select_result[factor].keys()):  # offset
                        _select_coin = local_select_result[factor][key]['select_coin']
                        local_select_result[factor][key]['select_coin'] = _select_coin[~_select_coin['symbol'].isin(delist)]

                # 保存仓位对应策略选币文件
                with open(file_path, 'wb') as f:
                    pickle.dump(local_select_result, f)

            # 判断非reb的order文件是否存在，如果存在则剔除拉黑的币种
            order_file = order_path / f'{account_name}_order.csv'
            if order_file.exists():
                local_order_df = pd.read_csv(order_file, encoding='gbk', parse_dates=['candle_begin_time', '换仓时间'])
                local_order_df = local_order_df[~local_order_df['symbol'].isin(delist)]
                local_order_df.reset_index(inplace=True, drop=True)
                local_order_df.to_csv(order_file, encoding='gbk', index=False)

            # ===发送信息推送
            send_wechat_work_msg(f'成功清仓下架币种，已将USDT转入U本位合约账户补充保证金', account_config.wechat_webhook_url)

            # ===休息一会儿
            time.sleep(2)


if __name__ == '__main__':
    try:
        timed_task()
    except KeyboardInterrupt:
        print('退出')
        exit()
    except BaseException as err:
        msg = '系统出错，10s之后重新运行，出错原因: ' + str(err)
        print(msg)
        send_wechat_work_msg(msg, error_webhook_url)
        traceback.print_exc()
