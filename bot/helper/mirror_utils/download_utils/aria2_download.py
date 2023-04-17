#!/usr/bin/env python3
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove

from bot import LOGGER, aria2, aria2_options, aria2c_global, config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.mirror_utils.status_utils.aria2_status import Aria2Status
from bot.helper.telegram_helper.message_utils import delete_links, sendMessage, sendStatusMessage


async def add_aria2c_download(link, path, listener, filename, auth, ratio, seed_time):
    a2c_opt = {**aria2_options}
    [a2c_opt.pop(k) for k in aria2c_global if k in aria2_options]
    a2c_opt['dir'] = path
    if filename:
        a2c_opt['out'] = filename
    if auth:
        a2c_opt['header'] = auth
    if ratio:
        a2c_opt['seed-ratio'] = ratio
    if seed_time:
        a2c_opt['seed-time'] = seed_time
    if TORRENT_TIMEOUT := config_dict['TORRENT_TIMEOUT']:
        a2c_opt['bt-stop-timeout'] = f'{TORRENT_TIMEOUT}'
    download = (await sync_to_async(aria2.add, link, a2c_opt))[0]
    if await aiopath.exists(link):
        await aioremove(link)
    if download.error_message:
        error = str(download.error_message).replace('<', ' ').replace('>', ' ')
        LOGGER.info(f"Download Error: {error}")
        await sendMessage(listener.message, error)
        await delete_links(listener.message)
        return
    gid = download.gid
    async with download_dict_lock:
        download_dict[listener.uid] = Aria2Status(gid, listener)
        LOGGER.info(f"Aria2Download started: {gid}")
    await listener.onDownloadStart()
    if not listener.select or not config_dict['BASE_URL']:
        await sendStatusMessage(listener.message)
    elif download.is_torrent and not download.is_metadata:
        await sync_to_async(aria2.client.force_pause, gid)
        SBUTTONS = bt_selection_buttons(gid)
        msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
        await sendMessage(listener.message, msg, SBUTTONS)
