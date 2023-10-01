from urllib.parse import urlparse
from base64 import b64encode
from datetime import datetime
from os import path as ospath
from pkg_resources import get_distribution
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from re import match as re_match
from time import time
from html import escape
from uuid import uuid4
from subprocess import run as srun
from asyncio import create_subprocess_exec, create_subprocess_shell, run_coroutine_threadsafe, sleep
from asyncio.subprocess import PIPE
from functools import partial, wraps
from concurrent.futures import ThreadPoolExecutor

from aiohttp import ClientSession as aioClientSession
from psutil import virtual_memory, cpu_percent, disk_usage
from requests import get as rget
from mega import MegaApi
from pyrogram.enums import ChatType
from pyrogram.types import BotCommand
from pyrogram.errors import PeerIdInvalid

from bot.helper.ext_utils.db_handler import DbManager
from bot import OWNER_ID, bot_name, DATABASE_URL, LOGGER, get_client, aria2, download_dict, download_dict_lock, botStartTime, user_data, config_dict, bot_loop, extra_buttons, user
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.ext_utils.shortners import short_url
from bot.helper.ext_utils.aeon_utils import tinyfy

THREADPOOL = ThreadPoolExecutor(max_workers = 1000)
MAGNET_REGEX = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*'
URL_REGEX = r'^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$'
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
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
        return next((dl for dl in download_dict.values() if len(gid) >= 8 and dl.gid().startswith(gid)), None)


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


async def get_user_tasks(user_id, maxtask):
    if tasks := await getAllDownload('all', user_id):
        return len(tasks) >= maxtask


