from time import time

from psutil import disk_usage
from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    Interval,
    bot,
    download_dict,
    bot_start_time,
    download_dict_lock,
    status_reply_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    SetInterval,
    new_task,
    turn_page,
    get_readable_time,
    get_readable_file_size,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    send_message,
    delete_message,
    one_minute_del,
    sendStatusMessage,
    update_all_messages,
)


@new_task
async def mirror_status(_, message):
    async with download_dict_lock:
        count = len(download_dict)

    if count == 0:
        current_time = get_readable_time(time() - bot_start_time)
        free = get_readable_file_size(disk_usage("/usr/src/app/downloads/").free)
        msg = "No downloads are currently in progress.\n"
        msg += f"\n<b>• Bot uptime</b>: {current_time}"
        msg += f"\n<b>• Free disk space</b>: {free}"

        reply_message = await send_message(message, msg)
        await delete_message(message)
        await one_minute_del(reply_message)
    else:
        await sendStatusMessage(message)
        await delete_message(message)
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(SetInterval(1, update_all_messages))


@new_task
async def status_pages(_, query):
    await query.answer()
    data = query.data.split()
    if data[1] == "ref":
        await update_all_messages(True)
    else:
        await turn_page(data)


bot.add_handler(
    MessageHandler(
        mirror_status,
        filters=command(BotCommands.StatusCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))
