import pandas as pd
from xtquant import xtdata
import pymysql
from datetime import datetime

# 设定一个标的列表
code_list = xtdata.get_stock_list_in_sector('沪深A股')
# 设定获取数据的周期
period = "1d"


# xtdata.download_history_data2(code_list, period=period)  # 增量下载行情数据（开高低收,等等）到本地

# 更多数据的下载方式可以通过数据字典查询

# 读取本地历史行情数据
history_data = xtdata.get_local_data(['amount'], code_list, period=period, start_time='20180409', end_time='20241129', count=-1,dividend_type ='back')


# 定义一个函数来计算每日amount最大的前五只股票的amount总和
def calculate_top_five_amount_sum(stock_data_dict):
    top_five_amount_sum = {}
    # 获取所有日期
    all_dates = set()
    for df in stock_data_dict.values():
        all_dates.update(df.index)

    for date in all_dates:
        # 创建一个临时DataFrame来存储所有股票在该日期的amount值
        temp_df = pd.DataFrame(index=stock_data_dict.keys(), columns=['amount'])
        for stock_code, df in stock_data_dict.items():
            if date in df.index and df.loc[date, 'amount']!= 0 and not pd.isna(df.loc[date, 'amount']):
                temp_df.loc[stock_code, 'amount'] =float(df.loc[date, 'amount'])
            else:
                # 如果该日期没有数据，填充为0
                temp_df.loc[stock_code, 'amount'] = float(0)

        # 合并所有股票在该日期的amount数据
        all_stocks_amount = pd.concat([temp_df['amount']], axis=1)
        # 计算amount总和并排序，取前五个
        # 对 DataFrame 按照 'amount' 字段降序排序
        df_sorted = all_stocks_amount.sort_values(by='amount', ascending=False)
        # 选择前五个股票
        top_five_stocks = df_sorted.head(5)
        # 累加前五个股票的 'amount' 值
        top_five_amount_sum[date] = top_five_stocks['amount'].sum()/100000000
    return top_five_amount_sum


# 使用函数进行计算
top_five_amount_sum = calculate_top_five_amount_sum(history_data)

db = pymysql.connect(host='axiba.idnmd.top', user='root', passwd='ilikecs123!', port=8306, db='quant')
cursor = db.cursor()
# 打印结果
for date, amount_sum in top_five_amount_sum.items():
    try:
        date_obj = datetime.strptime(str(date), "%Y%m%d")
        formatted_date = date_obj.strftime("%Y-%m-%d")

        # 定义查询语句
        select_query = """
        SELECT cj_turnover FROM a_cj
        WHERE cj_date = %s
        """

        # 执行查询
        cursor.execute(select_query, (formatted_date,))

        # 获取查询结果
        result = cursor.fetchone()
        cj_turnover = result[0]

        # 定义更新语句
        update_query = """
        UPDATE a_cj
        SET cj_top5 = %s, cj_top5_proportion = %s
        WHERE cj_date = %s
        """

        # 假设你有一些数据需要更新
        new_cj_top5_proportion = amount_sum/cj_turnover
        #保留小数点后4位
        new_cj_top5_proportion = round(new_cj_top5_proportion, 4)





        # 执行更新
        cursor.execute(update_query, (amount_sum, new_cj_top5_proportion, formatted_date))
        print(f"Date: {date}, Top Five Amount Sum: {amount_sum}")
    except Exception as e:
        print(e)
db.commit()
db.close()