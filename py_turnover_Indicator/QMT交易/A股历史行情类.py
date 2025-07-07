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
        根据官方文档，需要先下载板块数据
        
        Returns:
            List[str]: A股股票代码列表
        """
        try:
            # 根据官方文档，先下载板块分类信息
            self.logger.info("正在下载板块数据...")
            try:
                xtdata.download_sector_data()
                self.logger.info("板块数据下载完成")
            except Exception as e:
                self.logger.warning(f"下载板块数据失败: {str(e)}，尝试使用缓存数据")
            
            # 方法1: 尝试获取沪深A股板块
            try:
                stocks = xtdata.get_stock_list_in_sector('沪深A股')
                if stocks and len(stocks) > 0:
                    self.logger.info(f"通过沪深A股板块获取到 {len(stocks)} 只股票")
                    return stocks
            except Exception as e:
                self.logger.warning(f"获取沪深A股板块失败: {str(e)}")
            
            # 方法2: 尝试获取所有A股相关板块
            try:
                # 获取板块列表
                sectors = xtdata.get_sector_list()
                self.logger.info(f"获取到 {len(sectors) if sectors else 0} 个板块")
                
                if sectors:
                    # 查找A股相关板块
                    a_stock_sectors = []
                    for sector in sectors:
                        if any(keyword in sector for keyword in ['A股', '沪深', '上海A股', '深圳A股', '全部A股']):
                            a_stock_sectors.append(sector)
                    
                    self.logger.info(f"找到A股相关板块: {a_stock_sectors}")
                    
                    # 从这些板块中获取股票
                    all_stocks = []
                    for sector in a_stock_sectors:
                        try:
                            sector_stocks = xtdata.get_stock_list_in_sector(sector)
                            if sector_stocks:
                                all_stocks.extend(sector_stocks)
                                self.logger.info(f"从板块 {sector} 获取到 {len(sector_stocks)} 只股票")
                        except Exception as e:
                            self.logger.warning(f"获取板块 {sector} 成分股失败: {str(e)}")
                    
                    if all_stocks:
                        # 去重
                        all_stocks = list(set(all_stocks))
                        self.logger.info(f"通过板块合并获取到 {len(all_stocks)} 只股票")
                        return all_stocks
            except Exception as e:
                self.logger.warning(f"通过板块获取股票失败: {str(e)}")
            
            # 方法3: 分别获取沪市和深市股票
            try:
                all_stocks = []
                
                # 尝试获取上海A股
                try:
                    sh_stocks = xtdata.get_stock_list_in_sector('上海A股')
                    if sh_stocks:
                        all_stocks.extend(sh_stocks)
                        self.logger.info(f"获取上海A股 {len(sh_stocks)} 只")
                except:
                    pass
                
                # 尝试获取深圳A股
                try:
                    sz_stocks = xtdata.get_stock_list_in_sector('深圳A股')
                    if sz_stocks:
                        all_stocks.extend(sz_stocks)
                        self.logger.info(f"获取深圳A股 {len(sz_stocks)} 只")
                except:
                    pass
                
                if all_stocks:
                    # 去重
                    all_stocks = list(set(all_stocks))
                    self.logger.info(f"通过分板块获取到 {len(all_stocks)} 只股票")
                    return all_stocks
            except Exception as e:
                self.logger.warning(f"分板块获取股票失败: {str(e)}")
            
            # 方法4: 使用合约信息获取股票（最后备选方案）
            try:
                self.logger.info("尝试通过合约信息获取A股列表...")
                # 这个方法需要遍历所有合约，会比较慢
                # 这里我们只生成一些常见的A股代码作为示例
                sample_stocks = []
                
                # 生成一些示例股票代码用于测试
                for prefix in ['000', '001', '002', '003', '300']:  # 深圳
                    for i in range(1, 100):  # 生成前100个
                        code = f"{prefix}{i:03d}.SZ"
                        sample_stocks.append(code)
                
                for prefix in ['600', '601', '603', '605', '688']:  # 上海
                    for i in range(1, 100):  # 生成前100个
                        code = f"{prefix}{i:03d}.SH"
                        sample_stocks.append(code)
                
                self.logger.warning(f"使用示例股票代码 {len(sample_stocks)} 只，这可能不是完整列表")
                return sample_stocks[:500]  # 限制数量避免过多
                
            except Exception as e:
                self.logger.error(f"生成示例股票代码失败: {str(e)}")
            
            # 如果所有方法都失败，返回空列表
            self.logger.error("所有获取A股列表的方法都失败")
            return []
            
        except Exception as e:
            self.logger.error(f"获取A股列表时发生未知错误: {str(e)}")
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
        获取股票K线数据
        根据官方文档使用get_market_data接口
        
        Args:
            stock_code: 股票代码
            period: 数据周期，支持 '1d', '1w', '1m', '5m', '1h' 等
            start_time: 开始时间，格式如 '20231201'
            end_time: 结束时间，格式如 '20231231'
            count: 返回数据条数，-1表示全部
            dividend_type: 复权类型 'none'(不复权), 'front'(前复权), 'back'(后复权)
            
        Returns:
            pd.DataFrame: K线数据，包含时间、开高低收成交量等信息
        """
        try:
            # 格式化股票代码
            formatted_code = self.format_stock_code(stock_code)
            
            # 先下载历史数据到本地
            if not self.download_history_data(formatted_code, period):
                self.logger.warning(f"下载 {formatted_code} 历史数据失败，尝试直接获取")
            
            # 根据官方文档，使用get_market_data获取数据
            # 参数：field_list=[], stock_list=[], period='1d', start_time='', end_time='', count=-1, dividend_type='none', fill_data=True
            data = xtdata.get_market_data(
                field_list=[],  # 空列表表示获取全部字段
                stock_list=[formatted_code],  # 股票代码列表
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type=dividend_type,
                fill_data=True
            )
            
            # 根据官方文档，对于K线数据返回格式为：dict { field1: DataFrame, field2: DataFrame, ... }
            if not data:
                self.logger.warning(f"未获取到 {formatted_code} 的数据")
                return None
            
            # 检查返回的数据结构
            if not isinstance(data, dict):
                self.logger.error(f"{formatted_code} 返回数据格式不正确，期望dict，实际: {type(data)}")
                return None
            
            # 根据官方文档，每个字段对应的DataFrame: index为stock_list，columns为time_list
            # 我们需要提取该股票的数据并转置，使时间成为行索引
            
            result_data = {}
            time_index = None
            
            for field, df_field in data.items():
                if isinstance(df_field, pd.DataFrame) and not df_field.empty:
                    # 检查股票代码是否在DataFrame的index中
                    if formatted_code in df_field.index:
                        # 提取该股票的数据（这是一个Series，index是时间）
                        stock_series = df_field.loc[formatted_code]
                        
                        # 如果这是第一个字段，保存时间索引
                        if time_index is None:
                            time_index = stock_series.index
                        
                        # 将Series转换为适当的数据类型并存储
                        result_data[field] = stock_series.values
                    else:
                        self.logger.warning(f"股票 {formatted_code} 不在字段 {field} 的数据中")
            
            if not result_data or time_index is None:
                self.logger.warning(f"{formatted_code} 没有有效的数据字段")
                return None
            
            # 创建DataFrame，使用时间作为索引
            df = pd.DataFrame(result_data, index=time_index)
            
            if df.empty:
                self.logger.warning(f"{formatted_code} DataFrame为空")
                return None
            
            # 重置索引，将时间作为列
            df.reset_index(inplace=True)
            
            # 重命名列
            column_rename = {
                'index': '时间',
                'time': '时间',
                'open': '开盘价',
                'high': '最高价', 
                'low': '最低价',
                'close': '收盘价',
                'volume': '成交量',
                'amount': '成交额',
                'preClose': '前收价',
                'suspendFlag': '停牌标记'
            }
            
            # 只重命名存在的列
            existing_columns = {k: v for k, v in column_rename.items() if k in df.columns}
            df.rename(columns=existing_columns, inplace=True)
            
            # 添加股票代码列
            df.insert(0, '证券代码', formatted_code)
            
            # 格式化时间列
            if '时间' in df.columns:
                try:
                    df['时间'] = pd.to_datetime(df['时间'])
                except Exception as e:
                    self.logger.warning(f"时间格式转换失败: {str(e)}")
                    
            # 计算涨跌幅
            if '收盘价' in df.columns and len(df) > 1:
                # 使用前收价计算涨跌幅，如果没有前收价则用前一日收盘价
                if '前收价' in df.columns:
                    df['昨收价'] = df['前收价']
                else:
                    df['昨收价'] = df['收盘价'].shift(1)
                
                # 计算涨跌额和涨跌幅，处理可能的除零错误
                df['涨跌额'] = df['收盘价'] - df['昨收价']
                
                # 避免除零错误
                valid_mask = (df['昨收价'] != 0) & pd.notna(df['昨收价'])
                df['涨跌幅'] = 0.0
                df.loc[valid_mask, '涨跌幅'] = (df.loc[valid_mask, '涨跌额'] / df.loc[valid_mask, '昨收价'] * 100).round(2)
                
            self.logger.info(f"成功获取 {formatted_code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {stock_code} K线数据失败: {str(e)}")
            return None
    
    def download_financial_data(self, stock_codes: List[str] = None):
        """
        下载财务数据到本地
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载A股列表前100只股票的财务数据
        """
        try:
            if stock_codes:
                formatted_codes = [self.format_stock_code(code) for code in stock_codes]
                xtdata.download_financial_data(formatted_codes)
                self.logger.info(f"财务数据下载完成，共{len(formatted_codes)}只股票")
            else:
                # 如果没有指定股票列表，获取A股前100只作为示例
                self.logger.info("未指定股票列表，获取A股前100只股票的财务数据...")
                all_stocks = self.get_all_a_stock_list()
                if all_stocks:
                    sample_stocks = all_stocks[:100]  # 取前100只作为示例
                    xtdata.download_financial_data(sample_stocks)
                    self.logger.info(f"财务数据下载完成，共{len(sample_stocks)}只股票")
                else:
                    self.logger.warning("无法获取A股列表，跳过财务数据下载")
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