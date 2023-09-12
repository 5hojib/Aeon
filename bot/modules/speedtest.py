#!/usr/bin/env python3
from speedtest import Speedtest
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

from bot import bot, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, editMessage
from bot.helper.ext_utils.bot_utils import get_readable_file_size, new_task

@new_task
async def speedtest(_, message):
    speed = await sendMessage(message, "Initializing Speedtest...")
    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    path = result['share']
    string_speed = f'''
<b>SPEEDTEST INFO</b>

<b>• Upload:</b> <code>{get_readable_file_size(result['upload'] / 8)}/s</code>
<b>• Download:</b> <code>{get_readable_file_size(result['download'] / 8)}/s</code>
<b>• Ping:</b> <code>{result['ping']} ms</code>
<b>• IP Address:</b> <code>{result['client']['ip']}</code>
'''
    try:
        pho = await sendMessage(message, string_speed, photo=path)
        await deleteMessage(speed)
    except Exception as e:
        LOGGER.error(str(e))
        pho = await editMessage(speed, string_speed)

bot.add_handler(MessageHandler(speedtest, filters=command(
    BotCommands.SpeedCommand) & CustomFilters.authorized))
