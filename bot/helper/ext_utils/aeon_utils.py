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
]


def tinyfy(long_url):
    s = pyshorteners.Shortener()
    try:
        short_url = s.tinyurl.short(long_url)
        LOGGER.info(f'tinyfied {long_url} to {short_url}')
        return short_url
    except Exception:
        LOGGER.error(f'Failed to shorten URL: {long_url}')
        return long_url


def is_nsfw_content(message):
    for keyword in nsfw_keywords:
        pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
        if pattern.search(message):
            return True
    return False