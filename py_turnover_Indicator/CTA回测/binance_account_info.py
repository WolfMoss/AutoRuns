import ccxt

def main():
    # 创建币安交易所实例，使用你的 API 密钥和秘密
    exchange = ccxt.binance({
        'apiKey': 'bprxnRLbw88WiazXomrqnwNBokfkimAeZDBRjCQIjxla3VF2tde1muVjDAATWWIp',  # 替换为你的 API 密钥
        'secret': 'htPwvos5egbLLOTbekICD8v6iGujx8DF1Thfl1rljBokLLXfPrWxOrCwHZnwb3dk',  # 替换为你的 API 秘密
        'enableRateLimit': True,  # 启用请求频率限制
    })

    try:
        # 获取账户信息
        print("正在获取账户信息...")
        account_info = exchange.fetch_balance()  # 获取账户余额信息
        print("账户信息:")
        print(account_info)

        # 获取账户的交易信息
        print("正在获取交易信息...")
        trades = exchange.fetch_my_trades()  # 获取账户的交易记录
        print("交易记录:")
        for trade in trades:
            print(trade)

    except Exception as e:
        print(f"获取账户信息时发生错误: {e}")

if __name__ == '__main__':
    main() 