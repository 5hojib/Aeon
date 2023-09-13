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
    if is_nsfw_content(message.text):
        error_msg.extend['NSFW detected']
    elif message.reply_to_message:
        content = message.reply_to_message.caption or message.reply_to_message.document.file_name or message.reply_to_message.video.file_name or message.reply_to_message.text
        if content and is_nsfw_content(content):
            error_msg.extend['NSFW detected']


def tinyfy(long_url):
    s = pyshorteners.Shortener()
    try:
        short_url = s.tinyurl.short(long_url)
        LOGGER.info(f'tinyfied {long_url} to {short_url}')
        return short_url
    except Exception:
        LOGGER.error(f'Failed to shorten URL: {long_url}')
        return long_url
