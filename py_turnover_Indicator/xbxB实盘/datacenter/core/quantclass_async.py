from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

import aiohttp
import pandas as pd
import py7zr
import pytz


class QuantclassDataApi:

    def __init__(self, session: aiohttp.ClientSession, api_key, uuid):
        self.api_key = api_key
        self.uuid = uuid
        self.session = session

    async def aioreq_data_api(self, offset) -> dict:
        url = 'https://api.quantclass.cn/api/data/realtime/coin/binance-1h'
        params = {'offset': offset, 'uuid': self.uuid}
        headers = {'api-key': self.api_key}

        async with self.session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
            data = data['data']
            ts = datetime.strptime(data['ts'], '%Y%m%d%H%M')
            data['ts'] = pytz.timezone('Asia/Shanghai').localize(ts)

            return data

    async def aioreq_coincap_url(self, run_time: str | datetime):
        if isinstance(run_time, datetime):
            run_time = run_time.strftime("%Y-%m-%d")
        url = f'https://api.quantclass.cn/api/data/get-download-link/coin-cap-daily/{run_time}'

        params = {'uuid': self.uuid}
        headers = {'api-key': self.api_key}

        async with self.session.get(url, params=params, headers=headers) as resp:
            data = await resp.text()
            return data

    async def aioreq_coincap_df(self, url) -> Optional[pd.DataFrame]:
        async with self.session.get(url) as resp:
            if not str(resp.status).startswith('2'):
                return None
            raw_data = BytesIO(await resp.read())
        df = pd.read_csv(raw_data, encoding='gbk', skiprows=1, parse_dates=['candle_begin_time', 'date_added'])
        df['symbol'] = df['symbol'].str.replace('-', '')
        return df

    async def aioreq_candle_raw(self, url) -> BytesIO:
        async with self.session.get(url) as resp:
            archive_data = BytesIO(await resp.read())
        return archive_data

    async def aioreq_candle_df(self, url) -> pd.DataFrame:
        archive_data = await self.aioreq_candle_raw(url)

        with py7zr.SevenZipFile(archive_data, mode='r') as archive:
            for fname, bio in archive.readall().items():
                if fname.endswith('.csv'):
                    df = pd.read_csv(bio, parse_dates=['candle_begin_time'])
                    df['candle_begin_time'] = df['candle_begin_time'].dt.tz_localize('UTC')

                    # Data API 一定为 1 小时线
                    df['candle_end_time'] = df['candle_begin_time'] + timedelta(hours=1)

                    columns = [
                        'symbol', 'candle_begin_time', 'candle_end_time', 'open', 'high', 'low', 'close', 'volume',
                        'quote_volume', 'trade_num', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume'
                    ]
                    return df[columns]

    async def aioreq_product_infos(self):
        url = 'https://api.quantclass.cn/api/product/data/status/by_category/data-api-products'
        async with self.session.get(url) as resp:
            if not str(resp.status).startswith('2'):
                raise ValueError(f'Data API products 返回错误: {resp.status}')
            data = (await resp.json())['data']
        df = pd.DataFrame.from_dict(data, orient='index', columns=['name_en', 'name_zh', 'update_time', 'data_range'])
        df['update_time'] = pd.to_datetime(df['update_time']).dt.tz_localize('Asia/Shanghai').dt.tz_convert('utc')
        return df
