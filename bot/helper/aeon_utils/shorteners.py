from random import choice
from asyncio import sleep
from urllib.parse import quote

from aiohttp import ClientSession
from pyshorteners import Shortener

shorteners_list = [
    {
        "domain": "modijiurl.com",
        "api_key": "cd5b3b10ed0e7c30e795e7ab3c8778f799cafb5b",
    }
]


async def short(long_url):
    async with ClientSession() as session:
        for attempt in range(4):
            shortener_info = choice(shorteners_list)
            try:
                async with session.get(
                    f'https://{shortener_info["domain"]}/api?api={shortener_info["api_key"]}&url={quote(long_url)}'
                ) as response:
                    result = await response.json()
                    short_url = result.get("shortenedUrl", long_url)
                    if short_url != long_url:
                        long_url = short_url
                        break
            except Exception:
                continue

        s = Shortener()
        for attempt in range(4):
            try:
                return s.tinyurl.short(long_url)
            except Exception:
                await sleep(1)

        return long_url
