import pyshorteners
from bot import LOGGER
from re import IGNORECASE, search, escape
import json
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


def xcheckNSFW(data):
    data_list = eval(data)
    for item in data_list:
        if isNSFW(item['name']):
            return True
    return False

def checkNSFW(data):
    #data_list = eval(data)
    for item in data:
        for key, value in item.items():
            if isinstance(value, str) and isNSFW(value):
                return True
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
