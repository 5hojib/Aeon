from os import path, remove, environ
from logging import (
    INFO,
    ERROR,
    Formatter,
    FileHandler,
    StreamHandler,
    info,
    error,
    getLogger,
    basicConfig,
)
from datetime import datetime
from subprocess import run

from pytz import timezone
from dotenv import load_dotenv, dotenv_values
from pymongo.server_api import ServerApi
from pymongo.mongo_client import MongoClient


class CustomFormatter(Formatter):
    def formatTime(self, record, datefmt):
        dt = datetime.fromtimestamp(record.created, tz=timezone("Asia/Dhaka"))
        return dt.strftime(datefmt)

    def format(self, record):
        return super().format(record).replace(record.levelname, record.levelname[:1])


formatter = CustomFormatter(
    "[%(asctime)s] [%(levelname)s] %(message)s | [%(module)s:%(lineno)d]",
    datefmt="%d-%b %I:%M:%S %p",
)

file_handler = FileHandler("log.txt")
file_handler.setFormatter(formatter)

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)

basicConfig(handlers=[file_handler, stream_handler], level=INFO)

getLogger("pymongo").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)

if path.exists("log.txt"):
    with open("log.txt", "r+") as f:
        f.truncate(0)

if path.exists("rlog.txt"):
    remove("rlog.txt")


load_dotenv("config.env", override=True)

BOT_TOKEN = environ["BOT_TOKEN"]

BOT_ID = BOT_TOKEN.split(":", 1)[0]

DATABASE_URL = environ.get("DATABASE_URL", "")
if len(DATABASE_URL) == 0:
    DATABASE_URL = None

if DATABASE_URL is not None:
    try:
        conn = MongoClient(DATABASE_URL, server_api=ServerApi("1"))
        db = conn.luna
        old_config = db.settings.deployConfig.find_one({"_id": BOT_ID})
        config_dict = db.settings.config.find_one({"_id": BOT_ID})
        if old_config is not None:
            del old_config["_id"]
        if (
            old_config is not None
            and old_config == dict(dotenv_values("config.env"))
            or old_config is None
        ) and config_dict is not None:
            environ["UPSTREAM_REPO"] = config_dict["UPSTREAM_REPO"]
            environ["UPSTREAM_BRANCH"] = config_dict["UPSTREAM_BRANCH"]
        conn.close()
    except Exception as e:
        error(f"Database ERROR: {e}")

UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = None

UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "main"

if UPSTREAM_REPO is not None:
    if path.exists(".git"):
        run(["rm", "-rf", ".git"], check=False)

    update = run(
        [
            f"git init -q \
                     && git config --global user.email yesiamshojib@gmail.com \
                     && git config --global user.name 5hojib \
                     && git add . \
                     && git commit -sm update -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q"
        ],
        shell=True,
        check=False,
    )

    if update.returncode == 0:
        info("Successfully updated with latest commit from UPSTREAM_REPO")
    else:
        error(
            "Something went wrong while updating, check UPSTREAM_REPO if valid or not!"
        )
