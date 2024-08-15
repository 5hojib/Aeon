import sys
from os import path as ospath
from os import remove as osremove
from os import environ
from time import time, sleep
from socket import setdefaulttimeout
from asyncio import Lock
from logging import (
    INFO,
    ERROR,
    Formatter,
    FileHandler,
    StreamHandler,
    error,
    warning,
    getLogger,
    basicConfig,
)
from threading import Thread
from subprocess import Popen, check_output
from subprocess import run as srun
from faulthandler import enable as faulthandler_enable

from aria2p import API as ariaAPI
from aria2p import Client as ariaClient
from dotenv import load_dotenv, dotenv_values
from uvloop import install
from pymongo import MongoClient
from tzlocal import get_localzone
from pyrogram import Client as tgClient
from pyrogram import enums
from qbittorrentapi import Client as qbClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

faulthandler_enable()
install()
setdefaulttimeout(600)
getLogger("pymongo").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)
botStartTime = time()


class CustomFormatter(Formatter):
    def format(self, record):
        return super().format(record).replace(record.levelname, record.levelname[:1])


formatter = CustomFormatter(
    "[%(asctime)s] [%(levelname)s] - %(message)s", datefmt="%d-%b-%y %I:%M:%S %p"
)

file_handler = FileHandler("log.txt")
file_handler.setFormatter(formatter)

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)

basicConfig(handlers=[file_handler, stream_handler], level=INFO)

LOGGER = getLogger(__name__)

load_dotenv("config.env", override=True)

Interval = []
QbInterval = []
QbTorrents = {}
GLOBAL_EXTENSION_FILTER = ["aria2", "!qB"]
user_data = {}
extra_buttons = {}
list_drives_dict = {}
shorteners_list = []
aria2_options = {}
qbit_options = {}
queued_dl = {}
queued_up = {}
non_queued_dl = set()
non_queued_up = set()
download_dict_lock = Lock()
status_reply_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
status_reply_dict = {}
download_dict = {}

BOT_TOKEN = environ.get("BOT_TOKEN", "")
if len(BOT_TOKEN) == 0:
    error("BOT_TOKEN variable is missing! Exiting now")
    sys.exit(1)

bot_id = BOT_TOKEN.split(":", 1)[0]

DATABASE_URL = environ.get("DATABASE_URL", "")
if len(DATABASE_URL) == 0:
    DATABASE_URL = ""

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.luna
    current_config = dict(dotenv_values("config.env"))
    old_config = db.settings.deployConfig.find_one({"_id": bot_id})
    if old_config is None:
        db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )
    else:
        del old_config["_id"]
    if old_config and old_config != current_config:
        db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )
    elif config_dict := db.settings.config.find_one({"_id": bot_id}):
        del config_dict["_id"]
        for key, value in config_dict.items():
            environ[key] = str(value)
    if pf_dict := db.settings.files.find_one({"_id": bot_id}):
        del pf_dict["_id"]
        for key, value in pf_dict.items():
            if value:
                file_ = key.replace("__", ".")
                with open(file_, "wb+") as f:
                    f.write(value)
    if a2c_options := db.settings.aria2c.find_one({"_id": bot_id}):
        del a2c_options["_id"]
        aria2_options = a2c_options
    if qbit_opt := db.settings.qbittorrent.find_one({"_id": bot_id}):
        del qbit_opt["_id"]
        qbit_options = qbit_opt
    conn.close()
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    bot_id = BOT_TOKEN.split(":", 1)[0]
    DATABASE_URL = environ.get("DATABASE_URL", "")
else:
    config_dict = {}

GROUPS_EMAIL = environ.get("GROUPS_EMAIL", "")
if len(GROUPS_EMAIL) != 0:
    GROUPS_EMAIL = GROUPS_EMAIL.lower()

OWNER_ID = environ.get("OWNER_ID", "")
if len(OWNER_ID) == 0:
    error("OWNER_ID variable is missing! Exiting now")
    sys.exit(1)
