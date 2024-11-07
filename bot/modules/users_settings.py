from io import BytesIO
from os import getcwd
from html import escape
from time import time
from asyncio import sleep
from functools import partial

from aiofiles.os import path as aiopath
from aiofiles.os import remove, makedirs
from pyrogram.filters import regex, create, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    MAX_SPLIT_SIZE,
    GLOBAL_EXTENSION_FILTER,
    bot,
    user_data,
    config_dict,
)
from bot.helper.ext_utils.bot_utils import new_thread, update_user_ldata
from bot.helper.ext_utils.db_handler import Database
from bot.helper.ext_utils.media_utils import createThumb
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    sendFile,
    edit_message,
    send_message,
    delete_message,
    five_minute_del,
)

handler_dict = {}


async def get_user_settings(from_user):
    user_id = from_user.id
    buttons = ButtonMaker()

    paths = {
        "thumbpath": f"Thumbnails/{user_id}.jpg",
        "rclone_conf": f"rclone/{user_id}.conf",
        "token_pickle": f"tokens/{user_id}.pickle",
    }

    user_dict = user_data.get(user_id, {})
    settings = {
        "rccmsg": "Exists"
        if await aiopath.exists(paths["rclone_conf"])
        else "Not Exists",
        "tokenmsg": "Exists"
        if await aiopath.exists(paths["token_pickle"])
        else "Not Exists",
        "default_upload": "Gdrive API"
        if (user_dict.get("default_upload", config_dict["DEFAULT_UPLOAD"])) == "gd"
        else "Rclone",
        "ex_ex": user_dict.get(
            "excluded_extensions",
            GLOBAL_EXTENSION_FILTER
            if "excluded_extensions" not in user_dict
            else "None",
        )
        or "None",
        "meta_msg": user_dict.get("metadata", "None") or "None",
        "ns_msg": "Added" if user_dict.get("name_sub", False) else "None",
        "ytopt": user_dict.get("yt_opt", config_dict.get("YT_DLP_OPTIONS", "None"))
        or "None",
    }

    button_labels = [
        ("Leech", f"userset {user_id} leech"),
        ("Rclone", f"userset {user_id} rclone"),
        ("Gdrive Tools", f"userset {user_id} gdrive"),
        ("Excluded Extensions", f"userset {user_id} ex_ex"),
        ("Metadata key", f"userset {user_id} metadata_key"),
        ("Name Substitute", f"userset {user_id} name_substitute"),
        ("YT-DLP Options", f"userset {user_id} yto"),
        ("Reset All", f"userset {user_id} reset") if user_dict else None,
        ("Close", f"userset {user_id} close"),
    ]

    """ (
            f"Upload using {('Gdrive API' if settings['default_upload'] != 'Gdrive API' else 'Rclone')}",
            f"userset {user_id} {settings['default_upload']}",
        ),
        """  # TODO **Default Upload:** {settings['default_upload']}

    for label, callback in filter(None, button_labels):
        buttons.callback(label, callback)

    text = f""">Settings

**Rclone Config:** {settings['rccmsg']}
**Gdrive Token:** {settings['tokenmsg']}
**Name Substitution:** `{settings['ns_msg']}`
**Metadata Title:** `{settings['meta_msg']}`
**Excluded extension:** `{settings['ex_ex']}`
**YT-DLP Options:** `{escape(settings['ytopt'])}`
"""

    return text, buttons.menu(2)


async def update_user_settings(query):
    msg, button = await get_user_settings(query.from_user)
    user_id = query.from_user.id
    thumbnail = f"Thumbnails/{user_id}.jpg"
    if not await aiopath.exists(thumbnail):
        thumbnail = "https://graph.org/file/73ae908d18c6b38038071.jpg"
    await edit_message(query.message, msg, button, photo=thumbnail, MARKDOWN=True)


@new_thread
async def user_settings(_, message):
    from_user = message.from_user
    handler_dict[from_user.id] = False
    msg, button = await get_user_settings(from_user)
    user_id = from_user.id
    thumbnail = f"Thumbnails/{user_id}.jpg"
    if not await aiopath.exists(thumbnail):
        thumbnail = "https://graph.org/file/73ae908d18c6b38038071.jpg"
    x = await send_message(message, msg, button, photo=thumbnail, MARKDOWN=True)
    await five_minute_del(message)
    await delete_message(x)


