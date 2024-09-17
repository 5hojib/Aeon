from io import BytesIO
from os import getcwd, environ
from time import time
from asyncio import (
    sleep,
    gather,
    create_subprocess_exec,
    create_subprocess_shell,
)
from functools import partial
from collections import OrderedDict

from dotenv import load_dotenv
from aiofiles import open as aiopen
from aioshutil import rmtree
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from pyrogram.enums import ChatType
from pyrogram.filters import regex, create, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    DRIVES_IDS,
    INDEX_URLS,
    DRIVES_NAMES,
    GLOBAL_EXTENSION_FILTER,
    Intervals,
    bot,
    task_dict,
    user_data,
    config_dict,
)
from bot.modules.torrent_search import initiate_search_tools
from bot.helper.ext_utils.bot_utils import (
    new_thread,
    setInterval,
)
from bot.helper.ext_utils.db_handler import Database
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendFile,
    delete_links,
    edit_message,
    send_message,
    delete_message,
    update_status_message,
)

START = 0
STATE = "view"
handler_dict = {}

default_values = {
    "UPSTREAM_BRANCH": "main",
    "DEFAULT_UPLOAD": "gd",
}

boolean_variables = {
    "STOP_DUPLICATE",
    "IS_TEAM_DRIVE",
    "USE_SA",
    "AS_DOCUMENT",
}


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
        msg = "Send private files"
    elif edit_type == "editvar":
        msg = f"<b>Variable:</b> <code>{key}</code>\n\n"
        if mess.chat.type == ChatType.PRIVATE:
            msg += f'<b>Value:</b> <code>{config_dict.get(key, "None")}</code>\n\n'
        elif key not in boolean_variables:
            buttons.callback(
                "View value", f"botset showvar {key}", position="header"
            )
        buttons.callback("Back", "botset back var", position="footer")
        if key not in boolean_variables:
            if not edit_mode:
                buttons.callback("Edit Value", f"botset editvar {key} edit")
            else:
                buttons.callback("Stop Edit", f"botset editvar {key}")
            buttons.callback("Reset", f"botset resetvar {key}")
        buttons.callback("Close", "botset close", position="footer")
        if edit_mode and key in ["CMD_SUFFIX", "USER_SESSION_STRING"]:
            msg += "<b>Note:</b> Restart required for this edit to take effect!\n\n"
        if edit_mode and key not in boolean_variables:
            msg += "Send a valid value for the above Var. <b>Timeout:</b> 60 sec"
        if key in boolean_variables:
            if not config_dict.get(key):
                buttons.callback("Make it True", f"botset boolvar {key} on")
            else:
                buttons.callback("Make it False", f"botset boolvar {key} off")
    button = buttons.menu(1) if key is None else buttons.menu(2)
    return msg, button


async def update_buttons(message, key=None, edit_type=None, edit_mode=None):
    msg, button = await get_buttons(key, edit_type, edit_mode, message)
    await edit_message(message, msg, button)


async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "EXTENSION_FILTER":
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append(".aria2")
        for x in fx:
            x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
            DRIVES_IDS[0] = value
        else:
            DRIVES_IDS.insert(0, value)
    elif key == "INDEX_URL":
        if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
            INDEX_URLS[0] = value
        else:
            INDEX_URLS.insert(0, value)
    elif value.isdigit():
        value = int(value)
    config_dict[key] = value
    await update_buttons(pre_message, key, "editvar", False)
    await message.delete()
    await Database().update_config({key: value})
    if key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()


