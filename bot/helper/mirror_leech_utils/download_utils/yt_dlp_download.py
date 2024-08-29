import contextlib
from os import path as ospath
from os import listdir
from re import search as re_search
from logging import getLogger
from secrets import token_hex

from yt_dlp import YoutubeDL, DownloadError

from bot import download_dict, non_queued_dl, queue_dict_lock, download_dict_lock
from bot.helper.ext_utils.bot_utils import async_to_sync, sync_to_async
from bot.helper.ext_utils.task_manager import (
    is_queued,
    limit_checker,
    stop_duplicate_check,
)
from bot.helper.telegram_helper.message_utils import sendStatusMessage
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_leech_utils.status_utils.ytdlp_status import (
    YtDlpDownloadStatus,
)

LOGGER = getLogger(__name__)


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg):
        if not self.obj.is_playlist and (
            match := re_search(r".Merger..Merging formats into..(.*?).$", msg)
            or re_search(r".ExtractAudio..Destination..(.*?)$", msg)
        ):
            LOGGER.info(msg)
            newname = match.group(1)
            newname = newname.rsplit("/", 1)[-1]
            self.obj.name = newname

    @staticmethod
    def warning(msg):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg):
        if msg != "ERROR: Cancelling...":
            LOGGER.error(msg)


class YoutubeDLHelper:
    def __init__(self, listener):
        self.__last_downloaded = 0
        self.__size = 0
        self.__progress = 0
        self.__downloaded_bytes = 0
        self.__download_speed = 0
        self.__eta = "-"
        self.__listener = listener
        self.__gid = ""
        self.__is_cancelled = False
        self.__downloading = False
        self.__ext = ""
        self.name = ""
        self.is_playlist = False
        self.playlist_count = 0
        self.opts = {
            "progress_hooks": [self.__onDownloadProgress],
            "logger": MyLogger(self),
            "usenetrc": True,
            "cookiefile": "cookies.txt",
            "allow_multiple_video_streams": True,
            "allow_multiple_audio_streams": True,
            "noprogress": True,
            "allow_playlist_files": True,
            "overwrites": True,
            "writethumbnail": True,
            "trim_file_name": 220,
            "ffmpeg_location": "/bin/xtra",
            "retry_sleep_functions": {
                "http": lambda _: 3,
                "fragment": lambda _: 3,
                "file_access": lambda _: 3,
                "extractor": lambda _: 3,
            },
        }

    @property
    def download_speed(self):
        return self.__download_speed

    @property
    def downloaded_bytes(self):
        return self.__downloaded_bytes

    @property
    def size(self):
        return self.__size

    @property
    def progress(self):
        return self.__progress

    @property
    def eta(self):
        return self.__eta

    def __onDownloadProgress(self, d):
        self.__downloading = True
        if self.__is_cancelled:
            raise ValueError("Cancelling...")
        if d["status"] == "finished":
            if self.is_playlist:
                self.__last_downloaded = 0
        elif d["status"] == "downloading":
            self.__download_speed = d["speed"]
            if self.is_playlist:
                downloadedBytes = d["downloaded_bytes"]
                chunk_size = downloadedBytes - self.__last_downloaded
                self.__last_downloaded = downloadedBytes
                self.__downloaded_bytes += chunk_size
            else:
                if d.get("total_bytes"):
                    self.__size = d["total_bytes"]
                elif d.get("total_bytes_estimate"):
                    self.__size = d["total_bytes_estimate"]
                self.__downloaded_bytes = d["downloaded_bytes"]
                self.__eta = d.get("eta", "-") or "-"
            with contextlib.suppress(Exception):
                self.__progress = (self.__downloaded_bytes / self.__size) * 100

    async def __on_download_start(self, from_queue=False):
        async with download_dict_lock:
            download_dict[self.__listener.uid] = YtDlpDownloadStatus(
                self, self.__listener, self.__gid
            )
        if not from_queue:
            await self.__listener.on_download_start()
            await sendStatusMessage(self.__listener.message)

    def __on_download_error(self, error):
        self.__is_cancelled = True
        async_to_sync(self.__listener.onDownloadError, error)

    def extractMetaData(self, link, name):
        if link.startswith(("rtmp", "mms", "rstp", "rtmps")):
            self.opts["external_downloader"] = "ffmpeg"
        with YoutubeDL(self.opts) as ydl:
            try:
                result = ydl.extract_info(link, download=False)
                if result is None:
                    raise ValueError("Info result is None")
            except Exception as e:
                return self.__on_download_error(str(e))
            if self.is_playlist:
                self.playlist_count = result.get("playlist_count", 0)
            if "entries" in result:
                self.name = name
                for entry in result["entries"]:
                    if not entry:
                        continue
                    if "filesize_approx" in entry:
                        self.__size += entry["filesize_approx"]
                    elif "filesize" in entry:
                        self.__size += entry["filesize"]
                    if not self.name:
                        outtmpl_ = "%(series,playlist_title,channel)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d.%(ext)s"
                        self.name, ext = ospath.splitext(
                            ydl.prepare_filename(entry, outtmpl=outtmpl_)
                        )
                        if not self.__ext:
                            self.__ext = ext
                return None
            outtmpl_ = "%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"
            realName = ydl.prepare_filename(result, outtmpl=outtmpl_)
            ext = ospath.splitext(realName)[-1]
            self.name = f"{name}{ext}" if name else realName
            if not self.__ext:
                self.__ext = ext
            if result.get("filesize"):
                self.__size = result["filesize"]
                return None
            if result.get("filesize_approx"):
                self.__size = result["filesize_approx"]
                return None
            return None

    def __download(self, link, path):
        try:
            with YoutubeDL(self.opts) as ydl:
                try:
                    ydl.download([link])
                except DownloadError as e:
                    if not self.__is_cancelled:
                        self.__on_download_error(str(e))
                    return
            if self.is_playlist and (
                not ospath.exists(path) or len(listdir(path)) == 0
            ):
                self.__on_download_error(
                    "No video available to download from this playlist. Check logs for more details"
                )
                return
            if self.__is_cancelled:
                raise ValueError
            async_to_sync(self.__listener.on_download_complete)
        except ValueError:
            self.__on_download_error("Download Stopped by User!")

    async def add_download(self, link, path, name, qual, playlist, options):
        if playlist:
            self.opts["ignoreerrors"] = True
            self.is_playlist = True

        self.__gid = token_hex(4)

        await self.__on_download_start()

        self.opts["postprocessors"] = [
            {
                "add_chapters": True,
                "add_infojson": "if_exists",
                "add_metadata": True,
                "key": "FFmpegMetadata",
            }
        ]

        if qual.startswith("ba/b-"):
            audio_info = qual.split("-")
            qual = audio_info[0]
            audio_format = audio_info[1]
            rate = audio_info[2]
            self.opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": rate,
                }
            )
            if audio_format == "vorbis":
                self.__ext = ".ogg"
            elif audio_format == "alac":
                self.__ext = ".m4a"
            else:
                self.__ext = f".{audio_format}"

        self.opts["format"] = qual

        if options:
            self.__set_options(options)

        await sync_to_async(self.extractMetaData, link, name)
        if self.__is_cancelled:
            return

        base_name, ext = ospath.splitext(self.name)
        trim_name = self.name if self.is_playlist else base_name
        if len(trim_name.encode()) > 200:
            self.name = (
                self.name[:200] if self.is_playlist else f"{base_name[:200]}{ext}"
            )
            base_name = ospath.splitext(self.name)[0]

        if self.is_playlist:
            self.opts["outtmpl"] = {
                "default": f"{path}/{self.name}/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s",
                "thumbnail": f"{path}/yt-dlp-thumb/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s",
            }
        elif any(
            key in options
            for key in [
                "writedescription",
                "writeinfojson",
                "writeannotations",
                "writedesktoplink",
                "writewebloclink",
                "writeurllink",
                "writesubtitles",
                "writeautomaticsub",
            ]
        ):
            self.opts["outtmpl"] = {
                "default": f"{path}/{base_name}/{self.name}",
                "thumbnail": f"{path}/yt-dlp-thumb/{base_name}.%(ext)s",
            }
        else:
            self.opts["outtmpl"] = {
                "default": f"{path}/{self.name}",
                "thumbnail": f"{path}/yt-dlp-thumb/{base_name}.%(ext)s",
            }

        if qual.startswith("ba/b"):
            self.name = f"{base_name}{self.__ext}"

        if self.__listener.is_leech:
            self.opts["postprocessors"].append(
                {
                    "format": "jpg",
                    "key": "FFmpegThumbnailsConvertor",
                    "when": "before_dl",
                }
            )
        if self.__ext in [
            ".mp3",
            ".mkv",
            ".mka",
            ".ogg",
            ".opus",
            ".flac",
            ".m4a",
            ".mp4",
            ".mov",
            "m4v",
        ]:
            self.opts["postprocessors"].append(
                {
                    "already_have_thumbnail": self.__listener.is_leech,
                    "key": "EmbedThumbnail",
                }
            )
        elif not self.__listener.is_leech:
            self.opts["writethumbnail"] = False

        msg, button = await stop_duplicate_check(self.name, self.__listener)
        if msg:
            await self.__listener.onDownloadError(msg, button)
            return
        if limit_exceeded := await limit_checker(
            self.__size,
            self.__listener,
            is_ytdlp=True,
            is_playlist=self.playlist_count,
        ):
            await self.__listener.onDownloadError(limit_exceeded)
            return
        added_to_queue, event = await is_queued(self.__listener.uid)
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {self.name}")
            async with download_dict_lock:
                download_dict[self.__listener.uid] = QueueStatus(
                    self.name, self.__size, self.__gid, self.__listener, "dl"
                )
            await event.wait()
            async with download_dict_lock:
                if self.__listener.uid not in download_dict:
                    return
            LOGGER.info(f"Start Queued Download from YT_DLP: {self.name}")
            await self.__on_download_start(True)
        else:
            LOGGER.info(f"Download with YT_DLP: {self.name}")

        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)

        await sync_to_async(self.__download, link, path)

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.name}")
        if not self.__downloading:
            await self.__listener.onDownloadError("Download Cancelled by User!")

    def __set_options(self, options):
        options = options.split("|")
        for opt in options:
            key, value = map(str.strip, opt.split(":", 1))
            if key == "format" and value.startswith("ba/b-"):
                continue
            if value.startswith("^"):
                if "." in value or value == "^inf":
                    value = float(value.split("^", 1)[1])
                else:
                    value = int(value.split("^", 1)[1])
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.startswith(("{", "[", "(")) and value.endswith(
                ("}", "]", ")")
            ):
                value = eval(value)

            if key == "postprocessors":
                if isinstance(value, list):
                    self.opts[key].extend(tuple(value))
                elif isinstance(value, dict):
                    self.opts[key].append(value)
            else:
                self.opts[key] = value
