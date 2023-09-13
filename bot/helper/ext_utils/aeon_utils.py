import re
import pyshorteners
from bot import LOGGER

nsfw_keywords = [
    "xxx",
    "porn",
    "onlyfans",
    "nsfw",
    "Brazzers",
    "adult",
    "xnxx",
    "xvideos",
    "Carry"
]


def is_nsfw_content(text):
    return any(re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE) for keyword in nsfw_keywords)


async def check_nsfw(message, error_msg):
    nsfw = ['NSFW detected']
    nsfw_check = is_nsfw_content(message.text)
    if nsfw_check:
        error_msg.extend(nsfw)
    elif message.reply_to_message:
        if message.reply_to_message.caption:
            nsfw_check = is_nsfw_content(message.reply_to_message.caption)
            if nsfw_check:
                return error_msg.extend(nsfw)
        if message.reply_to_message.document:
            nsfw_check = is_nsfw_content(message.reply_to_message.document.file_name)
            if nsfw_check:
                return error_msg.extend(nsfw)
        if message.reply_to_message.video:
            nsfw_check = is_nsfw_content(message.reply_to_message.video.file_name)
            if nsfw_check:
                return error_msg.extend(nsfw)
        if message.reply_to_message.text:
        	nsfw_check = is_nsfw_content(message.reply_to_message.text)
        	if nsfw_check:
        		error_msg.extend(nsfw)


def tinyfy(long_url):
    s = pyshorteners.Shortener()
    try:
        short_url = s.tinyurl.short(long_url)
        LOGGER.info(f'tinyfied {long_url} to {short_url}')
        return short_url
    except Exception:
        LOGGER.error(f'Failed to shorten URL: {long_url}')
        return long_url
