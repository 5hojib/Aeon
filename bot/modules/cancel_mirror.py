from asyncio import sleep

from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import OWNER_ID, bot, bot_name, user_data, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import (
    MirrorStatus,
    new_task,
    getAllDownload,
    getDownloadByGid,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    deleteMessage,
    one_minute_del,
)


@new_task
async def cancel_mirror(_, message):
    user_id = message.from_user.id
    msg = message.text.split("_", maxsplit=1)
    await deleteMessage(message)

    if len(msg) > 1:
        cmd_data = msg[1].split("@", maxsplit=1)
        if len(cmd_data) > 1 and cmd_data[1].strip() != bot_name:
            return
        gid = cmd_data[0]
        dl = await getDownloadByGid(gid)
        if dl is None:
            await deleteMessage(message)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with download_dict_lock:
            dl = download_dict.get(reply_to_id, None)
        if dl is None:
            await deleteMessage(message)
            return
    elif len(msg) == 1:
        await deleteMessage(message)
        return

    if user_id not in (OWNER_ID, dl.message.from_user.id) and (
        user_id not in user_data or not user_data[user_id].get("is_sudo")
    ):
        await deleteMessage(message)
        return

    obj = dl.download()
    await obj.cancel_download()


async def cancel_all(status):
    matches = await getAllDownload(status)
    if not matches:
        return False
    for dl in matches:
        obj = dl.download()
        await obj.cancel_download()
        await sleep(1)
    return True


async def cancell_all_buttons(_, message):
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        await sendMessage(message, "No active tasks!")
        return

    buttons = ButtonMaker()
    buttons.callback("Downloading", f"stopall {MirrorStatus.STATUS_DOWNLOADING}")
    buttons.callback("Uploading", f"stopall {MirrorStatus.STATUS_UPLOADING}")
    buttons.callback("Seeding", f"stopall {MirrorStatus.STATUS_SEEDING}")
    buttons.callback("Cloning", f"stopall {MirrorStatus.STATUS_CLONING}")
    buttons.callback("Extracting", f"stopall {MirrorStatus.STATUS_EXTRACTING}")
    buttons.callback("Archiving", f"stopall {MirrorStatus.STATUS_ARCHIVING}")
    buttons.callback("QueuedDl", f"stopall {MirrorStatus.STATUS_QUEUEDL}")
    buttons.callback("QueuedUp", f"stopall {MirrorStatus.STATUS_QUEUEUP}")
    buttons.callback("Paused", f"stopall {MirrorStatus.STATUS_PAUSED}")
    buttons.callback("All", "stopall all")
    buttons.callback("Close", "stopall close")
    button = buttons.column(2)
    can_msg = await sendMessage(message, "Choose tasks to cancel.", button)
    await deleteMessage(message)
    await one_minute_del(can_msg)


@new_task
async def cancel_all_update(_, query):
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    await query.answer()
    if data[1] == "close":
        await deleteMessage(reply_to)
        await deleteMessage(message)
    else:
        res = await cancel_all(data[1])
        if not res:
            await sendMessage(reply_to, f"No matching tasks for {data[1]}!")


bot.add_handler(
    MessageHandler(
        cancel_mirror,
        filters=regex(r"^/stop(_\w+)?(?!all)") & CustomFilters.authorized,
    )
)
bot.add_handler(
    MessageHandler(
        cancell_all_buttons,
        filters=command(BotCommands.StopAllCommand) & CustomFilters.sudo,
    )
)
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex(r"^stopall")))
