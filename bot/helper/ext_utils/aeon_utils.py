import pyshorteners
from re import IGNORECASE, search, escape
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, DATABASE_URL
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.text_utils import nsfw_keywords


def isNSFW(text):
    pattern = r'(?:^|\W|_)(?:' + '|'.join(escape(keyword) for keyword in nsfw_keywords) + r')(?:$|\W|_)'
    return bool(search(pattern, text, flags=IGNORECASE))


def isNSFWdata(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, str) and isNSFW(value):
                        return True
            elif 'name' in item and isinstance(item['name'], str) and isNSFW(item['name']):
                return True
    elif isinstance(data, dict) and 'contents' in data:
        contents = data['contents']
        for item in contents:
            if 'filename' in item:
                filename = item['filename']
                if isNSFW(filename):
                    return True
    return False


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


async def RemoveAllTokens(_, message):
    if DATABASE_URL:
        await DbManager().delete_all_access_tokens()
        msg = 'All access tokens have been removed from the database.'
    else:
        msg = 'Database URL not added.'
    return await sendMessage(message, msg)


def tinyfy(long_url):
    s = pyshorteners.Shortener()
    try:
        short_url = s.tinyurl.short(long_url)
        LOGGER.info(f'tinyfied {long_url} to {short_url}')
        return short_url
    except Exception:
        LOGGER.error(f'Failed to shorten URL: {long_url}')
        return long_url


bot.add_handler(MessageHandler(RemoveAllTokens, filters=command(BotCommands.RemoveAllTokensCommand) & CustomFilters.sudo))