else:
    OWNER_ID = int(OWNER_ID)

TELEGRAM_API = environ.get("TELEGRAM_API", "")
if len(TELEGRAM_API) == 0:
    error("TELEGRAM_API variable is missing! Exiting now")
    sys.exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)

TELEGRAM_HASH = environ.get("TELEGRAM_HASH", "")
if len(TELEGRAM_HASH) == 0:
    error("TELEGRAM_HASH variable is missing! Exiting now")
    sys.exit(1)

GDRIVE_ID = environ.get("GDRIVE_ID", "")
if len(GDRIVE_ID) == 0:
    GDRIVE_ID = ""

METADATA_KEY = environ.get("METADATA_KEY", "")
if len(METADATA_KEY) == 0:
    METADATA_KEY = ""

RCLONE_PATH = environ.get("RCLONE_PATH", "")
if len(RCLONE_PATH) == 0:
    RCLONE_PATH = ""

ATTACHMENT_URL = environ.get("ATTACHMENT_URL", "")
if len(ATTACHMENT_URL) == 0:
    ATTACHMENT_URL = ""

RCLONE_FLAGS = environ.get("RCLONE_FLAGS", "")
if len(RCLONE_FLAGS) == 0:
    RCLONE_FLAGS = ""

DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
if DEFAULT_UPLOAD != "rc":
    DEFAULT_UPLOAD = "gd"

EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
        x = x.lstrip(".")
        GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

IS_PREMIUM_USER = False
user = ""
USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
if len(USER_SESSION_STRING) != 0:
    try:
        user = tgClient(
            "user",
            TELEGRAM_API,
            TELEGRAM_HASH,
            session_string=USER_SESSION_STRING,
            workers=1000,
            parse_mode=enums.ParseMode.HTML,
            no_updates=True,
        ).start()
        IS_PREMIUM_USER = user.me.is_premium
    except Exception as e:
        error(f"Failed making client from USER_SESSION_STRING : {e}")
        user = ""

MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

MEGA_EMAIL = environ.get("MEGA_EMAIL", "")
MEGA_PASSWORD = environ.get("MEGA_PASSWORD", "")
if len(MEGA_EMAIL) == 0 or len(MEGA_PASSWORD) == 0:
    MEGA_EMAIL = ""
    MEGA_PASSWORD = ""

FILELION_API = environ.get("FILELION_API", "")
if len(FILELION_API) == 0:
    FILELION_API = ""

INDEX_URL = environ.get("INDEX_URL", "").rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = ""

SEARCH_API_LINK = environ.get("SEARCH_API_LINK", "").rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = ""

STREAMWISH_API = environ.get("STREAMWISH_API", "")
if len(STREAMWISH_API) == 0:
    STREAMWISH_API = ""

BOT_MAX_TASKS = environ.get("BOT_MAX_TASKS", "")
BOT_MAX_TASKS = int(BOT_MAX_TASKS) if BOT_MAX_TASKS.isdigit() else ""

LEECH_LOG_ID = environ.get("LEECH_LOG_ID", "")
LEECH_LOG_ID = "" if len(LEECH_LOG_ID) == 0 else int(LEECH_LOG_ID)

YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
if len(YT_DLP_OPTIONS) == 0:
    YT_DLP_OPTIONS = ""

SEARCH_LIMIT = environ.get("SEARCH_LIMIT", "")
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

LEECH_DUMP_ID = environ.get("LEECH_DUMP_ID", "")
if len(LEECH_DUMP_ID) == 0:
    LEECH_DUMP_ID = ""

CMD_SUFFIX = environ.get("CMD_SUFFIX", "")

TORRENT_TIMEOUT = environ.get("TORRENT_TIMEOUT", "")
TORRENT_TIMEOUT = 3000 if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

QUEUE_ALL = environ.get("QUEUE_ALL", "")
QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

