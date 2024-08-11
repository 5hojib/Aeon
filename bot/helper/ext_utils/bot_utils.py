import contextlib
from os import path as ospath
from re import match as re_match
from html import escape
from time import time
from uuid import uuid4
from asyncio import (
    sleep,
    create_subprocess_exec,
    create_subprocess_shell,
    run_coroutine_threadsafe,
)
from functools import wraps, partial
from urllib.parse import urlparse
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor

from psutil import disk_usage
from aiohttp import ClientSession as aioClientSession
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import mkdir
from pyrogram.types import BotCommand

from bot import (
    LOGGER,
    DATABASE_URL,
    bot_loop,
    bot_name,
    user_data,
    config_dict,
    botStartTime,
    download_dict,
    extra_buttons,
    download_dict_lock,
)
from bot.helper.aeon_utils.tinyfy import tinyfy
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.shorteners import short_url
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

if config_dict.get("GDRIVE_ID"):
    commands = [
        "MirrorCommand",
        "LeechCommand",
        "YtdlCommand",
        "YtdlLeechCommand",
        "CloneCommand",
        "MediaInfoCommand",
        "CountCommand",
        "ListCommand",
        "SearchCommand",
        "UserSetCommand",
        "StatusCommand",
        "StatsCommand",
        "StopAllCommand",
        "HelpCommand",
        "BotSetCommand",
        "LogCommand",
        "RestartCommand",
    ]
else:
    commands = [
        "LeechCommand",
        "YtdlLeechCommand",
        "MediaInfoCommand",
        "SearchCommand",
        "UserSetCommand",
        "StatusCommand",
        "StatsCommand",
        "StopAllCommand",
        "HelpCommand",
        "BotSetCommand",
        "LogCommand",
        "RestartCommand",
    ]

command_descriptions = {
    "MirrorCommand": "- Start mirroring",
    "LeechCommand": "- Start leeching",
    "YtdlCommand": "- Mirror yt-dlp supported link",
    "YtdlLeechCommand": "- Leech through yt-dlp supported link",
    "CloneCommand": "- Copy file/folder to Drive",
    "MediaInfoCommand": "- Get MediaInfo",
    "CountCommand": "- Count file/folder on Google Drive.",
    "ListCommand": "- Search in Drive",
    "SearchCommand": "- Search in Torrent",
    "UserSetCommand": "- User settings",
    "StatusCommand": "- Get mirror status message",
    "StatsCommand": "- Check Bot & System stats",
    "StopAllCommand": "- Cancel all tasks added by you to the bot.",
    "HelpCommand": "- Get detailed help",
    "BotSetCommand": "- [ADMIN] Open Bot settings",
    "LogCommand": "- [ADMIN] View log",
    "RestartCommand": "- [ADMIN] Restart the bot",
}


THREADPOOL = ThreadPoolExecutor(max_workers=1000)
MAGNET_REGEX = r"magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*"
URL_REGEX = r"^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$"
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
STATUS_START = 0
PAGES = 1
PAGE_NO = 1
STATUS_LIMIT = 4


class MirrorStatus:
    STATUS_UPLOADING = "Uploading"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_CLONING = "Cloning"
    STATUS_QUEUEDL = "DL queued"
    STATUS_QUEUEUP = "UL queued"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Splitting"
    STATUS_CHECKING = "CheckUp"
    STATUS_SEEDING = "Seeding"
    STATUS_PROCESSING = "Processing"


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self.__set_interval())

    async def __set_interval(self):
        while True:
            await sleep(self.interval)
            await self.action()

    def cancel(self):
        self.task.cancel()


def isMkv(file):
    return file.lower().endswith("mkv")


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


async def getDownloadByGid(gid):
    async with download_dict_lock:
        return next(
            (
                dl
                for dl in download_dict.values()
                if len(gid) >= 8 and dl.gid().startswith(gid)
            ),
            None,
        )


async def getAllDownload(req_status, user_id=None):
    dls = []
    async with download_dict_lock:
        for dl in list(download_dict.values()):
            if user_id and user_id != dl.message.from_user.id:
                continue
            status = dl.status()
            if req_status in ["all", status]:
                dls.append(dl)
    return dls


async def get_user_tasks(user_id, maxtask):
    if tasks := await getAllDownload("all", user_id):
        return len(tasks) >= maxtask
    return None


def bt_selection_buttons(id_):
    gid = id_[:8]
    pincode = "".join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict["BASE_URL"]
    buttons.url("Select", f"{BASE_URL}/app/files/{id_}")
    buttons.callback("Pincode", f"btsel pin {gid} {pincode}")
    buttons.callback("Cancel", f"btsel rm {gid} {id_}")
    buttons.callback("Done Selecting", f"btsel done {gid} {id_}")
    return buttons.column(2)


