# config.json - Freqtrade配置文件
{
    "max_open_trades": 5,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "dry_run_wallet": 1000,
    "cancel_open_orders_on_exit": false,
    "trailing_stop": false,
    "trailing_stop_positive": 0.01,
    "trailing_stop_positive_offset": 0.0,
    "trailing_only_offset_is_reached": false,
    "minimal_roi": {
        "0": 0.10,
        "30": 0.05,
        "60": 0.02
    },
    "stoploss": -0.10,
    "timeframe": "1h",
    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": [
            "DOGE/USDT",
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT"
        ],
        "pair_blacklist": []
    },
    "pairlists": [
        {"method": "StaticPairList"}
    ],
    "datadir": "user_data/data",
    "user_data_dir": "user_data"
} 