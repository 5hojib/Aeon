import os
from hashlib import md5
from contextlib import suppress

from langcodes import Language
from aiofiles.os import path as aiopath

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.status_utils import (
    get_readable_time,
    get_readable_file_size,
)


class DefaultDict(dict):
    def __missing__(self, key):
        return "Unknown"


async def generate_caption(file, dirpath, lcaption):
    up_path = os.path.join(dirpath, file)

    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                up_path,
            ]
        )
        if result[1]:
            LOGGER.info(f"Get Media Info: {result[1]}")

        ffresult = eval(result[0])
    except Exception as e:
        LOGGER.error(f"Media Info: {e}. Mostly File not found!")
        return file

    format_info = ffresult.get("format")
    if not format_info:
        return file

    duration = round(float(format_info.get("duration", 0)))
    lang, stitles, qual = "", "", ""

    streams = ffresult.get("streams", [])
    if streams and streams[0].get("codec_type") == "video":
        qual = get_video_quality(streams[0].get("height"))

        for stream in streams:
            if stream.get("codec_type") == "audio":
                lang = update_language(lang, stream)
            if stream.get("codec_type") == "subtitle":
                stitles = update_subtitles(stitles, stream)

    lang = lang[:-2] if lang else "Unknown"
    stitles = stitles[:-2] if stitles else "Unknown"
    qual = qual if qual else "Unknown"
    md5_hex = calculate_md5(up_path)

    caption_dict = DefaultDict(
        filename=file,
        size=get_readable_file_size(await aiopath.getsize(up_path)),
        duration=get_readable_time(duration, True),
        quality=qual,
        audios=lang,
        subtitles=stitles,
        md5_hash=md5_hex,
    )

    return lcaption.format_map(caption_dict)


def get_video_quality(height):
    quality_map = {
        480: "480p",
        540: "540p",
        720: "720p",
        1080: "1080p",
        2160: "2160p",
        4320: "4320p",
        8640: "8640p",
    }
    for h, q in sorted(quality_map.items()):
        if height <= h:
            return q
    return "Unknown"


def update_language(lang, stream):
    language_code = stream.get("tags", {}).get("language")
    if language_code:
        with suppress(Exception):
            language_name = Language.get(language_code).display_name()
            if language_name not in lang:
                lang += f"{language_name}, "
    return lang


def update_subtitles(stitles, stream):
    subtitle_code = stream.get("tags", {}).get("language")
    if subtitle_code:
        with suppress(Exception):
            subtitle_name = Language.get(subtitle_code).display_name()
            if subtitle_name not in stitles:
                stitles += f"{subtitle_name}, "
    return stitles


def calculate_md5(filepath):
    hash_md5 = md5()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            hash_md5.update(byte_block)
    return hash_md5.hexdigest()
