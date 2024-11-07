from html import escape
from time import time
from asyncio import iscoroutinefunction
from contextlib import suppress

from psutil import disk_usage

from bot import (
    DOWNLOAD_DIR,
    task_dict,
    status_dict,
    bot_start_time,
    task_dict_lock,
)
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.telegram_helper.button_build import ButtonMaker

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOADING_TG = "Uploading to Telegram"
    STATUS_UPLOADING_GD = "Uploading to Gdrive"
    STATUS_UPLOADING_RC = "Uploading to Rclone"
    STATUS_DOWNLOADING_TG = "Downloading from Telegram"
    STATUS_DOWNLOADING_MEGA = "Downloading from Mega"
    STATUS_DOWNLOADING_GD = "Downloading from Gdrive"
    STATUS_DOWNLOADING_A = "Downloading with Aria"
    STATUS_DOWNLOADING_YT = "Downloading with yt-dlp"
    STATUS_DOWNLOADING_Q = "Downloading with qBitTorrent"
    STATUS_DOWNLOADING_RC = "Downloading from Rclone"
    STATUS_CLONING_GD = "Cloning to Gdrive"
    STATUS_CLONING_RC = "Cloning to Rclone"
    STATUS_QUEUEDL = "Download is pending"
    STATUS_QUEUEUP = "Upload is pending"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving with p7zip"
    STATUS_EXTRACTING = "Extracting with p7zip"
    STATUS_SPLITTING = "Splitting with p7zip"
    STATUS_CHECKING = "CheckUp"
    STATUS_SEEDING = "Seeding torrent"
    STATUS_SAMVID = "Generating sample video"
    STATUS_CONVERTING = "Converting format"
    STATUS_METADATA = "Metadata modifying"


async def getTaskByGid(gid: str):
    async with task_dict_lock:
        for task in task_dict.values():
            if hasattr(task, "seeding"):
                await sync_to_async(task.update)
            if task.gid().startswith(gid):
                return task
        return None


def getSpecificTasks(status, userId):
    if status == "All":
        if userId:
            return [tk for tk in task_dict.values() if tk.listener.userId == userId]
        return list(task_dict.values())
    if userId:
        return [
            tk
            for tk in task_dict.values()
            if tk.listener.userId == userId
            and (
                (st := tk.status())
                and st == status
                or status == MirrorStatus.STATUS_DOWNLOADING
            )
        ]
    return [
        tk
        for tk in task_dict.values()
        if (st := tk.status())
        and st == status
        or status == MirrorStatus.STATUS_DOWNLOADING
    ]


async def getAllTasks(req_status: str, userId):
    async with task_dict_lock:
        return await sync_to_async(getSpecificTasks, req_status, userId)


def get_readable_file_size(size_in_bytes: int):
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return (
        f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"
        if index > 0
        else f"{size_in_bytes:.2f}B"
    )


def get_readable_time(seconds, full_time=False):
    periods = [
        ("millennium", 31536000000),
        ("century", 3153600000),
        ("decade", 315360000),
        ("year", 31536000),
        ("month", 2592000),
        ("week", 604800),
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    ]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural_suffix = "s" if period_value > 1 else ""
            result += f"{int(period_value)} {period_name}{plural_suffix} "
            if not full_time:
                break
    return result.strip()


def time_to_seconds(time_duration):
    hours, minutes, seconds = map(int, time_duration.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def speed_string_to_bytes(size_text: str):
    size = 0
    size_text = size_text.lower()
    if "k" in size_text:
        size += float(size_text.split("k")[0]) * 1024
    elif "m" in size_text:
        size += float(size_text.split("m")[0]) * 1048576
    elif "g" in size_text:
        size += float(size_text.split("g")[0]) * 1073741824
    elif "t" in size_text:
        size += float(size_text.split("t")[0]) * 1099511627776
    elif "b" in size_text:
        size += float(size_text.split("b")[0])
    return size


def progress_bar(pct):
    if isinstance(pct, str):
        pct = float(pct.strip("%"))
    p = min(max(pct, 0), 100)
    cFull = int((p + 5) // 10)
    p_str = "●" * cFull
    p_str += "○" * (10 - cFull)
    return p_str


def source(self):
    return (
        sender_chat.title
        if (sender_chat := self.message.sender_chat)
        else self.message.from_user.username or self.message.from_user.id
    )


async def get_readable_message(sid, is_user, page_no=1, status="All", page_step=1):
    msg = ""
    button = None

    tasks = await sync_to_async(getSpecificTasks, status, sid if is_user else None)

    STATUS_LIMIT = 4
    tasks_no = len(tasks)
    pages = (max(tasks_no, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT
    if page_no > pages:
        page_no = (page_no - 1) % pages + 1
        status_dict[sid]["page_no"] = page_no
    elif page_no < 1:
        page_no = pages - (abs(page_no) % pages)
        status_dict[sid]["page_no"] = page_no
    start_position = (page_no - 1) * STATUS_LIMIT

    for index, task in enumerate(
        tasks[start_position : STATUS_LIMIT + start_position], start=1
    ):
        tstatus = await sync_to_async(task.status) if status == "All" else status
        msg += f"<b>{index + start_position}. {tstatus}:</b>\n"
        msg += f"{escape(f'{task.name()}')}"
        if tstatus not in [
            MirrorStatus.STATUS_SPLITTING,
            MirrorStatus.STATUS_SEEDING,
            MirrorStatus.STATUS_SAMVID,
            MirrorStatus.STATUS_CONVERTING,
            MirrorStatus.STATUS_QUEUEUP,
            MirrorStatus.STATUS_METADATA,
        ]:
            progress = (
                await task.progress()
                if iscoroutinefunction(task.progress)
                else task.progress()
            )
            msg += f"\n{progress_bar(progress)} {progress}"
            msg += f"\n{task.processed_bytes()} of {task.size()}"
            msg += f"\n<b>Speed:</b> {task.speed()}\n<b>Estimated:</b> {task.eta()}"
            if hasattr(task, "seeders_num"):
                with suppress(Exception):
                    msg += f"\n<b>Seeders:</b> {task.seeders_num()} <b>Leechers:</b> {task.leechers_num()}"
        elif tstatus == MirrorStatus.STATUS_SEEDING:
            msg += f"\n<b>Size: </b>{task.size()}"
            msg += f"\n<b>Speed: </b>{task.seed_speed()}"
            msg += f"\n<b>Uploaded: </b>{task.uploaded_bytes()}"
            msg += f"\n<b>Ratio: </b>{task.ratio()}"
        else:
            msg += f"\n<b>Size: </b>{task.size()}"
        msg += f"\n<b>Elapsed: </b>{get_readable_time(time() - task.message.date.timestamp())}"
        msg += f"\n<b>By: {source (task.listener)}</b>"
        msg += f"\n/stop_{task.gid()[:7]}\n\n"

    if len(msg) == 0:
        if status == "All":
            return None, None
        msg = f"No Active {status} Tasks!\n\n"
    if tasks_no > STATUS_LIMIT:
        buttons = ButtonMaker()
        msg += f"\n<b>Page:</b> {page_no}/{pages} | <b>Tasks:</b> {tasks_no}"
        buttons.callback("Prev", f"status {sid} pre", position="header")
        buttons.callback("Next", f"status {sid} nex", position="header")
        button = buttons.menu(8)
    msg += f"<b>\nFree disk:</b> {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}"
    msg += f"\n<b>Bot uptime:</b> {get_readable_time(time() - bot_start_time)}"
    return msg, button
