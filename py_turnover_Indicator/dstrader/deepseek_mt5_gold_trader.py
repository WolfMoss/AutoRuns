import os
import time
from openai import OpenAI
import pandas as pd
import MetaTrader5 as mt5
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import traceback
import sys

# 设置标准输出编码为UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# 获取API类型配置
AI_API_TYPE = os.getenv('AI_API_TYPE', 'deepseek')

# 根据配置初始化AI客户端
if AI_API_TYPE.lower() == 'siliconflow':
    print("使用硅基流动API")
    ai_client = OpenAI(
        api_key=os.getenv('SILICONFLOW_API_KEY'),
        base_url=os.getenv('SILICONFLOW_BASE_URL', 'https://api.siliconflow.com')
    )
else:
    print("使用DeepSeek API")
    ai_client = OpenAI(
        api_key=os.getenv('DEEPSEEK_API_KEY'),
        base_url=os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    )



# 交易参数配置 - 针对COMEX黄金期货
TRADE_CONFIG = {
    'symbol': 'GCEZ25',  # COMEX黄金期货主力合约
    'timeframe': '5m',  # 
    'test_mode': False,  # 测试模式
    'data_points': 240,  # 
    # 智能仓位参数
    'position_management': {
        'base_lot_amount': 1,  # 基础交易手数
        'high_confidence_multiplier': 1.0,
        'medium_confidence_multiplier': 1.0,
        'low_confidence_multiplier': 0.5,
        'max_position_ratio': 0.1,  # 单次最大仓位比例
        'trend_strength_multiplier': 1,
        'max_total_lots': 1.0,  # 最大总持仓手数（所有同方向订单加起来）
        'enable_position_limit': True  # 是否启用仓位限制
    }
}

def setup_mt5():
    """初始化MT5连接"""



    try:
        success = mt5.initialize()
        if success:
            print("✅ MT5连接成功")
            account_info = mt5.account_info()
            print(f"💰 账户余额: {account_info.balance:.2f} USD")
            print(f"📊 账户杠杆: 1:{account_info.leverage}")
            return True
        else:
            print("❌ MT5登录失败，错误代码:", mt5.last_error())
    except Exception as e:
        print(f"MT5初始化过程中发生异常: {str(e)}")
        print("=" * 50)
        return False



# 全局变量存储历史数据
price_history = []
signal_history = []
position = None

def get_timeframe_constant(timeframe_str):
    """将时间周期字符串转换为MT5常量"""
    timeframe_map = {
        '1m': mt5.TIMEFRAME_M1,
        '5m': mt5.TIMEFRAME_M5,
        '15m': mt5.TIMEFRAME_M15,
        '30m': mt5.TIMEFRAME_M30,
        '1h': mt5.TIMEFRAME_H1,
        '4h': mt5.TIMEFRAME_H4,
        '1d': mt5.TIMEFRAME_D1,
        '1w': mt5.TIMEFRAME_W1,
        '1M': mt5.TIMEFRAME_MN1
    }
    return timeframe_map.get(timeframe_str, mt5.TIMEFRAME_M15)

