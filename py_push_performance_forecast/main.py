import requests
from lxml import etree
import datetime
import uuid
from email.utils import formatdate
import pymysql
import json

#定义方法---------------------------------------------------------
def PostDingMes(title,msg):
    # 更改为自己的钉钉机器人
    baseUrl = "https://oapi.dingtalk.com/robot/send?access_token=9d052d8d2d1fc8956e0f8deb74443f48092d1ee27b0b85d1d6f53e0ed3cd354c"

    # please set charset= utf-8
    HEADERS = {
        "Content-Type": "application/json ;charset=utf-8 "
    }
    # 这里的message是你想要推送的文字消息
    stringBody = {
        "msgtype": "markdown",
        "markdown":{
            "title":"别管好啊",
            "text":f"### {title}\n\n"
                   f"{msg}"
        },
        "at": {
            "atMobiles": [""],
            "isAtAll": "true"  # @所有人 时为true，上面的atMobiles就失效了
        }
    }
    MessageBody = json.dumps(stringBody)
    result = requests.post(url=baseUrl, data=MessageBody, headers=HEADERS)
    print(result.text)
#----------------------------------------------------------------------

conn = pymysql.connect(
    host='axiba.idnmd.top',
    port=8306,
    user='root',
    password='ilikecs123!',
    db='quant'
)

# If-Modified-Since 使用当前的日期和时间
now = datetime.datetime.now()
# 转换成RFC2822格式，因为HTTP头中的日期一般需要这个格式
if_modified_since = formatdate(timeval=now.timestamp(), localtime=False, usegmt=True)

# If-None-Match 使用一个UUID作为随机字段
if_none_match = f'"{uuid.uuid4()}"'

url = "https://data.10jqka.com.cn/financial/yjyg/"

payload = {}
headers = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'Accept-Encoding': 'gzip, deflate, br, zstd',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
  'If-None-Match': if_none_match,
  'If-Modified-Since': if_modified_since,
}

response = requests.request("GET", url, headers=headers, data=payload)

#print(response.text)

# 使用lxml解析HTML内容
tree = etree.HTML(response.text)

# 报告类型
ths_report_type = tree.xpath('//span[@class="text-value" and @id="report"]')[0].text
print(ths_report_type)

tr_elements = tree.xpath('//tbody//tr')
ddmsg = ""
for tr in tr_elements:
    tds = tr.xpath('./td')
    ths_code = tds[1].xpath('./a')[0].text
    ths_name = tds[2].xpath('./a')[0].text
    ths_pf_type = tds[3].xpath('./span')[0].text
    ths_pf_desc = tds[4].xpath('./a')[0].text
    ths_profit_range = tds[5].text
    ths_profit_oldyear = tds[6].text
    ths_date = tds[7].text
    # 插入mysql
    try:
        with conn.cursor() as cursor:
            # 构造SQL查询语句
            sql = f"SELECT ths_code, ths_date FROM ths_push_performance_forecast where ths_code={ths_code} and ths_date='{ths_date}'"
            # 执行SQL语句
            cursor.execute(sql)
            # 获取查询结果
            result = cursor.fetchall()

            if len(result) > 0:
                print(f'{ths_code} {ths_date} already exists')
                continue

            # 构造SQL插入语句
            sql = "INSERT INTO ths_push_performance_forecast (ths_report_type, ths_code, ths_name, ths_pf_type, ths_pf_desc, ths_profit_range, ths_profit_oldyear, ths_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            # 设置需要插入数据库的数据
            data = (ths_report_type, ths_code, ths_name, ths_pf_type, ths_pf_desc, ths_profit_range.strip(),
                    ths_profit_oldyear, ths_date)
            # 执行SQL语句
            cursor.execute(sql, data)
            print(
                f'插入：{ths_report_type} {ths_code} {ths_name} {ths_pf_type} {ths_pf_desc} {ths_profit_range.strip()} {ths_profit_oldyear} {ths_date}')

            ddmsg =ddmsg+ f"【{ths_code} {ths_name}】{ths_pf_type} 变动幅度{ths_profit_range.strip()}% {ths_profit_oldyear}\n\n"
        # 提交更改
        conn.commit()

    except pymysql.Error as e:
        print(f"An error occurred while interacting with MySQL: {e}")

 # 最后，我们关闭数据库连接
conn.close()
PostDingMes('今日公告:'+ths_report_type,ddmsg)

your_access_tokenurl = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx27d12a15e6329c2e&secret=5ddab1f5eac8bd4afe5d9185442b2447"
response = requests.get(your_access_tokenurl).json()

# 获取到的access_token
if "response" in response:
    ACCESS_TOKEN = response.json()["access_token"]
else:
    print("获取access_token失败")

# 获取素材
draft_content = {
    "type":"image",
    "offset":0,
    "count":20
}
response = requests.post(f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={ACCESS_TOKEN}", data=json.dumps(draft_content))
response.encoding = 'utf-8'
for i in response.json()["item"]:
    if i["name"]=="开盘啦概念.png":
        your_thumb_media_id=i["media_id"]
# 草稿内容信息
draft_content = {
    "articles": [
        {
            "title": "今日业绩公告",
            "thumb_media_id": your_thumb_media_id,  # 缩略图媒体ID
            "author": "wolfmoss",
            #"digest": "摘要信息",
            "content": ddmsg,  # 正文，支持HTML标签
            #"content_source_url": "原文链接（可选）",
            "show_cover_pic": 1,  # 是否显示封面，0：不显示，1：显示
            "need_open_comment": 0,  # 是否开启评论，0：不开启，1：开启
            "only_fans_can_comment": 0,  # 是否粉丝才可评论，0：所有人可评论，1：仅粉丝可评论
        }
    ]
}

# 新建草稿接口URL
create_draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={ACCESS_TOKEN}"
response = requests.post(create_draft_url, data=json.dumps(draft_content).encode("utf-8"))

if response.status_code == 200:
    result = response.json()

    if "media_id" in result:
        print("草稿创建成功", result)
        media_id = result["media_id"]
        # 发布草稿接口URL
    else:
        print("草稿创建失败", result)
else:
    print("请求失败", response.status_code)