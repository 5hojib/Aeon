from time import time

from psutil import disk_usage
from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    DOWNLOAD_DIR,
    Intervals,
    bot,
    task_dict,
    status_dict,
    bot_start_time,
    task_dict_lock,
)
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import (
    get_readable_time,
    get_readable_file_size,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    send_message,
    delete_message,
    sendStatusMessage,
    auto_delete_message,
    update_status_message,
)


@new_task
async def mirror_status(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        currentTime = get_readable_time(time() - bot_start_time)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        msg = "No downloads are currently in progress.\n"
        msg += f"\n<b>Bot uptime</b>: {currentTime}"
        msg += f"\n<b>Free disk space</b>: {free}"
        reply_message = await send_message(message, msg)
        await auto_delete_message(message, reply_message)
    else:
        text = message.text.split()
        if len(text) > 1:
            user_id = message.from_user.id if text[1] == "me" else int(text[1])
        else:
            user_id = 0
            sid = message.chat.id
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
        await sendStatusMessage(message, user_id)
        await delete_message(message)


@new_task
async def status_pages(_, query):
    data = query.data.split()
    key = int(data[1])
    if data[2] in ["nex", "pre"]:
        await query.answer()
        async with task_dict_lock:
            if data[2] == "nex":
                status_dict[key]["page_no"] += status_dict[key]["page_step"]
            else:
                status_dict[key]["page_no"] -= status_dict[key]["page_step"]
    elif data[2] == "st":
        await query.answer()
        async with task_dict_lock:
            status_dict[key]["status"] = data[3]
        await update_status_message(key, force=True)


bot.add_handler(
    MessageHandler(
        mirror_status,
        filters=command(BotCommands.StatusCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))
