# -*- coding: utf-8 -*-
"""
回测网页版 | 邢不行 | 2025分享会
author: 邢不行
微信: xbx6660
"""
# 调试数据的时候用，非开发需要请保持：False
is_debug = False  # 调试模式，数据默认都放在 data 目录中

# B 圈产品列表
product_list = ['coin-binance-swap-candle-csv-1h', 'coin-binance-candle-csv-1h', 'coin-cap']

# B 圈产品中文名称
product_display_name_dict = {
    'coin-binance-swap-candle-csv-1h': '永续合约1小时数据-币对分类',
    'coin-binance-candle-csv-1h': '现货1小时数据-币对分类',
    'coin-binance-spot-swap-preprocess-pkl-1h': 'B圈预处理数据',
    'coin-cap': '市值数据(BN币对)',
}
