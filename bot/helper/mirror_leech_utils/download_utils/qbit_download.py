from time import time

from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove

from bot import (
    LOGGER,
    config_dict,
    xnox_client,
    download_dict,
    non_queued_dl,
    queue_dict_lock,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import sync_to_async, bt_selection_buttons
from bot.helper.ext_utils.task_manager import is_queued
from bot.helper.listeners.qbit_listener import on_download_start
from bot.helper.telegram_helper.message_utils import (
    send_message,
    delete_message,
    sendStatusMessage,
)
from bot.helper.mirror_leech_utils.status_utils.qbit_status import QbittorrentStatus


async def add_qb_torrent(link, path, listener, ratio, seed_time):
    ADD_TIME = time()
    try:
        url = link
        tpath = None
        if await aiopath.exists(link):
            url = None
            tpath = link
        added_to_queue, event = await is_queued(listener.uid)
        op = await sync_to_async(
            xnox_client.torrents_add,
            url,
            tpath,
            path,
            is_paused=added_to_queue,
            tags=f"{listener.uid}",
            ratio_limit=ratio,
            seeding_time_limit=seed_time,
            headers={"user-agent": "Wget/1.12"},
        )
        if op.lower() == "ok.":
            tor_info = await sync_to_async(
                xnox_client.torrents_info, tag=f"{listener.uid}"
            )
            if len(tor_info) == 0:
                while True:
                    tor_info = await sync_to_async(
                        xnox_client.torrents_info, tag=f"{listener.uid}"
                    )
                    if len(tor_info) > 0:
                        break
                    if time() - ADD_TIME >= 120:
                        await listener.onDownloadError(
                            "Not added! Check if the link is valid or not. If it's torrent file then report, this happens if torrent file size above 10mb."
                        )
                        return
            tor_info = tor_info[0]
            ext_hash = tor_info.hash
        else:
            await listener.onDownloadError(
                "This Torrent already added or unsupported/invalid link/file."
            )
            return

        async with download_dict_lock:
            download_dict[listener.uid] = QbittorrentStatus(
                listener, queued=added_to_queue
            )
        await on_download_start(f"{listener.uid}")

        if added_to_queue:
            LOGGER.info(
                f"Added to Queue/Download: {tor_info.name} - Hash: {ext_hash}"
            )
        else:
            async with queue_dict_lock:
                non_queued_dl.add(listener.uid)
            LOGGER.info(f"QbitDownload started: {tor_info.name} - Hash: {ext_hash}")

        await listener.on_download_start()

        if config_dict["BASE_URL"] and listener.select:
            if link.startswith("magnet:"):
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await send_message(listener.message, metamsg)
                while True:
                    tor_info = await sync_to_async(
                        xnox_client.torrents_info, tag=f"{listener.uid}"
                    )
                    if len(tor_info) == 0:
                        await delete_message(meta)
                        return
                    try:
                        tor_info = tor_info[0]
                        if tor_info.state not in [
                            "metaDL",
                            "checkingResumeData",
                            "pausedDL",
                        ]:
                            await delete_message(meta)
                            break
                    except Exception:
                        await delete_message(meta)
                        return

            ext_hash = tor_info.hash
            if not added_to_queue:
                await sync_to_async(
                    xnox_client.torrents_pause, torrent_hashes=ext_hash
                )
            s_buttons = bt_selection_buttons(ext_hash)
            msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
            await send_message(listener.message, msg, s_buttons)
        else:
            await sendStatusMessage(listener.message)

        if added_to_queue:
            await event.wait()

            async with download_dict_lock:
                if listener.uid not in download_dict:
                    return
                download_dict[listener.uid].queued = False

            await sync_to_async(xnox_client.torrents_resume, torrent_hashes=ext_hash)
            LOGGER.info(
                f"Start Queued Download from Qbittorrent: {tor_info.name} - Hash: {ext_hash}"
            )

            async with queue_dict_lock:
                non_queued_dl.add(listener.uid)
    except Exception as e:
        await send_message(listener.message, str(e))
    finally:
        if await aiopath.exists(link):
            await aioremove(link)
