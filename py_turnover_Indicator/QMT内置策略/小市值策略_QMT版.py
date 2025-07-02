#encoding:gbk
"""
QMT小市值策略 - 使用官方API优化版
执行频率: 周频, 每周一14:00执行
选股: A股市值最小的10只股票, 排除ST/科创板/北交所, 股价<=20元
交易: 等权重配置, 每只股票占总市值1/10
使用官方API: get_full_tick批量获取价格, get_instrument_detail获取市值
"""

import datetime

class a():
	pass
A = a() #创建空的类的实例 用来保存委托状态 

# 策略参数
MAX_POSITIONS = 10      # 最大持仓数量
MAX_PRICE = 20         # 最高股价限制
POSITION_RATIO = 0.1   # 每只股票仓位比例

def log_info(msg):
    """日志输出"""
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("[{}] {}".format(current_time, msg))

def is_execution_time():
    """判断是否为执行时间(周一14:00)"""
    now = datetime.datetime.now()
    return now.weekday() == 0 and now.hour == 14 and now.minute == 0

def format_stock_code(stock_code):
    """格式化股票代码为QMT格式"""
    if stock_code.startswith('0') or stock_code.startswith('3'):
        return "{}.SZ".format(stock_code)
    elif stock_code.startswith('6'):
        return "{}.SH".format(stock_code)
    else:
        return stock_code

def get_filtered_stocks():
    """获取过滤后的股票列表"""
    log_info("开始获取股票列表...")
    
    try:
        # 获取A股股票列表
        all_stocks = list(get_stock_list_in_sector('沪深A股'))
        log_info("获取到{}只股票".format(len(all_stocks)))
        
        filtered_stocks = []
        for stock in all_stocks:
            
            # 排除科创板(688开头)
            if stock.startswith('688'):
                continue
            
            # 排除北交所(43、83开头)
            if stock.startswith('43') or stock.startswith('83'):
                continue
            
            # 排除新三板(400、420开头)
            if stock.startswith('400') or stock.startswith('420'):
                continue
            
            # 获取股票基本信息
            try:
                instrument = A.ContextInfo.get_instrumentdetail(stock)
                
                if instrument:
                    stock_name = instrument.get('InstrumentName', '')
                    if 'ST' not in stock_name:
                        filtered_stocks.append(stock)
            except Exception as e:
                log_info("获取股票详细信息失败: {}".format(str(e)))
        
        log_info("过滤后剩余{}只股票".format(len(filtered_stocks)))
        return filtered_stocks
    
    except Exception as e:
        log_info("获取股票列表失败: {}".format(str(e)))
        return []

def get_stock_data_batch(stock_list):
    """使用官方API批量获取股票数据"""
    try:
        log_info("开始批量获取股票数据...")
        
        # 格式化股票代码列表
        #formatted_stocks = [format_stock_code(stock) for stock in stock_list]
        #log_info("格式化后的股票代码示例: {}".format(formatted_stocks[:5]))
        log_info(stock_list)
        # 批量获取实时价格数据
        ticks = A.ContextInfo.get_full_tick(stock_list)
        log_info("获取到{}只股票的实时数据".format(len(ticks)))
        
        stock_data = []
        processed_count = 0
        
        for i, original_code in enumerate(stock_list):
            try:
                formatted_code = stock_list[i]
                
                # 获取价格数据
                if formatted_code not in ticks:
                    continue
                    
                tick_data = ticks[formatted_code]
                price = tick_data.get("lastPrice", 0)
                
                # 价格过滤
                if price <= 0 or price > MAX_PRICE:
                    continue
                
                # 获取股票详细信息(总股本)
                instrument_detail = A.ContextInfo.get_instrumentdetail(formatted_code)
                if not instrument_detail:
                    continue
                    
                total_volume = instrument_detail.get('TotalVolumn', 0)
                if total_volume <= 0:
                    continue
                
                # 计算总市值
                market_cap = price * total_volume
                
                stock_data.append({
                    'code': original_code,
                    'formatted_code': formatted_code,
                    'price': price,
                    'total_volume': total_volume,
                    'market_cap': market_cap
                })
                
                processed_count += 1
                if processed_count % 100 == 0:
                    log_info("已处理{}只股票".format(processed_count))
                    
            except Exception as e:
                log_info("处理股票{}失败: {}".format(original_code, str(e)))
                continue
                
        log_info("成功获取{}只股票的完整数据".format(len(stock_data)))
        return stock_data
        
    except Exception as e:
        log_info("批量获取股票数据失败: {}".format(str(e)))
        return []