def get_gold_futures_data(timeframe_str=None, data_points=None):
    """从MT5获取黄金期货K线数据
    
    Args:
        timeframe_str: 时间周期字符串，如'5m', '4h'等。如果为None，使用配置的timeframe
        data_points: 获取的K线数量。如果为None，使用配置的data_points
    """
    try:
        symbol = TRADE_CONFIG['symbol']
        if timeframe_str is None:
            timeframe_str = TRADE_CONFIG['timeframe']
        if data_points is None:
            data_points = TRADE_CONFIG['data_points']
        
        timeframe = get_timeframe_constant(timeframe_str)
        timeframe_display = timeframe_str
        
        # 1. 确保品种在市场观察窗口中（这样数据才会实时更新）
        if not mt5.symbol_select(symbol, True):
            print(f"⚠️ 无法添加品种 {symbol} 到市场观察窗口")
        
        # 2. 获取品种信息，确认品种可用
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ 品种 {symbol} 不存在或不可用")
            return None
        
        # 3. 获取最新tick以获取服务器时间
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ 无法获取品种 {symbol} 的实时报价")
            return None
            
        server_time = datetime.fromtimestamp(tick.time)
        local_time = datetime.now()
        
        print(f"⏰ 服务器时间: {server_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 本地时间: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 当前报价: Bid={tick.bid:.2f}, Ask={tick.ask:.2f}")
        
        # 4. 使用 copy_rates_from 从服务器当前时间获取，确保获取最新数据
        # 获取比需要多一些的数据，确保包含最新已完成的K线
        rates = mt5.copy_rates_from(symbol, timeframe, server_time, data_points + 1)
        
        if rates is None or len(rates) == 0:
            print(f"❌ 无法从MT5获取K线数据: {mt5.last_error()}")
            # 尝试使用备用方法
            print("🔄 尝试使用备用方法获取数据...")
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, data_points)
            if rates is None or len(rates) == 0:
                return None
        
        # 转换为DataFrame
        df = pd.DataFrame(rates)
        
        # 转换时间戳为datetime
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        
        # 重命名列以匹配标准格式
        df = df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume'
        })
        
        # 选择需要的列
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # 按时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 确保获取指定数量的K线
        df = df.tail(data_points).reset_index(drop=True)
        
        # 获取最新数据
        current_data = df.iloc[-1]
        previous_data = df.iloc[-2] if len(df) > 1 else current_data
        
        print(f"✅ 成功从MT5获取 {len(df)} 根已完成的{timeframe_display}K线数据")
        print(f"   时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
        print(f"   最新K线时间: {df['timestamp'].iloc[-1]}")
        print(f"   最新收盘价: {current_data['close']:.2f}")
        
        # 显示最后5根K线的时间和收盘价，方便调试
        # print(f"   最后5根K线详情:")
        # for i in range(max(0, len(df)-5), len(df)):
        #     kline = df.iloc[i]
        #     print(f"      {kline['timestamp']} - 收盘: {kline['close']:.2f}")
        
        return {
            'price': float(current_data['close']),
            'timestamp': df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S'),
            'high': float(current_data['high']),
            'low': float(current_data['low']),
            'volume': float(current_data['volume']),
            'timeframe': timeframe_display,
            'price_change': ((current_data['close'] - previous_data['close']) / previous_data['close']) * 100,
            'kline_data': df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(30).to_dict('records'),
            'full_data': df
        }
        
    except Exception as e:
        print(f"❌ 获取MT5 K线数据失败: {e}")
        traceback.print_exc()
        return None

def calculate_technical_indicators(df):
    """计算技术指标（仅保留移动平均线）"""
    try:
        # 移动平均线
        df['sma_5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['sma_15'] = df['close'].rolling(window=15, min_periods=1).mean()
        df['sma_30'] = df['close'].rolling(window=30, min_periods=1).mean()
        df['sma_60'] = df['close'].rolling(window=60, min_periods=1).mean()
        df['sma_120'] = df['close'].rolling(window=120, min_periods=1).mean()
        df['sma_240'] = df['close'].rolling(window=240, min_periods=1).mean()

        # 填充NaN值
        df = df.bfill().ffill()

        return df
    except Exception as e:
        print(f"技术指标计算失败: {e}")
        return df

def get_market_trend(df):
    """准备移动平均线数据文本，不调用AI"""
    try:
        current_price = df['close'].iloc[-1]
        current_data = df.iloc[-1]
        
        # 准备移动平均线数据文本
        indicators_text = f"""
【移动平均线数据】
当前价格: {current_price:.2f}

📊 移动平均线系统:
- SMA_5: {current_data.get('sma_5', 0):.2f} (偏离: {((current_price - current_data.get('sma_5', current_price)) / current_price * 100):+.2f}%)
- SMA_15: {current_data.get('sma_15', 0):.2f} (偏离: {((current_price - current_data.get('sma_15', current_price)) / current_price * 100):+.2f}%)
- SMA_30: {current_data.get('sma_30', 0):.2f} (偏离: {((current_price - current_data.get('sma_30', current_price)) / current_price * 100):+.2f}%)
- SMA_60: {current_data.get('sma_60', 0):.2f} (偏离: {((current_price - current_data.get('sma_60', current_price)) / current_price * 100):+.2f}%)
- SMA_120: {current_data.get('sma_120', 0):.2f} (偏离: {((current_price - current_data.get('sma_120', current_price)) / current_price * 100):+.2f}%)
- SMA_240: {current_data.get('sma_240', 0):.2f} (偏离: {((current_price - current_data.get('sma_240', current_price)) / current_price * 100):+.2f}%)

说明：均线用于辅助判断趋势方向，结合K线形态和成交量进行分析。
"""
        
        return {
            'indicators_text': indicators_text
        }
            
    except Exception as e:
        print(f"❌ 移动平均线数据准备失败: {e}")
        traceback.print_exc()
        return {
            'indicators_text': '移动平均线数据不可用'
        }

def get_gold_ohlcv_enhanced():
    """增强版：获取黄金K线数据并计算技术指标，同时获取4小时周期数据"""
    try:
        # 获取配置周期的基础数据
        price_data = get_gold_futures_data()
        if not price_data:
            return None

        df = price_data['full_data']
        
        # 计算技术指标
        df = calculate_technical_indicators(df)
        

        # 获取技术指标文本（不调用AI）
        indicators_text = get_market_trend(df)['indicators_text']

        # 获取4小时周期的K线数据
        print(f"\n📊 获取4小时周期K线数据作为参考...")
        price_data_4h = get_gold_futures_data(timeframe_str='4h', data_points=TRADE_CONFIG['data_points'])
        
        h4_kline_data = None
        h4_indicators_text = ""
        if price_data_4h:
            # 获取4小时K线数据
            h4_kline_data = price_data_4h['kline_data']
            print(f"✅ 成功获取{len(h4_kline_data)}根4小时K线数据")
            
            # 计算4小时周期的技术指标
            df_4h = price_data_4h['full_data']
            df_4h = calculate_technical_indicators(df_4h)
            
            # 生成4小时周期的移动平均线文本
            trend_data_4h = get_market_trend(df_4h)
            h4_indicators_text = trend_data_4h['indicators_text'].replace('【移动平均线数据】', '【4小时周期移动平均线数据】')
        else:
            print(f"⚠️ 获取4小时K线数据失败")

        return {
            'price': price_data['price'],
            'timestamp': price_data['timestamp'],
            'high': price_data['high'],
            'low': price_data['low'],
            'volume': price_data['volume'],
            'timeframe': TRADE_CONFIG['timeframe'],
            'price_change': price_data['price_change'],
            'kline_data': price_data['kline_data'],
            'h4_kline_data': h4_kline_data,  # 4小时K线数据
            'indicators_text': indicators_text,  # 配置周期技术指标文本
            'h4_indicators_text': h4_indicators_text,  # 4小时周期技术指标文本
            'full_data': df
        }
    except Exception as e:
        print(f"获取增强K线数据失败: {e}")
        return None

def get_current_mt5_position():
    """获取MT5当前持仓情况"""
    try:
        positions = mt5.positions_get(symbol=TRADE_CONFIG['symbol'])
        
        if positions:
            position = positions[0]
            return {
                'side': 'buy' if position.type == mt5.ORDER_TYPE_BUY else 'sell',
                'volume': position.volume,
                'entry_price': position.price_open,
                'profit': position.profit,
                'symbol': position.symbol
            }
        return None
        
    except Exception as e:
        print(f"获取MT5持仓失败: {e}")
        return None

def get_total_position_by_direction(symbol):
    """获取指定方向的总持仓手数"""
    try:
        positions = mt5.positions_get(symbol=symbol)
        
        if not positions:
            return {'buy': 0.0, 'sell': 0.0, 'total': 0}
        
        buy_volume = 0.0
        sell_volume = 0.0
        
        for pos in positions:
            if pos.type == mt5.ORDER_TYPE_BUY:
                buy_volume += pos.volume
            else:  # SELL
                sell_volume += pos.volume
        
        return {
            'buy': buy_volume,
            'sell': sell_volume,
            'total': len(positions),
            'positions': [
                {
                    'ticket': pos.ticket,
                    'type': 'buy' if pos.type == mt5.ORDER_TYPE_BUY else 'sell',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'profit': pos.profit
                }
                for pos in positions
            ]
        }
        
    except Exception as e:
        print(f"❌ 获取总持仓失败: {e}")
        return {'buy': 0.0, 'sell': 0.0, 'total': 0}

def close_positions_by_direction(symbol, direction=None):
    """平掉指定方向的持仓
    
    Args:
        symbol: 交易品种
        direction: 'buy' 或 'sell'，如果为None则平掉所有持仓
    
    Returns:
        成功平仓的数量
    """
    try:
        positions = mt5.positions_get(symbol=symbol)
        
        if not positions:
            print("📭 当前无持仓")
            return 0
        
        closed_count = 0
        
        for position in positions:
            # 判断是否需要平掉这个持仓
            pos_type = 'buy' if position.type == mt5.ORDER_TYPE_BUY else 'sell'
            
            if direction is None or pos_type == direction:
                # 准备平仓请求
                close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                
                # 获取当前价格
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    print(f"❌ 无法获取 {symbol} 报价")
                    continue
                
                close_price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
                
                # 获取填充模式
                filling_type = get_supported_filling_mode(symbol)
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": position.volume,
                    "type": close_type,
                    "position": position.ticket,
                    "price": close_price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "反向信号平仓",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_type,
                }
                
                print(f"\n🔄 平仓操作:")
                print(f"   持仓单号: #{position.ticket}")
                print(f"   方向: {pos_type.upper()}")
                print(f"   手数: {position.volume}")
                print(f"   开仓价: {position.price_open:.2f}")
                print(f"   当前价: {close_price:.2f}")
                print(f"   浮动盈亏: {position.profit:.2f} USD")
                
                # 发送平仓请求
                result = mt5.order_send(request)
                
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print(f"❌ 平仓失败: {result.retcode}, 说明: {result.comment}")
                else:
                    print(f"✅ 平仓成功: {pos_type.upper()} {position.volume}手")
                    if result.price > 0:
                        print(f"   实际平仓价: {result.price:.2f}")
                    closed_count += 1
        
        return closed_count
        
    except Exception as e:
        print(f"❌ 平仓操作失败: {e}")
        import traceback
        traceback.print_exc()
        return 0

def calculate_intelligent_lot_size(signal_data, price_data, current_position):
    """计算智能仓位大小"""
    config = TRADE_CONFIG['position_management']
    symbol = TRADE_CONFIG['symbol']

    try:
        # 获取账户余额
        account_info = mt5.account_info()
        balance = account_info.balance

        # 获取交易品种信息
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ 无法获取交易品种信息: {symbol}")
            return 0.01  # 返回最小有效手数
            
        # 获取交易品种的交易量限制
        min_volume = symbol_info.volume_min
        max_volume = symbol_info.volume_max
        volume_step = symbol_info.volume_step

        # 基础交易手数
        base_lot = config['base_lot_amount']

        # 根据信心程度调整
        confidence_multiplier = {
            'HIGH': config['high_confidence_multiplier'],
            'MEDIUM': config['medium_confidence_multiplier'],
            'LOW': config['low_confidence_multiplier']
        }.get(signal_data['confidence'], 1.0)

        # 根据趋势强度调整（从signal_data中获取）
        trend_analysis = signal_data.get('trend_analysis', {})
        trend = trend_analysis.get('overall', '震荡整理')
        if trend in ['强势上涨', '强势下跌']:
            trend_multiplier = config['trend_strength_multiplier']
        else:
            trend_multiplier = 1.0

        # 计算建议交易手数
        suggested_lot = base_lot * confidence_multiplier * trend_multiplier

        # 风险管理
        max_lot = balance * config['max_position_ratio'] / price_data['price']
        final_lot = min(suggested_lot, max_lot)

        # 确保交易量符合品种要求
        # 向下舍入到最接近的volume_step
        final_lot = round(final_lot / volume_step) * volume_step
        
        # 确保在最小和最大交易量之间
        final_lot = max(min_volume, min(final_lot, max_volume))

        print(f"📊 仓位计算详情:")
        print(f"   - 基础手数: {base_lot}")
        print(f"   - 信心倍数: {confidence_multiplier}")
        print(f"   - 趋势倍数: {trend_multiplier}")
        print(f"   - 品种最小手数: {min_volume}")
        print(f"   - 品种最大手数: {max_volume}")
        print(f"   - 品种手数步长: {volume_step}")
        print(f"   - 最终手数: {final_lot:.2f}")

        return final_lot

    except Exception as e:
        print(f"❌ 仓位计算失败，使用最小有效手数: {e}")
        # 获取最小有效手数
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                return symbol_info.volume_min
            else:
                return 0.01  # 默认最小手数
        except:
            return 0.01  # 出错时返回默认最小手数

def get_supported_filling_mode(symbol):
    """获取交易品种支持的订单填充模式"""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"无法获取品种 {symbol} 信息，使用默认填充模式")
        return mt5.ORDER_FILLING_IOC
    
    # 检查支持的填充模式
    filling_mode = symbol_info.filling_mode
    
    # 按优先级检查支持的填充模式
    # 1 = FOK, 2 = IOC, 4 = RETURN
    if filling_mode & 2:  # IOC模式
        print(f"品种 {symbol} 支持 IOC 填充模式")
        return mt5.ORDER_FILLING_IOC
    elif filling_mode & 1:  # FOK模式
        print(f"品种 {symbol} 支持 FOK 填充模式")
        return mt5.ORDER_FILLING_FOK
    else:  # 默认使用RETURN模式
        print(f"品种 {symbol} 使用默认 RETURN 填充模式")
        return mt5.ORDER_FILLING_RETURN

