from core.utils.path_kit import get_folder_path

# ====================================================================================================
# ** 基础配置 **
# - K线数量
# - 全局报错机器人通知
# - 本地存储路径
# ====================================================================================================
# Resample(1h) 周期 K 线数量，默认: 2000 小时
kline_count_1h = 2644
# 全局报错机器人通知
# - 创建企业微信机器人 参考帖子: https://bbs.quantclass.cn/thread/10975
# - 配置案例  https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxxxxxxxxxx
error_webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=b9312317-19d6-4f2a-b2c6-a8b27a4c19e3'
# 数据存放路径，默认在项目目录的data文件夹
storage_path = get_folder_path('data')

# ====================================================================================================
# ** 彩虹API服务配置 **
# - 目前支持使用API来更新`K线数据`，`CoinCap数据`
# - True表示开启False表示关闭
# - 只要有一个选项为True，就必须配置data_api的uuid和key
# ====================================================================================================
# 只要有一个配置为true，就必须配置data_api的uuid和key
use_api = {
    # **使用API来更新K线**
    # 会使用DATA API服务来更新K线
    'kline': True,

    # **使用API来更新市值数据**
    # 使用DATA API服务来更新CoinCap数据
    # 1. 需要手动历史市值数据数据，下载地址：https://www.quantclass.cn/data/coin/coin-cap
    # 2. 然后上传历史数据到 `storage_path -> coin_cap`之后，
    # 3. 再启动BMAC
    'coin_cap': True,
}
# 个人中心里面的葫芦id。（网址：https://www.quantclass.cn/login）
data_api_uuid = 'e1388f20d6a43ee4838520e8ab0f61c1'
# 个人中心里面的api_key配置。（网址：https://www.quantclass.cn/login）
data_api_key = '1L9Z9IL0ELWATTBOIPCF2GD5MD4D235T'

# ====================================================================================================
# ** 其他配置 **
# 系统参数，别动就别碰，不了解也没关系，也不需要了解，动手之前务必请教林奇
# ====================================================================================================
# 如果使用代理 注意替换IP和Port
proxy = None
# proxy = 'http://127.0.0.1:7890'  # 如果你用clash的话

# 只更新部分分钟偏移（hour_offset），可有效节省你的硬盘，
# 当然如果你配置了新的hour_offset策略，需要同步更新数据中心这边的配置
# 默认所有的offset都需要更新，kline_count_1h=25000，大概占用68GB存储
enabled_hour_offsets = ('25m',)

# Base 周期，通常设为 5m，与 Data API 一致
base_interval = '5m'

# Resample 周期，通常设为 1h，与 Data API 一致
resample_interval = '1h'

# 是否使用资金费
funding_rate = True

# 是否生成预处理数据
preprocess = True

# 预处理数据近期 K 线条数（仓位管理框架）
preprocess_num_recent = 24

# 预处理数据拆分 Batch 大小
preprocess_num_batch = 64