def select_target_stocks():
    """选择目标股票"""
    log_info("开始选股...")
    
    # 获取过滤后的股票
    filtered_stocks = get_filtered_stocks()
    if not filtered_stocks:
        return []
    
    # 批量获取股票数据
    stock_data = get_stock_data_batch(filtered_stocks)
    if not stock_data:
        log_info("无有效股票数据")
        return []
    
    # 按市值排序, 选择最小的10只
    sorted_stocks = sorted(stock_data, key=lambda x: x['market_cap'])
    target_stocks = [item['code'] for item in sorted_stocks[:MAX_POSITIONS]]
    
    log_info("选出目标股票: {}".format(target_stocks))
    for i, item in enumerate(sorted_stocks[:MAX_POSITIONS]):
        log_info("第{}名: {} 价格:{:.2f} 总股本:{:.0f}万股 市值:{:.2f}万元".format(
            i+1, item['code'], item['price'], item['total_volume']/10000, item['market_cap']/10000))
    
    return target_stocks

def get_current_positions():
    """获取当前持仓"""
    try:
        positions = get_trade_detail_data('99080945','STOCK','POSITION')
        current_pos = {}
        #for dt in positions:
            #print(f'股票代码: {dt.m_strInstrumentID}, 市场类型: {dt.m_strExchangeID}, 证券名称: {dt.m_strInstrumentName}, 持仓量: {dt.m_nVolume}, 可用数量: {dt.m_nCanUseVolume}',
            #f'成本价: {dt.m_dOpenPrice:.2f}, 市值: {dt.m_dInstrumentValue:.2f}, 持仓成本: {dt.m_dPositionCost:.2f}, 盈亏: {dt.m_dPositionProfit:.2f}')
        
        if positions:
            for pos in positions:
                if hasattr(pos, 'volume') and pos.m_nVolume > 0:
                    current_pos[pos.stock_code] = pos.m_nVolume
        
        return current_pos
    except Exception as e:
        log_info("获取持仓失败: {}".format(str(e)))
        return {}

def get_account_total_value():
    """获取账户总市值"""
    try:
        accounts = get_trade_detail_data('99080945',"STOCK",'account')
        for dt in accounts:
            print(f'总资产: {dt.m_dBalance:.2f}, 净资产: {dt.m_dAssureAsset:.2f}, 总市值: {dt.m_dInstrumentValue:.2f}', 
            f'总负债: {dt.m_dTotalDebit:.2f}, 可用金额: {dt.m_dAvailable:.2f}, 盈亏: {dt.m_dPositionProfit:.2f}')
            return dt.m_dBalance
    except Exception as e:
        log_info("获取账户资产失败: {}".format(str(e)))
        return 0

def get_stock_current_price(stock_code):
    """获取单只股票当前价格"""
    try:
        ticks = A.ContextInfo.get_full_tick([stock_code])
        log_info(ticks)
        if formatted_code in ticks.values():
            return formatted_code.get("lastPrice", 0)
        else:
            log_info("无法获取股票{}的价格".format(stock_code))
            return 0
            
    except Exception as e:
        log_info("获取股票{}价格失败: {}".format(stock_code, str(e)))
        return 0

