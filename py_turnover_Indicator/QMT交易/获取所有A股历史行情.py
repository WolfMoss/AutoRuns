# -*-coding:utf-8-*-
"""
获取所有A股历史行情数据并保存到CSV文件
使用A股历史行情类批量获取数据
根据xtquant官方文档：https://dict.thinktrader.net/nativeApi/code_examples.html
"""
import os
import time
from datetime import datetime, timedelta
from A股历史行情类 import AStockHistoryData
from typing import List, Dict, Any
import pandas as pd

try:
    from xtquant import xtdata
    print("xtquant库导入成功")
except ImportError as e:
    print(f"xtquant库导入失败: {e}")
    print("请确保已安装QMT客户端并配置xtquant库")
    exit(1)


class AllAStockDataDownloader:
    """所有A股历史行情数据下载器"""
    
    def __init__(self, data_dir: str = "datas"):
        """
        初始化下载器
        
        Args:
            data_dir: 数据保存目录
        """
        self.data_dir = data_dir
        self.stock_data = AStockHistoryData()
        self.logger = self.stock_data.logger  # 使用相同的logger
        self.create_data_directory()
        
    def create_data_directory(self):
        """创建数据保存目录"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"创建数据目录: {self.data_dir}")
        else:
            print(f"数据目录已存在: {self.data_dir}")
    
    def download_basic_data(self):
        """
        下载基础数据（财务数据、板块数据等）
        根据官方文档，需要先下载这些基础数据
        """
        print("正在下载基础数据...")
        try:
            # 下载财务数据
            print("- 下载财务数据...")
            self.stock_data.download_financial_data()
            
            # 下载板块数据  
            print("- 下载板块数据...")
            self.stock_data.download_sector_data()
            
            print("基础数据下载完成")
            
        except Exception as e:
            print(f"下载基础数据失败: {str(e)}")

    def download_stock_data(self, 
                          stock_code: str,
                          period: str = '1d',
                          count: int = -1,
                          days_back: int = 365) -> bool:
        """
        下载单只股票历史数据
        
        Args:
            stock_code: 股票代码
            period: 数据周期
            count: 获取条数，-1表示所有
            days_back: 如果count为-1，往前取多少天
            
        Returns:
            bool: 下载是否成功
        """
        try:
            formatted_code = self.stock_data.format_stock_code(stock_code)
            
            # 先下载历史数据到本地（根据官方文档要求）
            print(f"  - 下载 {formatted_code} 历史数据到本地...")
            download_success = self.stock_data.download_history_data(formatted_code, period)
            
            if not download_success:
                print(f"  ✗ {formatted_code} 历史数据下载失败")
                return False
            
            # 获取股票数据
            print(f"  - 获取 {formatted_code} K线数据...")
            
            # 如果指定了天数而不是条数，计算时间范围
            start_time = ''
            end_time = ''
            if count == -1 and days_back > 0:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                start_time = start_date.strftime('%Y%m%d')
                end_time = end_date.strftime('%Y%m%d')
            
            df = self.stock_data.get_stock_kline_data(
                stock_code=formatted_code,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type='front'  # 前复权
            )
            
            if df is not None and not df.empty:
                # 生成文件名
                clean_code = formatted_code.replace('.', '_')
                if start_time and end_time:
                    filename = f"{clean_code}_{period}_{start_time}_{end_time}.csv"
                else:
                    today = datetime.now().strftime('%Y%m%d')
                    filename = f"{clean_code}_{period}_count{count}_{today}.csv"
                    
                filepath = os.path.join(self.data_dir, filename)
                
                # 保存为CSV
                self.stock_data.save_to_csv(df, filepath)
                print(f"  ✓ {formatted_code} 数据已保存: {filename} ({len(df)} 条记录)")
                return True
            else:
                print(f"  ✗ {formatted_code} 未获取到数据")
                return False
                
        except Exception as e:
            print(f"  ✗ {stock_code} 下载失败: {str(e)}")
            return False
    
    def download_all_stocks_data(self,
                                mode: str = 'example',
                                custom_list: List[str] = None,
                                period: str = '1d',
                                start_date: str = '',
                                end_date: str = '',
                                specified_stocks: List[str] = None) -> Dict[str, Any]:
        """
        批量下载A股历史数据
        根据官方文档修正API调用
        
        Args:
            mode: 下载模式 'all'全部, 'example'示例, 'custom'自定义, 'specified'指定股票
            custom_list: 自定义股票列表
            period: 数据周期
            start_date: 开始日期
            end_date: 结束日期  
            specified_stocks: 指定股票列表
            
        Returns:
            Dict: 下载结果统计
        """
        start_time = time.time()
        
        # 初始化结果统计
        result = {
            'success_count': 0,
            'failed_count': 0,
            'failed_stocks': [],
            'success_stocks': [],
            'total_time': 0,
            'saved_files': []
        }
        
        try:
            # 根据官方文档，先下载板块数据
            self.logger.info("开始下载任务，首先下载板块数据...")
            try:
                self.stock_data.download_sector_data()
                self.logger.info("板块数据下载完成")
            except Exception as e:
                self.logger.warning(f"下载板块数据失败: {str(e)}")
            
            # 获取股票列表
            if mode == 'all':
                stock_list = self.stock_data.get_all_a_stock_list()
                self.logger.info(f"全量模式：获取到 {len(stock_list)} 只A股")
            elif mode == 'example':
                # 示例模式：获取前50只股票作为示例
                all_stocks = self.stock_data.get_all_a_stock_list()
                stock_list = all_stocks[:50] if all_stocks else []
                self.logger.info(f"示例模式：选择前 {len(stock_list)} 只股票进行测试")
            elif mode == 'custom' and custom_list:
                stock_list = custom_list
                self.logger.info(f"自定义模式：共 {len(stock_list)} 只股票")
            elif mode == 'specified' and specified_stocks:
                stock_list = specified_stocks
                self.logger.info(f"指定股票模式：共 {len(stock_list)} 只股票")
            else:
                self.logger.error("无效的下载模式或缺少股票列表")
                return result
            
            if not stock_list:
                self.logger.error("未获取到股票列表")
                return result
            
            self.logger.info(f"开始批量下载 {len(stock_list)} 只股票的历史数据...")
            
            # 批量下载
            for i, stock_code in enumerate(stock_list, 1):
                try:
                    self.logger.info(f"进度 [{i}/{len(stock_list)}] 正在处理: {stock_code}")
                    
                    # 获取K线数据 - 使用修正后的API
                    df = self.stock_data.get_stock_kline_data(
                        stock_code=stock_code,
                        period=period,
                        start_time=start_date,
                        end_time=end_date,
                        count=-1,
                        dividend_type='front'
                    )
                    
                    if df is not None and not df.empty:
                        # 保存到CSV文件
                        try:
                            # 创建文件名
                            formatted_code = stock_code.replace('.', '_')
                            current_date = datetime.now().strftime('%Y%m%d')
                            filename = f"{formatted_code}_{period}_{current_date}.csv"
                            file_path = os.path.join(self.data_dir, filename)
                            
                            # 保存到CSV
                            df.to_csv(file_path, index=False, encoding='utf-8-sig')
                            
                            result['success_count'] += 1
                            result['success_stocks'].append(stock_code)
                            result['saved_files'].append(filename)
                            self.logger.info(f"✓ {stock_code} 数据保存成功: {filename}")
                        except Exception as save_error:
                            result['failed_count'] += 1
                            result['failed_stocks'].append(stock_code)
                            self.logger.error(f"✗ {stock_code} 数据保存失败: {str(save_error)}")
                    else:
                        result['failed_count'] += 1
                        result['failed_stocks'].append(stock_code)
                        self.logger.warning(f"✗ {stock_code} 未获取到有效数据")
                    
                    # 添加延时避免请求过于频繁
                    if i % 10 == 0:
                        self.logger.info(f"已处理 {i} 只股票，暂停 1 秒...")
                        time.sleep(1)
                        
                except Exception as e:
                    result['failed_count'] += 1
                    result['failed_stocks'].append(stock_code)
                    self.logger.error(f"✗ {stock_code} 处理失败: {str(e)}")
                    continue
            
            # 统计结果
            result['total_time'] = time.time() - start_time
            
            self.logger.info("=" * 60)
            self.logger.info("批量下载完成!")
            self.logger.info(f"总耗时: {result['total_time']:.2f} 秒")
            self.logger.info(f"成功: {result['success_count']} 只")
            self.logger.info(f"失败: {result['failed_count']} 只")
            self.logger.info(f"成功率: {result['success_count']/(result['success_count']+result['failed_count'])*100:.1f}%")
            
            if result['failed_stocks']:
                self.logger.warning(f"失败股票: {result['failed_stocks'][:10]}{'...' if len(result['failed_stocks']) > 10 else ''}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"批量下载过程中发生错误: {str(e)}")
            result['total_time'] = time.time() - start_time
            return result
    
    def download_sample_stocks(self, sample_size: int = 10):
        """
        下载部分股票数据作为示例
        
        Args:
            sample_size: 示例股票数量
        """
        print(f"=== 下载 {sample_size} 只股票作为示例 ===")
        
        # 下载基础数据
        self.download_basic_data()
        
        print("\n获取股票列表...")
        stock_list = self.stock_data.get_all_a_stock_list()
        if stock_list:
            # 取前面一部分股票作为示例
            sample_stocks = stock_list[:sample_size]
            
            print(f"开始下载示例股票: {sample_stocks}")
            
            success_count = 0
            for i, stock_code in enumerate(sample_stocks):
                print(f"\n[{i+1}/{len(sample_stocks)}] 正在处理 {stock_code}...")
                
                success = self.download_stock_data(
                    stock_code=stock_code,
                    period='1d',
                    count=100,  # 示例只下载100条数据
                    days_back=150
                )
                
                if success:
                    success_count += 1
                
                time.sleep(0.3)  # 示例间隔稍短
            
            print(f"\n=== 示例下载完成 ===")
            print(f"成功下载: {success_count}/{len(sample_stocks)} 只股票")
            print(f"数据保存在: {os.path.abspath(self.data_dir)}")
        else:
            print("无法获取股票列表")
    
    def download_custom_stocks(self, stock_codes: list, period: str = '1d', days_back: int = 365):
        """
        下载指定股票列表的数据
        
        Args:
            stock_codes: 股票代码列表
            period: 数据周期
            days_back: 获取天数
        """
        print(f"=== 下载指定 {len(stock_codes)} 只股票数据 ===")
        print(f"股票列表: {stock_codes}")
        
        # 下载基础数据
        self.download_basic_data()
        
        success_count = 0
        for i, stock_code in enumerate(stock_codes):
            print(f"\n[{i+1}/{len(stock_codes)}] 正在处理 {stock_code}...")
            
            success = self.download_stock_data(
                stock_code=stock_code,
                period=period,
                count=-1,
                days_back=days_back
            )
            
            if success:
                success_count += 1
            
            time.sleep(0.3)
        
        print(f"\n=== 指定股票下载完成 ===")
        print(f"成功下载: {success_count}/{len(stock_codes)} 只股票")

    def save_to_csv(self, df: pd.DataFrame, stock_code: str, period: str) -> str:
        """
        保存DataFrame到CSV文件
        
        Args:
            df: 股票数据DataFrame
            stock_code: 股票代码
            period: 数据周期
            
        Returns:
            str: 保存的文件路径，失败返回None
        """
        try:
            # 创建文件名
            formatted_code = stock_code.replace('.', '_')
            current_date = datetime.now().strftime('%Y%m%d')
            filename = f"{formatted_code}_{period}_{current_date}.csv"
            file_path = os.path.join(self.data_dir, filename)
            
            # 保存到CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.debug(f"数据已保存到: {file_path}")
            return filename
            
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {str(e)}")
            return None


def main():
    """主函数"""
    print("=== A股历史行情数据批量下载工具 ===")
    print("基于xtquant官方文档实现")
    
    # 创建下载器
    downloader = AllAStockDataDownloader(data_dir="datas")
    
    print("\n请选择下载模式:")
    print("1. 下载所有A股数据（需要很长时间，建议分批进行）")
    print("2. 下载示例数据（10只股票）")
    print("3. 自定义下载参数")
    print("4. 下载指定股票列表")
    
    try:
        choice = input("请输入选择 (1/2/3/4): ").strip()
        
        if choice == '1':
            # 下载所有A股
            print("\n=== 下载所有A股数据 ===")
            print("⚠️  注意：这可能需要很长时间（数小时），建议:")
            print("   - 在网络稳定时运行")
            print("   - 确保QMT客户端正常运行")
            print("   - 有足够的磁盘空间")
            
            confirm = input("\n确认继续？(y/N): ").strip().lower()
            
            if confirm == 'y':
                period = input("数据周期 (1d/1h/1w/1M，默认1d): ").strip() or '1d'
                days_str = input("获取天数 (默认365): ").strip() or '365'
                days_back = int(days_str)
                
                # 计算时间范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                start_time_str = start_date.strftime('%Y%m%d')
                end_time_str = end_date.strftime('%Y%m%d')
                
                downloader.download_all_stocks_data(
                    mode='all',
                    period=period,
                    start_date=start_time_str,
                    end_date=end_time_str
                )
            else:
                print("已取消下载")
                
        elif choice == '2':
            # 下载示例数据
            sample_size = input("示例股票数量 (默认10): ").strip()
            sample_size = int(sample_size) if sample_size else 10
            downloader.download_sample_stocks(sample_size=sample_size)
            
        elif choice == '3':
            # 自定义下载
            print("\n=== 自定义下载参数 ===")
            period = input("数据周期 (1d/1h/1w/1M，默认1d): ").strip() or '1d'
            days_back = int(input("获取天数 (默认365): ").strip() or '365')
            batch_size = int(input("批次大小 (默认15): ").strip() or '15')
            delay = float(input("请求间隔秒数 (默认0.5): ").strip() or '0.5')
            
            downloader.download_all_stocks_data(
                mode='custom',
                custom_list=None,
                period=period,
                start_date='',
                end_date='',
                specified_stocks=None
            )
            
        elif choice == '4':
            # 下载指定股票
            print("\n=== 下载指定股票 ===")
            print("请输入股票代码，用逗号分隔（如: 000001,000002,600519）")
            codes_input = input("股票代码: ").strip()
            
            if codes_input:
                stock_codes = [code.strip() for code in codes_input.split(',')]
                period = input("数据周期 (1d/1h/1w/1M，默认1d): ").strip() or '1d'
                days_back = int(input("获取天数 (默认365): ").strip() or '365')
                
                # 计算时间范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                start_time_str = start_date.strftime('%Y%m%d')
                end_time_str = end_date.strftime('%Y%m%d')
                
                downloader.download_all_stocks_data(
                    mode='specified',
                    custom_list=None,
                    period=period,
                    start_date=start_time_str,
                    end_date=end_time_str,
                    specified_stocks=stock_codes
                )
            else:
                print("未输入股票代码")
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断下载")
        print("已下载的数据保存在 datas 目录中")
    except Exception as e:
        print(f"\n❌ 程序出错: {str(e)}")
        print("请检查:")
        print("1. QMT客户端是否正常运行")
        print("2. 网络连接是否稳定")
        print("3. xtquant库是否正确安装")


if __name__ == "__main__":
    main() 