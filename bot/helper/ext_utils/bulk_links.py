#!/usr/bin/env python3
import re
from aiofiles import open as aiopen
from aiofiles.os import remove

async def extract_links_from_text(text):
    url_pattern = r'http[s]?://(?:[a-zA-Z0-9$_@.&+!*\\(\\)%,-]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    magnet_pattern = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*'
    urls = re.findall(url_pattern, text)
    magnets = re.findall(magnet_pattern, text)
    
    return urls + magnets

async def get_links_from_message(text, bulk_start, bulk_end):
    links_list = await extract_links_from_text(text)

    if bulk_start != 0 and bulk_end != 0:
        links_list = links_list[bulk_start:bulk_end]
    elif bulk_start != 0:
        links_list = links_list[bulk_start:]
    elif bulk_end != 0:
        links_list = links_list[:bulk_end]

    return links_list

async def get_links_from_file(message, bulk_start, bulk_end):
    links_list = []
    text_file_dir = await message.download()

    async with aiopen(text_file_dir, 'r+') as f:
        lines = await f.readlines()
        text = ''.join(lines)
        links_list.extend(await get_links_from_message(text, bulk_start, bulk_end))

    await remove(text_file_dir)

    return links_list

async def extract_bulk_links(message, bulk_start, bulk_end):
    bulk_start = int(bulk_start)
    bulk_end = int(bulk_end)
    if (reply_to := message.reply_to_message) and (file_ := reply_to.document) and (file_.mime_type == 'text/plain'):
        return await get_links_from_file(message.reply_to_message, bulk_start, bulk_end)
    elif text := message.reply_to_message.text:
        return await get_links_from_message(text, bulk_start, bulk_end)
    return []