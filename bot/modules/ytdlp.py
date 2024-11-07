from time import time
from asyncio import Event, wait_for, wrap_future
from functools import partial

from httpx import AsyncClient
from yt_dlp import YoutubeDL
from pyrogram.filters import user, regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import LOGGER, DOWNLOAD_DIR, bot, config_dict
from bot.helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    new_task,
    arg_parser,
    new_thread,
    sync_to_async,
)
from bot.helper.ext_utils.links_utils import is_url
from bot.helper.ext_utils.status_utils import (
    get_readable_time,
    get_readable_file_size,
)
from bot.helper.aeon_utils.access_check import error_check
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    delete_links,
    edit_message,
    send_message,
    delete_message,
    five_minute_del,
)
from bot.helper.mirror_leech_utils.download_utils.yt_dlp_download import (
    YoutubeDLHelper,
)


@new_task
async def select_format(_, query, obj):
    data = query.data.split()
    message = query.message
    await query.answer()

    if data[1] == "dict":
        b_name = data[2]
        await obj.qual_subbuttons(b_name)
    elif data[1] == "mp3":
        await obj.mp3_subbuttons()
    elif data[1] == "audio":
        await obj.audio_format()
    elif data[1] == "aq":
        if data[2] == "back":
            await obj.audio_format()
        else:
            await obj.audio_quality(data[2])
    elif data[1] == "back":
        await obj.back_to_main()
    elif data[1] == "cancel":
        await edit_message(message, "Task has been cancelled.")
        obj.qual = None
        obj.listener.isCancelled = True
        obj.event.set()
    else:
        if data[1] == "sub":
            obj.qual = obj.formats[data[2]][data[3]][1]
        elif "|" in data[1]:
            obj.qual = obj.formats[data[1]]
        else:
            obj.qual = data[1]
        obj.event.set()


