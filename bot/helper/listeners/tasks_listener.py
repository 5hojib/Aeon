from os import path as ospath
from os import walk
from html import escape
from time import time
from asyncio import Event, sleep, create_subprocess_exec

from requests import utils as rutils
from aioshutil import move
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from aiofiles.os import listdir, makedirs
from pyrogram.enums import ChatType

from bot import (
    LOGGER,
    MAX_SPLIT_SIZE,
    GLOBAL_EXTENSION_FILTER,
    Interval,
    aria2,
    queued_dl,
    queued_up,
    config_dict,
    download_dict,
    non_queued_dl,
    non_queued_up,
    queue_dict_lock,
    download_dict_lock,
    status_reply_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    extra_btns,
    sync_to_async,
    get_readable_time,
    get_readable_file_size,
)
from bot.helper.ext_utils.exceptions import ExtractionArchiveError
from bot.helper.ext_utils.files_utils import (
    is_archive,
    join_files,
    split_file,
    clean_target,
    process_file,
    get_base_name,
    get_path_size,
    clean_download,
    is_archive_split,
    is_first_archive_split,
)
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    delete_links,
    edit_message,
    send_message,
    sendCustomMsg,
    delete_message,
    five_minute_del,
    sendMultiMessage,
    delete_all_messages,
    update_all_messages,
)
from bot.helper.mirror_leech_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_leech_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_leech_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_leech_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_leech_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_leech_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_leech_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_leech_utils.upload_utils.telegramEngine import TgUploader
from bot.helper.mirror_leech_utils.status_utils.telegram_status import TelegramStatus