async def update_private_file(_, message, pre_message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        fn = file_name.rsplit(".zip", 1)[0]
        if await aiopath.isfile(fn) and file_name != "config.env":
            await remove(fn)
        if fn == "accounts":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            config_dict["USE_SA"] = False
            await Database().update_config({"USE_SA": False})
        elif file_name in [".netrc", "netrc"]:
            await (await create_subprocess_exec("touch", ".netrc")).wait()
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (
                await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
            ).wait()
        await delete_message(message)
    elif doc := message.document:
        file_name = doc.file_name
        await message.download(file_name=f"{getcwd()}/{file_name}")
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            await (
                await create_subprocess_exec(
                    "7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"
                )
            ).wait()
            await (
                await create_subprocess_exec("chmod", "-R", "777", "accounts")
            ).wait()
        elif file_name == "list_drives.txt":
            DRIVES_IDS.clear()
            DRIVES_NAMES.clear()
            INDEX_URLS.clear()
            if GDRIVE_ID := config_dict["GDRIVE_ID"]:
                DRIVES_NAMES.append("Main")
                DRIVES_IDS.append(GDRIVE_ID)
                INDEX_URLS.append(config_dict["INDEX_URL"])
            async with aiopen("list_drives.txt", "r+") as f:
                lines = await f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    DRIVES_IDS.append(temp[1])
                    DRIVES_NAMES.append(temp[0].replace("_", " "))
                    if len(temp) > 2:
                        INDEX_URLS.append(temp[2])
                    else:
                        INDEX_URLS.append("")
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
        await delete_message(message)
    await update_buttons(pre_message)
    await Database().update_private_file(file_name)
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
        await delete_links(message)
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
        elif data[2] == "BASE_URL":
            await (
                await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
            ).wait()
        elif data[2] == "GDRIVE_ID":
            if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
                DRIVES_NAMES.pop(0)
                DRIVES_IDS.pop(0)
                INDEX_URLS.pop(0)
        elif data[2] == "INDEX_URL":
            if DRIVES_NAMES and DRIVES_NAMES[0] == "Main":
                INDEX_URLS[0] = ""
        config_dict[data[2]] = value
        await update_buttons(message, data[2], "editvar", False)
        await Database().update_config({data[2]: value})
        if data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
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
        await Database().update_config({data[2]: value})
    elif data[1] == "editvar":
        handler_dict[message.chat.id] = False
        await query.answer()
        edit_mode = len(data) == 4
        await update_buttons(message, data[2], data[1], edit_mode)
        if data[2] in boolean_variables or not edit_mode:
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
    await send_message(message, msg, button)


async def load_config():
    GDRIVE_ID = environ.get("GDRIVE_ID", "")
    RCLONE_PATH = environ.get("RCLONE_PATH", "")
    DEFAULT_UPLOAD = environ.get("DEFAULT_UPLOAD", "")
    if DEFAULT_UPLOAD != "rc":
        DEFAULT_UPLOAD = "gd"

    RCLONE_FLAGS = environ.get("RCLONE_FLAGS", "")
    AUTHORIZED_CHATS = environ.get("AUTHORIZED_CHATS", "")
    if len(AUTHORIZED_CHATS) != 0:
        aid = AUTHORIZED_CHATS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {"is_auth": True}

    SUDO_USERS = environ.get("SUDO_USERS", "")
    if len(SUDO_USERS) != 0:
        aid = SUDO_USERS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {"is_sudo": True}

    EXTENSION_FILTER = environ.get("EXTENSION_FILTER", "")
    if len(EXTENSION_FILTER) > 0:
        fx = EXTENSION_FILTER.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.extend(["aria2", "!qB"])
        for x in fx:
            if x.strip().startswith("."):
                x = x.lstrip(".")
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

    FILELION_API = environ.get("FILELION_API", "")
    STREAMWISH_API = environ.get("STREAMWISH_API", "")
    INDEX_URL = environ.get("INDEX_URL", "").rstrip("/")

    if len(task_dict) != 0 and (st := Intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            Intervals["status"][key] = setInterval(1, update_status_message, key)

    YT_DLP_OPTIONS = environ.get("YT_DLP_OPTIONS", "")
    LEECH_DUMP_CHAT = environ.get("LEECH_DUMP_CHAT", "")
    LEECH_DUMP_CHAT = "" if len(LEECH_DUMP_CHAT) == 0 else int(LEECH_DUMP_CHAT)

    LOG_CHAT = environ.get("LOG_CHAT", "")
    LOG_CHAT = "" if len(LOG_CHAT) == 0 else int(LOG_CHAT)

    CMD_SUFFIX = environ.get("CMD_SUFFIX", "")
    FSUB_IDS = environ.get("FSUB_IDS", "")
    USER_SESSION_STRING = environ.get("USER_SESSION_STRING", "")
    MEGA_EMAIL = environ.get("MEGA_EMAIL", "")
    MEGA_PASSWORD = environ.get("MEGA_PASSWORD", "")
    PAID_CHAT_ID = environ.get("PAID_CHAT_ID", "")
    PAID_CHAT_ID = int(PAID_CHAT_ID) if PAID_CHAT_ID else ""
    PAID_CHAT_LINK = environ.get("PAID_CHAT_LINK", "")
    QUEUE_ALL = environ.get("QUEUE_ALL", "")
    QUEUE_ALL = "" if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

    TOKEN_TIMEOUT = environ.get("TOKEN_TIMEOUT", "")
    TOKEN_TIMEOUT = int(TOKEN_TIMEOUT) if TOKEN_TIMEOUT.isdigit() else ""

    QUEUE_DOWNLOAD = environ.get("QUEUE_DOWNLOAD", "")
    QUEUE_DOWNLOAD = "" if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

    QUEUE_UPLOAD = environ.get("QUEUE_UPLOAD", "")
    QUEUE_UPLOAD = "" if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

    STOP_DUPLICATE = environ.get("STOP_DUPLICATE", "").lower() == "true"

    IS_TEAM_DRIVE = environ.get("IS_TEAM_DRIVE", "").lower() == "true"

    USE_SA = environ.get("USE_SA", "").lower() == "true"

    AS_DOCUMENT = environ.get("AS_DOCUMENT", "").lower() == "true"

    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    BASE_URL = environ.get("BASE_URL", "").rstrip("/")
    if len(BASE_URL) == 0:
        BASE_URL = ""
    else:
        await create_subprocess_shell(
            "gunicorn web.wserver:app --bind 0.0.0.0:80 --worker-class gevent"
        )

    UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "main")
    UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "https://github.com/5hojib/Aeon")
    DRIVES_IDS.clear()
    DRIVES_NAMES.clear()
    INDEX_URLS.clear()

    if GDRIVE_ID:
        DRIVES_NAMES.append("Main")
        DRIVES_IDS.append(GDRIVE_ID)
        INDEX_URLS.append(INDEX_URL)

    if await aiopath.exists("list_drives.txt"):
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                DRIVES_IDS.append(temp[1])
                DRIVES_NAMES.append(temp[0].replace("_", " "))
                if len(temp) > 2:
                    INDEX_URLS.append(temp[2])
                else:
                    INDEX_URLS.append("")

    config_dict.update(
        {
            "AS_DOCUMENT": AS_DOCUMENT,
            "AUTHORIZED_CHATS": AUTHORIZED_CHATS,
            "BASE_URL": BASE_URL,
            "CMD_SUFFIX": CMD_SUFFIX,
            "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
            "EXTENSION_FILTER": EXTENSION_FILTER,
            "FILELION_API": FILELION_API,
            "FSUB_IDS": FSUB_IDS,
            "GDRIVE_ID": GDRIVE_ID,
            "INDEX_URL": INDEX_URL,
            "IS_TEAM_DRIVE": IS_TEAM_DRIVE,
            "LEECH_DUMP_CHAT": LEECH_DUMP_CHAT,
            "LOG_CHAT": LOG_CHAT,
            "MEGA_EMAIL": MEGA_EMAIL,
            "MEGA_PASSWORD": MEGA_PASSWORD,
            "PAID_CHAT_ID": PAID_CHAT_ID,
            "PAID_CHAT_LINK": PAID_CHAT_LINK,
            "QUEUE_ALL": QUEUE_ALL,
            "QUEUE_DOWNLOAD": QUEUE_DOWNLOAD,
            "QUEUE_UPLOAD": QUEUE_UPLOAD,
            "RCLONE_FLAGS": RCLONE_FLAGS,
            "RCLONE_PATH": RCLONE_PATH,
            "STOP_DUPLICATE": STOP_DUPLICATE,
            "STREAMWISH_API": STREAMWISH_API,
            "SUDO_USERS": SUDO_USERS,
            "TOKEN_TIMEOUT": TOKEN_TIMEOUT,
            "UPSTREAM_BRANCH": UPSTREAM_BRANCH,
            "UPSTREAM_REPO": UPSTREAM_REPO,
            "USER_SESSION_STRING": USER_SESSION_STRING,
            "USE_SA": USE_SA,
            "YT_DLP_OPTIONS": YT_DLP_OPTIONS,
        }
    )

    await Database().update_config(config_dict)
    await gather(initiate_search_tools(), start_from_queued())


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