class YtSelection:
    def __init__(self, listener):
        self.listener = listener
        self._is_m4a = False
        self._reply_to = None
        self._time = time()
        self._timeout = 120
        self._is_playlist = False
        self._main_buttons = None
        self.event = Event()
        self.formats = {}
        self.qual = None

    @new_thread
    async def _event_handler(self):
        pfunc = partial(select_format, obj=self)
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^ytq") & user(self.listener.userId)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except Exception:
            await edit_message(self._reply_to, "Timed Out. Task has been cancelled!")
            self.qual = None
            self.listener.isCancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    async def get_quality(self, result):
        future = self._event_handler()
        buttons = ButtonMaker()
        if "entries" in result:
            self._is_playlist = True
            for i in ["144", "240", "360", "480", "720", "1080", "1440", "2160"]:
                video_format = (
                    f"bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]"
                )
                b_data = f"{i}|mp4"
                self.formats[b_data] = video_format
                buttons.callback(f"{i}-mp4", f"ytq {b_data}")
                video_format = f"bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]"
                b_data = f"{i}|webm"
                self.formats[b_data] = video_format
                buttons.callback(f"{i}-webm", f"ytq {b_data}")
            buttons.callback("MP3", "ytq mp3")
            buttons.callback("Audio Formats", "ytq audio")
            buttons.callback("Best Videos", "ytq bv*+ba/b")
            buttons.callback("Best Audios", "ytq ba/b")
            buttons.callback("Cancel", "ytq cancel", "footer")
            self._main_buttons = buttons.menu(3)
            msg = f"Choose Playlist Videos Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        else:
            format_dict = result.get("formats")
            if format_dict is not None:
                for item in format_dict:
                    if item.get("tbr"):
                        format_id = item["format_id"]

                        if item.get("filesize"):
                            size = item["filesize"]
                        elif item.get("filesize_approx"):
                            size = item["filesize_approx"]
                        else:
                            size = 0

                        if item.get("video_ext") == "none" and (
                            item.get("resolution") == "audio only"
                            or item.get("acodec") != "none"
                        ):
                            if item.get("audio_ext") == "m4a":
                                self._is_m4a = True
                            b_name = (
                                f"{item.get('acodec') or format_id}-{item['ext']}"
                            )
                            v_format = format_id
                        elif item.get("height"):
                            height = item["height"]
                            ext = item["ext"]
                            fps = item["fps"] if item.get("fps") else ""
                            b_name = f"{height}p{fps}-{ext}"
                            ba_ext = (
                                "[ext=m4a]" if self._is_m4a and ext == "mp4" else ""
                            )
                            v_format = f"{format_id}+ba{ba_ext}/b[height=?{height}]"
                        else:
                            continue

                        self.formats.setdefault(b_name, {})[f"{item['tbr']}"] = [
                            size,
                            v_format,
                        ]

                for b_name, tbr_dict in self.formats.items():
                    if len(tbr_dict) == 1:
                        tbr, v_list = next(iter(tbr_dict.items()))
                        buttonName = (
                            f"{b_name} ({get_readable_file_size(v_list[0])})"
                        )
                        buttons.callback(buttonName, f"ytq sub {b_name} {tbr}")
                    else:
                        buttons.callback(b_name, f"ytq dict {b_name}")
            buttons.callback("MP3", "ytq mp3")
            buttons.callback("Audio Formats", "ytq audio")
            buttons.callback("Best Video", "ytq bv*+ba/b")
            buttons.callback("Best Audio", "ytq ba/b")
            buttons.callback("Cancel", "ytq cancel", "footer")
            self._main_buttons = buttons.menu(2)
            msg = f"Choose Video Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        self._reply_to = await send_message(
            self.listener.message, msg, self._main_buttons
        )
        await wrap_future(future)
        if not self.listener.isCancelled:
            await delete_message(self._reply_to)
        return self.qual

    async def back_to_main(self):
        if self._is_playlist:
            msg = f"Choose Playlist Videos Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        else:
            msg = f"Choose Video Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, self._main_buttons)

    async def qual_subbuttons(self, b_name):
        buttons = ButtonMaker()
        tbr_dict = self.formats[b_name]
        for tbr, d_data in tbr_dict.items():
            button_name = f"{tbr}K ({get_readable_file_size(d_data[0])})"
            buttons.callback(button_name, f"ytq sub {b_name} {tbr}")
        buttons.callback("Back", "ytq back", "footer")
        buttons.callback("Cancel", "ytq cancel", "footer")
        subbuttons = buttons.menu(2)
        msg = f"Choose Bit rate for <b>{b_name}</b>:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, subbuttons)

    async def mp3_subbuttons(self):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        audio_qualities = [64, 128, 320]
        for q in audio_qualities:
            audio_format = f"ba/b-mp3-{q}"
            buttons.callback(f"{q}K-mp3", f"ytq {audio_format}")
        buttons.callback("Back", "ytq back")
        buttons.callback("Cancel", "ytq cancel")
        subbuttons = buttons.menu(3)
        msg = f"Choose mp3 Audio{i} Bitrate:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, subbuttons)

    async def audio_format(self):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        for frmt in ["aac", "alac", "flac", "m4a", "opus", "vorbis", "wav"]:
            audio_format = f"ba/b-{frmt}-"
            buttons.callback(frmt, f"ytq aq {audio_format}")
        buttons.callback("Back", "ytq back", "footer")
        buttons.callback("Cancel", "ytq cancel", "footer")
        subbuttons = buttons.menu(3)
        msg = f"Choose Audio{i} Format:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, subbuttons)

    async def audio_quality(self, format):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        for qual in range(11):
            audio_format = f"{format}{qual}"
            buttons.callback(qual, f"ytq {audio_format}")
        buttons.callback("Back", "ytq aq back")
        buttons.callback("Cancel", "ytq aq cancel")
        subbuttons = buttons.menu(5)
        msg = f"Choose Audio{i} Qaulity:\n0 is best and 10 is worst\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        await edit_message(self._reply_to, msg, subbuttons)


def extract_info(link, options):
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info(link, download=False)
        if result is None:
            raise ValueError("Info result is None")
        return result


async def _mdisk(link, name):
    key = link.split("/")[-1]
    async with AsyncClient(verify=False) as client:
        resp = await client.get(
            f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={key}"
        )
    if resp.status_code == 200:
        resp_json = resp.json()
        link = resp_json["source"]
        if not name:
            name = resp_json["filename"]
    return name, link


