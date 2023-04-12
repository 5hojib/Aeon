#!/usr/bin/env python3
from re import match as re_match
from time import time
from html import escape
from psutil import virtual_memory, cpu_percent, disk_usage
from requests import head as rhead
from urllib.request import urlopen
from asyncio import create_subprocess_exec, create_subprocess_shell, run_coroutine_threadsafe, sleep
from asyncio.subprocess import PIPE
from pyrogram.types import BotCommand
from functools import partial, wraps
from concurrent.futures import ThreadPoolExecutor

from bot import download_dict, download_dict_lock, botStartTime, user_data, config_dict, bot_loop, extra_buttons
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

MAGNET_REGEX = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*'
URL_REGEX = r'^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$'
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
STATUS_START = 0
PAGES = 1
PAGE_NO = 1


class MirrorStatus:
    STATUS_UPLOADING = "Uploading"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_CLONING = "Cloning"
    STATUS_QUEUEDL = "DL waiting"
    STATUS_QUEUEUP = "UL waiting"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Splitting"
    STATUS_CHECKING = "CheckUp"
    STATUS_SEEDING = "Seeding"


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

def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes}B'

async def getDownloadByGid(gid):
    async with download_dict_lock:
        return next((dl for dl in download_dict.values() if dl.gid() == gid), None)

async def getAllDownload(req_status, user_id=None):
    dls = []
    async with download_dict_lock:
        for dl in list(download_dict.values()):
            if user_id and user_id != dl.message.from_user.id:
                continue
            status = dl.status()
            if req_status in ['all', status]:
                dls.append(dl)
    return dls

def bt_selection_buttons(id_, isCanCncl=True):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = ''.join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict['BASE_URL']
    if config_dict['WEB_PINCODE']:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.ibutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    if isCanCncl:
        buttons.ibutton("Cancel", f"btsel rm {gid} {id_}")
    buttons.ibutton("Done Selecting", f"btsel done {gid} {id_}")
    return buttons.build_menu(2)

def get_progress_bar_string(pct):
    pct = float(pct.strip('%'))
    p = min(max(pct, 0), 100)
    cFull = int(p / 6.25)
    cIncomplete = int(round((p / 6.25 - cFull) * 7))
    p_str = '●' * cFull
    if cIncomplete > 0:
        s = '○◔◔◑◑◕◕●'
        incomplete_char = s[cIncomplete - 1]
        p_str += incomplete_char
    p_str += '○' * (16 - len(p_str))
    return f"{p_str}"

