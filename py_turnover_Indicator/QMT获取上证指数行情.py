import pymysql
from xtquant import xtdata
from datetime import datetime

# # 下载指定合约历史行情
# xtdata.download_history_data('000001.SH', '1d', start_time='20180409', end_time='20241129')
# 获取指定合约历史行情
dic_df = xtdata.get_local_data(field_list = ['close'], stock_list = ['000001.SH'], period = '1d', start_time = '20180409', end_time = '20241129', count = -1, dividend_type = 'back', fill_data = True)

# 获取第一个值
df = list(dic_df.values())[0]

db = pymysql.connect(host='axiba.idnmd.top', user='root', passwd='ilikecs123!', port=8306, db='quant')
cursor = db.cursor()
# 按行遍历
for index, row in df.iterrows():
    date_obj = datetime.strptime(str(index), "%Y%m%d")
    formatted_date = date_obj.strftime("%Y-%m-%d")
    # 定义更新语句
    update_query = """
            UPDATE a_cj
            SET cj_szzs = %s
            WHERE cj_date = %s
            """


    # 执行更新
    cursor.execute(update_query, (row["close"], formatted_date))
    print(f'Index: {index}',f'close:{row["close"]}')

db.commit()
db.close()