async def get_telegraph_list(telegraph_content):
    path = [
        (await telegraph.create_page(title="Drive Search", content=content))["path"]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await telegraph.edit_telegraph(path, telegraph_content)
    buttons = ButtonMaker()
    buttons.url("View", f"https://telegra.ph/{path[0]}")
    buttons = extra_btns(buttons)
    return buttons.column(1)


def handleIndex(index, dic):
    while True:
        if abs(index) < len(dic):
            break
        if index < 0:
            index = len(dic) - abs(index)
        elif index > 0:
            index = index - len(dic)
    return index


async def fetch_user_tds(user_id, force=False):
    user_dict = user_data.get(user_id, {})
    if user_dict.get("td_mode", False) or force:
        return user_dict.get("user_tds", {})
    return {}


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


def get_readable_message():
    msg = "<b>Powered by Aeon</b>\n\n"
    button = None
    tasks = len(download_dict)
    currentTime = get_readable_time(time() - botStartTime)
    if config_dict["BOT_MAX_TASKS"]:
        bmax_task = f"/{config_dict['BOT_MAX_TASKS']}"
    else:
        bmax_task = ""
    globals()["PAGES"] = (tasks + STATUS_LIMIT - 1) // STATUS_LIMIT
    if PAGE_NO > PAGES and PAGES != 0:
        globals()["STATUS_START"] = STATUS_LIMIT * (PAGES - 1)
        globals()["PAGE_NO"] = PAGES
    for download in list(download_dict.values())[
        STATUS_START : STATUS_LIMIT + STATUS_START
    ]:
        msg += f"<b>{download.status()}:</b> {escape(f'{download.name()}')}\n"
        msg += f"by {source(download)}\n"
        if download.status() not in [
            MirrorStatus.STATUS_SPLITTING,
            MirrorStatus.STATUS_SEEDING,
            MirrorStatus.STATUS_PROCESSING,
        ]:
            msg += f"<blockquote><code>{progress_bar(download.progress())}</code> {download.progress()}"
            msg += f"\n{download.processed_bytes()} of {download.size()}"
            msg += f"\nSpeed: {download.speed()}"
            msg += f"\nEstimated: {download.eta()}"
            if hasattr(download, "seeders_num"):
                with contextlib.suppress(Exception):
                    msg += f"\nSeeders: {download.seeders_num()} | Leechers: {download.leechers_num()}"
        elif download.status() == MirrorStatus.STATUS_SEEDING:
            msg += f"<blockquote>Size: {download.size()}"
            msg += f"\nSpeed: {download.upload_speed()}"
            msg += f"\nUploaded: {download.uploaded_bytes()}"
            msg += f"\nRatio: {download.ratio()}"
            msg += f"\nTime: {download.seeding_time()}"
        else:
            msg += f"<blockquote>Size: {download.size()}"
        msg += f"\nElapsed: {get_readable_time(time() - download.message.date.timestamp())}</blockquote>"
        msg += f"\n<blockquote>/stop_{download.gid()[:8]}</blockquote>\n\n"
    if len(msg) == 0:
        return None, None
    if tasks > STATUS_LIMIT:
        buttons = ButtonMaker()
        buttons.callback("Prev", "status pre")
        buttons.callback(f"{PAGE_NO}/{PAGES}", "status ref")
        buttons.callback("Next", "status nex")
        button = buttons.column(3)
    msg += f"<b>• Tasks</b>: {tasks}{bmax_task}"
    msg += f"\n<b>• Bot uptime</b>: {currentTime}"
    msg += f"\n<b>• Free disk space</b>: {get_readable_file_size(disk_usage('/usr/src/app/downloads/').free)}"
    return msg, button


def text_to_bytes(size_text):
    size_text = size_text.lower()
    multiplier = {
        "k": 1024,
        "m": 1048576,
        "g": 1073741824,
        "t": 1099511627776,
        "p": 1125899906842624,
    }
    for unit, factor in multiplier.items():
        if unit in size_text:
            size_value = float(size_text.split(unit)[0])
            return size_value * factor
    return 0


async def turn_page(data):
    global STATUS_START, PAGE_NO
    async with download_dict_lock:
        if data[1] == "nex":
            if PAGE_NO == PAGES:
                STATUS_START = 0
                PAGE_NO = 1
            else:
                STATUS_START += STATUS_LIMIT
                PAGE_NO += 1
        elif data[1] == "pre":
            if PAGE_NO == 1:
                STATUS_START = STATUS_LIMIT * (PAGES - 1)
                PAGE_NO = PAGES
            else:
                STATUS_START -= STATUS_LIMIT
                PAGE_NO -= 1


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


def is_magnet(url):
    return bool(re_match(MAGNET_REGEX, url))


def is_url(url):
    return bool(re_match(URL_REGEX, url))


def is_gdrive_link(url):
    return "drive.google.com" in url


def is_telegram_link(url):
    return url.startswith(("https://t.me/", "tg://openmessage?user_id="))


def is_share_link(url):
    domain = urlparse(url).hostname
    return any(x in domain for x in ["appdirve", "hubdrive", "gdflix", "filepress"])


def is_mega_link(url):
    return "mega.nz" in url or "mega.co.nz" in url


def is_rclone_path(path):
    return bool(
        re_match(
            r"^(mrcc:)?(?!magnet:)(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$",
            path,
        )
    )


def get_mega_link_type(url):
    return "folder" if "folder" in url or "/#F!" in url else "file"


def arg_parser(items, arg_base):
    if not items:
        return arg_base
    bool_arg_set = {"-b", "-e", "-z", "-s", "-j", "-d"}
    t = len(items)
    i = 0
    arg_start = -1
    while i + 1 <= t:
        part = items[i].strip()
        if part in arg_base:
            if arg_start == -1:
                arg_start = i
            if i + 1 == t and part in bool_arg_set or part in ["-s", "-j"]:
                arg_base[part] = True
            else:
                sub_list = []
                for j in range(i + 1, t):
                    item = items[j].strip()
                    if item in arg_base:
                        if part in bool_arg_set and not sub_list:
                            arg_base[part] = True
                        break
                    sub_list.append(item.strip())
                    i += 1
                if sub_list:
                    arg_base[part] = " ".join(sub_list)
        i += 1
    link = []
    if items[0].strip() not in arg_base:
        if arg_start == -1:
            link.extend(item.strip() for item in items)
        else:
            link.extend(items[r].strip() for r in range(arg_start))
        if link:
            arg_base["link"] = " ".join(link)
    return arg_base


async def get_content_type(url):
    try:
        async with aioClientSession(trust_env=True) as session:
            async with session.get(url, verify_ssl=False) as response:
                return response.headers.get("Content-Type")
    except Exception:
        return None


def update_user_ldata(id_, key=None, value=None):
    exception_keys = ["is_sudo", "is_auth"]
    if not key and not value:
        if id_ in user_data:
            updated_data = {
                k: v for k, v in user_data[id_].items() if k in exception_keys
            }
            user_data[id_] = updated_data
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def download_image_url(url):
    path = "Images/"
    if not await aiopath.isdir(path):
        await mkdir(path)
    image_name = url.split("/")[-1]
    des_dir = ospath.join(path, image_name)
    async with aioClientSession() as session, session.get(url) as response:
        if response.status == 200:
            async with aiopen(des_dir, "wb") as file:
                async for chunk in response.content.iter_chunked(1024):
                    await file.write(chunk)
            LOGGER.info(f"Image Downloaded Successfully as {image_name}")
        else:
            LOGGER.error(f"Failed to Download Image from {url}")
    return des_dir


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    return stdout, stderr, proc.returncode


def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))

    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future

    return wrapper