def get_readable_message():
    msg = "<b>Powered by Luna</b>\n\n"
    button = None
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    tasks = len(download_dict)
    globals()['PAGES'] = (tasks + STATUS_LIMIT - 1) // STATUS_LIMIT
    if PAGE_NO > PAGES and PAGES != 0:
        globals()['STATUS_START'] = STATUS_LIMIT * (PAGES - 1)
        globals()['PAGE_NO'] = PAGES
    for download in list(download_dict.values())[STATUS_START:STATUS_LIMIT+STATUS_START]:
        msg += f"<b><i>{escape(f'{download.name()}')}</i></b>\n\n"
        msg += f"<b>┌ {download.status()} with {download.engine}</b>"
        if download.status() not in [MirrorStatus.STATUS_SPLITTING, MirrorStatus.STATUS_SEEDING]:
            msg += f"\n<b>├ <a href='https://github.com/5hojib/Luna'>{get_progress_bar_string(download.progress())}</a></b> {download.progress()}"
            msg += f"\n<b>├ Processed</b>: {download.processed_bytes()} of {download.size()}"
            msg += f"\n<b>├ Speed</b>: {download.speed()}"
            msg += f"\n<b>├ Estimated</b>: {download.eta()}"
            if hasattr(download, 'seeders_num'):
                try:
                    msg += f"\n<b>├ Seeders</b>: {download.seeders_num()} | <b>Leechers</b>: {download.leechers_num()}"
                except:
                    pass
        elif download.status() == MirrorStatus.STATUS_SEEDING:
            msg += f"\n<b>├ Size</b>: {download.size()}"
            msg += f"\n<b>├ Speed</b>: {download.upload_speed()}"
            msg += f"\n<b>├ Uploaded</b>: {download.uploaded_bytes()}"
            msg += f"\n<b>├ Ratio</b>: {download.ratio()}"
            msg += f"\n<b>├ Time</b>: {download.seeding_time()}"
        else:
            msg += f"\n<b>├ Size</b>: {download.size()}"
        msg += f"\n<b>├ Source</b>: {download.extra_details['source']}"
        msg += f"\n<b>├ Elapsed</b>: {get_readable_time(time() - download.extra_details['startTime'])}"
        msg += f"\n<b>└ </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>\n\n"
    if len(msg) == 0:
        return None, None
    dl_speed = 0
    up_speed = 0
    for download in list(download_dict.values()):
            if download.status() == MirrorStatus.STATUS_DOWNLOADING:
                spd = download.speed()
                if 'K' in spd:
                    dl_speed += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    dl_speed += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_UPLOADING:
                spd = download.speed()
                if 'KB/s' in spd:
                    up_speed += float(spd.split('K')[0]) * 1024
                elif 'MB/s' in spd:
                    up_speed += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_SEEDING:
                spd = download.upload_speed()
                if 'K' in spd:
                    up_speed += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    up_speed += float(spd.split('M')[0]) * 1048576
    if tasks > STATUS_LIMIT:
        buttons = ButtonMaker()
        buttons.ibutton("Prev", "status pre")
        buttons.ibutton(f"{PAGE_NO}/{PAGES}", "status ref")
        buttons.ibutton("Next", "status nex")
        button = buttons.build_menu(3)
    msg += f"<b>• Tasks</b>: {tasks}"
    msg += f"<b>• Bot uptime</b>: {get_readable_time(time() - botStartTime)}"
    msg += f"\n<b>• Free disk space</b>: {get_readable_file_size(disk_usage(config_dict['DOWNLOAD_DIR']).free)}"
    msg += f"\n<b>• Total uploading speed</b>: {get_readable_file_size(up_speed)}/s"
    msg += f"\n<b>• Total downloading speed</b>: {get_readable_file_size(dl_speed)}/s"
    return msg, button

def extra_btns(buttons):
    if extra_buttons:
        for btn_name, btn_url in extra_buttons.items():
            buttons.ubutton(btn_name, btn_url)
    return buttons

async def turn_page(data):
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
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

async def check_user_tasks(user_id, maxtask):
    if tasks:= await getAllDownload(MirrorStatus.STATUS_DOWNLOADING, user_id):
        return len(tasks) >= maxtask

