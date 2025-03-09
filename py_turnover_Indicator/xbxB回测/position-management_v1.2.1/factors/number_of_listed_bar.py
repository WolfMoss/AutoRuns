def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    
    # 新增K线数量因子（从1开始递增）
    df[factor_name] = range(1, len(df) + 1)

    return df
