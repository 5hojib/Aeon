from contextlib import suppress

from aiofiles.os import path as aiopath
from aiofiles.os import remove
from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from bot import (
    LOGGER,
    bot,
    aria2,
    xnox_client,
)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.status_utils import getTaskByGid
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    sendStatusMessage,
)


async def get_confirm(_, query):
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    task = await getTaskByGid(data[2])
    if task is None:
        await query.answer("This task has been cancelled!", show_alert=True)
        await delete_message(message)
        return
    if user_id != task.listener.userId:
        await query.answer("This task is not for you!", show_alert=True)
    elif data[1] == "pin":
        await query.answer(data[3], show_alert=True)
    elif data[1] == "done":
        await query.answer()
        id_ = data[3]
        if hasattr(task, "seeding"):
            if task.listener.isQbit:
                tor_info = (
                    await sync_to_async(xnox_client.torrents_info, torrent_hash=id_)
                )[0]
                path = tor_info.content_path.rsplit("/", 1)[0]
                res = await sync_to_async(
                    xnox_client.torrents_files, torrent_hash=id_
                )
                for f in res:
                    if f.priority == 0:
                        f_paths = [f"{path}/{f.name}", f"{path}/{f.name}.!qB"]
                        for f_path in f_paths:
                            if await aiopath.exists(f_path):
                                with suppress(Exception):
                                    await remove(f_path)
                if not task.queued:
                    await sync_to_async(
                        xnox_client.torrents_resume, torrent_hashes=id_
                    )
            else:
                res = await sync_to_async(aria2.client.get_files, id_)
                for f in res:
                    if f["selected"] == "false" and await aiopath.exists(f["path"]):
                        with suppress(Exception):
                            await remove(f["path"])
                if not task.queued:
                    try:
                        await sync_to_async(aria2.client.unpause, id_)
                    except Exception as e:
                        LOGGER.error(
                            f"{e} Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!"
                        )
        await sendStatusMessage(message)
        await delete_message(message)
    else:
        await delete_message(message)
        await task.cancel_task()


bot.add_handler(CallbackQueryHandler(get_confirm, filters=regex("^sel")))