def get_readable_time(seconds):
    periods = [(' Days ', 86400), (' Hours ', 3600), (' Min ', 60), (' Sec', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result

def is_magnet(url):
    magnet = re_match(MAGNET_REGEX, url)
    return bool(magnet)

def is_url(url):
    url = re_match(URL_REGEX, url)
    return bool(url)

def is_gdrive_link(url):
    return "drive.google.com" in url

def is_share_link(url: str):
    if 'gdtot' in url:
        regex = r'(https?:\/\/.+\.gdtot\..+\/file\/\d+)'
    else:
        regex = r'(https?:\/\/(\S+)\..+\/file\/\S+)'
    return bool(re_match(regex, url))

def is_mega_link(url):
    return "mega.nz" in url or "mega.co.nz" in url

def is_rclone_path(path):
    return bool(re_match(r'^(mrcc:)?(?!magnet:)(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$', path))

def get_mega_link_type(url):
    return "folder" if "folder" in url or "/#F!" in url else "file"

def get_content_type(link):
    try:
        res = rhead(link, allow_redirects=True, timeout=5, headers={'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            content_type = res.info().get_content_type()
        except:
            content_type = None
    return content_type

def update_user_ldata(id_, key, value):
    if not key and not value:
        user_data[id_] = {}
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value

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
    with ThreadPoolExecutor() as pool:
        future = bot_loop.run_in_executor(pool, pfunc)
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

async def set_commands(client):
    if config_dict['SET_COMMANDS']:
        await client.set_bot_commands([
            BotCommand(
                f'{BotCommands.MirrorCommand[0]}', f'or /{BotCommands.MirrorCommand[1]} Mirror'),
            BotCommand(
                f'{BotCommands.LeechCommand[0]}', f'or /{BotCommands.LeechCommand[1]} Leech'),
            BotCommand(
                f'{BotCommands.ZipMirrorCommand[0]}', f'or /{BotCommands.ZipMirrorCommand[1]} Mirror and upload as zip'),
            BotCommand(
                f'{BotCommands.ZipLeechCommand[0]}', f'or /{BotCommands.ZipLeechCommand[1]} Leech and upload as zip'),
            BotCommand(
                f'{BotCommands.UnzipMirrorCommand[0]}', f'or /{BotCommands.UnzipMirrorCommand[1]} Mirror and extract files'),
            BotCommand(
                f'{BotCommands.UnzipLeechCommand[0]}', f'or /{BotCommands.UnzipLeechCommand[1]} Leech and extract files'),
            BotCommand(
                f'{BotCommands.QbMirrorCommand[0]}', f'or /{BotCommands.QbMirrorCommand[1]} Mirror torrent using qBittorrent'),
            BotCommand(
                f'{BotCommands.QbLeechCommand[0]}', f'or /{BotCommands.QbLeechCommand[1]} Leech torrent using qBittorrent'),
            BotCommand(
                f'{BotCommands.QbZipMirrorCommand[0]}', f'or /{BotCommands.QbZipMirrorCommand[1]} Mirror torrent and upload as zip using qb'),
            BotCommand(
                f'{BotCommands.QbZipLeechCommand[0]}', f'or /{BotCommands.QbZipLeechCommand[1]} Leech torrent and upload as zip using qb'),
            BotCommand(
                f'{BotCommands.QbUnzipMirrorCommand[0]}', f'or /{BotCommands.QbUnzipMirrorCommand[1]} Mirror torrent and extract files using qb'),
            BotCommand(
                f'{BotCommands.QbUnzipLeechCommand[0]}', f'or /{BotCommands.QbUnzipLeechCommand[1]} Leech torrent and extract using qb'),
            BotCommand(
                f'{BotCommands.YtdlCommand[0]}', f'or /{BotCommands.YtdlCommand[1]} Mirror yt-dlp supported link'),
            BotCommand(
                f'{BotCommands.YtdlLeechCommand[0]}', f'or /{BotCommands.YtdlLeechCommand[1]} Leech through yt-dlp supported link'),
            BotCommand(
                f'{BotCommands.YtdlZipCommand[0]}', f'or /{BotCommands.YtdlZipCommand[1]} Mirror yt-dlp supported link as zip'),
            BotCommand(
                f'{BotCommands.YtdlZipLeechCommand[0]}', f'or /{BotCommands.YtdlZipLeechCommand[1]} Leech yt-dlp support link as zip'),
            BotCommand(f'{BotCommands.CloneCommand}',
                       'Copy file/folder to Drive'),
            BotCommand(
                f'{BotCommands.StatusCommand[0]}', f'or /{BotCommands.StatusCommand[1]} Get mirror status message'),
            BotCommand(f'{BotCommands.StatsCommand}', 'Check bot stats'),
            BotCommand(f'{BotCommands.BtSelectCommand}',
                       'Select files to download only torrents'),
            BotCommand(f'{BotCommands.CategorySelect}',
                       'Select category to upload only mirror'),
            BotCommand(f'{BotCommands.CancelMirror}', 'Cancel a Task'),
            BotCommand(
                f'{BotCommands.CancelAllCommand[0]}', f'Cancel all tasks which added by you or {BotCommands.CancelAllCommand[1]} to in bots.'),
            BotCommand(f'{BotCommands.ListCommand}', 'Search in Drive'),
            BotCommand(f'{BotCommands.SearchCommand}', 'Search in Torrent'),
            BotCommand(f'{BotCommands.UserSetCommand}', 'Users settings'),
            BotCommand(f'{BotCommands.HelpCommand}', 'Get detailed help'),
        ])