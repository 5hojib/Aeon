#!/usr/bin/env python3
from asyncio import sleep
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex

from bot import download_dict, bot, bot_name, download_dict_lock, OWNER_ID, user_data
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, one_minute_del
from bot.helper.ext_utils.bot_utils import getDownloadByGid, getAllDownload, MirrorStatus, new_task
from bot.helper.telegram_helper import button_build

@new_task
async def cancel_mirror(_, message):
    user_id = message.from_user.id
    msg = message.text.split('_', maxsplit=1)
    await deleteMessage(message)
    if len(msg) > 1:
        cmd_data = msg[1].split('@', maxsplit=1)
        if len(cmd_data) > 1 and cmd_data[1].strip() != bot_name:
            return
        gid = cmd_data[0]
        dl = await getDownloadByGid(gid)
        if dl is None:
            x = await sendMessage(message, f"GID: <code>{gid}</code> Not Found.")
            await one_minute_del(x)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with download_dict_lock:
            dl = download_dict.get(reply_to_id, None)
        if dl is None:
            x = await sendMessage(message, "This is not an active task!")
            await one_minute_del(x)
            return
    elif len(msg) == 1:
        msg = "Reply to an active Command message which was used to start the download" \
              f" or send <code>/{BotCommands.CancelMirror}_GID</code> to cancel it!"
        x = await sendMessage(message, msg)
        await one_minute_del(x)
        return
    if OWNER_ID != user_id and dl.message.from_user.id != user_id and \
       (user_id not in user_data or not user_data[user_id].get('is_sudo')):
        x = await sendMessage(message, "This task is not for you!")
        await one_minute_del(x)
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
    buttons = button_build.ButtonMaker()
    buttons.ibutton("Downloading", f"canall {MirrorStatus.STATUS_DOWNLOADING}")
    buttons.ibutton("Uploading", f"canall {MirrorStatus.STATUS_UPLOADING}")
    buttons.ibutton("Seeding", f"canall {MirrorStatus.STATUS_SEEDING}")
    buttons.ibutton("Cloning", f"canall {MirrorStatus.STATUS_CLONING}")
    buttons.ibutton("Extracting", f"canall {MirrorStatus.STATUS_EXTRACTING}")
    buttons.ibutton("Archiving", f"canall {MirrorStatus.STATUS_ARCHIVING}")
    buttons.ibutton("QueuedDl", f"canall {MirrorStatus.STATUS_QUEUEDL}")
    buttons.ibutton("QueuedUp", f"canall {MirrorStatus.STATUS_QUEUEUP}")
    buttons.ibutton("Paused", f"canall {MirrorStatus.STATUS_PAUSED}")
    buttons.ibutton("All", "canall all")
    buttons.ibutton("Close", "canall close")
    button = buttons.build_menu(2)
    can_msg = await sendMessage(message, 'Choose tasks to cancel.', button)
    await deleteMessage(message)
    await one_minute_del(can_msg)


@new_task
async def cancel_all_update(_, query):
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    await query.answer()
    if data[1] == 'close':
        await deleteMessage(reply_to)
        await deleteMessage(message)
    else:
        res = await cancel_all(data[1])
        if not res:
            await sendMessage(reply_to, f"No matching tasks for {data[1]}!")


bot.add_handler(MessageHandler(cancel_mirror, filters=regex(
    f"^/{BotCommands.CancelMirror}(_\w+)?(?!all)") & CustomFilters.authorized))
bot.add_handler(MessageHandler(cancell_all_buttons, filters=command(
    BotCommands.CancelAllCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex(r"^canall")))