def execute_mt5_trade(signal_data, price_data):
    """执行MT5交易（带止盈止损）"""
    try:
        symbol = TRADE_CONFIG['symbol']
        config = TRADE_CONFIG['position_management']
        
        # 确定交易方向
        if signal_data['signal'] == 'BUY':
            trade_type = mt5.ORDER_TYPE_BUY
            action = mt5.TRADE_ACTION_DEAL
            signal_direction = 'buy'
            opposite_direction = 'sell'
        elif signal_data['signal'] == 'SELL':
            trade_type = mt5.ORDER_TYPE_SELL
            action = mt5.TRADE_ACTION_DEAL
            signal_direction = 'sell'
            opposite_direction = 'buy'
        else:
            print("🔄 HOLD信号，不执行交易")
            return True
        
        # 检查是否存在反向持仓，如果存在则先平仓
        print(f"\n🔍 检查反向持仓...")
        total_positions = get_total_position_by_direction(symbol)
        opposite_volume = total_positions[opposite_direction]
        
        if opposite_volume > 0:
            print(f"\n⚠️ 检测到反向持仓！")
            print(f"   新信号方向: {signal_direction.upper()}")
            print(f"   反向持仓: {opposite_direction.upper()} {opposite_volume:.2f}手")
            print(f"   需要先平掉反向持仓...")
            
            # 平掉反向持仓
            closed_count = close_positions_by_direction(symbol, opposite_direction)
            
            if closed_count > 0:
                print(f"\n✅ 已平掉 {closed_count} 个反向持仓")
                # 等待一小段时间确保平仓完成
                time.sleep(1)
            else:
                print(f"\n❌ 反向持仓平仓失败，取消本次开仓")
                return False
        else:
            print(f"   无反向持仓，可以继续开仓")
        
        # 检查仓位限制（如果启用）
        remaining_lots = float('inf')  # 默认无限制
        
        if config.get('enable_position_limit', True):
            total_positions = get_total_position_by_direction(symbol)
            current_direction_volume = total_positions[signal_direction]
            max_total_lots = config.get('max_total_lots', 3.0)
            
            # 显示当前持仓情况
            print(f"\n📊 当前持仓情况:")
            print(f"   做多总手数: {total_positions['buy']:.2f}")
            print(f"   做空总手数: {total_positions['sell']:.2f}")
            print(f"   持仓订单数: {total_positions['total']}")
            
            if total_positions['total'] > 0:
                print(f"\n   详细持仓:")
                for pos in total_positions['positions']:
                    print(f"      #{pos['ticket']} {pos['type'].upper()} {pos['volume']:.2f}手 @{pos['price_open']:.2f} 盈亏:{pos['profit']:.2f}")
            
            # 检查是否超过最大仓位
            if current_direction_volume >= max_total_lots:
                print(f"\n⚠️ 已达到最大仓位限制！")
                print(f"   当前{signal_direction.upper()}方向持仓: {current_direction_volume:.2f}手")
                print(f"   最大允许持仓: {max_total_lots:.2f}手")
                print(f"   🚫 取消本次开仓操作")
                return False
            
            # 计算本次可以开仓的最大手数
            remaining_lots = max_total_lots - current_direction_volume
            print(f"\n✅ 仓位检查通过")
            print(f"   {signal_direction.upper()}方向剩余可用: {remaining_lots:.2f}手")
        
        # 获取当前持仓
        current_position = get_current_mt5_position()
        
        # 计算交易手数
        lot_size = calculate_intelligent_lot_size(signal_data, price_data, current_position)
        
        # 如果启用仓位限制，确保不超过剩余可用手数
        if config.get('enable_position_limit', True):
            if lot_size > remaining_lots:
                print(f"   ⚠️ 计划手数 {lot_size:.2f} 超过剩余可用手数，调整为 {remaining_lots:.2f}")
                lot_size = remaining_lots
            
            # 如果调整后手数太小，不执行交易
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info and lot_size < symbol_info.volume_min:
                print(f"   ⚠️ 调整后手数 {lot_size:.2f} 小于最小交易手数 {symbol_info.volume_min}，取消交易")
                return False

        # 获取支持的填充模式
        filling_type = get_supported_filling_mode(symbol)
        
        # 获取当前价格
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ 无法获取品种 {symbol} 的报价")
            return False
            
        current_price = tick.ask if trade_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # 获取AI建议的止损价格
        stop_loss_price = float(signal_data.get('stop_loss', 0))
        
        # 验证止损价格的合理性
        if stop_loss_price <= 0:
            print(f"\n❌ AI未提供有效的止损价格！")
            print(f"   止损价: {stop_loss_price:.2f}")
            print(f"   🚫 取消本次开仓操作（必须设置止损）")
            return False
        
        if trade_type == mt5.ORDER_TYPE_BUY:
            # 买入：止损应该低于当前价
            if stop_loss_price >= current_price:
                print(f"\n❌ 买入止损价格不合理！")
                print(f"   止损价: {stop_loss_price:.2f} >= 当前价: {current_price:.2f}")
                print(f"   止损价必须低于当前价格")
                print(f"   🚫 取消本次开仓操作")
                return False
            
            # 自动计算止盈价格（盈亏比1:1.1）
            stop_loss_distance = current_price - stop_loss_price  # 止损距离
            take_profit_distance = stop_loss_distance * 1.1  # 止盈距离
            take_profit_price = current_price + take_profit_distance  # 止盈价格
            
            print(f"\n💡 自动计算止盈价格（盈亏比1:1.1）")
            print(f"   止损距离: {stop_loss_distance:.2f}")
            print(f"   止盈距离: {take_profit_distance:.2f}")
            
        else:  # SELL
            # 卖出：止损应该高于当前价
            if stop_loss_price <= current_price:
                print(f"\n❌ 卖出止损价格不合理！")
                print(f"   止损价: {stop_loss_price:.2f} <= 当前价: {current_price:.2f}")
                print(f"   止损价必须高于当前价格")
                print(f"   🚫 取消本次开仓操作")
                return False
            
            # 自动计算止盈价格（盈亏比1:1.1）
            stop_loss_distance = stop_loss_price - current_price  # 止损距离
            take_profit_distance = stop_loss_distance * 1.1  # 止盈距离
            take_profit_price = current_price - take_profit_distance  # 止盈价格
            
            print(f"\n💡 自动计算止盈价格（盈亏比1:1.1）")
            print(f"   止损距离: {stop_loss_distance:.2f}")
            print(f"   止盈距离: {take_profit_distance:.2f}")
        
        # 准备交易请求
        request = {
            "action": action,
            "symbol": symbol,
            "volume": lot_size,
            "type": trade_type,
            "price": current_price,
            "deviation": 20,
            "magic": 234000,
            "comment": f"AI信号:{signal_data['confidence']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        
        # 添加止损
        if stop_loss_price > 0:
            request["sl"] = stop_loss_price
            
        # 添加止盈
        if take_profit_price > 0:
            request["tp"] = take_profit_price
        
        # 显示交易详情
        print(f"\n📋 交易订单详情:")
        print(f"   方向: {signal_data['signal']}")
        print(f"   手数: {lot_size}")
        print(f"   开仓价: {current_price:.2f}")
        if stop_loss_price > 0:
            sl_distance = abs(current_price - stop_loss_price)
            sl_pips = sl_distance * 10  # 假设1点=0.1价格单位
            print(f"   止损价: {stop_loss_price:.2f} (距离: {sl_distance:.2f} / {sl_pips:.0f}点)")
        else:
            print(f"   止损价: 未设置")
            
        if take_profit_price > 0:
            tp_distance = abs(take_profit_price - current_price)
            tp_pips = tp_distance * 10
            print(f"   止盈价: {take_profit_price:.2f} (距离: {tp_distance:.2f} / {tp_pips:.0f}点)")
        else:
            print(f"   止盈价: 未设置")
        
        # 计算风险回报比
        if stop_loss_price > 0 and take_profit_price > 0:
            risk = abs(current_price - stop_loss_price)
            reward = abs(take_profit_price - current_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0
            print(f"   风险回报比: 1:{risk_reward_ratio:.2f}")

        # 发送交易请求
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ 交易执行失败: {result.retcode}, 说明: {result.comment}")
            return False
        else:
            print(f"✅ 交易执行成功: {signal_data['signal']} {lot_size}手")
            if result.price > 0:
                print(f"   实际成交价: {result.price:.2f}")
            if hasattr(result, 'order') and result.order > 0:
                print(f"   订单号: {result.order}")
            return True

    except Exception as e:
        print(f"❌ MT5交易执行失败: {e}")
        traceback.print_exc()
        return False

def analyze_with_deepseek(price_data):
    """使用DeepSeek分析黄金市场并生成交易信号（一次性完成趋势分析和交易决策）"""
    
    # 构建配置周期K线数据文本
    kline_text = f"【最近30根{TRADE_CONFIG['timeframe']}K线数据】\n"
    for i, kline in enumerate(price_data['kline_data'][-30:]):
        trend = "阳线" if kline['close'] > kline['open'] else "阴线"
        change = ((kline['close'] - kline['open']) / kline['open']) * 100
        volume = kline.get('volume', 0)
        kline_text += f"K线{i + 1}: {trend} 开:{kline['open']:.2f} 高:{kline['high']:.2f} 低:{kline['low']:.2f} 收:{kline['close']:.2f} 涨跌:{change:+.2f}% 成交量:{volume:.0f}\n"
    
    # 构建4小时K线数据文本（如果有的话）
    h4_kline_text = ""
    if price_data.get('h4_kline_data'):
        h4_kline_text = f"\n【最近30根4h(四小时)K线数据 - 用于判断大周期趋势】\n"
        for i, kline in enumerate(price_data['h4_kline_data'][-30:]):
            trend = "阳线" if kline['close'] > kline['open'] else "阴线"
            change = ((kline['close'] - kline['open']) / kline['open']) * 100
            volume = kline.get('volume', 0)
            h4_kline_text += f"4H-K线{i + 1}: {trend} 开:{kline['open']:.2f} 高:{kline['high']:.2f} 低:{kline['low']:.2f} 收:{kline['close']:.2f} 涨跌:{change:+.2f}% 成交量:{volume:.0f}\n"
    
    #print(kline_text)

    # 添加上次交易信号
    signal_text = ""
    if signal_history:
        last_signal = signal_history[-1]
        signal_text = f"\n【上次交易信号】\n信号: {last_signal.get('signal', 'N/A')}\n信心: {last_signal.get('confidence', 'N/A')}"

    # 获取技术指标文本
    indicators_text = price_data.get('indicators_text', '技术指标数据不可用')
    h4_indicators_text = price_data.get('h4_indicators_text', '')

    prompt = f"""
    你是一个专业的黄金期货交易分析师。请基于以下COMEX黄金期货 {TRADE_CONFIG['timeframe']}周期数据进行分析：

    【当前行情】
    - 当前价格: ${price_data['price']:,.2f}
    - 时间: {price_data['timestamp']}
    - 本K线最高: ${price_data['high']:,.2f}
    - 本K线最低: ${price_data['low']:,.2f}
    - 本K线成交量: {price_data['volume']:.0f} 手
    - 价格变化: {price_data['price_change']:+.2f}%

    {kline_text}

    {h4_kline_text}

    {indicators_text}

    {h4_indicators_text}



    【分析要求】
    1. 结合给你的数据自行分析当前市场趋势
    2. 给出明确的交易信号和止损位


    请用以下JSON格式回复：
    {{
        "signal": "BUY|SELL|HOLD",
        "reason": "详细分析理由(包含趋势判断、技术依据、成交量分析、风险评估)",
        "stop_loss": 具体止损价格（必须提供）,
        "confidence": "HIGH|MEDIUM|LOW",
        "trend_analysis": {{
            "short_term": "上涨|下跌|震荡",
            "medium_term": "上涨|下跌|震荡",
            "overall": "强势上涨|上涨|震荡整理|下跌|强势下跌",
            "trend_strength": "强|中|弱"
        }}
    }}
    
    注意：你只需提供止损价格，止盈价格我自己会定
    """

    try:
        # 不需要额外的编码转换，直接使用原始prompt
        response = ai_client.chat.completions.create(
            model="deepseek-chat" if AI_API_TYPE.lower() == 'deepseek' else "deepseek-ai/DeepSeek-V3.2-Exp",
            messages=[
                {"role": "system",
                 "content": "您是一位急需资金为母亲治疗癌症的交易员，你现在需要从期货交易市场赚取足够的金额治疗你的母亲，专注于" + TRADE_CONFIG['timeframe'] + "周期趋势分析，尤其擅长K线形态和量价分析，精通并专注于威科夫订单流理论和Price Action交易法。严格遵循JSON格式要求。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=0.1
        )

        # 安全解析JSON
        result = response.choices[0].message.content
        # 确保结果中的中文能被正确处理
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        print(f"🤖 AI完整分析回复: {result}")

        # 提取JSON部分
        start_idx = result.find('{')
        end_idx = result.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            json_str = result[start_idx:end_idx]
            signal_data = json.loads(json_str)
        else:
            print("❌ 无法解析JSON响应")
            return None

        # 验证必需字段（不再需要take_profit，会自动计算）
        required_fields = ['signal', 'reason', 'stop_loss', 'confidence']
        if not all(field in signal_data for field in required_fields):
            print("❌ 信号数据不完整")
            print(f"   缺少字段: {[f for f in required_fields if f not in signal_data]}")
            return None

        # 保存信号到历史记录
        signal_data['timestamp'] = price_data['timestamp']
        signal_history.append(signal_data)
        if len(signal_history) > 30:
            signal_history.pop(0)

        return signal_data

    except Exception as e:
        error_msg = str(e)
        # 处理编码错误
        if isinstance(error_msg, bytes):
            try:
                error_msg = error_msg.decode('utf-8')
            except UnicodeDecodeError:
                error_msg = error_msg.decode('utf-8', errors='replace')
        
        # 打印完整的错误堆栈信息
        import traceback
        print(f"❌ DeepSeek分析失败: {error_msg}")
        traceback.print_exc()
        return None

def trading_bot():
    """主交易机器人函数"""
    print("\n" + "=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 获取黄金期货数据
    price_data = get_gold_ohlcv_enhanced()
    if not price_data:
        return

    print(f"黄金当前价格: ${price_data['price']:,.2f}")
    print(f"数据周期: {TRADE_CONFIG['timeframe']}")
    print(f"价格变化: {price_data['price_change']:+.2f}%")

    # 2. 使用DeepSeek分析
    signal_data = analyze_with_deepseek(price_data)
    if not signal_data:
        return

    print(f"📊 AI分析结果:")
    
    # 显示趋势分析（如果有）
    if 'trend_analysis' in signal_data:
        trend = signal_data['trend_analysis']
        print(f"   🎯 趋势判断:")
        print(f"      - 短期趋势: {trend.get('short_term', 'N/A')}")
        print(f"      - 中期趋势: {trend.get('medium_term', 'N/A')}")
        print(f"      - 整体趋势: {trend.get('overall', 'N/A')}")
        print(f"      - 趋势强度: {trend.get('trend_strength', 'N/A')}")
    
    print(f"   📈 交易信号:")
    print(f"      - 信号: {signal_data['signal']}")
    print(f"      - 信心: {signal_data['confidence']}")
    print(f"      - 理由: {signal_data['reason']}")
    
    # 显示止损价格
    if signal_data.get('stop_loss') is not None:
        print(f"      - AI止损: ${signal_data['stop_loss']:.2f}")
        print(f"      - 止盈策略: 自动计算（盈亏比1:1.1）")
    else:
        print(f"      - 止损: 未设置")

    # 3. 执行MT5交易
    if not TRADE_CONFIG['test_mode']:
        execute_mt5_trade(signal_data, price_data)
    else:
        print("🔄 测试模式，不执行真实交易")

def parse_timeframe_to_minutes(timeframe_str):
    """将时间周期字符串转换为分钟数"""
    timeframe_map = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '4h': 240,
        '1d': 1440,
        '1w': 10080,
        '1M': 43200
    }
    return timeframe_map.get(timeframe_str, 15)  # 默认15分钟

def calculate_next_run_time():
    """根据配置的timeframe计算下次运行时间（在K线即将完成前10秒执行）"""
    now = datetime.now()
    timeframe_minutes = parse_timeframe_to_minutes(TRADE_CONFIG['timeframe'])
    
    # 运行时机：在K线完成前10秒执行（例如15分钟周期在14:50执行）
    target_second = 50  # 提前10秒
    
    if timeframe_minutes < 60:
        # 小于1小时的周期（1m, 5m, 15m, 30m）
        current_minute = now.minute
        current_second = now.second
        
        # 计算当前周期内的目标分钟数
        # 例如：15分钟周期 -> 14, 29, 44, 59
        target_minutes = []
        for i in range(0, 60, timeframe_minutes):
            target_min = i + timeframe_minutes - 1  # K线完成的分钟数
            if target_min < 60:
                target_minutes.append(target_min)
        
        # 找到下一个目标时间
        next_target_minute = None
        for target_min in target_minutes:
            if current_minute < target_min or (current_minute == target_min and current_second < target_second):
                next_target_minute = target_min
                break
        
        # 如果当前小时内没有找到，则使用下一个小时的第一个目标时间
        if next_target_minute is None:
            next_run_time = now.replace(minute=target_minutes[0], second=target_second, microsecond=0) + timedelta(hours=1)
        else:
            next_run_time = now.replace(minute=next_target_minute, second=target_second, microsecond=0)
    
    elif timeframe_minutes == 60:
        # 1小时周期：每小时的59:50执行
        if now.minute < 59 or (now.minute == 59 and now.second < target_second):
            next_run_time = now.replace(minute=59, second=target_second, microsecond=0)
        else:
            next_run_time = (now + timedelta(hours=1)).replace(minute=59, second=target_second, microsecond=0)
    
    elif timeframe_minutes == 240:
        # 4小时周期：每4小时的最后一分钟执行（3:59, 7:59, 11:59, 15:59, 19:59, 23:59）
        target_hours = [3, 7, 11, 15, 19, 23]
        current_hour = now.hour
        
        next_target_hour = None
        for target_hour in target_hours:
            if current_hour < target_hour or (current_hour == target_hour and 
                (now.minute < 59 or (now.minute == 59 and now.second < target_second))):
                next_target_hour = target_hour
                break
        
        if next_target_hour is None:
            # 下一天的第一个时间点
            next_run_time = (now + timedelta(days=1)).replace(hour=target_hours[0], minute=59, second=target_second, microsecond=0)
        else:
            next_run_time = now.replace(hour=next_target_hour, minute=59, second=target_second, microsecond=0)
    
    else:
        # 1天及以上周期：每天的23:59:50执行
        if now.hour < 23 or (now.hour == 23 and now.minute < 59) or \
           (now.hour == 23 and now.minute == 59 and now.second < target_second):
            next_run_time = now.replace(hour=23, minute=59, second=target_second, microsecond=0)
        else:
            next_run_time = (now + timedelta(days=1)).replace(hour=23, minute=59, second=target_second, microsecond=0)
    
    return next_run_time

def wait_for_next_run():
    """等待到下次运行时间"""
    next_run_time = calculate_next_run_time()
    now = datetime.now()
    wait_seconds = (next_run_time - now).total_seconds()
    
    if wait_seconds > 0:
        print(f"\n⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 下次运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 等待时间: {int(wait_seconds // 60)}分{int(wait_seconds % 60)}秒")
        print("=" * 60)
        time.sleep(wait_seconds)
    
def is_in_run_window():
    """检查当前是否在运行时间窗口内（K线完成前10秒内）"""
    now = datetime.now()
    timeframe_minutes = parse_timeframe_to_minutes(TRADE_CONFIG['timeframe'])
    target_second = 50
    
    if timeframe_minutes < 60:
        # 小于1小时的周期
        current_minute = now.minute
        current_second = now.second
        
        # 计算目标分钟数
        target_minutes = []
        for i in range(0, 60, timeframe_minutes):
            target_min = i + timeframe_minutes - 1
            if target_min < 60:
                target_minutes.append(target_min)
        
        # 检查是否在目标分钟的50-59秒之间
        if current_minute in target_minutes and current_second >= target_second:
            return True
    
    elif timeframe_minutes == 60:
        # 1小时周期：59:50-59:59
        if now.minute == 59 and now.second >= target_second:
            return True
    
    elif timeframe_minutes == 240:
        # 4小时周期
        target_hours = [3, 7, 11, 15, 19, 23]
        if now.hour in target_hours and now.minute == 59 and now.second >= target_second:
            return True
    
    else:
        # 1天及以上：23:59:50-23:59:59
        if now.hour == 23 and now.minute == 59 and now.second >= target_second:
            return True
    
    return False

def get_execution_schedule_description():
    """获取执行计划描述"""
    timeframe_minutes = parse_timeframe_to_minutes(TRADE_CONFIG['timeframe'])
    
    if timeframe_minutes == 1:
        return "每1分钟执行一次（在每分钟的50-59秒运行）"
    elif timeframe_minutes == 5:
        return "每5分钟执行一次（在4:50, 9:50, 14:50, 19:50, 24:50, 29:50, 34:50, 39:50, 44:50, 49:50, 54:50, 59:50运行）"
    elif timeframe_minutes == 15:
        return "每15分钟执行一次（在14:50, 29:50, 44:50, 59:50运行）"
    elif timeframe_minutes == 30:
        return "每30分钟执行一次（在29:50, 59:50运行）"
    elif timeframe_minutes == 60:
        return "每1小时执行一次（在每小时的59:50运行）"
    elif timeframe_minutes == 240:
        return "每4小时执行一次（在3:59:50, 7:59:50, 11:59:50, 15:59:50, 19:59:50, 23:59:50运行）"
    elif timeframe_minutes == 1440:
        return "每天执行一次（在23:59:50运行）"
    else:
        return f"自定义周期执行（每{timeframe_minutes}分钟）"

def main():
    """主函数"""
    print("COMEX黄金期货 MT5自动交易机器人启动成功！")
    print("融合技术指标策略 + MT5实盘接口")

    if TRADE_CONFIG['test_mode']:
        print("⚠️ 当前为模拟模式，不会真实下单")
    else:
        print("🔴 实盘交易模式，请谨慎操作！")

    print(f"交易品种: {TRADE_CONFIG['symbol']}")
    print(f"交易周期: {TRADE_CONFIG['timeframe']}")

    # 初始化MT5
    if not setup_mt5():
        print("MT5初始化失败，程序退出")
        return

    # 显示执行计划
    schedule_desc = get_execution_schedule_description()
    print(f"执行频率: {schedule_desc}")
    print(f"运行窗口: K线完成前10秒内（避免数据延迟）")
    print(f"说明: 程序会在K线即将完成时执行分析，确保获取最新完整K线数据")

    # 循环执行
    while True:
        # 等待到下次运行时间
        wait_for_next_run()
        
        # 执行交易逻辑
        trading_bot()
        
        # 等待5秒，避免在同一个时间窗口内重复执行
        time.sleep(5)

if __name__ == "__main__":
    main()