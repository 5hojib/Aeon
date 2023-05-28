#!/usr/bin/env python3
from asyncio import Event, create_subprocess_exec, sleep
from html import escape
from os import path as ospath
from os import walk
from time import time
from urllib.parse import quote as url_quote

from aiofiles.os import listdir, makedirs
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from aioshutil import move

from bot import (DATABASE_URL, DOWNLOAD_DIR, LOGGER, MAX_SPLIT_SIZE, Interval,
                 aria2, config_dict, download_dict, download_dict_lock,
                 non_queued_dl, non_queued_up, queue_dict_lock, queued_dl,
                 queued_up, status_reply_dict_lock, user_data, GLOBAL_EXTENSION_FILTER)
from bot.helper.ext_utils.bot_utils import (extra_btns, get_readable_file_size,
                                            get_readable_time, sync_to_async)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.fs_utils import (clean_download, clean_target,
                                           get_base_name, get_path_size,
                                           is_archive, is_archive_split,
                                           is_first_archive_split)
from bot.helper.ext_utils.leech_utils import split_file
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (delete_all_messages,
                                                      delete_links,
                                                      send_to_chat,
                                                      sendMessage,
                                                      update_all_messages)


class MirrorLeechListener:
    def __init__(self, message, isZip=False, extract=False, isQbit=False,
                 isLeech=False, pswd=None, tag=None, select=False,
                 seed=False, sameDir=None, rcFlags=None, upPath=None, isClone=False, raw_url=None,
                 drive_id=None, index_link=None, dmMessage=None, logMessage=None):
        if not sameDir:
            sameDir = {}
        self.message = message
        self.uid = message.id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.pswd = pswd
        self.tag = tag
        self.seed = seed
        self.newDir = ""
        self.dir = f"{DOWNLOAD_DIR}{self.uid}"
        self.select = select
        self.isSuperGroup = self.message.chat.type in [
            self.message.chat.type.SUPERGROUP, self.message.chat.type.CHANNEL]
        self.suproc = None
        self.sameDir = sameDir
        self.rcFlags = rcFlags
        self.upPath = upPath
        self.isClone = isClone
        self.raw_url = raw_url
        self.drive_id = drive_id
        self.index_link = index_link
        self.dmMessage = dmMessage
        self.logMessage = logMessage
        self.extra_details = {'startTime': time()}
        self.__setMode()
        self.__source()

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

    def __setMode(self):
        if self.isLeech:
            mode = 'Leech'
        elif self.isClone:
            mode = 'Clone'
        elif self.upPath != 'gd':
            mode = 'Rclone'
        else:
            mode = 'Drive'
        if self.isZip:
            mode += ' as Zip'
        elif self.extract:
            mode += ' as Unzip'
        self.extra_details['mode'] = mode

    def __source(self):
        if sender_chat := self.message.sender_chat:
            source = sender_chat.title
        else:
            source = self.message.from_user.username or self.message.from_user.id
        if reply_to := self.message.reply_to_message:
            if sender_chat := reply_to.sender_chat:
                source = reply_to.sender_chat.title
            elif not reply_to.from_user.is_bot:
                source = reply_to.from_user.username or reply_to.from_user.id
        if self.isSuperGroup:
            self.extra_details['source'] = f"<a href='{self.message.link}'>{source}</a>"
        else:
            self.extra_details['source'] = f"<i>{source}</i>"

    async def onDownloadStart(self):
        if self.dmMessage == 'BotStarted':
            self.dmMessage = await send_to_chat(self.message._client, self.message.from_user.id, self.message.link)
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().add_download_url(self.raw_url, self.tag)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    async def onDownloadComplete(self):
        multi_links = False
        while True:
            if self.sameDir:
                if self.sameDir['total'] == 1 or self.sameDir['total'] > 1 and len(self.sameDir['tasks']) > 1:
                    break
            else:
                break
            await sleep(0)
        async with download_dict_lock:
            if self.sameDir and self.sameDir['total'] > 1:
                self.sameDir['tasks'].remove(self.uid)
                self.sameDir['total'] -= 1
                folder_name = (await listdir(self.dir))[-1]
                path = f"{self.dir}/{folder_name}"
                des_path = f"{DOWNLOAD_DIR}{list(self.sameDir['tasks'])[0]}/{folder_name}"
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(path):
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
            await self.onUploadError('Downloaded! Waiting for other tasks...')
            return
        if name == "None" or self.isQbit or not await aiopath.exists(f"{self.dir}/{name}"):
            files = await listdir(self.dir)
            name = files[-1]
            if name == "yt-dlp-thumb":
                name = files[0]
        m_path = f"{self.dir}/{name}"
        size = await get_path_size(m_path)
        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        await start_from_queued()
        user_dict = user_data.get(self.message.from_user.id, {})
        if self.isZip:
            if self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                path = f"{self.newDir}/{name}.zip"
            else:
                path = f"{m_path}.zip"
            async with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            LEECH_SPLIT_SIZE = user_dict.get(
                'split_size', False) or config_dict['LEECH_SPLIT_SIZE']
            LEECH_SPLIT_SIZE = min(LEECH_SPLIT_SIZE, MAX_SPLIT_SIZE)
            cmd = ["7z", f"-v{LEECH_SPLIT_SIZE}b", "a",
                   "-mx=0", f"-p{self.pswd}", path, m_path]
            for ext in GLOBAL_EXTENSION_FILTER:
                ex_ext = f'-xr!*.{ext}'
                cmd.append(ex_ext)
            if self.isLeech and int(size) > LEECH_SPLIT_SIZE:
                if self.pswd is None:
                    del cmd[4]
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
            else:
                del cmd[1]
                if self.pswd is None:
                    del cmd[3]
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
            if self.suproc == 'cancelled':
                return
            self.suproc = await create_subprocess_exec(*cmd)
            code = await self.suproc.wait()
            if code == -9:
                return
            elif not self.seed:
                await clean_target(m_path)
        elif self.extract:
            try:
                if await aiopath.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(
                        name, size, gid, self)
                if await aiopath.isdir(m_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        path = f"{self.newDir}/{name}"
                    else:
                        path = m_path
                    for dirpath, subdir, files in await sync_to_async(walk, m_path, topdown=False):
                        for file_ in files:
                            if is_first_archive_split(file_) or is_archive(file_) and not file_.endswith('.rar'):
                                f_path = ospath.join(dirpath, file_)
                                t_path = dirpath.replace(
                                    self.dir, self.newDir) if self.seed else dirpath
                                cmd = [
                                    "7z", "x", f"-p{self.pswd}", f_path, f"-o{t_path}", "-aot", "-xr!@PaxHeader"]
                                if self.pswd is None:
                                    del cmd[2]
                                if self.suproc == 'cancelled' or self.suproc is not None and self.suproc.returncode == -9:
                                    return
                                self.suproc = await create_subprocess_exec(*cmd)
                                code = await self.suproc.wait()
                                if code == -9:
                                    return
                                elif code != 0:
                                    LOGGER.error(
                                        'Unable to extract archive splits!')
                        if not self.seed and self.suproc is not None and self.suproc.returncode == 0:
                            for file_ in files:
                                if is_archive_split(file_) or is_archive(file_):
                                    del_path = ospath.join(dirpath, file_)
                                    try:
                                        await aioremove(del_path)
                                    except:
                                        return
                else:
                    if self.seed and self.isLeech:
                        self.newDir = f"{self.dir}10000"
                        path = path.replace(self.dir, self.newDir)
                    cmd = ["7z", "x", f"-p{self.pswd}", m_path,
                           f"-o{path}", "-aot", "-xr!@PaxHeader"]
                    if self.pswd is None:
                        del cmd[2]
                    if self.suproc == 'cancelled':
                        return
                    self.suproc = await create_subprocess_exec(*cmd)
                    code = await self.suproc.wait()
                    if code == -9:
                        return
                    elif code == 0:
                        LOGGER.info(f"Extracted Path: {path}")
                        if not self.seed:
                            try:
                                await aioremove(m_path)
                            except:
                                return
                    else:
                        LOGGER.error(
                            'Unable to extract archive! Uploading anyway')
                        self.newDir = ""
                        path = m_path
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                path = m_path
        else:
            path = m_path
        up_dir, up_name = path.rsplit('/', 1)
        size = await get_path_size(up_dir)
        if self.isLeech:
            m_size = []
            o_files = []
            if not self.isZip:
                checked = False
                LEECH_SPLIT_SIZE = user_dict.get(
                    'split_size', False) or config_dict['LEECH_SPLIT_SIZE']
                LEECH_SPLIT_SIZE = min(LEECH_SPLIT_SIZE, MAX_SPLIT_SIZE)
                for dirpath, _, files in await sync_to_async(walk, up_dir, topdown=False):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = await aiopath.getsize(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(
                                        up_name, size, gid, self)
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
                tg, size, self.message, gid, 'up', self.extra_details)
            async with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            await update_all_messages()
            await tg.upload(o_files, m_size, size)
        elif self.upPath == 'gd':
            size = await get_path_size(path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, self)
            upload_status = GdriveStatus(
                drive, size, self.message, gid, 'up', self.extra_details)
            async with download_dict_lock:
                download_dict[self.uid] = upload_status
            await update_all_messages()
            await sync_to_async(drive.upload, up_name, size, self.drive_id)
        else:
            size = await get_path_size(path)
            LOGGER.info(f"Upload Name: {up_name}")
            RCTransfer = RcloneTransferHelper(self, up_name)
            async with download_dict_lock:
                download_dict[self.uid] = RcloneStatus(
                    RCTransfer, self.message, gid, 'up', self.extra_details)
            await update_all_messages()
            await RCTransfer.upload(path, size)

    async def onUploadComplete(self, link, size, files, folders, mime_type, name, rclonePath=''):
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().remove_download(self.raw_url)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)
        msg = f"<i><b>{escape(name)}</b></i>\n"
        msg += f"\n<b>• Size: </b>{get_readable_file_size(size)}"
        LOGGER.info(f'Task Done: {name}')
        if self.isLeech:
            msg += f'\n<b>• Total Files</b>: {folders}'
            msg += f"\n<b>• Elapsed</b>: {get_readable_time(time() - self.extra_details['startTime'])}"
            if mime_type != 0:
                msg += f'\n<b>• Corrupted Files</b>: {mime_type}'
            msg += f'\n<b>• Leeched by</b>: {self.tag}\n\n'
            if not files:
                await sendMessage(self.message, msg)
                if self.logMessage:
                    await sendMessage(self.logMessage, msg)
            elif self.dmMessage and not config_dict['DUMP_CHAT_ID']:
                await sendMessage(self.dmMessage, msg)
                msg += '<b>Files has been sent in your DM.</b>'
                await sendMessage(self.message, msg)
                if self.logMessage:
                    await sendMessage(self.logMessage, msg)
            else:
                fmsg = ''
                buttons = ButtonMaker()
                buttons = extra_btns(buttons)
                if self.isSuperGroup and not self.message.chat.has_protected_content:
                    buttons.ibutton('Save This Message', 'save', 'footer')
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        if self.logMessage:
                            await sendMessage(self.logMessage, msg + fmsg)
                        await sendMessage(self.message, msg + fmsg, buttons.build_menu(2))
                        await sleep(1)
                        fmsg = ''
                if fmsg != '':
                    if self.logMessage:
                        await sendMessage(self.logMessage, msg + fmsg)
                    await sendMessage(self.message, msg + fmsg, buttons.build_menu(2))
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return
        else:
            msg += f'\n<b>• Type: </b>{mime_type}'
            if mime_type == "Folder":
                msg += f'\n<b>• SubFolders: </b>{folders}'
                msg += f'\n<b>• Files: </b>{files}'
            msg += f'\n<b>• Uploaded by</b>: {self.tag}'
            msg += f'\n<b>• Elapsed</b>: {get_readable_time(time() - self.extra_details["startTime"])}'
            if link or rclonePath and config_dict['RCLONE_SERVE_URL']:
                buttons = ButtonMaker()
                if link:
                    buttons.ubutton("Drive Link", link)
                else:
                    msg += f'\n\n<b>Path</b>: <code>{rclonePath}</code>'
                if rclonePath and (RCLONE_SERVE_URL := config_dict['RCLONE_SERVE_URL']):
                    remote, path = rclonePath.split(':', 1)
                    url_path = url_quote(f'{path}')
                    share_url = f'{RCLONE_SERVE_URL}/{remote}/{url_path}'
                    if mime_type == "Folder":
                        share_url += '/'
                    buttons.ubutton("Rclone Link", share_url)
                elif not rclonePath:
                    INDEX_URL = self.index_link if self.drive_id else config_dict['INDEX_URL']
                    if INDEX_URL:
                        url_path = url_quote(f'{name}')
                        share_url = f'{INDEX_URL}/{url_path}'
                        if mime_type == "Folder":
                            share_url += '/'
                            buttons.ubutton("Index Link", share_url)
                        else:
                            buttons.ubutton("Index Link", share_url)
                            if mime_type.startswith(('image', 'video', 'audio')):
                                share_urls = f'{INDEX_URL}/{url_path}?a=view'
                                buttons.ubutton("View Link", share_urls)
                buttons = extra_btns(buttons)
                if self.dmMessage:
                    msg += '\n\n<b>Links has been sent in your DM.</b>'
                    await sendMessage(self.message, msg)
                    await sendMessage(self.dmMessage, msg, buttons.build_menu(2))
                else:
                    if self.isSuperGroup and not self.message.chat.has_protected_content:
                        buttons.ibutton("Save This Message", 'save', 'footer')
                    await sendMessage(self.message, msg, buttons.build_menu(2))
                if self.logMessage:
                    await sendMessage(self.logMessage, msg, buttons.build_menu(2))
            else:
                msg += f'\n\nPath: <code>{rclonePath}</code>'
                await sendMessage(self.message, msg)
                if self.logMessage:
                    await sendMessage(self.logMessage, msg)
            if self.seed and not self.isClone:
                if self.isZip:
                    await clean_target(f"{self.dir}/{name}")
                elif self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return
        if not self.isClone:
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
        msg = f"{self.tag} Download: {escape(error)}\n\n<b>• Elapsed</b>: {get_readable_time(time() - self.extra_details['startTime'])}"
        await sendMessage(self.message, msg, button)
        if self.logMessage:
            await sendMessage(self.logMessage, msg, button)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().remove_download(self.raw_url)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

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
        await delete_links(self.message)
        await sleep(3)
        if not self.isClone:
            await clean_download(self.dir)
            if self.newDir:
                await clean_download(self.newDir)

    async def onUploadError(self, error):
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        msg = f"{self.tag} {escape(error)}\n\n<b>• Elapsed</b>: {get_readable_time(time() - self.extra_details['startTime'])}"
        await sendMessage(self.message, msg)
        if self.logMessage:
            await sendMessage(self.logMessage, msg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().remove_download(self.raw_url)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

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
        await delete_links(self.message)
        await sleep(3)
        if not self.isClone:
            await clean_download(self.dir)
            if self.newDir:
                await clean_download(self.newDir)