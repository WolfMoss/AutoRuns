import json
import time
import requests
import pymysql
import akshare as ak

stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
# 筛选成交额前五的数据
top_five = stock_zh_a_spot_em_df.nlargest(5, '成交额')
# 累加前五个数据的成交额
amount_sum = float(top_five['成交额'].sum())/100000000
print(amount_sum)


#生成时间戳例如1732807638776
def get_timestamp():
    return int(round(time.time() * 1000))


def method_name(shc):
    global response
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://www.jisilu.cn",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://www.jisilu.cn/data/idx_performance/stat/",
        "sec-ch-ua": "\"Chromium\";v=\"124\", \"Microsoft Edge\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {
        "kbz_newcookie": "1",
        "kbzw__Session": "dmfnp144991fg5v30hlmqvhh43",
        "Hm_lvt_164fe01b1433a19b507595a43bf58262": "1732720582,1732806400",
        "HMACCOUNT": "FC33479CA76191DA",
        "Hm_lpvt_164fe01b1433a19b507595a43bf58262": "1732807639"
    }
    url = "https://www.jisilu.cn/data/idx_performance/stat_list/"
    params = {
        "___jsl": f"LST___t={shc}"
    }
    data = {
        "rp": "22",
        "page": "1"
    }
    response = requests.post(url, headers=headers, cookies=cookies, params=params, data=data)
    return json.loads(response.text)

res = method_name(get_timestamp())
cj_date = res["rows"][0]["id"]
cj_turnover=float(res["rows"][0]["cell"]["trade_amount"])
print(res["rows"][0]["id"],res["rows"][0]["cell"]["trade_amount"])

# 假设你有一些数据需要更新
new_cj_top5_proportion = amount_sum / cj_turnover
# 保留小数点后4位
new_cj_top5_proportion = round(new_cj_top5_proportion, 4)

db = pymysql.connect(host='axiba.idnmd.top', user='root', passwd='ilikecs123!', port=8306, db='quant')
cursor = db.cursor()
sql = f"INSERT INTO `quant`.`a_cj`(`cj_date`, `cj_turnover`,`cj_top5`,`cj_top5_proportion`) VALUES ('{cj_date}', '{cj_turnover}', '{amount_sum}', '{new_cj_top5_proportion}')"
# 执行 SQL 语句
cursor.execute(sql)
print('插入成功', sql)
db.commit()
db.close()