class MirrorLeechListener:
    def __init__(
        self,
        message,
        compress=False,
        extract=False,
        is_qbit=False,
        is_leech=False,
        tag=None,
        select=False,
        seed=False,
        same_dir=None,
        rc_flags=None,
        upPath=None,
        is_clone=False,
        join=False,
        is_ytdlp=False,
        drive_id=None,
        index_link=None,
        attachment=None,
        files_utils={},
    ):
        if same_dir is None:
            same_dir = {}
        self.message = message
        self.uid = message.id
        self.extract = extract
        self.compress = compress
        self.is_qbit = is_qbit
        self.is_leech = is_leech
        self.is_clone = is_clone
        self.is_ytdlp = is_ytdlp
        self.tag = tag
        self.seed = seed
        self.newDir = ""
        self.dir = f"/usr/src/app/downloads/{self.uid}"
        self.select = select
        self.isSuperGroup = message.chat.type in [
            ChatType.SUPERGROUP,
            ChatType.CHANNEL,
        ]
        self.isPrivate = message.chat.type == ChatType.BOT
        self.suproc = None
        self.same_dir = same_dir
        self.rc_flags = rc_flags
        self.upPath = upPath
        self.join = join
        self.linkslogmsg = None
        self.botpmmsg = None
        self.drive_id = drive_id
        self.index_link = index_link
        self.files_utils = files_utils
        self.attachment = attachment

    async def clean(self):
        try:
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            await sync_to_async(aria2.purge)
            await delete_all_messages()
        except Exception:
            pass

    async def on_download_start(self):
        if config_dict["LEECH_LOG_ID"]:
            msg = "<b>Task Started</b>\n\n"
            msg += f"<b>• Task by:</b> {self.tag}\n"
            msg += f"<b>• User ID: </b><code>{self.message.from_user.id}</code>"
            self.linkslogmsg = await sendCustomMsg(config_dict["LEECH_LOG_ID"], msg)
        self.botpmmsg = await sendCustomMsg(
            self.message.from_user.id, "<b>Task started</b>"
        )

    async def on_download_complete(self):
        multi_links = False
        while True:
            if self.same_dir:
                if (
                    self.same_dir["total"] in [1, 0]
                    or self.same_dir["total"] > 1
                    and len(self.same_dir["tasks"]) > 1
                ):
                    break
            else:
                break
            await sleep(0.2)
        async with download_dict_lock:
            if self.same_dir and self.same_dir["total"] > 1:
                self.same_dir["tasks"].remove(self.uid)
                self.same_dir["total"] -= 1
                folder_name = self.same_dir["name"]
                spath = f"{self.dir}/{folder_name}"
                des_path = f"/usr/src/app/downloads/{next(iter(self.same_dir['tasks']))}/{folder_name}"
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(spath):
                    if item.endswith((".aria2", ".!qB")):
                        continue
                    item_path = f"{self.dir}/{folder_name}/{item}"
                    if item in await listdir(des_path):
                        await move(item_path, f"{des_path}/{self.uid}-{item}")
                    else:
                        await move(item_path, f"{des_path}/{item}")
                multi_links = True
            download = download_dict[self.uid]
            name = str(download.name()).replace("/", "")
            gid = download.gid()
        LOGGER.info(f"Download completed: {name}")
        if multi_links:
            await self.onUploadError(
                "Downloaded! Starting other part of the Task..."
            )
            return
        if (
            name == "None"
            or self.is_qbit
            or not await aiopath.exists(f"{self.dir}/{name}")
        ):
            try:
                files = await listdir(self.dir)
            except Exception as e:
                await self.onUploadError(str(e))
                return
            name = files[-1]
            if name == "yt-dlp-thumb":
                name = files[0]

        dl_path = f"{self.dir}/{name}"
        up_path = ""
        size = await get_path_size(dl_path)
        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        await start_from_queued()

        if self.join and await aiopath.isdir(dl_path):
            await join_files(dl_path)

        if self.extract:
            pswd = self.extract if isinstance(self.extract, str) else ""
            try:
                if await aiopath.isfile(dl_path):
                    up_path = get_base_name(dl_path)
                LOGGER.info(f"Extracting: {name}")
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                if await aiopath.isdir(dl_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        up_path = f"{self.newDir}/{name}"
                    else:
                        up_path = dl_path
                    for dirpath, _, files in await sync_to_async(
                        walk, dl_path, topdown=False
                    ):
                        for file_ in files:
                            if (
                                is_first_archive_split(file_)
                                or is_archive(file_)
                                and not file_.endswith(".rar")
                            ):
                                f_path = ospath.join(dirpath, file_)
                                t_path = (
                                    dirpath.replace(self.dir, self.newDir)
                                    if self.seed
                                    else dirpath
                                )
                                cmd = [
                                    "7z",
                                    "x",
                                    f"-p{pswd}",
                                    f_path,
                                    f"-o{t_path}",
                                    "-aot",
                                    "-xr!@PaxHeader",
                                ]
                                if not pswd:
                                    del cmd[2]
                                if (
                                    self.suproc == "cancelled"
                                    or self.suproc is not None
                                    and self.suproc.returncode == -9
                                ):
                                    return
                                self.suproc = await create_subprocess_exec(*cmd)
                                code = await self.suproc.wait()
                                if code == -9:
                                    return
                                if code != 0:
                                    LOGGER.error("Unable to extract archive splits!")
                        if (
                            not self.seed
                            and self.suproc is not None
                            and self.suproc.returncode == 0
                        ):
                            for file_ in files:
                                if is_archive_split(file_) or is_archive(file_):
                                    del_path = ospath.join(dirpath, file_)
                                    try:
                                        await aioremove(del_path)
                                    except Exception:
                                        return
                else:
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        up_path = up_path.replace(self.dir, self.newDir)
                    cmd = [
                        "7z",
                        "x",
                        f"-p{pswd}",
                        dl_path,
                        f"-o{up_path}",
                        "-aot",
                        "-xr!@PaxHeader",
                    ]
                    if not pswd:
                        del cmd[2]
                    if self.suproc == "cancelled":
                        return
                    self.suproc = await create_subprocess_exec(*cmd)
                    code = await self.suproc.wait()
                    if code == -9:
                        return
                    if code == 0:
                        LOGGER.info(f"Extracted Path: {up_path}")
                        if not self.seed:
                            try:
                                await aioremove(dl_path)
                            except Exception:
                                return
                    else:
                        LOGGER.error("Unable to extract archive! Uploading anyway")
                        self.newDir = ""
                        up_path = dl_path
            except ExtractionArchiveError:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                up_path = dl_path

        if self.compress:
            pswd = self.compress if isinstance(self.compress, str) else ""
            if up_path:
                dl_path = up_path
                up_path = f"{up_path}.zip"
            elif self.seed and self.is_leech:
                self.newDir = f"{self.dir}10000"
                up_path = f"{self.newDir}/{name}.zip"
            else:
                up_path = f"{dl_path}.zip"
            async with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
            cmd = [
                "7z",
                f"-v{LEECH_SPLIT_SIZE}b",
                "a",
                "-mx=0",
                f"-p{pswd}",
                up_path,
                dl_path,
            ]
            for ext in GLOBAL_EXTENSION_FILTER:
                ex_ext = f"-xr!*.{ext}"
                cmd.append(ex_ext)
            if self.is_leech and int(size) > LEECH_SPLIT_SIZE:
                if not pswd:
                    del cmd[4]
                LOGGER.info(f"Zip: orig_path: {dl_path}, zip_path: {up_path}.0*")
            else:
                del cmd[1]
                if not pswd:
                    del cmd[3]
                LOGGER.info(f"Zip: orig_path: {dl_path}, zip_path: {up_path}")
            if self.suproc == "cancelled":
                return
            self.suproc = await create_subprocess_exec(*cmd)
            code = await self.suproc.wait()
            if code == -9:
                return
            if not self.seed:
                await clean_target(dl_path)

        if not self.compress and not self.extract:
            up_path = dl_path

        up_dir, up_name = up_path.rsplit("/", 1)
        size = await get_path_size(up_dir)
        if self.is_leech:
            m_size = []
            o_files = []
            if not self.compress:
                checked = False
                LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
                for dirpath, _, files in await sync_to_async(
                    walk, up_dir, topdown=False
                ):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = await aiopath.getsize(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(
                                        up_name, size, gid, self
                                    )
                                LOGGER.info(f"Splitting: {up_name}")
                            res = await split_file(
                                f_path,
                                f_size,
                                file_,
                                dirpath,
                                LEECH_SPLIT_SIZE,
                                self,
                            )
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= MAX_SPLIT_SIZE:
                                    continue
                                try:
                                    await aioremove(f_path)
                                except Exception:
                                    return
                            elif not self.seed or self.newDir:
                                try:
                                    await aioremove(f_path)
                                except Exception:
                                    return
                            else:
                                m_size.append(f_size)
                                o_files.append(file_)

        up_limit = config_dict["QUEUE_UPLOAD"]
        all_limit = config_dict["QUEUE_ALL"]
        added_to_queue = False
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (
                all_limit
                and dl + up >= all_limit
                and (not up_limit or up >= up_limit)
            ) or (up_limit and up >= up_limit):
                added_to_queue = True
                LOGGER.info(f"Added to Queue/Upload: {name}")
                event = Event()
                queued_up[self.uid] = event
        if added_to_queue:
            async with download_dict_lock:
                download_dict[self.uid] = QueueStatus(name, size, gid, self, "Up")
            await event.wait()
            async with download_dict_lock:
                if self.uid not in download_dict:
                    return
            LOGGER.info(f"Start from Queued/Upload: {name}")
        async with queue_dict_lock:
            non_queued_up.add(self.uid)
        if self.is_leech:
            size = await get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, self)
            tg_upload_status = TelegramStatus(tg, size, self.message, gid, "up")
            async with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            await update_all_messages()
            await tg.upload(o_files, m_size, size)
        elif self.upPath == "gd":
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, self)
            upload_status = GdriveStatus(drive, size, self.message, gid, "up")
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
                    RCTransfer, self.message, gid, "up"
                )
            await update_all_messages()
            await RCTransfer.upload(up_path, size)

    async def onUploadComplete(
        self, link, size, files, folders, mime_type, name, rclonePath=""
    ):
        user_id = self.message.from_user.id
        name, _ = await process_file(name, user_id, is_mirror=not self.is_leech)
        msg = f"{escape(name)}\n\n"
        msg += f"<blockquote><b>• Size: </b>{get_readable_file_size(size)}\n"
        msg += f"<b>• Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n"
        LOGGER.info(f"Task Done: {name}")
        buttons = ButtonMaker()
        inboxButton = ButtonMaker()
        inboxButton.callback("View in inbox", f"aeon {user_id} private", "header")
        inboxButton = extra_btns(inboxButton)
        if self.is_leech:
            if folders > 1:
                msg += f"<b>• Total files: </b>{folders}\n"
            if mime_type != 0:
                msg += f"<b>• Corrupted files: </b>{mime_type}\n"
            msg += f"<b>• User ID: </b><code>{self.message.from_user.id}</code>\n"
            msg += f"<b>• By: </b>{self.tag}</blockquote>\n\n"
            if not files:
                if self.isPrivate:
                    msg += (
                        "<b>Files have not been sent for an unspecified reason</b>"
                    )
                await send_message(self.message, msg)
            else:
                attachmsg = True
                fmsg, totalmsg = "\n\n", ""
                lmsg = "<b>Files have been sent. Access them via the provided links.</b>"
                for index, (dlink, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{dlink}'>{name}</a>\n"
                    totalmsg = (msg + lmsg + fmsg) if attachmsg else fmsg
                    if len(totalmsg.encode()) > 3900:
                        if self.linkslogmsg:
                            await edit_message(self.linkslogmsg, totalmsg)
                            await send_message(self.botpmmsg, totalmsg)
                            self.linkslogmsg = await send_message(
                                self.linkslogmsg, "Fetching Details..."
                            )
                        attachmsg = False
                        await sleep(1)
                        fmsg = "\n\n"
                if fmsg != "\n\n" and self.linkslogmsg:
                    await send_message(self.linkslogmsg, msg + lmsg + fmsg)
                    await delete_message(self.linkslogmsg)
                await send_message(self.botpmmsg, msg + lmsg + fmsg)
                await delete_message(self.botpmmsg)
                if self.isSuperGroup:
                    await send_message(
                        self.message,
                        f"{msg}<b>Files has been sent to your inbox</b>",
                        inboxButton.column(1),
                    )
                else:
                    await delete_message(self.botpmmsg)
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
                msg += f"<b>• Total files: </b>{files}\n"
            if link:
                buttons.url("Cloud link", link)
                INDEX_URL = (
                    self.index_link if self.drive_id else config_dict["INDEX_URL"]
                )
                if not rclonePath and INDEX_URL:
                    url_path = rutils.quote(f"{name}")
                    share_url = f"{INDEX_URL}/{url_path}"
                    if mime_type == "Folder":
                        share_url += "/"
                    buttons.url("Index link", share_url)
                buttons = extra_btns(buttons)
                button = buttons.column(2)
            elif rclonePath:
                msg += f"<b>• Path: </b><code>{rclonePath}</code>\n"
                button = None
                buttons = extra_btns(buttons)
                button = buttons.column(2)
            msg += f"<b>• User ID: </b><code>{self.message.from_user.id}</code>\n"
            msg += f"<b>• By: </b>{self.tag}</blockquote>\n\n"

            if config_dict["MIRROR_LOG_ID"]:
                await sendMultiMessage(config_dict["MIRROR_LOG_ID"], msg, button)
                if self.linkslogmsg:
                    await delete_message(self.linkslogmsg)
            await send_message(self.botpmmsg, msg, button, "Random")
            await delete_message(self.botpmmsg)
            if self.isSuperGroup:
                await send_message(
                    self.message,
                    f"{msg} <b>Links has been sent to your inbox</b>",
                    inboxButton.column(1),
                )
            else:
                await delete_message(self.botpmmsg)
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
            if self.uid in download_dict:
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
            if self.uid in download_dict:
                del download_dict[self.uid]
            count = len(download_dict)
            if self.same_dir and self.uid in self.same_dir["tasks"]:
                self.same_dir["tasks"].remove(self.uid)
                self.same_dir["total"] -= 1
        msg = f"Hey, {self.tag}!\n"
        msg += "Your download has been stopped!\n\n"
        msg += f"<blockquote><b>Reason:</b> {escape(error)}\n"
        msg += f"<b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}</blockquote>"
        x = await send_message(self.message, msg, button)
        await delete_links(self.message)
        if self.botpmmsg:
            await delete_message(self.botpmmsg)
        if self.linkslogmsg:
            await delete_message(self.linkslogmsg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()
        if self.isSuperGroup and self.botpmmsg:
            await send_message(self.botpmmsg, msg, button)
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
            if self.uid in download_dict:
                del download_dict[self.uid]
            count = len(download_dict)
        msg = f"Hey, {self.tag}!\n"
        msg += "Your upload has been stopped!\n\n"
        msg += f"<blockquote><b>Reason:</b> {escape(error)}\n"
        msg += f"<b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}</blockquote>"
        x = await send_message(self.message, msg)
        if self.linkslogmsg:
            await delete_message(self.linkslogmsg)
        await delete_links(self.message)
        if self.botpmmsg:
            await delete_message(self.botpmmsg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()
        if self.isSuperGroup and self.botpmmsg:
            await send_message(self.botpmmsg, msg)
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
