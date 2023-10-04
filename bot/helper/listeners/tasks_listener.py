from random import choice
from time import time
from pytz import timezone
from datetime import datetime
from urllib.parse import unquote, quote
from requests import utils as rutils
from aiofiles.os import path as aiopath, remove as aioremove, listdir, makedirs
from os import walk, path as ospath
from html import escape
from aioshutil import move
from asyncio import create_subprocess_exec, sleep, Event
from pyrogram.enums import ChatType

from bot import OWNER_ID, Interval, aria2, download_dict, download_dict_lock, LOGGER, bot_name, DATABASE_URL, MAX_SPLIT_SIZE, config_dict, status_reply_dict_lock, user_data, non_queued_up, non_queued_dl, queued_up, queued_dl, queue_dict_lock, bot, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import extra_btns, sync_to_async, get_readable_file_size, get_readable_time, is_mega_link, new_thread
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, clean_download, clean_target, is_first_archive_split, is_archive, is_archive_split, join_files
from bot.helper.ext_utils.leech_utils import split_file, format_filename
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.telegram_helper.message_utils import sendCustomMsg, sendMessage, editMessage, delete_all_messages, delete_links, sendMultiMessage, update_all_messages, deleteMessage, five_minute_del
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManager


class MirrorLeechListener:
    def __init__(self, message, compress=False, extract=False, isQbit=False, isLeech=False, tag=None, select=False, seed=False, sameDir=None, rcFlags=None, upPath=None, isClone=False, join=False, isYtdlp=False, drive_id=None, index_link=None, leech_utils={}):
        if sameDir is None:
            sameDir = {}
        self.message = message
        self.uid = message.id
        self.extract = extract
        self.compress = compress
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.isClone = isClone
        self.isYtdlp = isYtdlp
        self.tag = tag
        self.seed = seed
        self.newDir = ""
        self.dir = f"/usr/src/app/downloads/{self.uid}"
        self.select = select
        self.isSuperGroup = message.chat.type in [ChatType.SUPERGROUP, ChatType.CHANNEL]
        self.isPrivate = message.chat.type == ChatType.BOT
        self.suproc = None
        self.sameDir = sameDir
        self.rcFlags = rcFlags
        self.upPath = upPath
        self.random_pic = 'IMAGES'
        self.join = join
        self.linkslogmsg = None
        self.botpmmsg = None
        self.drive_id = drive_id
        self.index_link = index_link
        self.leech_utils = leech_utils

    async def clean(self):
        try:
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            await sync_to_async(aria2.purge)
            await delete_all_messages()
        except:
            pass

    async def onDownloadStart(self):
        if config_dict['LEECH_LOG_ID']:
            msg = f'<b>Task Started</b>\n\n'
            msg += f'<b>• Task by:</b> {self.tag}\n'
            msg += f'<b>• User ID: </b><code>{self.message.from_user.id}</code>'
            self.linkslogmsg = await sendCustomMsg(config_dict['LEECH_LOG_ID'], msg)
        user_dict = user_data.get(self.message.from_user.id, {})
        self.botpmmsg = await sendCustomMsg(self.message.from_user.id, '<b>Task started</b>')

    async def onDownloadComplete(self):
        multi_links = False
        while True:
            if self.sameDir:
                if self.sameDir['total'] in [1, 0] or self.sameDir['total'] > 1 and len(self.sameDir['tasks']) > 1:
                    break
            else:
                break
            await sleep(0.2)
        async with download_dict_lock:
            if self.sameDir and self.sameDir['total'] > 1:
                self.sameDir['tasks'].remove(self.uid)
                self.sameDir['total'] -= 1
                folder_name = self.sameDir['name']
                spath = f"{self.dir}/{folder_name}"
                des_path = f"/usr/src/app/downloads/{list(self.sameDir['tasks'])[0]}/{folder_name}"
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(spath):
                    if item.endswith(('.aria2', '.!qB')):
                        continue
                    item_path = f"{self.dir}/{folder_name}/{item}"
                    if item in await listdir(des_path):
                        await move(item_path, f'{des_path}/{self.uid}-{item}')
                    else:
                        await move(item_path, f'{des_path}/{item}')
                multi_links = True
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f"Download completed: {name}")
        if multi_links:
            await self.onUploadError('Downloaded! Starting other part of the Task...')
            return
        if name == "None" or self.isQbit or not await aiopath.exists(f"{self.dir}/{name}"):
            try:
                files = await listdir(self.dir)
            except Exception as e:
                await self.onUploadError(str(e))
                return
            name = files[-1]
            if name == "yt-dlp-thumb":
                name = files[0]

        dl_path = f"{self.dir}/{name}"
        up_path = ''
        size = await get_path_size(dl_path)
        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        await start_from_queued()
        user_dict = user_data.get(self.message.from_user.id, {})
        
        if self.join:
            if await aiopath.isdir(dl_path):
                await join_files(dl_path)

        if self.extract:
            pswd = self.extract if isinstance(self.extract, str) else ''
            try:
                if await aiopath.isfile(dl_path):
                    up_path = get_base_name(dl_path)
                LOGGER.info(f"Extracting: {name}")
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(
                        name, size, gid, self)
                if await aiopath.isdir(dl_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        up_path = f"{self.newDir}/{name}"
                    else:
                        up_path = dl_path
                    for dirpath, _, files in await sync_to_async(walk, dl_path, topdown=False):
                        for file_ in files:
                            if is_first_archive_split(file_) or is_archive(file_) and not file_.endswith('.rar'):
                                f_path = ospath.join(dirpath, file_)
                                t_path = dirpath.replace(
                                    self.dir, self.newDir) if self.seed else dirpath
                                cmd = ["7z", "x", f"-p{pswd}", f_path, f"-o{t_path}", "-aot", "-xr!@PaxHeader"]
                                if not pswd:
                                    del cmd[2]
                                if self.suproc == 'cancelled' or self.suproc is not None and self.suproc.returncode == -9:
                                    return
                                self.suproc = await create_subprocess_exec(*cmd)
                                code = await self.suproc.wait()
                                if code == -9:
                                    return
                                elif code != 0:
                                    LOGGER.error('Unable to extract archive splits!')
                        if not self.seed and self.suproc is not None and self.suproc.returncode == 0:
                            for file_ in files:
                                if is_archive_split(file_) or is_archive(file_):
                                    del_path = ospath.join(dirpath, file_)
                                    try:
                                        await aioremove(del_path)
                                    except:
                                        return
                else:
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        up_path = up_path.replace(self.dir, self.newDir)
                    cmd = ["7z", "x", f"-p{pswd}", dl_path, f"-o{up_path}", "-aot", "-xr!@PaxHeader"]
                    if not pswd:
                        del cmd[2]
                    if self.suproc == 'cancelled':
                        return
                    self.suproc = await create_subprocess_exec(*cmd)
                    code = await self.suproc.wait()
                    if code == -9:
                        return
                    elif code == 0:
                        LOGGER.info(f"Extracted Path: {up_path}")
                        if not self.seed:
                            try:
                                await aioremove(dl_path)
                            except:
                                return
                    else:
                        LOGGER.error(
                            'Unable to extract archive! Uploading anyway')
                        self.newDir = ""
                        up_path = dl_path
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                up_path = dl_path

        if self.compress:
            pswd = self.compress if isinstance(self.compress, str) else ''
            if up_path:
                dl_path = up_path
                up_path = f"{up_path}.zip"
            elif self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                up_path = f"{self.newDir}/{name}.zip"
            else:
                up_path = f"{dl_path}.zip"
            async with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
            cmd = ["7z", f"-v{LEECH_SPLIT_SIZE}b", "a",
                   "-mx=0", f"-p{pswd}", up_path, dl_path]
            for ext in GLOBAL_EXTENSION_FILTER:
                ex_ext = f'-xr!*.{ext}'
                cmd.append(ex_ext)
            if self.isLeech and int(size) > LEECH_SPLIT_SIZE:
                if not pswd:
                    del cmd[4]
                LOGGER.info(f'Zip: orig_path: {dl_path}, zip_path: {up_path}.0*')
            else:
                del cmd[1]
                if not pswd:
                    del cmd[3]
                LOGGER.info(f'Zip: orig_path: {dl_path}, zip_path: {up_path}')
            if self.suproc == 'cancelled':
                return
            self.suproc = await create_subprocess_exec(*cmd)
            code = await self.suproc.wait()
            if code == -9:
                return
            elif not self.seed:
                await clean_target(dl_path)

        if not self.compress and not self.extract:
            up_path = dl_path

        up_dir, up_name = up_path.rsplit('/', 1)
        size = await get_path_size(up_dir)
        if self.isLeech:
            m_size = []
            o_files = []
            if not self.compress:
                checked = False
                LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
                for dirpath, _, files in await sync_to_async(walk, up_dir, topdown=False):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = await aiopath.getsize(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(up_name, size, gid, self)
                                LOGGER.info(f"Splitting: {up_name}")
                            res = await split_file(f_path, f_size, file_, dirpath, LEECH_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= MAX_SPLIT_SIZE:
                                    continue
                                try:
                                    await aioremove(f_path)
                                except:
                                    return
                            elif not self.seed or self.newDir:
                                try:
                                    await aioremove(f_path)
                                except:
                                    return
                            else:
                                m_size.append(f_size)
                                o_files.append(file_)

        up_limit = config_dict['QUEUE_UPLOAD']
        all_limit = config_dict['QUEUE_ALL']
        added_to_queue = False
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not up_limit or up >= up_limit)) or (up_limit and up >= up_limit):
                added_to_queue = True
                LOGGER.info(f"Added to Queue/Upload: {name}")
                event = Event()
                queued_up[self.uid] = event
        if added_to_queue:
            async with download_dict_lock:
                download_dict[self.uid] = QueueStatus(
                    name, size, gid, self, 'Up')
            await event.wait()
            async with download_dict_lock:
                if self.uid not in download_dict:
                    return
            LOGGER.info(f'Start from Queued/Upload: {name}')
        async with queue_dict_lock:
            non_queued_up.add(self.uid)
        if self.isLeech:
            size = await get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, self)
            tg_upload_status = TelegramStatus(
                tg, size, self.message, gid, 'up')
            async with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            await update_all_messages()
            await tg.upload(o_files, m_size, size)
        elif self.upPath == 'gd':
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, self)
            upload_status = GdriveStatus(drive, size, self.message, gid, 'up')
            async with download_dict_lock:
                download_dict[self.uid] = upload_status
            await update_all_messages()
            await sync_to_async(drive.upload, up_name, size, self.drive_id)
        else:
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name} via RClone")
            RCTransfer = RcloneTransferHelper(self, up_name)
            async with download_dict_lock:
                download_dict[self.uid] = RcloneStatus(
                    RCTransfer, self.message, gid, 'up')
            await update_all_messages()
            await RCTransfer.upload(up_path, size)

    async def onUploadComplete(self, link, size, files, folders, mime_type, name, rclonePath=''):
        user_id = self.message.from_user.id
        name, _ = await format_filename(name, user_id, isMirror=not self.isLeech)
        user_dict = user_data.get(user_id, {})
        msg = f'{escape(name)}\n\n'
        msg += f'<b>• Size: </b>{get_readable_file_size(size)}\n'
        msg += f'<b>• Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
        LOGGER.info(f'Task Done: {name}')
        buttons = ButtonMaker()
        iButton = ButtonMaker()
        iButton.ibutton('View in inbox', f"aeon {user_id} botpm", 'header')
        iButton = extra_btns(iButton)
        if self.isLeech:
            if folders > 1:
                msg += f'<b>• Total files: </b>{folders}\n'
            if mime_type != 0:
                msg += f'<b>• Corrupted files: </b>{mime_type}\n'
            msg += f'<b>• Uploaded by: </b>{self.tag}\n'
            msg += f'<b>• User ID: </b><code>{self.message.from_user.id}</code>\n\n'
            if not files:
                if self.isPrivate:
                    msg += '<b>Files have not been sent for an unspecified reason</b>'
                await sendMessage(self.message, msg)
            else:
                attachmsg = True
                fmsg, totalmsg = '\n\n', ''
                lmsg = '<b>Files have been sent. Access them via the provided links.</b>'
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    totalmsg = (msg + lmsg + fmsg) if attachmsg else fmsg
                    if len(totalmsg.encode()) > 3900:
                        if self.linkslogmsg:
                            await editMessage(self.linkslogmsg, totalmsg)
                            await sendMessage(self.botpmmsg,  totalmsg)
                            self.linkslogmsg = await sendMessage(self.linkslogmsg, "Fetching Details...")
                        attachmsg = False
                        await sleep(1)
                        fmsg = '\n\n'
                if fmsg != '\n\n':
                    if self.linkslogmsg:
                        await sendMessage(self.linkslogmsg, msg + lmsg + fmsg)
                        await deleteMessage(self.linkslogmsg)
                await sendMessage(self.botpmmsg, msg + lmsg + fmsg)
                await deleteMessage(self.botpmmsg)
                if self.isSuperGroup:
                    await sendMessage(self.message, f'{msg}<b>Files has been sent to your inbox</b>', iButton.build_menu(1))
                else:
                    await deleteMessage(self.botpmmsg)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return
        else:
            if mime_type == "Folder":
                msg += f'<b>• Total files: </b>{files}\n'
            if link:
                buttons.ubutton('Cloud link', link)
                INDEX_URL = self.index_link if self.drive_id else config_dict['INDEX_URL']
                if not rclonePath:
                    if INDEX_URL:
                        drive = GoogleDriveHelper()
                        dir_id = drive.getIdFromUrl(link)
                        share_url = f'{INDEX_URL}findpath?id={dir_id}'
                        buttons.ubutton('Index link', share_url)
                buttons = extra_btns(buttons)
                button = buttons.build_menu(2)
            elif rclonePath:
                msg += f'<b>• Path: </b><code>{rclonePath}</code>\n'
                button = None
                buttons = extra_btns(buttons)
                button = buttons.build_menu(2)
            msg += f'<b>• Uploaded by: </b>{self.tag}\n'
            msg += f'<b>• User ID: </b><code>{self.message.from_user.id}</code>\n\n'

            if config_dict['MIRROR_LOG_ID']:
                log_msg = list((await sendMultiMessage(config_dict['MIRROR_LOG_ID'], msg, button)).values())[0]
                if self.linkslogmsg:
                    await deleteMessage(self.linkslogmsg)
            await sendMessage(self.botpmmsg, msg, button, self.random_pic)
            await deleteMessage(self.botpmmsg)
            if self.isSuperGroup:
                await sendMessage(self.message, f'{msg} <b>Links has been sent to your inbox</b>', iButton.build_menu(1))
            else:
                await deleteMessage(self.botpmmsg)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                elif self.compress:
                    await clean_target(f"{self.dir}/{name}")
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return

        await clean_download(self.dir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        async with queue_dict_lock:
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await delete_links(self.message)

    async def onDownloadError(self, error, button=None):
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
            if self.sameDir and self.uid in self.sameDir['tasks']:
                self.sameDir['tasks'].remove(self.uid)
                self.sameDir['total'] -= 1
        msg = f'Hey, {self.tag}!\n'
        msg += 'Your download has been stopped!\n\n'
        msg += f'<b>Reason:</b> {escape(error)}\n'
        msg += f'<b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}'
        x = await sendMessage(self.message, msg, button)
        await delete_links(self.message)
        if self.botpmmsg:
        	  await deleteMessage(self.botpmmsg)
        if self.linkslogmsg:
            await deleteMessage(self.linkslogmsg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()
        if self.isSuperGroup and self.botpmmsg:
            await sendMessage(self.botpmmsg, msg, button)
        await five_minute_del(x)
        
        async with queue_dict_lock:
            if self.uid in queued_dl:
                queued_dl[self.uid].set()
                del queued_dl[self.uid]
            if self.uid in queued_up:
                queued_up[self.uid].set()
                del queued_up[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
    
    async def onUploadError(self, error):
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        msg = f'Hey, {self.tag}!\n'
        msg += 'Your upload has been stopped!\n\n'
        msg += f'<b>Reason:</b> {escape(error)}\n'
        msg += f'<b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}'
        x = await sendMessage(self.message, msg)
        if self.linkslogmsg:
            await deleteMessage(self.linkslogmsg)
        await delete_links(self.message)
        if self.botpmmsg:
         	  await deleteMessage(self.botpmmsg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()
        if self.isSuperGroup and self.botpmmsg:
            await sendMessage(self.botpmmsg, msg)
        await five_minute_del(x)
        
        async with queue_dict_lock:
            if self.uid in queued_dl:
                queued_dl[self.uid].set()
                del queued_dl[self.uid]
            if self.uid in queued_up:
                queued_up[self.uid].set()
                del queued_up[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
