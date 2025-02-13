import calendar
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal

import pandas as pd


class DataFrequency(Enum):
    """
    数据频率枚举类，用于表示数据的分区类型。

    枚举值：
        yearly: 年分区，表示数据按年划分。
        monthly: 月分区，表示数据按月划分。
        daily: 日分区，表示数据按日划分。
    """
    yearly = 'yearly'  # 年分区，表示数据按年划分
    monthly = 'monthly'  # 月分区，表示数据按月划分
    daily = 'daily'  # 日分区，表示数据按日划分


class SaveType(Enum):
    """
    存储类型枚举类，用于表示数据的存储格式。

    枚举值：
        parquet: Parquet 格式
        pickle: Pickle 格式
    """
    parquet = 'parquet'
    pickle = 'pickle'


def get_partition(dt: datetime, data_freq: DataFrequency) -> str:
    """
    根据给定的日期和数据频率，生成对应的分区名称。

    Args:
        dt (datetime): 日期时间对象，表示需要分区的具体时间。
        data_freq (DataFrequency): 数据频率枚举值，表示分区的类型（年、月、日）。

    Returns:
        str: 分区名称，格式为年分区 YYYY、月分区YYYYMM 或日分区 YYYYMMDD
    """
    match data_freq:
        case DataFrequency.yearly:
            # 年分区：返回年份，格式为 YYYY
            return dt.strftime('%Y')
        case DataFrequency.monthly:
            # 月分区：返回年份和月份，格式为 YYYYMM
            return dt.strftime('%Y%m')
        case DataFrequency.daily:
            # 日分区：返回年份、月份和日期，格式为 YYYYMMDD
            return dt.strftime('%Y%m%d')


def get_partition_range(part_start: str, part_end: str, data_freq: DataFrequency) -> list[str]:
    """
    根据数据频率（年、月、日）生成从 start 到 end 的分区范围。

    参数:
        part_start (str): 分区范围的开始，格式为年 YYYY、月YYYYMM 或日 YYYYMMDD
        part_end (str): 分区范围的结束，格式与 part_start 相同。
        data_freq (DataFrequency): 数据频率枚举值，表示分区的类型（年、月、日）。

    返回:
        list[str]: 分区范围的列表，格式与输入一致。
    """
    match data_freq:
        case DataFrequency.yearly:
            # 处理年分区
            year_start, year_end = int(part_start), int(part_end)
            return [str(year) for year in range(year_start, year_end + 1)]

        case DataFrequency.monthly:
            # 处理月分区
            date_format = "%Y%m"  # 日期格式为 YYYYMM
            freq = 'MS'  # 频率为每月的开始

        case DataFrequency.daily:
            # 处理日分区
            date_format = "%Y%m%d"  # 日期格式为 YYYYMMDD
            freq = 'D'  # 频率为每天

    # 统一处理月分区和日分区的逻辑
    start_date = pd.to_datetime(part_start, format=date_format)  # 将开始日期字符串转换为 datetime 对象
    end_date = pd.to_datetime(part_end, format=date_format)  # 将结束日期字符串转换为 datetime 对象
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)  # 生成日期范围
    return [date.strftime(date_format) for date in date_range]  # 将日期格式化为字符串并返回


def get_partition_start_end(partition_name: str, data_freq: DataFrequency) -> tuple[datetime, datetime]:
    """
    根据分区名称和数据类型频率，返回分区的起始时间和结束时间。

    Args:
        partition_name (str): 分区名称，格式为 YYYY、YYYYMM 或 YYYYMMDD。
        data_freq (DataFrequency): 数据频率，表示分区的类型（年、月、日）。

    Returns:
        tuple[datetime, datetime]: 分区的起始时间和结束时间。
    """
    # 从 partition_name 中提取年份
    year = int(partition_name[:4])

    # 处理年分区
    if data_freq == DataFrequency.yearly:
        # 起始时间：该年1月1日 00:00:00
        start = datetime(year=year, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone.utc)

        # 结束时间：该年12月31日 23:59:59
        end = datetime(year=year, month=12, day=31, hour=23, minute=59, second=59, tzinfo=timezone.utc)
        return start, end

    # 从 partition_name 中提取月份
    month = int(partition_name[4:6])

    # 处理月分区
    if data_freq == DataFrequency.monthly:
        # 起始时间：该月1日 00:00:00
        start = datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, tzinfo=timezone.utc)

        # 结束时间：该月最后一天 23:59:59
        # 使用 calendar.monthrange 获取该月的最后一天
        _, end_day = calendar.monthrange(year, month)
        end = datetime(year=year, month=month, day=end_day, hour=23, minute=59, second=59, tzinfo=timezone.utc)
        return start, end

    # 从 partition_name 中提取日期
    day = int(partition_name[6:8])

    # 处理日分区
    # 起始时间：该日 00:00:00
    start = datetime(year=year, month=month, day=day, hour=0, minute=0, second=0, tzinfo=timezone.utc)

    # 结束时间：该日 23:59:59
    end = datetime(year=year, month=month, day=day, hour=23, minute=59, second=59, tzinfo=timezone.utc)

    return start, end


