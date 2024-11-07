from html import escape
from asyncio import sleep, gather
from contextlib import suppress

from aioshutil import move
from aiofiles.os import path as aiopath
from aiofiles.os import remove, listdir, makedirs

from bot import (
    LOGGER,
    DOWNLOAD_DIR,
    Intervals,
    aria2,
    queued_dl,
    queued_up,
    task_dict,
    config_dict,
    non_queued_dl,
    non_queued_up,
    task_dict_lock,
    queue_dict_lock,
)
from bot.helper.common import TaskConfig
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.files_utils import (
    join_files,
    clean_target,
    get_path_size,
    clean_download,
)
from bot.helper.ext_utils.links_utils import is_gdrive_id
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.task_manager import start_from_queued, check_running_tasks
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    send_message,
    delete_status,
    update_status_message,
)
from bot.helper.mirror_leech_utils.telegram_uploader import TgUploader
from bot.helper.mirror_leech_utils.gdrive_utils.upload import gdUpload
from bot.helper.mirror_leech_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_leech_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_leech_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_leech_utils.status_utils.telegram_status import TelegramStatus


class TaskListener(TaskConfig):
    def __init__(self):
        super().__init__()

    async def clean(self):
        with suppress(Exception):
            if st := Intervals["status"]:
                for intvl in list(st.values()):
                    intvl.cancel()
            Intervals["status"].clear()
            await gather(sync_to_async(aria2.purge), delete_status())

    def rm_from_sm_dir(self):
        if self.same_dir and self.mid in self.same_dir["tasks"]:
            self.same_dir["tasks"].remove(self.mid)
            self.same_dir["total"] -= 1

    async def on_download_start(self):
        # Feature will added in future
        pass

    async def on_download_complete(self):
        multi_links = False
        if self.same_dir and self.mid in self.same_dir["tasks"]:
            while not (
                self.same_dir["total"] in [1, 0]
                or self.same_dir["total"] > 1
                and len(self.same_dir["tasks"]) > 1
            ):
                await sleep(0.5)

        async with task_dict_lock:
            if (
                self.same_dir
                and self.same_dir["total"] > 1
                and self.mid in self.same_dir["tasks"]
            ):
                self.same_dir["tasks"].remove(self.mid)
                self.same_dir["total"] -= 1
                folder_name = self.same_dir["name"]
                spath = f"{self.dir}{folder_name}"
                des_path = f"{DOWNLOAD_DIR}{next(iter(self.same_dir['tasks']))}{folder_name}"
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(spath):
                    if item.endswith((".aria2", ".!qB")):
                        continue
                    item_path = f"{self.dir}{folder_name}/{item}"
                    if item in await listdir(des_path):
                        await move(item_path, f"{des_path}/{self.mid}-{item}")
                    else:
                        await move(item_path, f"{des_path}/{item}")
                multi_links = True
            download = task_dict[self.mid]
            self.name = download.name()
            gid = download.gid()

        if not (self.isTorrent or self.isQbit):
            self.seed = False

        unwanted_files = []
        unwanted_files_size = []
        files_to_delete = []

        if multi_links:
            await self.onUploadError("Downloaded! Waiting for other tasks...")
            return

        if not await aiopath.exists(f"{self.dir}/{self.name}"):
            try:
                files = await listdir(self.dir)
                self.name = files[-1]
                if self.name == "yt-dlp-thumb":
                    self.name = files[0]
            except Exception as e:
                await self.onUploadError(str(e))
                return

        up_path = f"{self.dir}/{self.name}"
        self.size = await get_path_size(up_path)
        if not config_dict["QUEUE_ALL"]:
            async with queue_dict_lock:
                if self.mid in non_queued_dl:
                    non_queued_dl.remove(self.mid)
            await start_from_queued()

        if self.join and await aiopath.isdir(up_path):
            await join_files(up_path)

        if self.extract:
            up_path = await self.proceedExtract(up_path, gid)
            if self.isCancelled:
                return
            up_dir, self.name = up_path.rsplit("/", 1)
            self.size = await get_path_size(up_dir)

        up_path = await self.remove_website(up_path)
        self.name = up_path.rsplit("/", 1)[1]
        if self.nameSub:
            up_path = await self.substitute(up_path)
            if self.isCancelled:
                return
            self.name = up_path.rsplit("/", 1)[1]

        if self.metadata:
            up_path = await self.proceedMetadata(up_path, gid)
            if self.isCancelled:
                return

        if self.screenShots:
            up_path = await self.generateScreenshots(up_path)
            if self.isCancelled:
                return
            up_dir, self.name = up_path.rsplit("/", 1)
            self.size = await get_path_size(up_dir)

        if self.convertAudio or self.convertVideo:
            up_path = await self.convertMedia(
                up_path, gid, unwanted_files, unwanted_files_size, files_to_delete
            )
            if self.isCancelled:
                return
            up_dir, self.name = up_path.rsplit("/", 1)
            self.size = await get_path_size(up_dir)

        if self.sampleVideo:
            up_path = await self.generateSampleVideo(
                up_path, gid, unwanted_files, files_to_delete
            )
            if self.isCancelled:
                return
            up_dir, self.name = up_path.rsplit("/", 1)
            self.size = await get_path_size(up_dir)

        if self.compress:
            up_path = await self.proceedCompress(
                up_path, gid, unwanted_files, files_to_delete
            )
            if self.isCancelled:
                return

        up_dir, self.name = up_path.rsplit("/", 1)
        self.size = await get_path_size(up_dir)

        if self.is_leech and not self.compress:
            await self.proceedSplit(up_dir, unwanted_files_size, unwanted_files, gid)
            if self.isCancelled:
                return

        add_to_queue, event = await check_running_tasks(self, "up")
        await start_from_queued()
        if add_to_queue:
            LOGGER.info(f"Added to Queue/Upload: {self.name}")
            async with task_dict_lock:
                task_dict[self.mid] = QueueStatus(self, gid, "Up")
            await event.wait()
            if self.isCancelled:
                return
            async with queue_dict_lock:
                non_queued_up.add(self.mid)
            LOGGER.info(f"Start from Queued/Upload: {self.name}")

        self.size = await get_path_size(up_dir)
        for s in unwanted_files_size:
            self.size -= s

        if self.is_leech:
            tg = TgUploader(self, up_dir)
            async with task_dict_lock:
                task_dict[self.mid] = TelegramStatus(self, tg, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                tg.upload(unwanted_files, files_to_delete),
            )
        elif is_gdrive_id(self.upDest):
            LOGGER.info(f"Gdrive Upload Name: {self.name}")
            drive = gdUpload(self, up_path)
            async with task_dict_lock:
                task_dict[self.mid] = GdriveStatus(self, drive, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                sync_to_async(drive.upload, unwanted_files, files_to_delete),
            )
        else:
            LOGGER.info(f"Rclone Upload Name: {self.name}")
            RCTransfer = RcloneTransferHelper(self)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(self, RCTransfer, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                RCTransfer.upload(up_path, unwanted_files, files_to_delete),
            )

    async def onUploadComplete(
        self, link, files, folders, mime_type, rclonePath="", dir_id=""
    ):
        msg = f"<b>Name: </b><code>{escape(self.name)}</code>\n\n<b>Size: </b>{get_readable_file_size(self.size)}"
        done_msg = f"{self.tag}\nYour task is complete\nPlease check your inbox."
        if self.is_leech:
            msg += f"\n<b>Total Files: </b>{folders}"
            if mime_type != 0:
                msg += f"\n<b>Corrupted Files: </b>{mime_type}"
            msg += f"\nBy: {self.tag}\nUid: {self.userId}\n\n"
            if not files:
                await send_message(self.message, msg)
            else:
                fmsg = ""
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        await send_message(
                            self.userId,
                            f"{msg}<blockquote expandable>{fmsg}</blockquote>",
                        )
                        if config_dict["LOG_CHAT"]:
                            await send_message(
                                config_dict["LOG_CHAT"],
                                f"{msg}<blockquote expandable>{fmsg}</blockquote>",
                            )
                        await sleep(1)
                        fmsg = ""
                if fmsg != "":
                    await send_message(
                        self.userId,
                        f"{msg}<blockquote expandable>{fmsg}</blockquote>",
                    )
                    if config_dict["LOG_CHAT"]:
                        await send_message(
                            config_dict["LOG_CHAT"],
                            f"{msg}<blockquote expandable>{fmsg}</blockquote>",
                        )
                await send_message(self.message, done_msg)
        else:
            if mime_type == "Folder":
                msg += f"\n<b>SubFolders: </b>{folders}"
                msg += f"\n<b>Files: </b>{files}"
            if link or rclonePath and not self.privateLink:
                buttons = ButtonMaker()
                if link:
                    buttons.url("Cloud Link", link)
                else:
                    msg += f"\n\nPath: <code>{rclonePath}</code>"
                if not rclonePath and dir_id:
                    INDEX_URL = ""
                    if self.privateLink:
                        INDEX_URL = self.userDict.get("index_url", "") or ""
                    elif config_dict["INDEX_URL"]:
                        INDEX_URL = config_dict["INDEX_URL"]
                    if INDEX_URL:
                        share_url = f"{INDEX_URL}findpath?id={dir_id}"
                        buttons.url("Index Link", share_url)
                        if mime_type.startswith(("image", "video", "audio")):
                            share_urls = f"{INDEX_URL}findpath?id={dir_id}&view=true"
                            buttons.url("View Link", share_urls)
                button = buttons.menu(2)
            else:
                msg += f"\n\nPath: <code>{rclonePath}</code>"
                button = None
            msg += f"\n\nBy: {self.tag}\nUid: {self.userId}"
            await send_message(self.userId, msg, button)
            if config_dict["LOG_CHAT"]:
                await send_message(config_dict["LOG_CHAT"], msg, button)
            await send_message(self.message, done_msg)
        if self.seed:
            if self.newDir:
                await clean_target(self.newDir)
            async with queue_dict_lock:
                if self.mid in non_queued_up:
                    non_queued_up.remove(self.mid)
            await start_from_queued()
            return
        await clean_download(self.dir)
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        async with queue_dict_lock:
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()

    async def onDownloadError(self, error, button=None):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
            self.rm_from_sm_dir()
        msg = f"{self.tag} Download: {escape(error)}"
        await send_message(self.message, msg, button)
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
        if self.thumb and await aiopath.exists(self.thumb):
            await remove(self.thumb)

    async def onUploadError(self, error):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        await send_message(self.message, f"{self.tag} {escape(error)}")
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
        if self.thumb and await aiopath.exists(self.thumb):
            await remove(self.thumb)
