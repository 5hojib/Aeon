from os import path as ospath
from os import remove, environ
from time import time
from socket import setdefaulttimeout
from asyncio import Lock, get_event_loop
from logging import (
    INFO,
    ERROR,
    Formatter,
    FileHandler,
    StreamHandler,
    getLogger,
    basicConfig,
)
from datetime import datetime
from subprocess import Popen, run, check_output

from pytz import timezone
from aria2p import API as ariaAPI
from aria2p import Client as ariaClient
from dotenv import load_dotenv, dotenv_values
from uvloop import install
from tzlocal import get_localzone
from pyrogram import Client as tgClient
from pyrogram import enums
from qbittorrentapi import Client as qbClient
from pymongo.server_api import ServerApi
from pymongo.mongo_client import MongoClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv("config.env", override=True)

LOG_FILE = "log.txt"
TORRENT_TIMEOUT = 1800
DOWNLOAD_DIR = "/usr/src/app/downloads/"


install()
setdefaulttimeout(600)
bot_start_time = time()
bot_loop = get_event_loop()

getLogger("pyrogram").setLevel(ERROR)
getLogger("pymongo").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)


class CustomFormatter(Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone("Asia/Dhaka"))
        return dt.strftime(datefmt) if datefmt else dt.isoformat()

    def format(self, record):
        return super().format(record).replace(record.levelname, record.levelname[:1])


formatter = CustomFormatter(
    "[%(asctime)s] [%(levelname)s] %(message)s | [%(module)s:%(lineno)d]",
    datefmt="%d-%b %I:%M:%S %p",
)

file_handler = FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)

basicConfig(handlers=[file_handler, stream_handler], level=INFO)
LOGGER = getLogger(__name__)

Intervals = {"status": {}, "qb": "", "stopAll": False}
QbTorrents, DRIVES_NAMES, DRIVES_IDS, INDEX_URLS = {}, [], [], []
GLOBAL_EXTENSION_FILTER = [
    "aria2",
    "!qB",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "html",
    "nfo",
    "url",
    "php",
    "aspx",
]
user_data = {}
shorteners_list = []
aria2_options, qbit_options = {}, {}
queued_dl, queued_up = {}, {}
non_queued_dl, non_queued_up = set(), set()
multi_tags, status_dict, task_dict = set(), {}, {}
task_dict_lock = Lock()
queue_dict_lock, qb_listener_lock, cpu_eater_lock, subprocess_lock = (
    Lock(),
    Lock(),
    Lock(),
    Lock(),
)

BOT_TOKEN = environ["BOT_TOKEN"]
DATABASE_URL = environ.get("DATABASE_URL", "")
TELEGRAM_API = int(environ["TELEGRAM_API"])
TELEGRAM_HASH = environ["TELEGRAM_HASH"]
OWNER_ID = int(environ["OWNER_ID"])
bot_id = BOT_TOKEN.split(":")[0]


def initialize_database():
    try:
        conn = MongoClient(DATABASE_URL, server_api=ServerApi("1"))
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
            aria2_options.update(a2c_options)
        if qbit_opt := db.settings.qbittorrent.find_one({"_id": bot_id}):
            del qbit_opt["_id"]
            qbit_options.update(qbit_opt)
        conn.close()
    except Exception as e:
        LOGGER.error(f"Database ERROR: {e}")


initialize_database()

if not ospath.exists(".netrc"):
    with open(".netrc", "w"):
        pass

if ospath.exists("shorteners.txt"):
    with open("shorteners.txt", "r+") as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                shorteners_list.append({"domain": temp[0], "api_key": temp[1]})


def init_user_client():
    user_session = environ.get("USER_SESSION_STRING", "")
    if user_session:
        LOGGER.info("Creating client from USER_SESSION_STRING")
        try:
            user = tgClient(
                "user",
                TELEGRAM_API,
                TELEGRAM_HASH,
                session_string=user_session,
                parse_mode=enums.ParseMode.HTML,
                no_updates=True,
            ).start()
            return user.me.is_premium, user
        except Exception as e:
            LOGGER.error(e)
            return False, ""
    return False, ""


IS_PREMIUM_USER, user = init_user_client()
MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
if DEFAULT_UPLOAD != "rc":
    DEFAULT_UPLOAD = "gd"


def load_user_data():
    AUTHORIZED_CHATS = environ.get("AUTHORIZED_CHATS", "")
    if AUTHORIZED_CHATS:
        for id_ in AUTHORIZED_CHATS.split():
            user_data[int(id_.strip())] = {"is_auth": True}

    SUDO_USERS = environ.get("SUDO_USERS", "")
    if SUDO_USERS:
        for id_ in SUDO_USERS.split():
            user_data[int(id_.strip())] = {"is_sudo": True}

    EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
    if EXTENSION_FILTER:
        for x in EXTENSION_FILTER.split():
            x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())


load_user_data()


def get_env_int(key):
    value = environ.get(key, None)
    if value is None or value == "" or int(value) == 0:
        return ""
    return int(value)


