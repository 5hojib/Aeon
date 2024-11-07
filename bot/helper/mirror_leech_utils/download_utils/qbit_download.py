from asyncio import sleep

from aiofiles.os import path as aiopath
from aiofiles.os import remove

from bot import (
    LOGGER,
    task_dict,
    config_dict,
    xnox_client,
    non_queued_dl,
    task_dict_lock,
    queue_dict_lock,
)
from bot.helper.ext_utils.bot_utils import sync_to_async, bt_selection_buttons
from bot.helper.ext_utils.task_manager import check_running_tasks
from bot.helper.listeners.qbit_listener import on_download_start
from bot.helper.telegram_helper.message_utils import (
    send_message,
    delete_message,
    sendStatusMessage,
)
from bot.helper.mirror_leech_utils.status_utils.qbit_status import QbittorrentStatus


async def add_qb_torrent(listener, path, ratio, seed_time):
    try:
        url = listener.link
        tpath = None
        if await aiopath.exists(listener.link):
            url = None
            tpath = listener.link
        add_to_queue, event = await check_running_tasks(listener)
        op = await sync_to_async(
            xnox_client.torrents_add,
            url,
            tpath,
            path,
            is_paused=add_to_queue,
            tags=f"{listener.mid}",
            ratio_limit=ratio,
            seeding_time_limit=seed_time,
            headers={"user-agent": "Wget/1.12"},
        )
        if op.lower() == "ok.":
            tor_info = await sync_to_async(
                xnox_client.torrents_info, tag=f"{listener.mid}"
            )
            if len(tor_info) == 0:
                while True:
                    tor_info = await sync_to_async(
                        xnox_client.torrents_info, tag=f"{listener.mid}"
                    )
                    if len(tor_info) > 0:
                        break
                    await sleep(1)
            tor_info = tor_info[0]
            listener.name = tor_info.name
            ext_hash = tor_info.hash
        else:
            await listener.onDownloadError(
                "This Torrent already added or unsupported/invalid link/file.",
            )
            return

        async with task_dict_lock:
            task_dict[listener.mid] = QbittorrentStatus(
                listener, queued=add_to_queue
            )
        await on_download_start(f"{listener.mid}")

        if add_to_queue:
            LOGGER.info(
                f"Added to Queue/Download: {tor_info.name} - Hash: {ext_hash}"
            )
        else:
            LOGGER.info(f"QbitDownload started: {tor_info.name} - Hash: {ext_hash}")

        await listener.on_download_start()

        if config_dict["BASE_URL"] and listener.select:
            if listener.link.startswith("magnet:"):
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await send_message(listener.message, metamsg)
                while True:
                    tor_info = await sync_to_async(
                        xnox_client.torrents_info, tag=f"{listener.mid}"
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
            if not add_to_queue:
                await sync_to_async(
                    xnox_client.torrents_pause, torrent_hashes=ext_hash
                )
            SBUTTONS = bt_selection_buttons(ext_hash)
            msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
            await send_message(listener.message, msg, SBUTTONS)
        elif listener.multi <= 1:
            await sendStatusMessage(listener.message)

        if add_to_queue:
            await event.wait()
            if listener.isCancelled:
                return
            async with queue_dict_lock:
                non_queued_dl.add(listener.mid)
            async with task_dict_lock:
                task_dict[listener.mid].queued = False

            await sync_to_async(xnox_client.torrents_resume, torrent_hashes=ext_hash)
            LOGGER.info(
                f"Start Queued Download from Qbittorrent: {tor_info.name} - Hash: {ext_hash}"
            )
    except Exception as e:
        await listener.onDownloadError(f"{e}")
    finally:
        if tpath and await aiopath.exists(listener.link):
            await remove(listener.link)
