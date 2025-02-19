from datetime import datetime
import time
import traceback
import pymysql
import json
import requests

#获取北交所股票列表
def getBeiJiaoSuo():
    url = "https://51.push2.eastmoney.com/api/qt/clist/get?cb=jQuery112408724937567036273_1705859585055&pn=1&pz=300&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f3&fs=m:0+t:81+s:2048&fields=f12&_=1705859585056"

    payload = {}
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Cookie': 'qgqp_b_id=c3b2a1922a1dbd5aa35030c1f25ea597; websitepoptg_api_time=1705859149860; st_si=46807620978862; st_asi=delete; st_pvi=72842216484327; st_sp=2023-04-05%2023%3A25%3A32; st_inirUrl=https%3A%2F%2Fcn.bing.com%2F; st_sn=2; st_psi=20240122014557745-113200301321-2631077219',
        'Referer': 'https://quote.eastmoney.com/center/gridlist.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    data = json.loads(response.text[42:-2])
    return  data
#获取概念列表
def getGainian(count:str, page:str,riqi:str):

    url = "https://apphq.longhuvip.com/w1/api/index.php"

    payload = f"Order=1&st={count}&a=RealRankingInfo_W8&c=NewStockRanking&PhoneOSNew=2&DeviceID=ca883df0-1b0d-3b8a-9836-e07c2f69840d&index={page}&Date={riqi}&apiv=w21&Type=7&Filter=0&Ratio=6&"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G955N Build/NRD90M.G955NKSU1AQDC)',
      'Host': 'apphq.longhuvip.com',
      'Connection': 'Keep-Alive'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()

def getKplGn(code):
    url = "https://apparticle.longhuvip.com/w1/api/index.php"

    payload = f"a=GetIndex&apiv=w21&c=StockF10Basic&StockID={code}&PhoneOSNew=1&DeviceID=ca883df0-1b0d-3b8a-9836-e07c2f69840d&"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G955N Build/NRD90M.G955NKSU1AQDC)',
        'Host': 'apparticle.longhuvip.com',
        'Connection': 'Keep-Alive'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()




#获取北交所股票列表概念
def doBeiJiaoSuo(table_name):
    beiJiaoList = getBeiJiaoSuo()['data']['diff']

    db = pymysql.connect(host='64.110.105.176', user='root', passwd='ilikecs123!', port=3306, db='quant')
    cursor = db.cursor()
    cursor.execute(f"DELETE FROM {table_name}")


    for row in beiJiaoList:
        try:
            bjcode = row['f12']
            datajson = getKplGn(bjcode)
            Cname = datajson['Concept'][0]['CName']
            if Cname == '融资融券' and len(datajson['Concept']) > 1:
                Cname = datajson['Concept'][1]['CName']
            sql = f"INSERT INTO `quant`.`{table_name}`(`code`, `name`,  `conceptall`) VALUES ('{bjcode}', '{datajson['Company']['Name']}', '{Cname}')"
            cursor.execute(sql)
            print(f'code=[{bjcode}],name=[{Cname}]')
        except:
            continue


    db.commit()
    db.close()
#-------------------------主逻辑--------------------------------
if __name__ == "__main__":

    jsondata = getGainian(56, 0, '')

    # 获取当前时间戳和日期
    timestamp = str(int(datetime.now().timestamp()))
    date = datetime.now().strftime('%Y%m%d')

    # 构建表名
    table_name = f'gainian'

    db = pymysql.connect(host='64.110.105.176', user='root', passwd='ilikecs123!', port=3306, db='quant')
    cursor = db.cursor()
    sql = "DELETE FROM gainian"
    # 执行 SQL 语句
    cursor.execute(sql)


    db.commit()
    db.close()

    #北交所
    doBeiJiaoSuo(table_name)
    print("北交所完成,开始沪深")
    #沪深
    for i in range(0, 90):
        try:

            # 延迟
            time.sleep(0.5)


            st=56

            jsondata = getGainian(st, st*i, '')
            print(len(jsondata['list']))

            db = pymysql.connect(host='64.110.105.176', user='root', passwd='ilikecs123!', port=3306, db='quant')
            cursor = db.cursor()
            for row in jsondata['list']:

                sql = f"INSERT INTO `quant`.`{table_name}`(`code`, `name`,  `conceptall`) VALUES ('{row[0]}', '{row[1]}', '{str(row[4]).split('、')[0]}')"
                cursor.execute(sql)
            db.commit()
            db.close()
        except:
            print(traceback.print_exc())


    #退出程序
    exit(0)