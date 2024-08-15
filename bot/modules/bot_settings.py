from io import BytesIO
from os import getcwd, environ
from time import time
from asyncio import sleep, create_subprocess_exec, create_subprocess_shell
from functools import partial
from collections import OrderedDict

from dotenv import load_dotenv
from aiofiles import open as aiopen
from aioshutil import rmtree as aiormtree
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from pyrogram.enums import ChatType
from pyrogram.filters import regex, create, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    LOGGER,
    DATABASE_URL,
    GLOBAL_EXTENSION_FILTER,
    Interval,
    bot,
    aria2,
    config_dict,
    aria2_options,
    download_dict,
    extra_buttons,
    shorteners_list,
    list_drives_dict,
    status_reply_dict_lock,
)
from bot.modules.torrent_search import initiate_search_tools
from bot.helper.ext_utils.bot_utils import new_thread, setInterval, sync_to_async
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.help_strings import bset_display_dict
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendFile,
    editMessage,
    sendMessage,
    update_all_messages,
)

START = 0
STATE = "view"
handler_dict = {}
default_values = {
    "DEFAULT_UPLOAD": "gd",
    "SEARCH_LIMIT": 0,
    "UPSTREAM_BRANCH": "main",
    "TORRENT_TIMEOUT": 3000,
}
bool_vars = [
    "AS_DOCUMENT",
    "DELETE_LINKS",
    "STOP_DUPLICATE",
    "SET_COMMANDS",
    "SHOW_MEDIAINFO",
    "USE_SERVICE_ACCOUNTS",
]