STOP_DUPLICATE = environ.get("STOP_DUPLICATE", "")
STOP_DUPLICATE = STOP_DUPLICATE.lower() == "true"

USE_SERVICE_ACCOUNTS = environ.get("USE_SERVICE_ACCOUNTS", "")
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == "true"

AS_DOCUMENT = environ.get("AS_DOCUMENT", "")
AS_DOCUMENT = AS_DOCUMENT.lower() == "true"

SHOW_MEDIAINFO = environ.get("SHOW_MEDIAINFO", "")
SHOW_MEDIAINFO = SHOW_MEDIAINFO.lower() == "true"

MEDIA_GROUP = environ.get("MEDIA_GROUP", "")
MEDIA_GROUP = MEDIA_GROUP.lower() == "true"

BASE_URL = environ.get("BASE_URL", "").rstrip("/")
if len(BASE_URL) == 0:
    warning("BASE_URL not provided!")
    BASE_URL = ""

UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = ""

UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "main"

TORRENT_LIMIT = environ.get("TORRENT_LIMIT", "")
TORRENT_LIMIT = "" if len(TORRENT_LIMIT) == 0 else float(TORRENT_LIMIT)

DIRECT_LIMIT = environ.get("DIRECT_LIMIT", "")
DIRECT_LIMIT = "" if len(DIRECT_LIMIT) == 0 else float(DIRECT_LIMIT)

YTDLP_LIMIT = environ.get("YTDLP_LIMIT", "")
YTDLP_LIMIT = "" if len(YTDLP_LIMIT) == 0 else float(YTDLP_LIMIT)

GDRIVE_LIMIT = environ.get("GDRIVE_LIMIT", "")
GDRIVE_LIMIT = "" if len(GDRIVE_LIMIT) == 0 else float(GDRIVE_LIMIT)

CLONE_LIMIT = environ.get("CLONE_LIMIT", "")
CLONE_LIMIT = "" if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

MEGA_LIMIT = environ.get("MEGA_LIMIT", "")
MEGA_LIMIT = "" if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

LEECH_LIMIT = environ.get("LEECH_LIMIT", "")
LEECH_LIMIT = "" if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

USER_MAX_TASKS = environ.get("USER_MAX_TASKS", "")
USER_MAX_TASKS = "" if len(USER_MAX_TASKS) == 0 else int(USER_MAX_TASKS)

PLAYLIST_LIMIT = environ.get("PLAYLIST_LIMIT", "")
PLAYLIST_LIMIT = "" if len(PLAYLIST_LIMIT) == 0 else int(PLAYLIST_LIMIT)

DELETE_LINKS = environ.get("DELETE_LINKS", "")
DELETE_LINKS = DELETE_LINKS.lower() == "true"

FSUB_IDS = environ.get("FSUB_IDS", "")
if len(FSUB_IDS) == 0:
    FSUB_IDS = ""

MIRROR_LOG_ID = environ.get("MIRROR_LOG_ID", "")
if len(MIRROR_LOG_ID) == 0:
    MIRROR_LOG_ID = ""

IMAGES = environ.get("IMAGES", "")
IMAGES = (
    IMAGES.replace("'", "")
    .replace('"', "")
    .replace("[", "")
    .replace("]", "")
    .replace(",", "")
).split()


SET_COMMANDS = environ.get("SET_COMMANDS", "")
SET_COMMANDS = SET_COMMANDS.lower() == "true"

TOKEN_TIMEOUT = environ.get("TOKEN_TIMEOUT", "")
TOKEN_TIMEOUT = int(TOKEN_TIMEOUT) if TOKEN_TIMEOUT.isdigit() else ""