def bt_selection_buttons(id_):
    gid = id_[:8]
    pincode = ''.join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict['BASE_URL']
    if config_dict['WEB_PINCODE']:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}")
        buttons.ibutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.ubutton("Select Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    buttons.ibutton("Cancel", f"btsel rm {gid} {id_}")
    buttons.ibutton("Done Selecting", f"btsel done {gid} {id_}")
    return buttons.build_menu(2)


async def get_telegraph_list(telegraph_content):
    path = [(await telegraph.create_page(title="Drive Search", content=content))["path"] for content in telegraph_content]
    if len(path) > 1:
        await telegraph.edit_telegraph(path, telegraph_content)
    buttons = ButtonMaker()
    buttons.ubutton("View", f"https://telegra.ph/{path[0]}")
    buttons = extra_btns(buttons)
    return buttons.build_menu(1)


def handleIndex(index, dic):
    while True:
        if abs(index) < len(dic):
            break
        if index < 0: index = len(dic) - abs(index)
        elif index > 0: index = index - len(dic)
    return index


async def fetch_user_tds(user_id, force=False):
    user_dict = user_data.get(user_id, {})
    if user_dict.get('td_mode', False) or force:
        return user_dict.get('user_tds', {})
    return {}


def progress_bar(pct):
    if isinstance(pct, str):
        pct = float(pct.strip('%'))
    p = min(max(pct, 0), 100)
    cFull = int((p + 5)// 10)
    p_str = '●' * cFull
    p_str += '○' * (10 - cFull)
    return p_str


def source(self):
    return (sender_chat.title if (sender_chat := self.message.sender_chat) else self.message.from_user.username or self.message.from_user.id)


def get_readable_message():
    msg = '<b>Powered by Aeon</b>\n\n'
    button = None
    tasks = len(download_dict)
    currentTime = get_readable_time(time() - botStartTime)
    if config_dict['BOT_MAX_TASKS']:
        bmax_task = f"/{config_dict['BOT_MAX_TASKS']}"
    else:
        bmax_task = ''
    globals()['PAGES'] = (tasks + STATUS_LIMIT - 1) // STATUS_LIMIT
    if PAGE_NO > PAGES and PAGES != 0:
        globals()['STATUS_START'] = STATUS_LIMIT * (PAGES - 1)
        globals()['PAGE_NO'] = PAGES
    for download in list(download_dict.values())[STATUS_START:STATUS_LIMIT+STATUS_START]:
        msg += f"{escape(f'{download.name()}')}\n"
        msg += f"by {source(download)}\n\n"
        msg += f"<b>{download.status()}...</b>"
        if download.status() not in [MirrorStatus.STATUS_SPLITTING, MirrorStatus.STATUS_SEEDING]:
            msg += f"\n<code>{progress_bar(download.progress())}</code> {download.progress()}"
            msg += f"\n{download.processed_bytes()} of {download.size()}"
            msg += f"\nSpeed: {download.speed()}"
            msg += f'\nEstimated: {download.eta()}'
            if hasattr(download, 'seeders_num'):
                try:
                    msg += f"\nSeeders: {download.seeders_num()} | Leechers: {download.leechers_num()}"
                except:
                    pass
        elif download.status() == MirrorStatus.STATUS_SEEDING:
            msg += f"\nSize: {download.size()}"
            msg += f"\nSpeed: {download.upload_speed()}"
            msg += f"\nUploaded: {download.uploaded_bytes()}"
            msg += f"\nRatio: {download.ratio()}"
            msg += f"\nTime: {download.seeding_time()}"
        else:
            msg += f"\nSize: {download.size()}"
        msg += f"\nElapsed: {get_readable_time(time() - download.message.date.timestamp())}"
        msg += f"\n/stop_{download.gid()[:8]}\n\n"
    if len(msg) == 0:
        return None, None
    dl_speed = 0
    up_speed = 0
    for download in download_dict.values():
            tstatus = download.status()
            if tstatus == MirrorStatus.STATUS_DOWNLOADING:
                dl_speed += text_size_to_bytes(download.speed())
            elif tstatus == MirrorStatus.STATUS_UPLOADING:
                up_speed += text_size_to_bytes(download.speed())
            elif tstatus == MirrorStatus.STATUS_SEEDING:
                up_speed += text_size_to_bytes(download.upload_speed())
    if tasks > STATUS_LIMIT:
        buttons = ButtonMaker()
        buttons.ibutton("Prev", "status pre")
        buttons.ibutton(f"{PAGE_NO}/{PAGES}", "status ref")
        buttons.ibutton("Next", "status nex")
        button = buttons.build_menu(3)
    msg += f"<b>• Tasks</b>: {tasks}{bmax_task}"
    msg += f"\n<b>• Bot uptime</b>: {currentTime}"
    msg += f"\n<b>• Free disk space</b>: {get_readable_file_size(disk_usage('/usr/src/app/downloads/').free)}"
    msg += f"\n<b>• Uploading speed</b>: {get_readable_file_size(up_speed)}/s"
    msg += f"\n<b>• Downloading speed</b>: {get_readable_file_size(dl_speed)}/s"
    return msg, button


def text_size_to_bytes(size_text):
    size = 0
    size_text = size_text.lower()
    if 'k' in size_text:
        size += float(size_text.split('k')[0]) * 1024
    elif 'm' in size_text:
        size += float(size_text.split('m')[0]) * 1048576
    elif 'g' in size_text:
        size += float(size_text.split('g')[0]) * 1073741824
    elif 't' in size_text:
        size += float(size_text.split('t')[0]) * 1099511627776
    return size


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


def get_readable_time(seconds):
    periods = [('millennium', 31536000000), ('century', 3153600000), ('decade', 315360000), ('year', 31536000), ('month', 2592000), ('week', 604800), ('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural_suffix = 's' if period_value > 1 else ''
            result += f'{int(period_value)} {period_name}{plural_suffix} '
            if len(result.split()) == 2:
                break
    return result.strip()


def is_magnet(url):
    return bool(re_match(MAGNET_REGEX, url))


def is_url(url):
    return bool(re_match(URL_REGEX, url))


def is_gdrive_link(url):
    return "drive.google.com" in url


def is_telegram_link(url):
    return url.startswith(('https://t.me/', 'tg://openmessage?user_id='))


def is_share_link(url):
    domain = urlparse(url).hostname
    return any(x in domain for x in ['appdirve', 'hubdrive', 'jiodrive', 'filepress'])


def is_mega_link(url):
    return "mega.nz" in url or "mega.co.nz" in url


def is_rclone_path(path):
    return bool(re_match(r'^(mrcc:)?(?!magnet:)(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$', path))


def get_mega_link_type(url):
    return "folder" if "folder" in url or "/#F!" in url else "file"


def arg_parser(items, arg_base):
    if not items:
        return arg_base
    bool_arg_set = {'-b', '-e', '-z', '-s', '-j', '-d'}
    t = len(items)
    i = 0
    arg_start = -1
    while i + 1 <= t:
        part = items[i].strip()
        if part in arg_base:
            if arg_start == -1:
                arg_start = i
            if i + 1 == t and part in bool_arg_set or part in ['-s', '-j']:
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
            arg_base['link'] = " ".join(link)
    return arg_base


async def get_content_type(url):
    try:
        async with aioClientSession(trust_env=True) as session:
            async with session.get(url, verify_ssl=False) as response:
                return response.headers.get('Content-Type')
    except:
        return None


def update_user_ldata(id_, key=None, value=None):
    exception_keys = ['is_sudo', 'is_auth']
    if not key and not value:
        if id_ in user_data:
            updated_data = {k: v for k, v in user_data[id_].items() if k in exception_keys}
            user_data[id_] = updated_data
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def download_image_url(url):
    path = "Images/"
    if not await aiopath.isdir(path):
        await mkdir(path)
    image_name = url.split('/')[-1]
    des_dir = ospath.join(path, image_name)
    async with aioClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiopen(des_dir, 'wb') as file:
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
    token_timeout = config_dict['TOKEN_TIMEOUT']
    if not token_timeout:
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    if DATABASE_URL:
        data['time'] = await DbManager().get_token_expire_time(user_id)
    expire = data.get('time')
    isExpired = (expire is None or expire is not None and (time() - expire) > token_timeout)
    if isExpired:
        token = data['token'] if expire is None and 'token' in data else str(uuid4())
        if expire is not None:
            del data['time']
        data['token'] = token
        if DATABASE_URL:
            await DbManager().update_user_token(user_id, token)
        user_data[user_id].update(data)
        time_str = format_validity_time(token_timeout)
        if button is None:
            button = ButtonMaker()
        button.ubutton('Collect token', tinyfy(short_url(f'https://telegram.me/{bot_name}?start={token}')))
        return f'Your token has expired, please collect a new token.\n<b>It will expire after {time_str}</b>!', button
    return None, button


def format_validity_time(seconds):
    periods = [('millennium', 31536000000), ('century', 3153600000), ('decade', 315360000), ('year', 31536000), ('month', 2592000), ('week', 604800), ('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            plural_suffix = 's' if period_value > 1 else ''
            result += f'{int(period_value)} {period_name}{plural_suffix} '
    return result


def extra_btns(buttons):
    if extra_buttons:
        for btn_name, btn_url in extra_buttons.items():
            buttons.ubutton(btn_name, btn_url)
    return buttons


async def set_commands(client):
    if config_dict['SET_COMMANDS']:
        await client.set_bot_commands(
            [BotCommand(f'{BotCommands.MirrorCommand[0]}', f'or /{BotCommands.MirrorCommand[1]} Mirror'),
             BotCommand(f'{BotCommands.LeechCommand[0]}', f'or /{BotCommands.LeechCommand[1]} Leech'),
             BotCommand(f'{BotCommands.QbMirrorCommand[0]}', f'or /{BotCommands.QbMirrorCommand[1]} Mirror torrent using qBittorrent'),
             BotCommand(f'{BotCommands.QbLeechCommand[0]}', f'or /{BotCommands.QbLeechCommand[1]} Leech torrent using qBittorrent'),
             BotCommand(f'{BotCommands.YtdlCommand[0]}', f'or /{BotCommands.YtdlCommand[1]} Mirror yt-dlp supported link'),
             BotCommand(f'{BotCommands.YtdlLeechCommand[0]}', f'or /{BotCommands.YtdlLeechCommand[1]} Leech through yt-dlp supported link'),
             BotCommand(f'{BotCommands.CloneCommand}', 'Copy file/folder to Drive'),
             BotCommand(f'{BotCommands.StatusCommand[0]}', f'or /{BotCommands.StatusCommand[1]} Get mirror status message'),
             BotCommand(f'{BotCommands.StatsCommand[0]}', 'Check Bot & System stats'),
             BotCommand(f'{BotCommands.StopAllCommand[0]}', 'Cancel all tasks which added by you to in bots.'),
             BotCommand(f'{BotCommands.ListCommand}', 'Search in Drive'),
             BotCommand(f'{BotCommands.SearchCommand}', 'Search in Torrent'),
             BotCommand(f'{BotCommands.UserSetCommand[0]}', 'Users settings'),
             BotCommand(f'{BotCommands.HelpCommand}', 'Get detailed help'),
             BotCommand(f'{BotCommands.BotSetCommand}', 'Open Bot settings'),
             BotCommand(f'{BotCommands.LogCommand}', 'View log'),
             BotCommand(f'{BotCommands.MediaInfoCommand}', 'Get MediaInfo'),
             BotCommand(f'{BotCommands.CountCommand}', 'Count file/folder of Google Drive.'),
             BotCommand(f'{BotCommands.RestartCommand[0]}', 'Restart bot')])
