from re import match as re_match
from base64 import b64encode
from asyncio import create_task

from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, DOWNLOAD_DIR, bot
from bot.helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    new_task,
    arg_parser,
    sync_to_async,
    get_content_type,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.links_utils import (
    is_url,
    is_magnet,
    is_gdrive_id,
    is_mega_link,
    is_gdrive_link,
    is_rclone_path,
    is_telegram_link,
)
from bot.helper.aeon_utils.access_check import error_check
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    delete_links,
    send_message,
    five_minute_del,
    get_tg_link_message,
)
from bot.helper.mirror_leech_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_leech_utils.download_utils.mega_download import (
    add_mega_download,
)
from bot.helper.mirror_leech_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_leech_utils.download_utils.aria2_download import (
    add_aria2c_download,
)
from bot.helper.mirror_leech_utils.download_utils.rclone_download import (
    add_rclone_download,
)
from bot.helper.mirror_leech_utils.download_utils.direct_downloader import (
    add_direct_download,
)
from bot.helper.mirror_leech_utils.download_utils.telegram_download import (
    TelegramDownloadHelper,
)
from bot.helper.mirror_leech_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)


class Mirror(TaskListener):
    def __init__(
        self,
        client,
        message,
        isQbit=False,
        is_leech=False,
        same_dir=None,
        bulk=None,
        multi_tag=None,
        options="",
    ):
        if same_dir is None:
            same_dir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multi_tag = multi_tag
        self.options = options
        self.same_dir = same_dir
        self.bulk = bulk
        super().__init__()
        self.isQbit = isQbit
        self.is_leech = is_leech

    @new_task
    async def new_event(self):
        error_msg, error_button = await error_check(self.message)
        if error_msg:
            await delete_links(self.message)
            error = await send_message(self.message, error_msg, error_button)
            await five_minute_del(error)
            return None

        text = self.message.text.split("\n")
        user_id = self.message.from_user.id
        input_list = text[0].split(" ")

        args = {
            "-d": False,
            "-j": False,
            "-s": False,
            "-b": False,
            "-e": False,
            "-z": False,
            "-sv": False,
            "-ss": False,
            "-i": 0,
            "link": "",
            "-n": "",
            "-m": "",
            "-up": "",
            "-rcf": "",
            "-au": "",
            "-ap": "",
            "-h": "",
            "-t": "",
            "-ca": "",
            "-cv": "",
            "-ns": "",
            "-md": "",
        }

        arg_parser(input_list[1:], args)

        self.select = args["-s"]
        self.seed = args["-d"]
        self.name = args["-n"]
        self.upDest = args["-up"]
        self.rcFlags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"]
        self.extract = args["-e"]
        self.join = args["-j"]
        self.thumb = args["-t"]
        self.sampleVideo = args["-sv"]
        self.screenShots = args["-ss"]
        self.convertAudio = args["-ca"]
        self.convertVideo = args["-cv"]
        self.nameSub = args["-ns"]
        self.metadata = args["-md"]

        headers = args["-h"]
        is_bulk = args["-b"]
        folder_name = args["-m"]

        bulk_start = 0
        bulk_end = 0
        ratio = None
        seed_time = None
        reply_to = None
        file_ = None
        session = ""

        try:
            self.multi = int(args["-i"])
        except Exception:
            self.multi = 0

        if not isinstance(self.seed, bool):
            dargs = self.seed.split(":")
            ratio = dargs[0] or None
            if len(dargs) == 2:
                seed_time = dargs[1] or None
            self.seed = True

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or 0
            if len(dargs) == 2:
                bulk_end = dargs[1] or 0
            is_bulk = True

        if not is_bulk:
            if folder_name:
                self.seed = False
                ratio = None
                seed_time = None
                folder_name = f"/{folder_name}"
                if not self.same_dir:
                    self.same_dir = {
                        "total": self.multi,
                        "tasks": set(),
                        "name": folder_name,
                    }
                self.same_dir["tasks"].add(self.mid)
            elif self.same_dir:
                self.same_dir["total"] -= 1

        else:
            await self.initBulk(input_list, bulk_start, bulk_end, Mirror)
            return None

        if len(self.bulk) != 0:
            del self.bulk[0]

        self.run_multi(input_list, folder_name, Mirror)

        await self.getTag(text)

        path = f"{DOWNLOAD_DIR}{self.mid}{folder_name}"

        if not self.link and (reply_to := self.message.reply_to_message):
            if reply_to.text:
                self.link = reply_to.text.split("\n", 1)[0].strip()
        if is_telegram_link(self.link):
            try:
                reply_to, session = await get_tg_link_message(self.link, user_id)
            except Exception as e:
                x = await send_message(self.message, f"ERROR: {e}")
                self.rm_from_sm_dir()
                await delete_links(self.message)
                return await five_minute_del(x)

        if isinstance(reply_to, list):
            self.bulk = reply_to
            self.same_dir = {}
            b_msg = input_list[:1]
            self.options = " ".join(input_list[1:])
            b_msg.append(f"{self.bulk[0]} -i {len(self.bulk)} {self.options}")
            nextmsg = await send_message(self.message, " ".join(b_msg))
            nextmsg = await self.client.get_messages(
                chat_id=self.message.chat.id, message_ids=nextmsg.id
            )
            if self.message.from_user:
                nextmsg.from_user = self.user
            else:
                nextmsg.sender_chat = self.user
            Mirror(
                self.client,
                nextmsg,
                self.isQbit,
                self.is_leech,
                self.same_dir,
                self.bulk,
                self.multi_tag,
                self.options,
            ).new_event()
            return await delete_links(self.message)

        if reply_to:
            file_ = (
                reply_to.document
                or reply_to.photo
                or reply_to.video
                or reply_to.audio
                or reply_to.voice
                or reply_to.video_note
                or reply_to.sticker
                or reply_to.animation
                or None
            )

            if file_ is None:
                if reply_text := reply_to.text:
                    self.link = reply_text.split("\n", 1)[0].strip()
                else:
                    reply_to = None
            elif reply_to.document and (
                file_.mime_type == "application/x-bittorrent"
                or file_.file_name.endswith((".torrent", ".dlc"))
            ):
                self.link = await reply_to.download()
                file_ = None

        if self.link and (
            is_magnet(self.link)
            or self.link.endswith(".torrent")
            or (file_ and file_.file_name.endswith(".torrent"))
        ):
            self.isQbit = True

        if (
            not self.link
            and file_ is None
            or is_telegram_link(self.link)
            and reply_to is None
            or file_ is None
            and not is_url(self.link)
            and not is_magnet(self.link)
            and not is_mega_link(self.link)
            and not await aiopath.exists(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_id(self.link)
            and not is_gdrive_link(self.link)
        ):
            x = await send_message(
                self.message, COMMAND_USAGE["mirror"][0], COMMAND_USAGE["mirror"][1]
            )
            self.rm_from_sm_dir()
            await delete_links(self.message)
            return await five_minute_del(x)

        try:
            await self.beforeStart()
        except Exception as e:
            x = await send_message(self.message, e)
            self.rm_from_sm_dir()
            await delete_links(self.message)
            return await five_minute_del(x)

        if (
            not self.isQbit
            and not is_mega_link(self.link)
            and not is_magnet(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_link(self.link)
            and not self.link.endswith(".torrent")
            and file_ is None
            and not is_gdrive_id(self.link)
        ):
            content_type = await get_content_type(self.link)
            if content_type is None or re_match(
                r"text/html|text/plain", content_type
            ):
                try:
                    self.link = await sync_to_async(direct_link_generator, self.link)
                    if isinstance(self.link, tuple):
                        self.link, headers = self.link
                except DirectDownloadLinkException as e:
                    e = str(e)
                    if "This link requires a password!" not in e:
                        LOGGER.info(e)
                    if e.startswith("ERROR:"):
                        x = await send_message(self.message, e)
                        self.rm_from_sm_dir()
                        await delete_links(self.message)
                        return await five_minute_del(x)

        if file_ is not None:
            create_task(
                TelegramDownloadHelper(self).add_download(
                    reply_to, f"{path}/", session
                )
            )
        elif isinstance(self.link, dict):
            create_task(add_direct_download(self, path))
        elif self.isQbit:
            create_task(add_qb_torrent(self, path, ratio, seed_time))
        elif is_rclone_path(self.link):
            create_task(add_rclone_download(self, f"{path}/"))
        elif is_gdrive_link(self.link) or is_gdrive_id(self.link):
            create_task(add_gd_download(self, path))
        elif is_mega_link(self.link):
            create_task(add_mega_download(self, f"{path}/"))
        else:
            ussr = args["-au"]
            pssw = args["-ap"]
            if ussr or pssw:
                auth = f"{ussr}:{pssw}"
                headers += f" authorization: Basic {b64encode(auth.encode()).decode('ascii')}"
            create_task(add_aria2c_download(self, path, headers, ratio, seed_time))
        await delete_links(self.message)
        return None


async def mirror(client, message):
    Mirror(client, message).new_event()


async def leech(client, message):
    Mirror(client, message, is_leech=True).new_event()


bot.add_handler(
    MessageHandler(
        mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized
    )
)
