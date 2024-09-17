from asyncio import sleep

from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import OWNER_ID, bot, task_dict, user_data, multi_tags, task_dict_lock
from bot.helper.telegram_helper import button_build
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import MirrorStatus, getAllTasks, getTaskByGid
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    edit_message,
    send_message,
    delete_message,
    auto_delete_message,
)


async def cancel_task(_, message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    msg = message.text.split("_", maxsplit=1)
    await delete_message(message)
    if len(msg) > 1:
        gid = msg[1].split("@", maxsplit=1)
        gid = gid[0]
        if len(gid) == 4:
            multi_tags.discard(gid)
            return
        task = await getTaskByGid(gid)
        if task is None:
            await delete_message(message)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if task is None:
            return
    elif len(msg) == 1:
        return
    if user_id not in (OWNER_ID, task.listener.userId) and (
        user_id not in user_data or not user_data[user_id].get("is_sudo")
    ):
        return
    obj = task.task()
    await obj.cancel_task()


async def cancel_multi(_, query):
    data = query.data.split()
    user_id = query.from_user.id
    if user_id != int(data[1]) and not await CustomFilters.sudo("", query):
        await query.answer("Not Yours!", show_alert=True)
        return
    tag = int(data[2])
    if tag in multi_tags:
        multi_tags.discard(int(data[2]))
        msg = "Stopped!"
    else:
        msg = "Already Stopped/Finished!"
    await query.answer(msg, show_alert=True)
    await delete_message(query.message)


async def cancel_all(status, userId):
    matches = await getAllTasks(status.strip(), userId)
    if not matches:
        return False
    for task in matches:
        obj = task.task()
        await obj.cancel_task()
        await sleep(2)
    return True


def create_cancel_buttons(isSudo, userId=""):
    buttons = button_build.ButtonMaker()
    buttons.callback(
        "Downloading", f"canall ms {MirrorStatus.STATUS_DOWNLOADING} {userId}"
    )
    buttons.callback(
        "Uploading", f"canall ms {MirrorStatus.STATUS_UPLOADING} {userId}"
    )
    buttons.callback("Seeding", f"canall ms {MirrorStatus.STATUS_SEEDING} {userId}")
    buttons.callback(
        "Spltting", f"canall ms {MirrorStatus.STATUS_SPLITTING} {userId}"
    )
    buttons.callback("Cloning", f"canall ms {MirrorStatus.STATUS_CLONING} {userId}")
    buttons.callback(
        "Extracting", f"canall ms {MirrorStatus.STATUS_EXTRACTING} {userId}"
    )
    buttons.callback(
        "Archiving", f"canall ms {MirrorStatus.STATUS_ARCHIVING} {userId}"
    )
    buttons.callback("QueuedDl", f"canall ms {MirrorStatus.STATUS_QUEUEDL} {userId}")
    buttons.callback("QueuedUp", f"canall ms {MirrorStatus.STATUS_QUEUEUP} {userId}")
    buttons.callback(
        "SampleVideo", f"canall ms {MirrorStatus.STATUS_SAMVID} {userId}"
    )
    buttons.callback(
        "ConvertMedia", f"canall ms {MirrorStatus.STATUS_CONVERTING} {userId}"
    )
    buttons.callback("Paused", f"canall ms {MirrorStatus.STATUS_PAUSED} {userId}")
    buttons.callback("All", f"canall ms All {userId}")
    if isSudo:
        if userId:
            buttons.callback("All Added Tasks", f"canall bot ms {userId}")
        else:
            buttons.callback("My Tasks", f"canall user ms {userId}")
    buttons.callback("Close", f"canall close ms {userId}")
    return buttons.menu(2)


async def cancell_all_buttons(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        await send_message(message, "No active tasks!")
        return
    isSudo = await CustomFilters.sudo("", message)
    button = create_cancel_buttons(isSudo, message.from_user.id)
    can_msg = await send_message(message, "Choose tasks to cancel!", button)
    await auto_delete_message(message, can_msg)


@new_task
async def cancel_all_update(_, query):
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    userId = int(data[3]) if len(data) > 3 else ""
    isSudo = await CustomFilters.sudo("", query)
    if not isSudo and userId and userId != query.from_user.id:
        await query.answer("Not Yours!", show_alert=True)
    else:
        await query.answer()
    if data[1] == "close":
        await delete_message(reply_to)
        await delete_message(message)
    elif data[1] == "back":
        button = create_cancel_buttons(isSudo, userId)
        await edit_message(message, "Choose tasks to cancel!", button)
    elif data[1] == "bot":
        button = create_cancel_buttons(isSudo, "")
        await edit_message(message, "Choose tasks to cancel!", button)
    elif data[1] == "user":
        button = create_cancel_buttons(isSudo, query.from_user.id)
        await edit_message(message, "Choose tasks to cancel!", button)
    elif data[1] == "ms":
        buttons = button_build.ButtonMaker()
        buttons.callback("Yes!", f"canall {data[2]} confirm {userId}")
        buttons.callback("Back", f"canall back confirm {userId}")
        buttons.callback("Close", f"canall close confirm {userId}")
        button = buttons.menu(2)
        await edit_message(
            message, f"Are you sure you want to cancel all {data[2]} tasks", button
        )
    else:
        button = create_cancel_buttons(isSudo, userId)
        await edit_message(message, "Choose tasks to cancel.", button)
        res = await cancel_all(data[1], userId)
        if not res:
            await send_message(reply_to, f"No matching tasks for {data[1]}!")


bot.add_handler(
    MessageHandler(
        cancel_task,
        filters=regex(r"^/stop(_\w+)?(?!all)") & CustomFilters.authorized,
    )
)
bot.add_handler(
    MessageHandler(
        cancell_all_buttons,
        filters=command(BotCommands.CancelAllCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex("^canall")))
bot.add_handler(CallbackQueryHandler(cancel_multi, filters=regex("^stopm")))