config_dict = {
    "AS_DOCUMENT": environ.get("AS_DOCUMENT", "").lower() == "true",
    "AUTHORIZED_CHATS": environ.get("AUTHORIZED_CHATS", ""),
    "BASE_URL": environ.get("BASE_URL", "").rstrip("/"),
    "CMD_SUFFIX": environ.get("CMD_SUFFIX", ""),
    "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
    "EXTENSION_FILTER": environ.get("EXTENSION_FILTER", ""),
    "FSUB_IDS": environ.get("FSUB_IDS", ""),
    "FILELION_API": environ.get("FILELION_API", ""),
    "GDRIVE_ID": environ.get("GDRIVE_ID", ""),
    "INDEX_URL": environ.get("INDEX_URL", "").rstrip("/"),
    "IS_TEAM_DRIVE": environ.get("IS_TEAM_DRIVE", "").lower() == "true",
    "LEECH_DUMP_CHAT": int(environ.get("LEECH_DUMP_CHAT", 0)),
    "LOG_CHAT": int(environ.get("LOG_CHAT", 0)),
    "MEGA_EMAIL": environ.get("MEGA_EMAIL", ""),
    "MEGA_PASSWORD": environ.get("MEGA_PASSWORD", ""),
    "PAID_CHAT_ID": environ.get("PAID_CHAT_ID", ""),
    "PAID_CHAT_LINK": environ.get("PAID_CHAT_LINK", ""),
    "QUEUE_ALL": get_env_int("QUEUE_ALL"),
    "QUEUE_DOWNLOAD": get_env_int("QUEUE_DOWNLOAD"),
    "QUEUE_UPLOAD": get_env_int("QUEUE_UPLOAD"),
    "RCLONE_FLAGS": environ.get("RCLONE_FLAGS", ""),
    "RCLONE_PATH": environ.get("RCLONE_PATH", ""),
    "STOP_DUPLICATE": environ.get("STOP_DUPLICATE", "").lower() == "true",
    "STREAMWISH_API": environ.get("STREAMWISH_API", ""),
    "SUDO_USERS": environ.get("SUDO_USERS", ""),
    "TOKEN_TIMEOUT": get_env_int("TOKEN_TIMEOUT"),
    "UPSTREAM_REPO": environ.get("UPSTREAM_REPO", "https://github.com/5hojib/Aeon"),
    "UPSTREAM_BRANCH": environ.get("UPSTREAM_BRANCH", "main"),
    "USER_SESSION_STRING": environ.get("USER_SESSION_STRING", ""),
    "USE_SA": environ.get("USE_SA", "").lower() == "true",
    "YT_DLP_OPTIONS": environ.get("YT_DLP_OPTIONS", ""),
}

if GDID := environ.get("GDRIVE_ID"):
    DRIVES_NAMES.append("Main")
    DRIVES_IDS.append(GDID)
    INDEX_URLS.append(config_dict["INDEX_URL"])

PORT = environ.get("PORT")
Popen(
    f"gunicorn web.wserver:app --bind 0.0.0.0:{PORT} --worker-class gevent",
    shell=True,
)

run(["xnox", "-d", "--profile=."], check=False)
if not ospath.exists(".netrc"):
    with open(".netrc", "w"):
        pass
run(["chmod", "600", ".netrc"], check=False)
run(["cp", ".netrc", "/root/.netrc"], check=False)

trackers = (
    check_output(
        "curl -Ns https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/all.txt https://ngosang.github.io/trackerslist/trackers_all_http.txt https://newtrackon.com/api/all https://raw.githubusercontent.com/hezhijie0327/Trackerslist/main/trackerslist_tracker.txt | awk '$0' | tr '\n\n' ','",
        shell=True,
    )
    .decode("utf-8")
    .rstrip(",")
)
with open("a2c.conf", "a+") as a:
    a.write(f"bt-stop-timeout={TORRENT_TIMEOUT}\n")
    a.write(f"bt-tracker=[{trackers}]")
run(["xria", "--conf-path=/usr/src/app/a2c.conf"], check=False)

if ospath.exists("accounts.zip"):
    if ospath.exists("accounts"):
        run(["rm", "-rf", "accounts"], check=False)
    run(
        ["7z", "x", "-o.", "-bd", "-aoa", "accounts.zip", "accounts/*.json"],
        check=False,
    )
    run(["chmod", "-R", "777", "accounts"], check=False)
    remove("accounts.zip")
if not ospath.exists("accounts"):
    config_dict["USE_SA"] = False

alive = Popen(["python3", "alive.py"])

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
aria2_options = aria2_options or aria2.client.get_global_option()
aria2.set_global_options(
    {op: aria2_options[op] for op in aria2c_global if op in aria2_options}
)


def get_qb_options():
    global qbit_options
    if not qbit_options:
        qbit_options = dict(xnox_client.app_preferences())
        del qbit_options["listen_port"]
        for k in list(qbit_options.keys()):
            if k.startswith("rss"):
                del qbit_options[k]
    else:
        xnox_client.app_set_preferences(qbit_options)


get_qb_options()

bot = tgClient(
    "bot",
    TELEGRAM_API,
    TELEGRAM_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML,
).start()
bot_loop = bot.loop
bot_username = bot.me.username

scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)
