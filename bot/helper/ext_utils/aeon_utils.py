import pyshorteners
from bot import LOGGER
from re import IGNORECASE, search, escape

from bot.helper.ext_utils.text_utils import nsfw_keywords


def isNSFW(text):
    pattern = r'(?:^|\W|_)(?:' + '|'.join(escape(keyword) for keyword in nsfw_keywords) + r')(?:$|\W|_)'
    return bool(search(pattern, text, flags=IGNORECASE))


async def nsfw_precheck(message):
    if isNSFW(message.text):
        return True
    elif reply_to := message.reply_to_message:
        if reply_to.caption:
            if isNSFW(reply_to.caption):
                return True
        if reply_to.document:
            if isNSFW(reply_to.document.file_name):
                return True
        if reply_to.video:
            if isNSFW(reply_to.video.file_name):
                return True
        if reply_to.text:
            if isNSFW(reply_to.text):
                return True
    return False


def isNSFWfolder(data):
    if 'contents' in data:
        contents = data['contents']
        for item in contents:
            if 'filename' in item:
                filename = item['filename']
                if isNSFW(filename):
                    return True
    return False


def checkNSFW(data):
    if isinstance(data, list):
        data = [item for item in data if isinstance(item, dict)]
        values = [value for item in data for value in item.values() if isinstance(value, str)]
        return any(isNSFW(value) for value in values)
    elif isinstance(data, dict):
        values = [value for value in data.values() if isinstance(value, str)]
        return any(isNSFW(value) for value in values)
    return False


def tinyfy(long_url):
    s = pyshorteners.Shortener()
    try:
        short_url = s.tinyurl.short(long_url)
        LOGGER.info(f'tinyfied {long_url} to {short_url}')
        return short_url
    except Exception:
        LOGGER.error(f'Failed to shorten URL: {long_url}')
        return long_url
