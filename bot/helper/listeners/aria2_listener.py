from asyncio import sleep
from time import time
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from bot import LOGGER, aria2, config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, get_telegraph_list, getDownloadByGid, new_thread, sync_to_async
from bot.helper.ext_utils.fs_utils import clean_unwanted, get_base_name
from bot.helper.ext_utils.task_manager import limit_checker
from bot.helper.mirror_utils.status_utils.aria2_status import Aria2Status
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import deleteMessage, delete_links, sendMessage, update_all_messages


@new_thread
async def __onDownloadStarted(api, gid):
    download = await sync_to_async(api.get_download, gid)
    if download.options.follow_torrent == 'false':
        return
    if download.is_metadata:
        LOGGER.info(f'onDownloadStarted: {gid} METADATA')
        await sleep(1)
        if dl := await getDownloadByGid(gid):
            listener = dl.listener()
            if listener.select:
                metamsg = "Downloading Metadata, wait then you can select files. Use torrent file to avoid this wait."
                meta = await sendMessage(listener.message, metamsg)
                while True:
                    await sleep(0.5)
                    if download.is_removed or download.followed_by_ids:
                        await deleteMessage(meta)
                        break
                    download = download.live
        return
    else:
        LOGGER.info(f'onDownloadStarted: {download.name} - Gid: {gid}')
    dl = None
    if config_dict['STOP_DUPLICATE']:
        await sleep(1)
        if dl is None:
            dl = await getDownloadByGid(gid)
        if dl:
            if not hasattr(dl, 'listener'):
                LOGGER.warning(
                    f"onDownloadStart: {gid}. STOP_DUPLICATE didn't pass since download completed earlier!")
                return
            listener = dl.listener()
            if not listener.isLeech and not listener.select and listener.upPath == 'gd':
                download = await sync_to_async(api.get_download, gid)
                if not download.is_torrent:
                    await sleep(3)
                    download = download.live
                LOGGER.info('Checking File/Folder if already in Drive...')
                name = download.name
                if listener.compress:
                    name = f"{name}.zip"
                elif listener.extract:
                    try:
                        name = get_base_name(name)
                    except:
                        name = None
                if name is not None:
                    telegraph_content, contents_no = await sync_to_async(GoogleDriveHelper().drive_list, name, True)
                    if telegraph_content:
                        msg = f"File/Folder is already available in Drive.\nHere are {contents_no} list results:"
                        button = await get_telegraph_list(telegraph_content)
                        await listener.onDownloadError(msg, button)
                        await sync_to_async(api.remove, [download], force=True, files=True)
                        await delete_links(listener.message)
                        return
    if any([config_dict['DIRECT_LIMIT'],
            config_dict['TORRENT_LIMIT'],
            config_dict['LEECH_LIMIT'],
            config_dict['STORAGE_THRESHOLD']]):
        await sleep(1)
        if dl is None:
            dl = await getDownloadByGid(gid)
        if dl is not None:
            if not hasattr(dl, 'listener'):
                LOGGER.warning(
                    f"onDownloadStart: {gid}. at Download limit didn't pass since download completed earlier!")
                return
            listener = dl.listener()
            download = await sync_to_async(api.get_download, gid)
            download = download.live
            if download.total_length == 0:
                start_time = time()
                while time() - start_time <= 15:
                    await sleep(0.5)
                    download = await sync_to_async(api.get_download, gid)
                    download = download.live
                    if download.followed_by_ids:
                        download = await sync_to_async(api.get_download, download.followed_by_ids[0])
                    if download.total_length > 0:
                        break
            size = download.total_length
            if limit_exceeded := await limit_checker(size, listener, download.is_torrent):
                await listener.onDownloadError(limit_exceeded)
                await sync_to_async(api.remove, [download], force=True, files=True)
                await delete_links(listener.message)


