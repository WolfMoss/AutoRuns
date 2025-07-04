# -*-coding:utf-8-*-
"""
A股历史行情获取类
基于miniqmt(xtquant)实现A股历史行情数据获取
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import List, Optional, Union

# 配置pandas显示选项
pd.set_option('expand_frame_repr', False)  # 当列太多时显示完整
pd.set_option('display.max_rows', 5000)  # 最多显示数据的行数

try:
    from xtquant import xtdata
    print("xtquant库导入成功")
except ImportError as e:
    print(f"xtquant库导入失败: {e}")
    print("请确保已安装QMT客户端并配置xtquant库")


class AStockHistoryData:
    """
    A股历史行情数据获取类
    基于miniqmt(xtquant)接口实现
    """
    
    def __init__(self):
        """初始化A股历史行情类"""
        self.logger = self._setup_logger()
        self.period_map = {
            '1m': '1m',      # 1分钟
            '5m': '5m',      # 5分钟
            '15m': '15m',    # 15分钟
            '30m': '30m',    # 30分钟
            '60m': '1h',     # 60分钟/1小时
            '1h': '1h',      # 1小时
            '1d': '1d',      # 日线
            '1w': '1w',      # 周线
            '1M': '1M'       # 月线
        }
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('AStockHistoryData')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def format_stock_code(self, code: str) -> str:
        """
        格式化股票代码
        将6位股票代码转换为xtquant需要的格式
        
        Args:
            code: 股票代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            str: 格式化后的代码，如 '000001.SZ'
        """
        if '.' in code:
            return code.upper()
        
        # 6位纯数字代码处理
        if len(code) == 6 and code.isdigit():
            if code.startswith(('000', '001', '002', '003', '300')):
                return f"{code}.SZ"  # 深交所
            elif code.startswith(('600', '601', '603', '605', '688')):
                return f"{code}.SH"  # 上交所
            else:
                self.logger.warning(f"无法识别股票代码前缀: {code}")
                return f"{code}.SZ"  # 默认深交所
        
        return code
    
    def download_history_data(self, stock_code: str, period: str = '1d') -> bool:
        """
        下载股票历史数据到本地
        根据官方文档，需要先下载数据到本地才能获取
        
        Args:
            stock_code: 股票代码
            period: 数据周期
            
        Returns:
            bool: 下载是否成功
        """
        try:
            formatted_code = self.format_stock_code(stock_code)
            self.logger.info(f"正在下载 {formatted_code} 的 {period} 历史数据到本地...")
            
            # 增量下载行情数据到本地
            xtdata.download_history_data(formatted_code, period=period, incrementally=True)
            
            self.logger.info(f"成功下载 {formatted_code} 历史数据")
            return True
            
        except Exception as e:
            self.logger.error(f"下载 {stock_code} 历史数据失败: {str(e)}")
            return False
    
    def get_all_a_stock_list(self) -> List[str]:
        """
        获取所有A股股票列表
        
        Returns:
            List[str]: A股股票代码列表
        """
        try:
            # 方法1: 尝试获取沪深A股板块
            try:
                stocks = xtdata.get_stock_list_in_sector('沪深A股')
                if stocks and len(stocks) > 0:
                    self.logger.info(f"通过沪深A股板块获取到 {len(stocks)} 只股票")
                    return stocks
            except:
                pass
            
            # 方法2: 分别获取沪市和深市股票
            try:
                sh_stocks = xtdata.get_stock_list_in_sector('上海A股')
                sz_stocks = xtdata.get_stock_list_in_sector('深圳A股')
                
                all_stocks = []
                if sh_stocks:
                    all_stocks.extend(sh_stocks)
                if sz_stocks:
                    all_stocks.extend(sz_stocks)
                
                if all_stocks:
                    # 去重
                    all_stocks = list(set(all_stocks))
                    self.logger.info(f"通过分板块获取到 {len(all_stocks)} 只股票")
                    return all_stocks
            except:
                pass
            
            # 方法3: 获取所有股票然后过滤
            try:
                all_instruments = xtdata.get_instrument_detail()
                if all_instruments:
                    a_stocks = []
                    for code in all_instruments.keys():
                        if self.is_valid_a_stock(code):
                            a_stocks.append(code)
                    
                    if a_stocks:
                        self.logger.info(f"通过全量过滤获取到 {len(a_stocks)} 只A股")
                        return a_stocks
            except:
                pass
            
            # 备用方案：返回一些常见股票作为示例
            sample_stocks = [
                '000001.SZ', '000002.SZ', '000858.SZ', '000876.SZ',
                '600000.SH', '600036.SH', '600519.SH', '600887.SH',
                '300001.SZ', '300015.SZ', '300059.SZ', '300122.SZ'
            ]
            self.logger.warning(f"使用备用股票列表，共 {len(sample_stocks)} 只")
            return sample_stocks
            
        except Exception as e:
            self.logger.error(f"获取A股列表失败: {str(e)}")
            return []
    
    def is_valid_a_stock(self, stock_code: str) -> bool:
        """
        判断是否为有效的A股股票
        
        Args:
            stock_code: 股票代码
            
        Returns:
            bool: 是否为有效A股
        """
        # 排除ETF、基金、债券等
        if stock_code.startswith(('51', '15', '16', '50', '11', '12')):
            return False
        
        # 只保留沪深A股
        if stock_code.endswith('.SH'):
            # 沪市：600、601、603、605、688开头
            return stock_code.startswith(('600', '601', '603', '605', '688'))
        elif stock_code.endswith('.SZ'):
            # 深市：000、001、002、003、300开头
            return stock_code.startswith(('000', '001', '002', '003', '300'))
        
        return False

    def get_stock_kline_data(self,
                           stock_code: str,
                           period: str = '1d',
                           start_time: str = '',
                           end_time: str = '',
                           count: int = -1,
                           dividend_type: str = 'front') -> Optional[pd.DataFrame]:
        """
        获取股票K线历史数据
        根据官方文档，使用get_market_data_ex方法
        
        Args:
            stock_code: 股票代码，如 '000001.SZ' 或 '000001'
            period: 数据周期，支持 '1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M'
            start_time: 开始时间，格式 'YYYYMMDD' 或 'YYYY-MM-DD'
            end_time: 结束时间，格式 'YYYYMMDD' 或 'YYYY-MM-DD'
            count: 返回数据条数，-1表示返回所有数据
            dividend_type: 复权类型，'front'前复权, 'back'后复权, 'none'不复权
            
        Returns:
            pd.DataFrame: K线数据，包含时间、开高低收成交量等信息
        """
        try:
            # 格式化股票代码
            formatted_code = self.format_stock_code(stock_code)
            
            # 先下载历史数据到本地
            if not self.download_history_data(formatted_code, period):
                self.logger.warning(f"下载 {formatted_code} 历史数据失败，尝试直接获取")
            
            # 构建字段列表
            field_list = []  # 空列表表示获取所有字段
            
            # 使用官方推荐的get_market_data_ex方法
            self.logger.info(f"正在获取 {formatted_code} 的 {period} K线数据...")
            
            data = xtdata.get_market_data_ex(
                field_list=field_list,
                stock_list=[formatted_code], 
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type=dividend_type,
                fill_data=True
            )
            
            if not data or formatted_code not in data:
                self.logger.warning(f"未获取到 {formatted_code} 的数据")
                return None
                
            # 获取该股票的数据
            stock_data = data[formatted_code]
            
            if not stock_data:
                self.logger.warning(f"{formatted_code} 返回的数据为空")
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(stock_data)
            
            if df.empty:
                self.logger.warning(f"{formatted_code} DataFrame为空")
                return None
            
            # 重置索引，将时间作为列
            df.reset_index(inplace=True)
            
            # 重命名列
            column_rename = {
                'time': '时间',
                'open': '开盘价',
                'high': '最高价', 
                'low': '最低价',
                'close': '收盘价',
                'volume': '成交量',
                'amount': '成交额'
            }
            
            # 只重命名存在的列
            existing_columns = {k: v for k, v in column_rename.items() if k in df.columns}
            df.rename(columns=existing_columns, inplace=True)
            
            # 添加股票代码列
            df.insert(0, '证券代码', formatted_code)
            
            # 格式化时间列
            if '时间' in df.columns:
                df['时间'] = pd.to_datetime(df['时间'])
                
            # 计算涨跌幅
            if '收盘价' in df.columns and len(df) > 1:
                df['昨收价'] = df['收盘价'].shift(1)
                df['涨跌额'] = df['收盘价'] - df['昨收价']
                df['涨跌幅'] = (df['涨跌额'] / df['昨收价'] * 100).round(2)
                
            self.logger.info(f"成功获取 {formatted_code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {stock_code} K线数据失败: {str(e)}")
            return None
    
    def download_financial_data(self, stock_codes: List[str] = None):
        """
        下载财务数据到本地
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载所有
        """
        try:
            if stock_codes:
                formatted_codes = [self.format_stock_code(code) for code in stock_codes]
                xtdata.download_financial_data(formatted_codes)
            else:
                xtdata.download_financial_data()
            self.logger.info("财务数据下载完成")
        except Exception as e:
            self.logger.error(f"下载财务数据失败: {str(e)}")
    
    def download_sector_data(self):
        """下载板块数据到本地"""
        try:
            xtdata.download_sector_data()
            self.logger.info("板块数据下载完成")
        except Exception as e:
            self.logger.error(f"下载板块数据失败: {str(e)}")

    def get_multiple_stocks_data(self,
                               stock_codes: List[str],
                               period: str = '1d',
                               start_time: str = '',
                               end_time: str = '',
                               count: int = -1,
                               dividend_type: str = 'front') -> dict:
        """
        批量获取多只股票的历史数据
        
        Args:
            stock_codes: 股票代码列表
            period: 数据周期
            start_time: 开始时间
            end_time: 结束时间
            count: 返回数据条数
            dividend_type: 复权类型
            
        Returns:
            dict: {股票代码: DataFrame} 格式的数据字典
        """
        result = {}
        
        # 先批量下载数据
        formatted_codes = [self.format_stock_code(code) for code in stock_codes]
        
        self.logger.info(f"开始批量下载 {len(formatted_codes)} 只股票的历史数据...")
        for code in formatted_codes:
            self.download_history_data(code, period)
        
        # 然后获取数据
        for code in stock_codes:
            df = self.get_stock_kline_data(
                stock_code=code,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type=dividend_type
            )
            
            if df is not None:
                result[code] = df
                
        self.logger.info(f"批量获取完成，成功获取 {len(result)}/{len(stock_codes)} 只股票数据")
        return result
    
    def get_index_data(self, index_code: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取指数数据
        
        Args:
            index_code: 指数代码，如 '000001.SH'(上证指数), '399001.SZ'(深证成指)
            **kwargs: 其他参数，与get_stock_kline_data相同
            
        Returns:
            pd.DataFrame: 指数数据
        """
        return self.get_stock_kline_data(index_code, **kwargs)
    
    def get_etf_data(self, etf_code: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取ETF数据
        
        Args:
            etf_code: ETF代码，如 '510300.SH'(沪深300ETF)
            **kwargs: 其他参数，与get_stock_kline_data相同
            
        Returns:
            pd.DataFrame: ETF数据
        """
        return self.get_stock_kline_data(etf_code, **kwargs)
    
    def get_sector_stocks(self, sector_name: str) -> Optional[List[str]]:
        """
        获取板块成份股
        
        Args:
            sector_name: 板块名称
            
        Returns:
            List[str]: 成份股代码列表
        """
        try:
            stocks = xtdata.get_stock_list_in_sector(sector_name)
            if stocks:
                self.logger.info(f"获取到板块 {sector_name} 成份股 {len(stocks)} 只")
            return stocks
        except Exception as e:
            self.logger.error(f"获取板块 {sector_name} 成份股失败: {str(e)}")
            return None
    
    def get_all_sectors(self) -> Optional[List[str]]:
        """
        获取所有板块列表
        
        Returns:
            List[str]: 板块名称列表
        """
        try:
            sectors = xtdata.get_sector_list()
            if sectors:
                self.logger.info(f"获取到板块列表 {len(sectors)} 个")
            return sectors
        except Exception as e:
            self.logger.error(f"获取板块列表失败: {str(e)}")
            return None
    
    def save_to_csv(self, df: pd.DataFrame, filename: str, encoding: str = 'utf-8-sig'):
        """
        将数据保存为CSV文件
        
        Args:
            df: 要保存的DataFrame
            filename: 文件名
            encoding: 编码格式，默认utf-8-sig（Excel兼容）
        """
        try:
            df.to_csv(filename, index=False, encoding=encoding)
            self.logger.info(f"数据已保存至: {filename}")
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
    
    def save_to_excel(self, data_dict: dict, filename: str):
        """
        将多只股票数据保存到Excel文件的不同工作表
        
        Args:
            data_dict: {股票代码: DataFrame} 格式的数据字典
            filename: Excel文件名
        """
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                for code, df in data_dict.items():
                    # Excel工作表名称不能包含特殊字符
                    sheet_name = code.replace('.', '_')
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            self.logger.info(f"数据已保存至Excel文件: {filename}")
        except Exception as e:
            self.logger.error(f"保存Excel文件失败: {str(e)}")
    
    def get_latest_trading_date(self) -> str:
        """
        获取最新交易日期
        
        Returns:
            str: 最新交易日期，格式YYYYMMDD
        """
        try:
            # 使用上证指数获取最新交易日
            df = self.get_stock_kline_data('000001.SH', period='1d', count=1)
            if df is not None and not df.empty:
                latest_date = df['时间'].iloc[-1].strftime('%Y%m%d')
                return latest_date
        except Exception as e:
            self.logger.error(f"获取最新交易日期失败: {str(e)}")
        
        # 返回当前日期作为备选
        return datetime.now().strftime('%Y%m%d')


# 使用示例
if __name__ == "__main__":
    # 创建历史行情对象
    history_data = AStockHistoryData()
    
    # 示例1: 获取单只股票日线数据
    print("=== 示例1: 获取平安银行日线数据 ===")
    df_payh = history_data.get_stock_kline_data(
        stock_code='000001',  # 平安银行
        period='1d',
        count=30,  # 获取最近30天
        dividend_type='front'
    )
    
    if df_payh is not None:
        print(f"数据形状: {df_payh.shape}")
        print(df_payh.head())
        print(df_payh.tail())
    
    # 示例2: 获取多只股票数据
    print("\n=== 示例2: 获取多只股票数据 ===")
    stock_list = ['000001', '000002', '600519', '000858']
    multi_data = history_data.get_multiple_stocks_data(
        stock_codes=stock_list,
        period='1d',
        count=10
    )
    
    for code, df in multi_data.items():
        print(f"{code}: {len(df)} 条数据")
    
    # 示例3: 获取所有A股列表
    print("\n=== 示例3: 获取所有A股列表 ===")
    all_stocks = history_data.get_all_a_stock_list()
    print(f"获取到A股总数: {len(all_stocks)}")
    if all_stocks:
        print("前10只股票:", all_stocks[:10]) 