def calculate_buy_volume(stock_code, target_amount):
    """计算买入股数"""
    try:
        current_price = get_stock_current_price(stock_code)
        
        if current_price <= 0:
            log_info("股票{}价格异常: {}".format(stock_code, current_price))
            return 0
            
        # 计算可买股数(手数向下取整)
        shares = int(target_amount / current_price)
        lots = shares // 100  # 转换为手数
        final_shares = lots * 100  # 最终股数(整手)
        
        log_info("股票{}: 价格{:.2f}, 目标金额{:.0f}, 可买{}手({}股)".format(
            stock_code, current_price, target_amount, lots, final_shares))
            
        return final_shares
        
    except Exception as e:
        log_info("计算买入股数失败: {}".format(str(e)))
        return 0

def place_order(stock_code, order_type, volume, price_type=11, price=0):
    """使用passorder下单"""
    try:
        # 订单参数
        order_info = {
            'stock_code': stock_code,
            'order_type': order_type,  # 23=买入, 24=卖出
            'volume': volume,
            'price_type': price_type,  # 11=市价, 12=限价
            'price': price
        }
        
        log_info("准备下单: {}".format(order_info))
        
        # 使用passorder下单
        order_result = passorder(
            optype=order_type,
            ordercode=stock_code,
            pricemode=price_type,
            volume=volume,
            price=price,
            extra='',
            ContextInfo=A.ContextInfo
        )
        
        if order_result and order_result.get('success'):
            log_info("下单成功: {} 委托单号: {}".format(
                stock_code, order_result.get('order_id', 'N/A')))
            return True
        else:
            error_msg = order_result.get('error_msg', '未知错误') if order_result else '下单返回空'
            log_info("下单失败: {} 错误: {}".format(stock_code, error_msg))
            return False
            
    except Exception as e:
        log_info("下单异常: {} 错误: {}".format(stock_code, str(e)))
        return False

def execute_strategy():
    """执行策略"""
    log_info("开始执行策略...")
    
    # 获取目标股票
    target_stocks = select_target_stocks()
    if not target_stocks:
        log_info("未选出目标股票")
        return
    
    # 获取当前持仓
    current_positions = get_current_positions()
    log_info("当前持仓: {}".format(current_positions))
    
    # 获取账户总市值
    total_value = get_account_total_value()
    log_info("账户总市值: {}".format(total_value))
    
    if total_value <= 0:
        log_info("账户总市值为0, 停止执行")
        return
    
    # 1. 卖出不在目标股票中的持仓
    for stock_code, volume in current_positions.items():
        if stock_code not in target_stocks:
            log_info("准备卖出: {}, 数量: {}".format(stock_code, volume))
            place_order(stock_code, 24, volume, 11, 0)  # 24=卖出, 11=市价
    
    # 2. 买入目标股票
    for stock_code in target_stocks:
        current_volume = current_positions.get(stock_code, 0)
        target_volume = calculate_buy_volume(stock_code, total_value * POSITION_RATIO)
        
        if target_volume > current_volume:
            buy_volume = target_volume - current_volume
            if buy_volume >= 100:  # 至少1手
                log_info("准备买入: {}, 数量: {}".format(stock_code, buy_volume))
                place_order(stock_code, 23, buy_volume, 11, 0)  # 23=买入, 11=市价
    
    log_info("策略执行完成")

def init(ContextInfo):
    """策略初始化"""
    log_info("=== 小市值策略初始化 (官方API版) ===")
    A.ContextInfo = ContextInfo
    if hasattr(ContextInfo, 'strategy_name'):
        ContextInfo.strategy_name = "小市值策略_官方API版"

def handlebar(ContextInfo):
    """主策略函数"""
    # 检查执行时间
    #if not is_execution_time():
        #return
    
    log_info("满足执行条件, 开始执行策略")
    A.ContextInfo = ContextInfo
    try:
        execute_strategy()
    except Exception as e:
        log_info("策略执行异常: {}".format(str(e)))