@new_thread
async def __onDownloadComplete(api, gid):
    try:
        download = await sync_to_async(api.get_download, gid)
    except:
        return
    if download.options.follow_torrent == 'false':
        return
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f'Gid changed from {gid} to {new_gid}')
        if dl := await getDownloadByGid(new_gid):
            listener = dl.listener()
            if config_dict['BASE_URL'] and listener.select:
                if not dl.queued:
                    await sync_to_async(api.client.force_pause, new_gid)
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
                await sendMessage(listener.message, msg, SBUTTONS)
    elif download.is_torrent:
        if dl := await getDownloadByGid(gid):
            if hasattr(dl, 'listener') and dl.seeding:
                LOGGER.info(
                    f"Cancelling Seed: {download.name} onDownloadComplete")
                listener = dl.listener()
                await listener.onUploadError(f"Seeding stopped with Ratio: {dl.ratio()} and Time: {dl.seeding_time()}")
                await sync_to_async(api.remove, [download], force=True, files=True)
    else:
        LOGGER.info(f"onDownloadComplete: {download.name} - Gid: {gid}")
        if dl := await getDownloadByGid(gid):
            listener = dl.listener()
            await listener.onDownloadComplete()
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def __onBtDownloadComplete(api, gid):
    seed_start_time = time()
    await sleep(1)
    download = await sync_to_async(api.get_download, gid)
    if download.options.follow_torrent == 'false':
        return
    LOGGER.info(f"onBtDownloadComplete: {download.name} - Gid: {gid}")
    if dl := await getDownloadByGid(gid):
        listener = dl.listener()
        if listener.select:
            res = download.files
            for file_o in res:
                f_path = file_o.path
                if not file_o.selected and await aiopath.exists(f_path):
                    try:
                        await aioremove(f_path)
                    except:
                        pass
            await clean_unwanted(download.dir)
        if listener.seed:
            try:
                await sync_to_async(api.set_options, {'max-upload-limit': '0'}, [download])
            except Exception as e:
                LOGGER.error(
                    f'{e} You are not able to seed because you added global option seed-time=0 without adding specific seed_time for this torrent GID: {gid}')
        else:
            try:
                await sync_to_async(api.client.force_pause, gid)
            except Exception as e:
                LOGGER.error(f"{e} GID: {gid}")
        await listener.onDownloadComplete()
        download = download.live
        if listener.seed:
            if download.is_complete:
                if dl := await getDownloadByGid(gid):
                    LOGGER.info(f"Cancelling Seed: {download.name}")
                    await listener.onUploadError(f"Seeding stopped with Ratio: {dl.ratio()} and Time: {dl.seeding_time()}")
                    await sync_to_async(api.remove, [download], force=True, files=True)
            else:
                async with download_dict_lock:
                    if listener.uid not in download_dict:
                        await sync_to_async(api.remove, [download], force=True, files=True)
                        return
                    download_dict[listener.uid] = Aria2Status(
                        gid, listener, True)
                    download_dict[listener.uid].start_time = seed_start_time
                LOGGER.info(f"Seeding started: {download.name} - Gid: {gid}")
                await update_all_messages()
        else:
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def __onDownloadStopped(api, gid):
    await sleep(6)
    if dl := await getDownloadByGid(gid):
        listener = dl.listener()
        await listener.onDownloadError('Dead torrent!')


@new_thread
async def __onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    error = "None"
    try:
        download = await sync_to_async(api.get_download, gid)
        if download.options.follow_torrent == 'false':
            return
        error = download.error_message
        LOGGER.info(f"Download Error: {error}")
    except:
        pass
    if dl := await getDownloadByGid(gid):
        listener = dl.listener()
        await listener.onDownloadError(error)


def start_aria2_listener():
    aria2.listen_to_notifications(threaded=False,
                                  on_download_start=__onDownloadStarted,
                                  on_download_error=__onDownloadError,
                                  on_download_stop=__onDownloadStopped,
                                  on_download_complete=__onDownloadComplete,
                                  on_bt_download_complete=__onBtDownloadComplete,
                                  timeout=60)