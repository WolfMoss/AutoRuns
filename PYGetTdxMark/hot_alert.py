import json

import requests
import aiohttp
import asyncio
import socketio
import aiohttp_cors


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

# 创建一个 Socket.IO 服务器实例
sio = socketio.AsyncServer(cors_allowed_origins='*')
app = aiohttp.web.Application()
sio.attach(app)


@sio.event
async def connect(sid, environ):
    print(f"服务器收到客户端链接，客户端ID=== {sid}")

# 消息事件处理
@sio.event
async def message(sid, data):
    print(f"服务器接收客户端的消息，客户端ID===: {sid}, 消息内容===: {data}")
    # 广播消息给所有客户端
    await sio.emit('message', f"你好客户端")

# 断开连接事件处理
@sio.event
async def disconnect(sid):
    print(f"服务器收到客户端断开，客户端ID=== {sid}")


async def send_periodic_message():
    while True:
        jsondata = getGainian(56, 0, '')
        ptdatas = []
        for row in jsondata['list']:
            code=row[0]
            name=row[1]
            conceptall=row[4]
            ptdatas.append({'code': code, 'name': name, 'conceptall': conceptall})
        # 定时发送消息给所有客户端
        await sio.emit('message', json.dumps(ptdatas))
        await asyncio.sleep(2)

async def main():
    # 启动定时发送消息任务
    sio.start_background_task(send_periodic_message)
    # 运行 aiohttp 服务器
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', 8601)
    await site.start()
    print("服务器已启动在端口 8601")
    while True:
        await asyncio.sleep(3600)  # 保持程序运行

if __name__ == "__main__":
    asyncio.run(main())
