import pyshorteners
from bot import LOGGER
from re import IGNORECASE, search, escape

from bot.helper.ext_utils.text_utils import nsfw_keywords


def is_nsfw(text):
    pattern = r'(?:^|\W|_)(?:' + '|'.join(escape(keyword) for keyword in nsfw_keywords) + r')(?:$|\W|_)'
    if search(pattern, text, flags=IGNORECASE):
        return True
    return False


async def check_nsfw_tg(message, error_msg):
    nsfw_msg = ['NSFW detected']
    if nsfw := is_nsfw(message.text):
        error_msg.extend(nsfw_msg)
    elif message.reply_to_message:
        if message.reply_to_message.caption:
            if nsfw := is_nsfw(message.reply_to_message.caption):
                return error_msg.extend(nsfw_msg)
        if message.reply_to_message.document:
            if nsfw := is_nsfw(message.reply_to_message.document.file_name):
                return error_msg.extend(nsfw_msg)
        if message.reply_to_message.video:
            if nsfw := is_nsfw(message.reply_to_message.video.file_name):
                return error_msg.extend(nsfw_msg)
        if message.reply_to_message.text:
            if nsfw := is_nsfw(message.reply_to_message.text):
                error_msg.extend(nsfw_msg)


def check_nsfw_details(data):
    if 'contents' in data:
        contents = data['contents']
        for item in contents:
            if 'filename' in item:
                filename = item['filename']
                if is_nsfw(filename):
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
