import asyncio

import aiohttp

from core.utils.log_kit import logger


async def async_retry_getter(func, _max_times=5, _sleep_seconds=1, **kwargs):
    while True:
        try:
            return await func(**kwargs)
        except Exception as e:
            if _max_times == 0:
                logger.error('错误 %s, 剩余 0 次重试机会, 出错函数 %s', repr(e), repr(func))
                raise e

            await asyncio.sleep(_sleep_seconds)
            _max_times -= 1
            _sleep_seconds *= 2


def create_aiohttp_session(timeout_sec):
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    session = aiohttp.ClientSession(timeout=timeout)
    return session