async def load_config():
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    if len(BOT_TOKEN) == 0:
        BOT_TOKEN = config_dict["BOT_TOKEN"]

    TELEGRAM_API = environ.get("TELEGRAM_API", "")
    if len(TELEGRAM_API) == 0:
        TELEGRAM_API = config_dict["TELEGRAM_API"]
    else:
        TELEGRAM_API = int(TELEGRAM_API)

    TELEGRAM_HASH = environ.get("TELEGRAM_HASH", "")
    if len(TELEGRAM_HASH) == 0:
        TELEGRAM_HASH = config_dict["TELEGRAM_HASH"]

    BOT_MAX_TASKS = environ.get("BOT_MAX_TASKS", "")
    BOT_MAX_TASKS = int(BOT_MAX_TASKS) if BOT_MAX_TASKS.isdigit() else ""

    OWNER_ID = environ.get("OWNER_ID", "")
    OWNER_ID = config_dict["OWNER_ID"] if len(OWNER_ID) == 0 else int(OWNER_ID)

    GROUPS_EMAIL = environ.get("GROUPS_EMAIL", "")
    if len(GROUPS_EMAIL) != 0:
        GROUPS_EMAIL = GROUPS_EMAIL.lower()

    DATABASE_URL = environ.get("DATABASE_URL", "")
    if len(DATABASE_URL) == 0:
        DATABASE_URL = ""

    GDRIVE_ID = environ.get("GDRIVE_ID", "")
    if len(GDRIVE_ID) == 0:
        GDRIVE_ID = ""

    RCLONE_PATH = environ.get("RCLONE_PATH", "")
    if len(RCLONE_PATH) == 0:
        RCLONE_PATH = ""

    DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
    if DEFAULT_UPLOAD != "rc":
        DEFAULT_UPLOAD = "gd"

    RCLONE_FLAGS = environ.get("RCLONE_FLAGS", "")
    if len(RCLONE_FLAGS) == 0:
        RCLONE_FLAGS = ""

    EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
    if len(EXTENSION_FILTER) > 0:
        fx = EXTENSION_FILTER.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append("aria2")
        for x in fx:
            if x.strip().startswith("."):
                x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

    METADATA_KEY = environ.get("METADATA_KEY", "")
    if len(METADATA_KEY) == 0:
        METADATA_KEY = ""

    MEGA_EMAIL = environ.get("MEGA_EMAIL", "")
    MEGA_PASSWORD = environ.get("MEGA_PASSWORD", "")
    if len(MEGA_EMAIL) == 0 or len(MEGA_PASSWORD) == 0:
        MEGA_EMAIL = ""
        MEGA_PASSWORD = ""

    INDEX_URL = environ.get("INDEX_URL", "").rstrip("/")
    if len(INDEX_URL) == 0:
        INDEX_URL = ""

    SEARCH_API_LINK = environ.get("SEARCH_API_LINK", "").rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        SEARCH_API_LINK = ""

    FILELION_API = environ.get("FILELION_API", "")
    if len(FILELION_API) == 0:
        FILELION_API = ""

    LEECH_LOG_ID = environ.get("LEECH_LOG_ID", "")
    LEECH_LOG_ID = "" if len(LEECH_LOG_ID) == 0 else int(LEECH_LOG_ID)

    if len(download_dict) != 0:
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(1, update_all_messages))

    YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
    if len(YT_DLP_OPTIONS) == 0:
        YT_DLP_OPTIONS = ""

    SEARCH_LIMIT = environ.get("SEARCH_LIMIT", "")
    SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

    LEECH_DUMP_ID = environ.get("LEECH_DUMP_ID", "")
    if len(LEECH_DUMP_ID) == 0:
        LEECH_DUMP_ID = ""

    CMD_SUFFIX = environ.get("CMD_SUFFIX", "")

    USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")

    TORRENT_TIMEOUT = environ.get("TORRENT_TIMEOUT", "")
    TORRENT_TIMEOUT = 3000 if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)
    downloads = aria2.get_downloads()
    if len(TORRENT_TIMEOUT) == 0:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": "0"},
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options["bt-stop-timeout"] = "0"
        if DATABASE_URL:
            await DbManager().update_aria2("bt-stop-timeout", "0")
        TORRENT_TIMEOUT = ""
    else:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": TORRENT_TIMEOUT},
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options["bt-stop-timeout"] = TORRENT_TIMEOUT
        if DATABASE_URL:
            await DbManager().update_aria2("bt-stop-timeout", TORRENT_TIMEOUT)
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)

    QUEUE_ALL = environ.get("QUEUE_ALL", "")
    QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

    QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
    QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

    QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
    QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

    STREAMWISH_API = environ.get("STREAMWISH_API", "")
    if len(STREAMWISH_API) == 0:
        STREAMWISH_API = ""

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

    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    BASE_URL = environ.get("BASE_URL", "").rstrip("/")
    if len(BASE_URL) == 0:
        BASE_URL = ""
    else:
        await create_subprocess_shell(
            "gunicorn web.wserver:app --bind 0.0.0.0:80 --worker-class gevent"
        )

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

    DELETE_LINKS = environ.get("DELETE_LINKS", "")
    DELETE_LINKS = DELETE_LINKS.lower() == "true"

    FSUB_IDS = environ.get("FSUB_IDS", "")
    if len(FSUB_IDS) == 0:
        FSUB_IDS = ""

    MIRROR_LOG_ID = environ.get("MIRROR_LOG_ID", "")
    if len(MIRROR_LOG_ID) == 0:
        MIRROR_LOG_ID = ""

    ATTACHMENT_URL = environ.get("ATTACHMENT_URL", "")
    if len(ATTACHMENT_URL) == 0:
        ATTACHMENT_URL = ""

    USER_MAX_TASKS = environ.get("USER_MAX_TASKS", "")
    USER_MAX_TASKS = "" if len(USER_MAX_TASKS) == 0 else int(USER_MAX_TASKS)

    PLAYLIST_LIMIT = environ.get("PLAYLIST_LIMIT", "")
    PLAYLIST_LIMIT = "" if len(PLAYLIST_LIMIT) == 0 else int(PLAYLIST_LIMIT)

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

    list_drives_dict.clear()

    if GDRIVE_ID:
        list_drives_dict["Main"] = {"drive_id": GDRIVE_ID, "index_link": INDEX_URL}

    if await aiopath.exists("list_drives.txt"):
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                sep = 2 if line.strip().split()[-1].startswith("http") else 1
                temp = line.strip().rsplit(maxsplit=sep)
                name = "Main Custom" if temp[0].casefold() == "Main" else temp[0]
                list_drives_dict[name] = {
                    "drive_id": temp[1],
                    "index_link": (temp[2] if sep == 2 else ""),
                }

    extra_buttons.clear()
    if await aiopath.exists("buttons.txt"):
        async with aiopen("buttons.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(extra_buttons.keys()) == 4:
                    break
                if len(temp) == 2:
                    extra_buttons[temp[0].replace("_", " ")] = temp[1]

    shorteners_list.clear()
    if await aiopath.exists("shorteners.txt"):
        async with aiopen("shorteners.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shorteners_list.append({"domain": temp[0], "api_key": temp[1]})

    config_dict.update(
        {
            "AS_DOCUMENT": AS_DOCUMENT,
            "BASE_URL": BASE_URL,
            "BOT_TOKEN": BOT_TOKEN,
            "BOT_MAX_TASKS": BOT_MAX_TASKS,
            "CMD_SUFFIX": CMD_SUFFIX,
            "DATABASE_URL": DATABASE_URL,
            "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
            "DELETE_LINKS": DELETE_LINKS,
            "TORRENT_LIMIT": TORRENT_LIMIT,
            "DIRECT_LIMIT": DIRECT_LIMIT,
            "YTDLP_LIMIT": YTDLP_LIMIT,
            "GDRIVE_LIMIT": GDRIVE_LIMIT,
            "CLONE_LIMIT": CLONE_LIMIT,
            "MEGA_LIMIT": MEGA_LIMIT,
            "LEECH_LIMIT": LEECH_LIMIT,
            "FSUB_IDS": FSUB_IDS,
            "FILELION_API": FILELION_API,
            "USER_MAX_TASKS": USER_MAX_TASKS,
            "PLAYLIST_LIMIT": PLAYLIST_LIMIT,
            "MIRROR_LOG_ID": MIRROR_LOG_ID,
            "LEECH_DUMP_ID": LEECH_DUMP_ID,
            "IMAGES": IMAGES,
            "EXTENSION_FILTER": EXTENSION_FILTER,
            "ATTACHMENT_URL": ATTACHMENT_URL,
            "GDRIVE_ID": GDRIVE_ID,
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
    )

    if DATABASE_URL:
        await DbManager().update_config(config_dict)
    await initiate_search_tools()
    await start_from_queued()


async def get_buttons(key=None, edit_type=None, edit_mode=None, mess=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.callback("Config Variables", "botset var")
        buttons.callback("Private Files", "botset private")
        buttons.callback("Close", "botset close")
        msg = "Bot Settings:"
    elif key == "var":
        for k in list(OrderedDict(sorted(config_dict.items())).keys())[
            START : 10 + START
        ]:
            buttons.callback(k, f"botset editvar {k}")
        buttons.callback("Back", "botset back")
        buttons.callback("Close", "botset close")
        for x in range(0, len(config_dict) - 1, 10):
            buttons.callback(
                f"{int(x/10)+1}", f"botset start var {x}", position="footer"
            )
        msg = f"<b>Config Variables<b> | Page: {int(START/10)+1}"
    elif key == "private":
        buttons.callback("Back", "botset back")
        buttons.callback("Close", "botset close")
        msg = "Send private files: config.env, token.pickle, cookies.txt, accounts.zip, terabox.txt, .netrc, or any other files!\n\nTo delete a private file, send only the file name as a text message.\n\n<b>Please note:</b> Changes to .netrc will not take effect for aria2c until it's restarted.\n\n<b>Timeout:</b> 60 seconds"
    elif edit_type == "editvar":
        msg = f"<b>Variable:</b> <code>{key}</code>\n\n"
        msg += f'<b>Description:</b> {bset_display_dict.get(key, "No Description Provided")}\n\n'
        if mess.chat.type == ChatType.PRIVATE:
            msg += f'<b>Value:</b> <code>{config_dict.get(key, "None")}</code>\n\n'
        elif key not in bool_vars:
            buttons.callback(
                "View value", f"botset showvar {key}", position="header"
            )
        buttons.callback("Back", "botset back var", position="footer")
        if key not in bool_vars:
            if not edit_mode:
                buttons.callback("Edit Value", f"botset editvar {key} edit")
            else:
                buttons.callback("Stop Edit", f"botset editvar {key}")
        if (
            key not in ["TELEGRAM_HASH", "TELEGRAM_API", "OWNER_ID", "BOT_TOKEN"]
            and key not in bool_vars
        ):
            buttons.callback("Reset", f"botset resetvar {key}")
        buttons.callback("Close", "botset close", position="footer")
        if edit_mode and key in [
            "CMD_SUFFIX",
            "OWNER_ID",
            "USER_SESSION_STRING",
            "TELEGRAM_HASH",
            "TELEGRAM_API",
            "DATABASE_URL",
            "BOT_TOKEN",
        ]:
            msg += "<b>Note:</b> Restart required for this edit to take effect!\n\n"
        if edit_mode and key not in bool_vars:
            msg += "Send a valid value for the above Var. <b>Timeout:</b> 60 sec"
        if key in bool_vars:
            if not config_dict.get(key):
                buttons.callback("Make it True", f"botset boolvar {key} on")
            else:
                buttons.callback("Make it False", f"botset boolvar {key} off")
    button = buttons.column(1) if key is None else buttons.column(2)
    return msg, button


async def update_buttons(message, key=None, edit_type=None, edit_mode=None):
    msg, button = await get_buttons(key, edit_type, edit_mode, message)
    await editMessage(message, msg, button)


async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "LEECH_LOG_ID":
        value = int(value)
    elif key == "TORRENT_TIMEOUT":
        value = int(value)
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(
                        aria2.client.change_option,
                        download.gid,
                        {"bt-stop-timeout": f"{value}"},
                    )
                except Exception as e:
                    LOGGER.error(e)
        aria2_options["bt-stop-timeout"] = f"{value}"
    elif key == "EXTENSION_FILTER":
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append(".aria2")
        for x in fx:
            if x.strip().startswith("."):
                x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        list_drives_dict["Main"] = {
            "drive_id": value,
            "index_link": config_dict["INDEX_URL"],
        }
    elif key == "INDEX_URL":
        list_drives_dict["Main"] = {
            "drive_id": config_dict["GDRIVE_ID"],
            "index_link": value,
        }
    elif value.isdigit():
        value = int(value)
    config_dict[key] = value
    await update_buttons(pre_message, key, "editvar", False)
    await message.delete()
    if DATABASE_URL:
        await DbManager().update_config({key: value})
    if key == "SEARCH_API_LINK":
        await initiate_search_tools()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()


async def update_private_file(_, message, pre_message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        fn = file_name.rsplit(".zip", 1)[0]
        if await aiopath.isfile(fn) and file_name != "config.env":
            await remove(fn)
        if fn == "accounts":
            if await aiopath.exists("accounts"):
                await aiormtree("accounts")
            if await aiopath.exists("rclone_sa"):
                await aiormtree("rclone_sa")
            config_dict["USE_SERVICE_ACCOUNTS"] = False
            if DATABASE_URL:
                await DbManager().update_config({"USE_SERVICE_ACCOUNTS": False})
        elif file_name in [".netrc", "netrc"]:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (
                await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
            ).wait()
        elif file_name in ["buttons.txt", "buttons"]:
            extra_buttons.clear()
        await message.delete()
    elif doc := message.document:
        file_name = doc.file_name
        await message.download(file_name=f"{getcwd()}/{file_name}")
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await aiormtree("accounts")
            if await aiopath.exists("rclone_sa"):
                await aiormtree("rclone_sa")
            await (
                await create_subprocess_exec(
                    "7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"
                )
            ).wait()
            await (
                await create_subprocess_exec("chmod", "-R", "777", "accounts")
            ).wait()
        elif file_name == "list_drives.txt":
            list_drives_dict.clear()
            if GDRIVE_ID := config_dict["GDRIVE_ID"]:
                list_drives_dict["Main"] = {
                    "drive_id": GDRIVE_ID,
                    "index_link": config_dict["INDEX_URL"],
                }
            async with aiopen("list_drives.txt", "r+") as f:
                lines = await f.readlines()
                for line in lines:
                    sep = 2 if line.strip().split()[-1].startswith("http") else 1
                    temp = line.strip().rsplit(maxsplit=sep)
                    name = "Main Custom" if temp[0].casefold() == "Main" else temp[0]
                    list_drives_dict[name] = {
                        "drive_id": temp[1],
                        "index_link": (temp[2] if sep == 2 else ""),
                    }
        elif file_name == "buttons.txt":
            extra_buttons.clear()
            async with aiopen("buttons.txt", "r+") as f:
                lines = await f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(extra_buttons.keys()) == 4:
                        break
                    if len(temp) == 2:
                        extra_buttons[temp[0].replace("_", " ")] = temp[1]
        elif file_name == "shorteners.txt":
            shorteners_list.clear()
            async with aiopen("shorteners.txt", "r+") as f:
                lines = await f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(temp) == 2:
                        shorteners_list.append(
                            {"domain": temp[0], "api_key": temp[1]}
                        )
        elif file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (
                await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
            ).wait()
        elif file_name == "config.env":
            load_dotenv("config.env", override=True)
            await load_config()
        await message.delete()
    await update_buttons(pre_message)
    if DATABASE_URL:
        await DbManager().update_private_file(file_name)
    if await aiopath.exists("accounts.zip"):
        await remove("accounts.zip")


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == query.from_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
    client.remove_handler(*handler)


@new_thread
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    if data[1] == "close":
        handler_dict[message.chat.id] = False
        await query.answer()
        await message.delete()
        await message.reply_to_message.delete()
    elif data[1] == "back":
        handler_dict[message.chat.id] = False
        await query.answer()
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()["START"] = 0
        await update_buttons(message, key)
    elif data[1] == "var":
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        handler_dict[message.chat.id] = False
        await query.answer("Reset done!", show_alert=True)
        value = ""
        if data[2] in default_values:
            value = default_values[data[2]]
        elif data[2] == "EXTENSION_FILTER":
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.append(".aria2")
        elif data[2] == "TORRENT_TIMEOUT":
            downloads = await sync_to_async(aria2.get_downloads)
            for download in downloads:
                if not download.is_complete:
                    try:
                        await sync_to_async(
                            aria2.client.change_option,
                            download.gid,
                            {"bt-stop-timeout": "0"},
                        )
                    except Exception as e:
                        LOGGER.error(e)
            aria2_options["bt-stop-timeout"] = "0"
            if DATABASE_URL:
                await DbManager().update_aria2("bt-stop-timeout", "0")
        elif data[2] == "BASE_URL":
            await (
                await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
            ).wait()
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
        if data[2] == "SEARCH_API_LINK":
            await initiate_search_tools()
        elif data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
            await start_from_queued()
    elif data[1] == "private":
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[1])
        pfunc = partial(update_private_file, pre_message=message)
        rfunc = partial(update_buttons, message)
        await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "boolvar":
        handler_dict[message.chat.id] = False
        value = data[3] == "on"
        await query.answer(
            f"Successfully variable	 changed to {value}!", show_alert=True
        )
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        if DATABASE_URL:
            await DbManager().update_config({data[2]: value})
    elif data[1] == "editvar":
        handler_dict[message.chat.id] = False
        await query.answer()
        edit_mode = len(data) == 4
        await update_buttons(message, data[2], data[1], edit_mode)
        if data[2] in bool_vars or not edit_mode:
            return
        pfunc = partial(edit_variable, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, data[2], data[1], edit_mode)
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "showvar":
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await sendFile(message, out_file)
            return
        if value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["STATE"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["STATE"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if int(data[3]) != START:
            globals()["START"] = int(data[3])
            await update_buttons(message, data[2])


async def bot_settings(_, message):
    msg, button = await get_buttons()
    globals()["START"] = 0
    await sendMessage(message, msg, button)


bot.add_handler(
    MessageHandler(
        bot_settings, filters=command(BotCommands.BotSetCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    CallbackQueryHandler(
        edit_bot_settings, filters=regex("^botset") & CustomFilters.sudo
    )
)
