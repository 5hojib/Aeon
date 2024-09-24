from os import path as ospath
from os import walk
from re import sub as re_sub
from re import match as re_match
from time import time
from asyncio import sleep
from logging import getLogger

from PIL import Image
from natsort import natsorted
from tenacity import (
    RetryError,
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)
from aioshutil import copy, rmtree
from aiofiles.os import (
    path as aiopath,
)
from aiofiles.os import (
    remove,
    rename,
    makedirs,
)
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
from pyrogram.errors import RPCError, FloodWait

from bot import bot, user, config_dict
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.files_utils import (
    is_archive,
    get_base_name,
    clean_unwanted,
)
from bot.helper.ext_utils.media_utils import (
    get_media_info,
    get_audio_thumb,
    create_thumbnail,
    get_document_type,
)
from bot.helper.aeon_utils.caption_gen import generate_caption
from bot.helper.telegram_helper.message_utils import delete_message

LOGGER = getLogger(__name__)


class TgUploader:
    def __init__(self, listener, path):
        self._last_uploaded = 0
        self._processed_bytes = 0
        self._listener = listener
        self._path = path
        self._start_time = time()
        self._total_files = 0
        self._thumb = self._listener.thumb or f"Thumbnails/{listener.userId}.jpg"
        self._msgs_dict = {}
        self._corrupted = 0
        self._is_corrupted = False
        self._media_dict = {"videos": {}, "documents": {}}
        self._last_msg_in_group = False
        self._up_path = ""
        self._user_dump = ""
        self._lprefix = ""
        self._lcaption = ""
        self._is_private = False
        self._sent_msg = None
        self._user_id = listener.userId
        self._user_session = user

    async def _upload_progress(self, current, _):
        if self._listener.isCancelled:
            if self._user_session:
                user.stop_transmission()
            else:
                self._listener.client.stop_transmission()
        chunk_size = current - self._last_uploaded
        self._last_uploaded = current
        self._processed_bytes += chunk_size

    async def _user_settings(self):
        self._user_dump = self._listener.userDict.get("user_dump")
        self._lprefix = self._listener.userDict.get("lprefix")
        self._lcaption = self._listener.userDict.get("lcaption")
        if not await aiopath.exists(self._thumb):
            self._thumb = None

    async def _msg_to_reply(self):
        msg = "Task started"
        self._listener.upDest = config_dict["LEECH_DUMP_CHAT"]
        try:
            if self._user_session:
                self._sent_msg = await user.send_message(
                    chat_id=self._listener.upDest,
                    text=msg,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
            else:
                self._sent_msg = await self._listener.client.send_message(
                    chat_id=self._listener.upDest,
                    text=msg,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
                self._is_private = self._sent_msg.chat.type.name == "PRIVATE"
        except Exception as e:
            await self._listener.onUploadError(str(e))
            return False
        return True

    async def _prepare_file(self, file_, dirpath, delete_file):
        if self._lcaption:
            cap_mono = await generate_caption(file_, dirpath, self._lcaption)
        if self._lprefix:
            if not self._lcaption:
                cap_mono = f"{self._lprefix} <code>{file_}</code>"
            self._lprefix = re_sub("<.*?>", "", self._lprefix)
            if (
                self._listener.seed
                and not self._listener.newDir
                and not dirpath.endswith("/splited_files_joya")
                and not delete_file
            ):
                dirpath = f"{dirpath}/copied_joya"
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, f"{self._lprefix} {file_}")
                self._up_path = await copy(self._up_path, new_path)
            else:
                new_path = ospath.join(dirpath, f"{self._lprefix} {file_}")
                await rename(self._up_path, new_path)
                self._up_path = new_path
        if not self._lcaption and not self._lprefix:
            cap_mono = f"<code>{file_}</code>"
        if len(file_) > 60:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(name, 1)[1]
            elif match := re_match(
                r".+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+$)", file_
            ):
                name = match.group(0)
                ext = file_.split(name, 1)[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name = fsplit[0]
                ext = fsplit[1]
            else:
                name = file_
                ext = ""
            extn = len(ext)
            remain = 60 - extn
            name = name[:remain]
            if (
                self._listener.seed
                and not self._listener.newDir
                and not dirpath.endswith("/splited_files_joya")
                and not delete_file
            ):
                dirpath = f"{dirpath}/copied_joya"
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, f"{name}{ext}")
                self._up_path = await copy(self._up_path, new_path)
            else:
                new_path = ospath.join(dirpath, f"{name}{ext}")
                await rename(self._up_path, new_path)
                self._up_path = new_path
        return cap_mono

    def _get_input_media(self, subkey, key):
        rlist = []
        for msg in self._media_dict[key][subkey]:
            if key == "videos":
                input_media = InputMediaVideo(
                    media=msg.video.file_id, caption=msg.caption
                )
            else:
                input_media = InputMediaDocument(
                    media=msg.document.file_id, caption=msg.caption
                )
            rlist.append(input_media)
        return rlist

    async def _send_screenshots(self, dirpath, outputs):
        inputs = [
            InputMediaPhoto(ospath.join(dirpath, p), p.rsplit("/", 1)[-1])
            for p in outputs
        ]
        send_ss = await self._sent_msg.reply_media_group(
            media=inputs,
            quote=True,
            disable_notification=True,
        )
        await bot.copy_media_group(self._user_id, send_ss[0].chat.id, send_ss[0].id)
        self._sent_msg = (send_ss)[-1]

    async def _send_media_group(self, subkey, key, msgs):
        for index, msg in enumerate(msgs):
            if not self._user_session:
                msgs[index] = await self._listener.client.get_messages(
                    chat_id=msg[0], message_ids=msg[1]
                )
            else:
                msgs[index] = await user.get_messages(
                    chat_id=msg[0], message_ids=msg[1]
                )
        msgs_list = await msgs[0].reply_to_message.reply_media_group(
            media=self._get_input_media(subkey, key),
            quote=True,
            disable_notification=True,
        )
        for msg in msgs:
            if msg.link in self._msgs_dict:
                del self._msgs_dict[msg.link]
            await delete_message(msg)
        del self._media_dict[key][subkey]
        if self._listener.isSuperChat or self._listener.upDest:
            for m in msgs_list:
                self._msgs_dict[m.link] = m.caption
        self._sent_msg = msgs_list[-1]

    async def upload(self, o_files, ft_delete):
        await self._user_settings()
        res = await self._msg_to_reply()
        if not res:
            return
        for dirpath, _, files in natsorted(await sync_to_async(walk, self._path)):
            if dirpath.endswith("/yt-dlp-thumb"):
                continue
            if dirpath.endswith("_joyass"):
                await self._send_screenshots(dirpath, files)
                await rmtree(dirpath, ignore_errors=True)
                continue
            for file_ in natsorted(files):
                delete_file = False
                self._up_path = f_path = ospath.join(dirpath, file_)
                if self._up_path in ft_delete:
                    delete_file = True
                if self._up_path in o_files:
                    continue
                if file_.lower().endswith(tuple(self._listener.extensionFilter)):
                    if not self._listener.seed or self._listener.newDir:
                        await remove(self._up_path)
                    continue
                try:
                    f_size = await aiopath.getsize(self._up_path)
                    self._total_files += 1
                    if f_size == 0:
                        LOGGER.error(
                            f"{self._up_path} size is zero, telegram don't upload zero size files"
                        )
                        self._corrupted += 1
                        continue
                    if self._listener.isCancelled:
                        return
                    cap_mono = await self._prepare_file(file_, dirpath, delete_file)
                    if self._last_msg_in_group:
                        group_lists = [
                            x for v in self._media_dict.values() for x in v
                        ]
                        match = re_match(
                            r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", f_path
                        )
                        if not match or match and match.group(0) not in group_lists:
                            for key, value in list(self._media_dict.items()):
                                for subkey, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        await self._send_media_group(
                                            subkey, key, msgs
                                        )
                    self._last_msg_in_group = False
                    self._last_uploaded = 0
                    await self._upload_file(cap_mono, file_, f_path)
                    if self._listener.isCancelled:
                        return
                    if (
                        not self._is_corrupted
                        and (self._listener.isSuperChat or self._listener.upDest)
                        and not self._is_private
                    ):
                        self._msgs_dict[self._sent_msg.link] = file_
                    await sleep(1)
                except Exception as err:
                    if isinstance(err, RetryError):
                        LOGGER.info(
                            f"Total Attempts: {err.last_attempt.attempt_number}"
                        )
                        err = err.last_attempt.exception()
                    LOGGER.error(f"{err}. Path: {self._up_path}")
                    self._corrupted += 1
                    if self._listener.isCancelled:
                        return
                    continue
                finally:
                    if (
                        not self._listener.isCancelled
                        and await aiopath.exists(self._up_path)
                        and (
                            not self._listener.seed
                            or self._listener.newDir
                            or dirpath.endswith("/splited_files_joya")
                            or "/copied_joya/" in self._up_path
                            or delete_file
                        )
                    ):
                        await remove(self._up_path)
        for key, value in list(self._media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    try:
                        await self._send_media_group(subkey, key, msgs)
                    except Exception as e:
                        LOGGER.error(
                            f"While sending media group at the end of task. Error: {e}"
                        )
        if self._listener.isCancelled:
            return
        if self._listener.seed and not self._listener.newDir:
            await clean_unwanted(self._path)
        if self._total_files == 0:
            await self._listener.onUploadError(
                "No files to upload. In case you have filled EXTENSION_FILTER, then check if all files have those extensions or not."
            )
            return
        if self._total_files <= self._corrupted:
            await self._listener.onUploadError(
                "Files Corrupted or unable to upload. Check logs!"
            )
            return
        await self._listener.onUploadComplete(
            None, self._msgs_dict, self._total_files, self._corrupted
        )

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    async def _upload_file(self, cap_mono, file, o_path, force_document=False):
        if self._thumb and not await aiopath.exists(self._thumb):
            self._thumb = None
        thumb = self._thumb
        is_doc = False
        self._is_corrupted = False

        try:
            is_video, is_audio, is_image = await get_document_type(self._up_path)

            if not is_image and not thumb:
                file_name = ospath.splitext(file)[0]
                thumb_path = f"{self._path}/yt-dlp-thumb/{file_name}.jpg"
                if await aiopath.isfile(thumb_path):
                    thumb = thumb_path
                elif is_audio and not is_video:
                    thumb = await get_audio_thumb(self._up_path)

            if (
                self._listener.asDoc
                or force_document
                or (not is_video and not is_audio and not is_image)
            ):
                is_doc = True
                await self._upload_document(cap_mono, thumb, is_video)
            elif is_video:
                await self._upload_video(cap_mono, thumb)
            elif is_audio:
                await self._upload_audio(cap_mono, thumb)
            else:
                await self._upload_photo(cap_mono, thumb)

            if not self._thumb and thumb and await aiopath.exists(thumb):
                await remove(thumb)

        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.3)
            if not self._thumb and thumb and await aiopath.exists(thumb):
                await remove(thumb)
            return await self._upload_file(cap_mono, file, o_path)
        except Exception as err:
            if not self._thumb and thumb and await aiopath.exists(thumb):
                await remove(thumb)
            err_type = "RPCError: " if isinstance(err, RPCError) else ""
            LOGGER.error(f"{err_type}{err}. Path: {self._up_path}")
            if "Telegram says: [400" in str(err) and not is_doc:
                LOGGER.error(f"Retrying As Document. Path: {self._up_path}")
                return await self._upload_file(cap_mono, file, o_path, True)
            raise err

    async def _upload_document(self, cap_mono, thumb, is_video):
        if is_video and not thumb:
            thumb = await create_thumbnail(self._up_path, None)
        if self._listener.isCancelled:
            return
        self._sent_msg = await self._sent_msg.reply_document(
            document=self._up_path,
            quote=True,
            thumb=thumb,
            caption=cap_mono,
            force_document=True,
            disable_notification=True,
            progress=self._upload_progress,
        )
        await self._copy_message()

    async def _upload_video(self, cap_mono, thumb):
        duration = (await get_media_info(self._up_path))[0]
        if not thumb:
            thumb = await create_thumbnail(self._up_path, duration)
        width, height = self._get_image_dimensions(thumb)
        if self._listener.isCancelled:
            return
        self._sent_msg = await self._sent_msg.reply_video(
            video=self._up_path,
            quote=True,
            caption=cap_mono,
            duration=duration,
            width=width,
            height=height,
            thumb=thumb,
            supports_streaming=True,
            disable_notification=True,
            progress=self._upload_progress,
        )
        await self._copy_message()

    async def _upload_audio(self, cap_mono, thumb):
        duration, artist, title = await get_media_info(self._up_path)
        if self._listener.isCancelled:
            return
        self._sent_msg = await self._sent_msg.reply_audio(
            audio=self._up_path,
            quote=True,
            caption=cap_mono,
            duration=duration,
            performer=artist,
            title=title,
            thumb=thumb,
            disable_notification=True,
            progress=self._upload_progress,
        )
        await self._copy_message()

    async def _upload_photo(self, cap_mono, thumb):
        if self._listener.isCancelled:
            return
        self._sent_msg = await self._sent_msg.reply_photo(
            photo=self._up_path,
            quote=True,
            caption=cap_mono,
            disable_notification=True,
            progress=self._upload_progress,
        )
        await self._copy_message()

    async def _copy_message(self):
        await sleep(1)

        async def _copy(target, retries=3):
            for attempt in range(retries):
                try:
                    msg = await bot.get_messages(
                        self._listener.upDest, self._sent_msg.id
                    )
                    await msg.copy(target)
                    return
                except Exception as e:
                    LOGGER.error(f"Attempt {attempt + 1} failed: {e} {msg.id}")
                    if attempt < retries - 1:
                        await sleep(0.5)
            LOGGER.error(f"Failed to copy message after {retries} attempts")

        await _copy(self._user_id)

        if self._user_dump:
            await _copy(self._user_dump)

    def _get_image_dimensions(self, thumb):
        if thumb:
            with Image.open(thumb) as img:
                width, height = img.size
        else:
            width = 480
            height = 320
        return width, height

    @property
    def speed(self):
        try:
            return self._processed_bytes / (time() - self._start_time)
        except Exception:
            return 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    async def cancel_task(self):
        self._listener.isCancelled = True
        LOGGER.info(f"Cancelling Upload: {self._listener.name}")
        await self._listener.onUploadError("Your upload has been stopped!")