class TSManager:
    """
    时间序列数据管理器，用于管理按时间分区的数据存储和读取。

    属性：
        TYPE_EXTENSIONS (dict): 存储类型与文件扩展名的映射。
        data_dir (Path): 数据存储目录。
        data_freq (DataFrequency): 数据分区频率（年、月、日）。
        save_type (SaveType): 数据存储格式 (Parquet 或 Pickle)。
        time_key (str): 时间列的名称，默认为 'candle_begin_time'。
    """
    TYPE_EXTENSIONS = {
        SaveType.parquet: 'pqt',  # Parquet 文件扩展名
        SaveType.pickle: 'pkl',  # Pickle 文件扩展名
    }

    def __init__(self,
                 data_dir: str | Path,
                 time_key: str = 'candle_begin_time',
                 data_freq: Literal['daily', 'monthly', 'yearly'] | DataFrequency = DataFrequency.monthly,
                 save_type: Literal['pickle', 'parquet'] | SaveType = SaveType.pickle):
        """
        初始化时间序列数据管理器。

        Args:
            data_dir (str | Path): 数据存储目录路径。
            time_key (str): 时间列的名称，默认为 'candle_begin_time'。
            data_freq (Literal['daily', 'monthly', 'yearly'] | DataFrequency): 数据分区频率，默认为 monthly (月分区)。
            save_type (Literal['pickle', 'parquet'] | SaveType): 数据存储格式，默认为 Pickle。
        """
        self.data_dir = Path(data_dir)  # 将数据目录转换为 Path 对象
        self.data_freq = DataFrequency(data_freq)  # 设置数据分区频率
        self.save_type = SaveType(save_type)  # 设置数据存储格式
        self.time_key = time_key  # 设置时间列名称

        # 创建数据目录（如果不存在）
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def format_data_file(self, partition_name: str) -> Path:
        """
        根据分区名称生成数据文件路径。

        Args:
            partition_name (str): 分区名称，格式为 YYYY、YYYYMM 或 YYYYMMDD。

        Returns:
            Path: 数据文件的完整路径。
        """
        ext = self.TYPE_EXTENSIONS[self.save_type]  # 获取文件扩展名
        filename = f'{partition_name}.{ext}'  # 生成文件名
        data_file = self.data_dir / filename  # 拼接文件路径
        return data_file

    def read_partition(self, partition_name: str) -> pd.DataFrame | None:
        """
        读取指定分区的数据。

        Args:
            partition_name (str): 分区名称，格式为 YYYY、YYYYMM 或 YYYYMMDD。

        Returns:
            pd.DataFrame | None: 读取的数据，如果文件不存在或读取失败则返回 None。
        """
        data_file = self.format_data_file(partition_name)  # 获取数据文件路径

        if not data_file.exists():  # 检查文件是否存在
            return None

        try:
            match self.save_type:
                case SaveType.parquet:
                    return pd.read_parquet(data_file)  # 读取 Parquet 文件
                case SaveType.pickle:
                    return pd.read_pickle(data_file)  # 读取 Pickle 文件
        except:
            data_file.unlink()  # 如果读取失败，删除损坏的文件
            return None

    def write_partition(self, partition_name: str, df: pd.DataFrame):
        """
        将数据写入指定分区。

        Args:
            partition_name (str): 分区名称，格式为 YYYY、YYYYMM 或 YYYYMMDD。
            df (pd.DataFrame): 要写入的数据。
        """
        data_file = self.format_data_file(partition_name)  # 获取数据文件路径

        if df.empty and data_file.exists():
            data_file.unlink()
            return

        match self.save_type:
            case SaveType.parquet:
                df.to_parquet(data_file)  # 写入 Parquet 文件
            case SaveType.pickle:
                df.to_pickle(data_file)  # 写入 Pickle 文件

    def list_partitions(self) -> list[str]:
        """
        列出所有分区的名称。

        Returns:
            list[str]: 分区名称列表，按字母顺序排序。
        """
        ext = self.TYPE_EXTENSIONS[self.save_type]  # 获取文件扩展名
        files = self.data_dir.glob(f'*.{ext}')  # 查找所有匹配的文件
        partition_names = sorted(f.stem for f in files)  # 提取分区名称并排序
        return partition_names

    def read_all(self) -> pd.DataFrame | None:
        """
        读取所有分区的数据并合并。

        Returns:
            pd.DataFrame: 合并后的数据，按时间列排序并去重。
        """
        partition_names = self.list_partitions()  # 获取所有分区名称
        dfs = [self.read_partition(partition_name) for partition_name in partition_names]  # 读取所有分区数据
        dfs = [df for df in dfs if df is not None]  # 过滤掉读取失败的分区

        if not dfs:
            return None

        df = pd.concat(dfs, ignore_index=True)  # 合并数据
        df.drop_duplicates(self.time_key, inplace=True, ignore_index=True)  # 去重
        df.sort_values(self.time_key, inplace=True, ignore_index=True)  # 按时间列排序
        return df

    def trim_partition(self, partition_name: str, dt_start: datetime, dt_end: datetime):
        """
        修剪指定分区的数据，只保留指定时间范围内的数据。
        时间范围的条件为: dt_start <= time_key < dt_end。

        Args:
            partition_name (str): 分区名称，格式为 YYYY、YYYYMM 或 YYYYMMDD。
            dt_start (datetime): 时间范围的起始时间。
            dt_end (datetime): 时间范围的结束时间。
        """
        df_part = self.read_partition(partition_name)  # 读取分区数据
        if df_part is None:  # 如果分区数据不存在，直接返回
            return
        # 过滤时间范围内的数据
        df_part = df_part[df_part[self.time_key].between(dt_start, dt_end, 'left')]
        self.write_partition(partition_name, df_part)  # 重新写入分区数据

    def trim(self, dt_start: datetime, dt_end: datetime):
        """
        修剪数据，只保留指定时间范围内的数据。
        使 dt_start <= time_key < dt_end

        Args:
            dt_start (datetime): 时间范围的起始时间。
            dt_end (datetime): 时间范围的结束时间。
        """
        partition_names = self.list_partitions()  # 获取所有分区名称
        for partition_name in partition_names:
            self.trim_partition(partition_name, dt_start, dt_end)

    def update_partition(self, partition_name: str, df: pd.DataFrame):
        """
        更新指定分区的数据。

        Args:
            partition_name (str): 分区名称，格式为 YYYY、YYYYMM 或 YYYYMMDD。
            df (pd.DataFrame): 包含新数据的数据框。
        """
        # 获取分区的起始时间和结束时间
        part_start, part_end = get_partition_start_end(partition_name, self.data_freq)
        # 过滤出属于当前分区时间范围内的数据
        df_update = df[df[self.time_key].between(part_start, part_end, 'left')]

        if df_update.empty:  # 如果没有新数据，直接返回
            return

        df_part = self.read_partition(partition_name)  # 读取现有分区数据
        if df_part is None:  # 如果分区不存在，直接写入新数据
            self.write_partition(partition_name, df_update)
            return

        # 合并现有数据和新数据，去重并排序
        df = pd.concat([df_part, df_update])
        df.drop_duplicates(self.time_key, keep='last', inplace=True, ignore_index=True)
        df.sort_values(self.time_key, inplace=True, ignore_index=True)

        # 写入更新后的数据
        self.write_partition(partition_name, df)

    def update(self, df: pd.DataFrame):
        """
        更新所有相关分区的数据。

        Args:
            df (pd.DataFrame): 包含新数据的数据框。
        """
        if df.empty:  # 如果数据为空，直接返回
            return

        # 获取新数据的最小时间和最大时间
        dt_min = df[self.time_key].min()
        dt_max = df[self.time_key].max()

        # 获取最小时间和最大时间对应的分区名称
        partition_min = get_partition(dt_min, self.data_freq)
        partition_max = get_partition(dt_max, self.data_freq)

        # 筛选出需要更新的分区
        partitions_update = get_partition_range(partition_min, partition_max, self.data_freq)
        # 更新每个相关分区
        for partition_name in partitions_update:
            self.update_partition(partition_name, df)
