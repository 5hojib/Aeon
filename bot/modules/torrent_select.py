import contextlib

from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from bot import LOGGER, bot, aria2, xnox_client
from bot.helper.ext_utils.bot_utils import sync_to_async, get_task_by_gid
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendStatusMessage


async def handle_query(client, query):
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    download = await get_task_by_gid(data[2])

    if not download:
        await query.answer("This task has been cancelled!", show_alert=True)
        await message.delete()
        return

    listener = getattr(download, "listener", None)
    if not listener:
        await query.answer(
            "Not in download state anymore! Keep this message to resume the seed if seed enabled!",
            show_alert=True,
        )
        return

    if (
        user_id != listener().message.from_user.id
        and not await CustomFilters.sudo_user(client, query)
    ):
        await query.answer("This task is not for you!", show_alert=True)
        return

    action = data[1]
    if action == "pin":
        await query.answer(data[3], show_alert=True)
    elif action == "done":
        await handle_done_action(data[3], download, message, query)
    elif action == "rm":
        await download.download().cancel_download()
        await message.delete()


async def handle_done_action(id_, download, message, query):
    await query.answer()

    if len(id_) > 20:
        await handle_torrent_done(id_, download)
    else:
        await handle_aria2_done(id_, download)

    await sendStatusMessage(message)
    await message.delete()


async def handle_torrent_done(torrent_hash, download):
    client = xnox_client
    torrent_info = (
        await sync_to_async(client.torrents_info, torrent_hash=torrent_hash)
    )[0]
    path = torrent_info.content_path.rsplit("/", 1)[0]
    files = await sync_to_async(client.torrents_files, torrent_hash=torrent_hash)

    for file in files:
        if file.priority == 0:
            for file_path in [f"{path}/{file.name}", f"{path}/{file.name}.!qB"]:
                if await aiopath.exists(file_path):
                    with contextlib.suppress(Exception):
                        await aioremove(file_path)

    if not download.queued:
        await sync_to_async(client.torrents_resume, torrent_hashes=torrent_hash)


async def handle_aria2_done(gid, download):
    files = await sync_to_async(aria2.client.get_files, gid)

    for file in files:
        if file["selected"] == "false" and await aiopath.exists(file["path"]):
            with contextlib.suppress(Exception):
                await aioremove(file["path"])

    if not download.queued:
        try:
            await sync_to_async(aria2.client.unpause, gid)
        except Exception as e:
            LOGGER.error(
                f"{e} Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!"
            )


bot.add_handler(CallbackQueryHandler(handle_query, filters=regex("^btsel")))