async def checking_access(user_id, button=None):
    token_timeout = config_dict["TOKEN_TIMEOUT"]
    if not token_timeout:
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    if DATABASE_URL:
        data["time"] = await DbManager().get_token_expiry(user_id)
    expire = data.get("time")
    isExpired = (
        expire is None or expire is not None and (time() - expire) > token_timeout
    )
    if isExpired:
        token = data["token"] if expire is None and "token" in data else str(uuid4())
        if expire is not None:
            del data["time"]
        data["token"] = token
        if DATABASE_URL:
            await DbManager().update_user_token(user_id, token)
        user_data[user_id].update(data)
        time_str = get_readable_time(token_timeout, True)
        if button is None:
            button = ButtonMaker()
        button.url(
            "Collect token",
            tinyfy(short_url(f"https://telegram.me/{bot_name}?start={token}")),
        )
        return (
            f"Your token has expired, please collect a new token.\n<b>It will expire after {time_str}</b>!",
            button,
        )
    return None, button


def extra_btns(buttons):
    if extra_buttons:
        for btn_name, btn_url in extra_buttons.items():
            buttons.url(btn_name, btn_url)
    return buttons


commands = [
    BotCommand(
        getattr(BotCommands, cmd)[0]
        if isinstance(getattr(BotCommands, cmd), list)
        else getattr(BotCommands, cmd),
        command_descriptions[cmd],
    )
    for cmd in commands
]


async def set_commands(bot):
    if config_dict["SET_COMMANDS"]:
        await bot.set_bot_commands(commands)