config_dict = {
    "AS_DOCUMENT": AS_DOCUMENT,
    "BASE_URL": BASE_URL,
    "BOT_TOKEN": BOT_TOKEN,
    "BOT_MAX_TASKS": BOT_MAX_TASKS,
    "CMD_SUFFIX": CMD_SUFFIX,
    "DATABASE_URL": DATABASE_URL,
    "DELETE_LINKS": DELETE_LINKS,
    "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
    "FILELION_API": FILELION_API,
    "TORRENT_LIMIT": TORRENT_LIMIT,
    "DIRECT_LIMIT": DIRECT_LIMIT,
    "YTDLP_LIMIT": YTDLP_LIMIT,
    "GDRIVE_LIMIT": GDRIVE_LIMIT,
    "CLONE_LIMIT": CLONE_LIMIT,
    "MEGA_LIMIT": MEGA_LIMIT,
    "LEECH_LIMIT": LEECH_LIMIT,
    "FSUB_IDS": FSUB_IDS,
    "USER_MAX_TASKS": USER_MAX_TASKS,
    "PLAYLIST_LIMIT": PLAYLIST_LIMIT,
    "MIRROR_LOG_ID": MIRROR_LOG_ID,
    "LEECH_DUMP_ID": LEECH_DUMP_ID,
    "IMAGES": IMAGES,
    "EXTENSION_FILTER": EXTENSION_FILTER,
    "GDRIVE_ID": GDRIVE_ID,
    "ATTACHMENT_URL": ATTACHMENT_URL,
    "INDEX_URL": INDEX_URL,
    "LEECH_LOG_ID": LEECH_LOG_ID,
    "TOKEN_TIMEOUT": TOKEN_TIMEOUT,
    "MEDIA_GROUP": MEDIA_GROUP,
    "MEGA_EMAIL": MEGA_EMAIL,
    "MEGA_PASSWORD": MEGA_PASSWORD,
    "METADATA_KEY": METADATA_KEY,
    "OWNER_ID": OWNER_ID,
    "QUEUE_ALL": QUEUE_ALL,
    "QUEUE_DOWNLOAD": QUEUE_DOWNLOAD,
    "QUEUE_UPLOAD": QUEUE_UPLOAD,
    "RCLONE_FLAGS": RCLONE_FLAGS,
    "RCLONE_PATH": RCLONE_PATH,
    "SEARCH_API_LINK": SEARCH_API_LINK,
    "SEARCH_LIMIT": SEARCH_LIMIT,
    "SET_COMMANDS": SET_COMMANDS,
    "SHOW_MEDIAINFO": SHOW_MEDIAINFO,
    "STOP_DUPLICATE": STOP_DUPLICATE,
    "STREAMWISH_API": STREAMWISH_API,
    "TELEGRAM_API": TELEGRAM_API,
    "TELEGRAM_HASH": TELEGRAM_HASH,
    "TORRENT_TIMEOUT": TORRENT_TIMEOUT,
    "UPSTREAM_REPO": UPSTREAM_REPO,
    "UPSTREAM_BRANCH": UPSTREAM_BRANCH,
    "USER_SESSION_STRING": USER_SESSION_STRING,
    "GROUPS_EMAIL": GROUPS_EMAIL,
    "USE_SERVICE_ACCOUNTS": USE_SERVICE_ACCOUNTS,
    "YT_DLP_OPTIONS": YT_DLP_OPTIONS,
}

if GDRIVE_ID:
    list_drives_dict["Main"] = {"drive_id": GDRIVE_ID, "index_link": INDEX_URL}