class YtDlp(TaskListener):
    def __init__(
        self,
        client,
        message,
        _=None,
        is_leech=False,
        __=None,
        ___=None,
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
        self.isYtDlp = True
        self.is_leech = is_leech

    @new_task
    async def new_event(self):
        error_msg, error_button = await error_check(self.message)
        await delete_links(self.message)
        if error_msg:
            error = await send_message(self.message, error_msg, error_button)
            await five_minute_del(error)
            return
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")
        qual = ""

        args = {
            "-s": False,
            "-b": False,
            "-z": False,
            "-sv": False,
            "-ss": False,
            "-i": 0,
            "link": "",
            "-m": "",
            "-opt": "",
            "-n": "",
            "-up": "",
            "-rcf": "",
            "-t": "",
            "-ca": "",
            "-cv": "",
            "-ns": "",
        }

        arg_parser(input_list[1:], args)

        try:
            self.multi = int(args["-i"])
        except Exception:
            self.multi = 0

        self.select = args["-s"]
        self.name = args["-n"]
        self.upDest = args["-up"]
        self.rcFlags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"]
        self.thumb = args["-t"]
        self.sampleVideo = args["-sv"]
        self.screenShots = args["-ss"]
        self.convertAudio = args["-ca"]
        self.convertVideo = args["-cv"]
        self.nameSub = args["-ns"]

        is_bulk = args["-b"]
        folder_name = args["-m"]

        bulk_start = 0
        bulk_end = 0
        reply_to = None
        opt = args["-opt"]

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            is_bulk = True

        if not is_bulk:
            if folder_name:
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
            await self.initBulk(input_list, bulk_start, bulk_end, YtDlp)
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        path = f"{DOWNLOAD_DIR}{self.mid}{folder_name}"

        await self.getTag(text)

        opt = opt or self.userDict.get("yt_opt") or config_dict["YT_DLP_OPTIONS"]

        if not self.link and (reply_to := self.message.reply_to_message):
            self.link = reply_to.text.split("\n", 1)[0].strip()

        if not is_url(self.link):
            await send_message(
                self.message, COMMAND_USAGE["yt"][0], COMMAND_USAGE["yt"][1]
            )
            self.rm_from_sm_dir()
            return

        if "mdisk.me" in self.link:
            self.name, self.link = await _mdisk(self.link, self.name)

        try:
            await self.beforeStart()
        except Exception as e:
            await send_message(self.message, e)
            self.rm_from_sm_dir()
            return

        options = {"usenetrc": True, "cookiefile": "cookies.txt"}
        if opt:
            yt_opts = opt.split("|")
            for ytopt in yt_opts:
                key, value = map(str.strip, ytopt.split(":", 1))
                if key == "postprocessors":
                    continue
                if key == "format" and not self.select:
                    if value.startswith("ba/b-"):
                        qual = value
                        continue
                    qual = value
                if value.startswith("^"):
                    if "." in value or value == "^inf":
                        value = float(value.split("^")[1])
                    else:
                        value = int(value.split("^")[1])
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.startswith(("{", "[", "(")) and value.endswith(
                    ("}", "]", ")")
                ):
                    value = eval(value)
                options[key] = value
        options["playlist_items"] = "0"

        try:
            result = await sync_to_async(extract_info, self.link, options)
        except Exception as e:
            msg = str(e).replace("<", " ").replace(">", " ")
            await send_message(self.message, f"{self.tag} {msg}")
            self.rm_from_sm_dir()
            return
        finally:
            self.run_multi(input_list, folder_name, YtDlp)

        if not qual:
            qual = await YtSelection(self).get_quality(result)
            if qual is None:
                self.rm_from_sm_dir()
                return

        LOGGER.info(f"Downloading with YT-DLP: {self.link}")
        playlist = "entries" in result
        ydl = YoutubeDLHelper(self)
        await ydl.add_download(path, qual, playlist, opt)


async def ytdl(client, message):
    YtDlp(client, message).new_event()


async def ytdlleech(client, message):
    YtDlp(client, message, is_leech=True).new_event()


bot.add_handler(
    MessageHandler(
        ytdl, filters=command(BotCommands.YtdlCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        ytdlleech,
        filters=command(BotCommands.YtdlLeechCommand) & CustomFilters.authorized,
    )
)