async def set_thumb(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    des_dir = await createThumb(message, user_id)
    update_user_ldata(user_id, "thumb", des_dir)
    await delete_message(message)
    await update_user_settings(pre_event)
    await Database().update_user_doc(user_id, "thumb", des_dir)


async def add_rclone(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    rpath = f"{getcwd()}/rclone/"
    await makedirs(rpath, exist_ok=True)
    des_dir = f"{rpath}{user_id}.conf"
    await message.download(file_name=des_dir)
    update_user_ldata(user_id, "rclone_config", f"rclone/{user_id}.conf")
    await delete_message(message)
    await update_user_settings(pre_event)
    await Database().update_user_doc(user_id, "rclone_config", des_dir)


async def add_token_pickle(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    tpath = f"{getcwd()}/tokens/"
    await makedirs(tpath, exist_ok=True)
    des_dir = f"{tpath}{user_id}.pickle"
    await message.download(file_name=des_dir)
    update_user_ldata(user_id, "token_pickle", f"tokens/{user_id}.pickle")
    await delete_message(message)
    await update_user_settings(pre_event)
    await Database().update_user_doc(user_id, "token_pickle", des_dir)


async def delete_path(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    names = message.text.split()
    for name in names:
        if name in user_dict["upload_paths"]:
            del user_dict["upload_paths"][name]
    new_value = user_dict["upload_paths"]
    update_user_ldata(user_id, "upload_paths", new_value)
    await delete_message(message)
    await update_user_settings(pre_event)
    await Database().update_user_doc(user_id, "upload_paths", new_value)


async def set_option(_, message, pre_event, option):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    if option == "excluded_extensions":
        fx = value.split()
        value = ["aria2", "!qB"]
        for x in fx:
            x = x.lstrip(".")
            value.append(x.strip().lower())
    elif option == "upload_paths":
        user_dict = user_data.get(user_id, {})
        user_dict.setdefault("upload_paths", {})
        lines = value.split("/n")
        for line in lines:
            data = line.split(maxsplit=1)
            if len(data) != 2:
                await send_message(
                    message, "Wrong format! Add <name> <path>", MARKDOWN=True
                )
                await update_user_settings(pre_event)
                return
            name, path = data
            user_dict["upload_paths"][name] = path
        value = user_dict["upload_paths"]
    update_user_ldata(user_id, option, value)
    await delete_message(message)
    await update_user_settings(pre_event)
    await Database().update_user_data(user_id)


async def event_handler(client, query, pfunc, photo=False, document=False):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(
            user.id == user_id and event.chat.id == query.message.chat.id and mtype
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )

    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await update_user_settings(query)
    client.remove_handler(*handler)


@new_thread
async def edit_user_settings(client, query):
    from_user = query.from_user
    user_id = from_user.id
    message = query.message
    data = query.data.split()
    handler_dict[user_id] = False
    thumb_path = f"Thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] in [
        "as_doc",
        "stop_duplicate",
    ]:
        update_user_ldata(user_id, data[2], data[3] == "true")
        await query.answer()
        await update_user_settings(query)
        await Database().update_user_data(user_id)
    elif data[2] in ["thumb", "rclone_config", "token_pickle"]:
        if data[2] == "thumb":
            fpath = thumb_path
        elif data[2] == "rclone_config":
            fpath = rclone_conf
        else:
            fpath = token_pickle
        if await aiopath.exists(fpath):
            await query.answer()
            await remove(fpath)
            update_user_ldata(user_id, data[2], "")
            await update_user_settings(query)
            await Database().update_user_doc(user_id, data[2])
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] in [
        "yt_opt",
        "lcaption",
        "index_url",
        "excluded_extensions",
        "name_sub",
        "metadata",
        "user_dump",
        "session_string",
    ]:
        await query.answer()
        update_user_ldata(user_id, data[2], "")
        await update_user_settings(query)
        await Database().update_user_data(user_id)
    elif data[2] in ["rclone_path", "gdrive_id"]:
        await query.answer()
        if data[2] in user_data.get(user_id, {}):
            del user_data[user_id][data[2]]
            await update_user_settings(query)
            await Database().update_user_data(user_id)
    elif data[2] == "leech":
        await query.answer()
        thumbpath = f"Thumbnails/{user_id}.jpg"
        buttons = ButtonMaker()
        buttons.callback("Thumbnail", f"userset {user_id} sthumb")
        thumbmsg = "Exists" if await aiopath.exists(thumbpath) else "Not Exists"
        split_size = MAX_SPLIT_SIZE
        buttons.callback("Leech caption", f"userset {user_id} leech_caption")
        if user_dict.get("lcaption", False):
            lcaption = user_dict["lcaption"]
        else:
            lcaption = "None"
        buttons.callback("Leech Prefix", f"userset {user_id} leech_prefix")
        lprefix = user_dict["lprefix"] if user_dict.get("lprefix", False) else "None"
        buttons.callback("User dump", f"userset {user_id} u_dump")
        if user_dict.get("user_dump", False):
            user_dump = user_dict["user_dump"]
        else:
            user_dump = "None"
        buttons.callback("Session string", f"userset {user_id} s_string")
        if user_dict.get("session_string", False):
            session_string = "Exists"
        else:
            session_string = "Not exists"
        if (
            user_dict.get("as_doc", False)
            or "as_doc" not in user_dict
            and config_dict["AS_DOCUMENT"]
        ):
            ltype = "DOCUMENT"
            buttons.callback("Send As Media", f"userset {user_id} as_doc false")
        else:
            ltype = "MEDIA"
            buttons.callback("Send As Document", f"userset {user_id} as_doc true")
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        text = f""">Leech Settings

**Leech Type:** {ltype}
**Custom Thumbnail:** {thumbmsg}
**Leech Split Size:** {split_size}
**Session string:** {session_string}
**User Custom Dump:** `{user_dump}`
**Leech Prefix:** `{lprefix}`
**Leech Caption:** `{lcaption}`
"""
        await edit_message(message, text, buttons.menu(2), MARKDOWN=True)
    elif data[2] == "rclone":
        await query.answer()
        buttons = ButtonMaker()
        buttons.callback("Rclone Config", f"userset {user_id} rcc")
        buttons.callback("Default Rclone Path", f"userset {user_id} rcp")
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        rccmsg = "Exists" if await aiopath.exists(rclone_conf) else "Not Exists"
        if user_dict.get("rclone_path", False):
            rccpath = user_dict["rclone_path"]
        elif RP := config_dict["RCLONE_PATH"]:
            rccpath = RP
        else:
            rccpath = "None"
        text = f""">Rclone Settings

**Rclone Config:** {rccmsg}
**Rclone Path:** `{rccpath}`"""
        await edit_message(message, text, buttons.menu(1), MARKDOWN=True)
    elif data[2] == "gdrive":
        await query.answer()
        buttons = ButtonMaker()
        buttons.callback("token.pickle", f"userset {user_id} token")
        buttons.callback("Default Gdrive ID", f"userset {user_id} gdid")
        buttons.callback("Index URL", f"userset {user_id} index")
        if (
            user_dict.get("stop_duplicate", False)
            or "stop_duplicate" not in user_dict
            and config_dict["STOP_DUPLICATE"]
        ):
            buttons.callback(
                "Disable Stop Duplicate", f"userset {user_id} stop_duplicate false"
            )
            sd_msg = "Enabled"
        else:
            buttons.callback(
                "Enable Stop Duplicate", f"userset {user_id} stop_duplicate true"
            )
            sd_msg = "Disabled"
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        tokenmsg = "Exists" if await aiopath.exists(token_pickle) else "Not Exists"
        if user_dict.get("gdrive_id", False):
            gdrive_id = user_dict["gdrive_id"]
        elif GDID := config_dict["GDRIVE_ID"]:
            gdrive_id = GDID
        else:
            gdrive_id = "None"
        index = (
            user_dict["index_url"] if user_dict.get("index_url", False) else "None"
        )
        text = f""">Gdrive Tools Settings

**Gdrive Token:** {tokenmsg}
**Gdrive ID:** `{gdrive_id}`
**Index URL:** `{index}`
**Stop Duplicate:** {sd_msg}"""
        await edit_message(message, text, buttons.menu(1), MARKDOWN=True)
    elif data[2] == "sthumb":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(thumb_path):
            buttons.callback("Delete Thumbnail", f"userset {user_id} thumb")
        buttons.callback("Back", f"userset {user_id} leech")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send a photo to save it as custom thumbnail. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_thumb, pre_event=query)
        await event_handler(client, query, pfunc, True)
    elif data[2] == "yto":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("yt_opt", False) or config_dict["YT_DLP_OPTIONS"]:
            buttons.callback(
                "Remove YT-DLP Options", f"userset {user_id} yt_opt", "header"
            )
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        rmsg = """
Send YT-DLP Options. Timeout: 60 sec
Format: key:value|key:value|key:value.
Example: format:bv*+mergeall[vcodec=none]|nocheckcertificate:True
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
        """
        await edit_message(message, rmsg, buttons.menu(1), MARKDOWN=True)
        pfunc = partial(set_option, pre_event=query, option="yt_opt")
        await event_handler(client, query, pfunc)
    elif data[2] == "rcc":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(rclone_conf):
            buttons.callback(
                "Delete rclone.conf", f"userset {user_id} rclone_config"
            )
        buttons.callback("Back", f"userset {user_id} rclone")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send rclone.conf. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(add_rclone, pre_event=query)
        await event_handler(client, query, pfunc, document=True)
    elif data[2] == "rcp":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("rclone_path", False):
            buttons.callback("Reset Rclone Path", f"userset {user_id} rclone_path")
        buttons.callback("Back", f"userset {user_id} rclone")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send Rclone Path. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="rclone_path")
        await event_handler(client, query, pfunc)
    elif data[2] == "token":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(token_pickle):
            buttons.callback(
                "Delete token.pickle", f"userset {user_id} token_pickle"
            )
        buttons.callback("Back", f"userset {user_id} gdrive")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send token.pickle. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(add_token_pickle, pre_event=query)
        await event_handler(client, query, pfunc, document=True)
    elif data[2] == "gdid":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("gdrive_id", False):
            buttons.callback("Reset Gdrive ID", f"userset {user_id} gdrive_id")
        buttons.callback("Back", f"userset {user_id} gdrive")
        buttons.callback("Close", f"userset {user_id} close")
        rmsg = "Send Gdrive ID. Timeout: 60 sec"
        await edit_message(message, rmsg, buttons.menu(1), MARKDOWN=True)
        pfunc = partial(set_option, pre_event=query, option="gdrive_id")
        await event_handler(client, query, pfunc)
    elif data[2] == "index":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("index_url", False):
            buttons.callback("Remove Index URL", f"userset {user_id} index_url")
        buttons.callback("Back", f"userset {user_id} gdrive")
        buttons.callback("Close", f"userset {user_id} close")
        rmsg = "Send Index URL. Timeout: 60 sec"
        await edit_message(message, rmsg, buttons.menu(1), MARKDOWN=True)
        pfunc = partial(set_option, pre_event=query, option="index_url")
        await event_handler(client, query, pfunc)
    elif data[2] == "leech_prefix":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("lprefix", False):
            buttons.callback("Remove Leech Prefix", f"userset {user_id} lprefix")
        buttons.callback("Back", f"userset {user_id} leech")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send Leech Filename Prefix. You can add HTML tags. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="lprefix")
        await event_handler(client, query, pfunc)
    elif data[2] == "leech_caption":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("lcaption", False):
            buttons.callback("Remove Leech Caption", f"userset {user_id} lcaption")
        buttons.callback("Back", f"userset {user_id} leech")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send Leech Filename caption. You can add HTML tags. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="lcaption")
        await event_handler(client, query, pfunc)
    elif data[2] == "u_dump":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("user_dump", False):
            buttons.callback("Remove user dump", f"userset {user_id} user_dump")
        buttons.callback("Back", f"userset {user_id} leech")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send your custom dump channel starts with -100, bot must be admin in your channel. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="user_dump")
        await event_handler(client, query, pfunc)
    elif data[2] == "s_string":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("session_string", False):
            buttons.callback("Remove session", f"userset {user_id} session_string")
        buttons.callback("Back", f"userset {user_id} leech")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send your pyrogram V2 session string for download content from private channel or restricted channel. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="session_string")
        await event_handler(client, query, pfunc)
    elif data[2] == "ex_ex":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get("excluded_extensions", False)
            or "excluded_extensions" not in user_dict
            and GLOBAL_EXTENSION_FILTER
        ):
            buttons.callback(
                "Remove Excluded Extensions",
                f"userset {user_id} excluded_extensions",
            )
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send exluded extenions seperated by space without dot at beginning. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="excluded_extensions")
        await event_handler(client, query, pfunc)
    elif data[2] == "name_substitute":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("name_sub", False):
            buttons.callback("Remove Name Subtitute", f"userset {user_id} name_sub")
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        emsg = r"""Word Subtitions. You can add pattern instead of normal text. Timeout: 60 sec
NOTE: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-
Example-1: text : code : s|mirror : leech|tea :  : s|clone
1. text will get replaced by code with sensitive case
2. mirror will get replaced by leech
4. tea will get removed with sensitive case
5. clone will get removed
Example-2: \(text\) | \[test\] : test | \\text\\ : text : s
1. (text) will get removed
2. [test] will get replaced by test
3. \text\ will get replaced by text with sensitive case
"""
        emsg += (
            f"Your Current Value is {user_dict.get('name_sub') or 'not added yet!'}"
        )
        await edit_message(message, emsg, buttons.menu(1), MARKDOWN=True)
        pfunc = partial(set_option, pre_event=query, option="name_sub")
        await event_handler(client, query, pfunc)
    elif data[2] == "metadata_key":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get("metadata", False):
            buttons.callback("Remove Metadata key", f"userset {user_id} metadata")
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        emsg = "Metadata will change MKV video files including all audio, streams, and subtitle titles."
        emsg += (
            f"Your Current Value is {user_dict.get('metadata') or 'not added yet!'}"
        )
        await edit_message(message, emsg, buttons.menu(1), MARKDOWN=True)
        pfunc = partial(set_option, pre_event=query, option="metadata")
        await event_handler(client, query, pfunc)
    elif data[2] in ["gd", "rc"]:
        await query.answer()
        du = "rc" if data[2] == "gd" else "gd"
        update_user_ldata(user_id, "default_upload", du)
        await update_user_settings(query)
        await Database().update_user_data(user_id)
    elif data[2] == "upload_paths":
        await query.answer()
        buttons = ButtonMaker()
        buttons.callback("New Path", f"userset {user_id} new_path")
        if user_dict.get(data[2], False):
            buttons.callback("Show All Paths", f"userset {user_id} show_path")
            buttons.callback("Remove Path", f"userset {user_id} rm_path")
        buttons.callback("Back", f"userset {user_id} back")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message, "Add or remove upload path.\n", buttons.menu(1), MARKDOWN=True
        )
    elif data[2] == "new_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.callback("Back", f"userset {user_id} upload_paths")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send path name(no space in name) which you will use it as a shortcut and the path/id seperated by space. You can add multiple names and paths separated by new line. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(set_option, pre_event=query, option="upload_paths")
        await event_handler(client, query, pfunc)
    elif data[2] == "rm_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.callback("Back", f"userset {user_id} upload_paths")
        buttons.callback("Close", f"userset {user_id} close")
        await edit_message(
            message,
            "Send paths names which you want to delete, separated by space. Timeout: 60 sec",
            buttons.menu(1),
            MARKDOWN=True,
        )
        pfunc = partial(delete_path, pre_event=query)
        await event_handler(client, query, pfunc)
    elif data[2] == "show_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.callback("Back", f"userset {user_id} upload_paths")
        buttons.callback("Close", f"userset {user_id} close")
        user_dict = user_data.get(user_id, {})
        msg = "".join(
            f"**{key}**: `{value}`\n"
            for key, value in user_dict["upload_paths"].items()
        )
        await edit_message(message, msg, buttons.menu(1), MARKDOWN=True)
    elif data[2] == "reset":
        await query.answer()
        if ud := user_data.get(user_id, {}):
            if ud and ("is_sudo" in ud or "is_auth" in ud):
                for k in list(ud.keys()):
                    if k not in ["is_sudo", "is_auth"]:
                        del user_data[user_id][k]
            else:
                user_data[user_id].clear()
        await update_user_settings(query)
        await Database().update_user_data(user_id)
        for fpath in [thumb_path, rclone_conf, token_pickle]:
            if await aiopath.exists(fpath):
                await remove(fpath)
    elif data[2] == "back":
        await query.answer()
        await update_user_settings(query)
    else:
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)


async def send_users_settings(_, message):
    if user_data:
        msg = ""
        for u, d in user_data.items():
            kmsg = f"\n<b>{u}:</b>\n"
            if vmsg := "".join(
                f"{k}: <code>{v}</code>\n" for k, v in d.items() if f"{v}"
            ):
                msg += kmsg + vmsg

        msg_ecd = msg.encode()
        if len(msg_ecd) > 4000:
            with BytesIO(msg_ecd) as ofile:
                ofile.name = "users_settings.txt"
                await sendFile(message, ofile)
        else:
            await send_message(message, msg)
    else:
        await send_message(message, "No users data!")


bot.add_handler(
    MessageHandler(
        send_users_settings,
        filters=command(BotCommands.UsersCommand) & CustomFilters.sudo,
    )
)
bot.add_handler(
    MessageHandler(
        user_settings,
        filters=command(BotCommands.UserSetCommand) & CustomFilters.authorized_uset,
    )
)
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=regex("^userset")))