if ospath.exists("list_drives.txt"):
    with open("list_drives.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            sep = 2 if line.strip().split()[-1].startswith("http") else 1
            temp = line.strip().rsplit(maxsplit=sep)
            name = "Main Custom" if temp[0].casefold() == "Main" else temp[0]
            list_drives_dict[name] = {
                "drive_id": temp[1],
                "index_link": (temp[2] if sep == 2 else ""),
            }

if ospath.exists("buttons.txt"):
    with open("buttons.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(extra_buttons.keys()) == 4:
                break
            if len(temp) == 2:
                extra_buttons[temp[0].replace("_", " ")] = temp[1]

if ospath.exists("shorteners.txt"):
    with open("shorteners.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                shorteners_list.append({"domain": temp[0], "api_key": temp[1]})

PORT = environ.get("PORT")
Popen(
    f"gunicorn web.wserver:app --bind 0.0.0.0:{PORT} --worker-class gevent",
    shell=True,
)

srun(["xnox", "-d", "--profile=."], check=False)
if not ospath.exists(".netrc"):
    with open(".netrc", "w"):
        pass
srun(["chmod", "600", ".netrc"], check=False)
srun(["cp", ".netrc", "/root/.netrc"], check=False)

trackers = (
    check_output(
        "curl -Ns https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/all.txt https://ngosang.github.io/trackerslist/trackers_all_http.txt https://newtrackon.com/api/all https://raw.githubusercontent.com/hezhijie0327/Trackerslist/main/trackerslist_tracker.txt | awk '$0' | tr '\n\n' ','",
        shell=True,
    )
    .decode("utf-8")
    .rstrip(",")
)
with open("a2c.conf", "a+") as a:
    if TORRENT_TIMEOUT is not None:
        a.write(f"bt-stop-timeout={TORRENT_TIMEOUT}\n")
    a.write(f"bt-tracker=[{trackers}]")
srun(["xria", "--conf-path=/usr/src/app/a2c.conf"], check=False)

if ospath.exists("accounts.zip"):
    if ospath.exists("accounts"):
        srun(["rm", "-rf", "accounts"], check=False)
    srun(
        ["7z", "x", "-o.", "-bd", "-aoa", "accounts.zip", "accounts/*.json"],
        check=False,
    )
    srun(["chmod", "-R", "777", "accounts"], check=False)
    osremove("accounts.zip")
if not ospath.exists("accounts"):
    config_dict["USE_SERVICE_ACCOUNTS"] = False
alive = Popen(["python3", "alive.py"])
sleep(0.5)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))


xnox_client = qbClient(
    host="localhost",
    port=8090,
    VERIFY_WEBUI_CERTIFICATE=False,
    REQUESTS_ARGS={"timeout": (30, 60)},
    HTTPADAPTER_ARGS={
        "pool_maxsize": 500,
        "max_retries": 10,
        "pool_block": True,
    },
)


def aria2c_init():
    try:
        link = "https://linuxmint.com/torrents/lmde-5-cinnamon-64bit.iso.torrent"
        dire = "/usr/src/app/downloads/".rstrip("/")
        aria2.add_uris([link], {"dir": dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(10)
        aria2.remove(downloads, force=True, files=True, clean=True)
    except Exception as e:
        error(f"Aria2c initializing error: {e}")


Thread(target=aria2c_init).start()
sleep(1.5)

aria2c_global = [
    "bt-max-open-files",
    "download-result",
    "keep-unfinished-download-result",
    "log",
    "log-level",
    "max-concurrent-downloads",
    "max-download-result",
    "max-overall-download-limit",
    "save-session",
    "max-overall-upload-limit",
    "optimize-concurrent-downloads",
    "save-cookies",
    "server-stat-of",
]

if not aria2_options:
    aria2_options = aria2.client.get_global_option()
else:
    a2c_glo = {op: aria2_options[op] for op in aria2c_global if op in aria2_options}
    aria2.set_global_options(a2c_glo)

if not qbit_options:
    qbit_options = dict(xnox_client.app_preferences())
    del qbit_options["listen_port"]
    for k in list(qbit_options.keys()):
        if k.startswith("rss"):
            del qbit_options[k]
else:
    qb_opt = {**qbit_options}
    xnox_client.app_set_preferences(qb_opt)

bot = tgClient(
    "bot",
    TELEGRAM_API,
    TELEGRAM_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    parse_mode=enums.ParseMode.HTML,
).start()
bot_loop = bot.loop
bot_name = bot.me.username
scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)
