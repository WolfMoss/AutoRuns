import requests
import datetime
import pymysql



def geturl(formatted_date):
    url = f"https://query.sse.com.cn/commonQuery.do?isPagination=true&sqlId=COMMON_SSE_ZQPZ_YSP_QQ_SJTJ_MRTJ_CX&tradeDate={formatted_date}&pageHelp.pageSize=25&pageHelp.cacheSize=1&pageHelp.pageNo=1&pageHelp.beginPage=1&pageHelp.endPage=1"
    payload = {}
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Cookie': 'ba17301551dcbaf9_gdp_session_id=dd7cee88-6434-4b44-857c-815c6b048270; gdp_user_id=gioenc-0cc458b2%2Cb789%2C59c9%2Cc06e%2Cc454gd35b2b3; ba17301551dcbaf9_gdp_session_id_sent=dd7cee88-6434-4b44-857c-815c6b048270; ba17301551dcbaf9_gdp_sequence_ids={%22globalKey%22:42%2C%22VISIT%22:2%2C%22PAGE%22:7%2C%22VIEW_CLICK%22:35}',
        'Referer': 'https://www.sse.com.cn/',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
        'sec-ch-ua': '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    return  response.json()

# 获取当前日期和时间
current_date = datetime.datetime.today() - datetime.timedelta(days=0)

db = pymysql.connect(host='axiba.idnmd.top', user='root', passwd='ilikecs123!', port=8306, db='quant')
cursor = db.cursor()

for day in range(1):

    # 将日期格式化为'YYYYMMDD'格式的字符串
    formatted_date = current_date.strftime('%Y%m%d')
    # 将日期向前推进一天
    current_date -= datetime.timedelta(days=1)

    resjson = geturl(formatted_date)
    if len(resjson['result'])<=0:
        continue

    for item in resjson['result']:
        item['LEAVES_PUT_QTY']=str(item['LEAVES_PUT_QTY']).replace(',','')
        item['LEAVES_CALL_QTY'] = str(item['LEAVES_CALL_QTY']).replace(',', '')
        item['PC_RATE']=float(item['LEAVES_PUT_QTY'])/float(item['LEAVES_CALL_QTY'])
        sql = f"INSERT INTO `quant`.`pcr`(`SECURITY_CODE`, `TRADE_DATE`, `SECURITY_ABBR`, `LEAVES_CALL_QTY`, `LEAVES_PUT_QTY`, `PC_RATE`) VALUES ('{item['SECURITY_CODE']}', '{item['TRADE_DATE']}', '{item['SECURITY_ABBR']}', '{item['LEAVES_CALL_QTY']}', '{item['LEAVES_PUT_QTY']}', '{item['PC_RATE']}')"
        # 执行 SQL 语句
        cursor.execute(sql)
        print('插入成功',sql)


db.commit()
db.close()