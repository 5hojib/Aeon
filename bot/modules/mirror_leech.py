import contextlib
from re import match as re_match
from base64 import b64encode
from asyncio import sleep

from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, bot, user_data, config_dict
from bot.helper.ext_utils.bot_utils import (
    is_url,
    new_task,
    is_magnet,
    arg_parser,
    is_mega_link,
    sync_to_async,
    fetch_user_tds,
    is_gdrive_link,
    is_rclone_path,
    get_content_type,
    is_telegram_link,
)
from bot.helper.ext_utils.bulk_links import extract_bulk_links
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.aeon_utils.nsfw_check import nsfw_precheck
from bot.helper.aeon_utils.send_react import send_react
from bot.helper.ext_utils.help_strings import MIRROR_HELP_MESSAGE
from bot.helper.ext_utils.task_manager import task_utils
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    editMessage,
    sendMessage,
    delete_links,
    deleteMessage,
    one_minute_del,
    five_minute_del,
    get_tg_link_content,
)
from bot.helper.mirror_leech_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_leech_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_leech_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_leech_utils.download_utils.mega_download import (
    add_mega_download,
)
from bot.helper.mirror_leech_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_leech_utils.download_utils.aria2_download import (
    add_aria2c_download,
)
from bot.helper.mirror_leech_utils.download_utils.rclone_download import (
    add_rclone_download,
)
from bot.helper.mirror_leech_utils.download_utils.direct_downloader import (
    add_direct_download,
)
from bot.helper.mirror_leech_utils.download_utils.telegram_download import (
    TelegramDownloadHelper,
)
from bot.helper.mirror_leech_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)


@new_task
async def _mirror_leech(
    client, message, isQbit=False, isLeech=False, sameDir=None, bulk=[]
):
    await send_react(message)
    user = message.from_user or message.sender_chat
    user_id = user.id
    user_dict = user_data.get(user_id, {})
    text = message.text.split("\n")
    input_list = text[0].split(" ")
    arg_base = {
        "link": "",
        "-t": "",
        "-m": "",
        "-n": "",
        "-h": "",
        "-u": "",
        "-p": "",
        "-up": "",
        "-rcf": "",
        "-id": "",
        "-index": "",
        "-d": False,
        "-j": False,
        "-s": False,
        "-b": False,
        "-e": False,
        "-z": False,
        "-i": "0",
        "-ss": "0",
        "-atc": "",
    }

    args = arg_parser(input_list[1:], arg_base)
    attachment = (
        args["-atc"]
        or user_dict.get("attachment", "")
        or config_dict["ATTACHMENT_URL"]
    )
    i = args["-i"]
    link = args["link"]
    headers = args["-h"]
    folder_name = args["-m"]
    seed = args["-d"]
    join = args["-j"]
    select = args["-s"]
    isBulk = args["-b"]
    name = args["-n"]
    extract = args["-e"]
    compress = args["-z"]
    up = args["-up"]
    thumb = args["-t"]
    rcf = args["-rcf"]
    drive_id = args["-id"]
    index_link = args["-index"]
    ss = args["-ss"]
    multi = int(i) if i.isdigit() else 0
    sshots = min(int(ss) if ss.isdigit() else 0, 10)
    bulk_start = 0
    bulk_end = 0
    ratio = None
    seed_time = None
    reply_to = None
    file_ = None
    session = ""

    if link:
        if is_magnet(link) or link.endswith(".torrent"):
            isQbit = True
    elif not link and (reply_to := message.reply_to_message) and reply_to.text:
        reply_text = reply_to.text.split("\n", 1)[0].strip()
        if reply_text and is_magnet(reply_text):
            isQbit = True
    if reply_to := message.reply_to_message:
        file_ = getattr(reply_to, reply_to.media.value) if reply_to.media else None
        if reply_to.document and (
            file_.mime_type == "application/x-bittorrent"
            or file_.file_name.endswith(".torrent")
        ):
            isQbit = True
    if not isinstance(seed, bool):
        dargs = seed.split(":")
        ratio = dargs[0] or None
        if len(dargs) == 2:
            seed_time = dargs[1] or None
        seed = True

    if not isinstance(isBulk, bool):
        dargs = isBulk.split(":")
        bulk_start = dargs[0] or None
        if len(dargs) == 2:
            bulk_end = dargs[1] or None
        isBulk = True

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    if folder_name and not isBulk:
        seed = False
        ratio = None
        seed_time = None
        folder_name = f"/{folder_name}"
        if sameDir is None:
            sameDir = {"total": multi, "tasks": set(), "name": folder_name}
        sameDir["tasks"].add(message.id)

    if isBulk:
        try:
            bulk = await extract_bulk_links(message, bulk_start, bulk_end)
            if len(bulk) == 0:
                raise ValueError("Bulk Empty!")
        except Exception:
            await sendMessage(
                message,
                "Reply to text file or tg message that have links seperated by new line!",
            )
            return None
        b_msg = input_list[:1]
        b_msg.append(f"{bulk[0]} -i {len(bulk)}")
        nextmsg = await sendMessage(message, " ".join(b_msg))
        nextmsg = await client.get_messages(
            chat_id=message.chat.id, message_ids=nextmsg.id
        )
        nextmsg.from_user = message.from_user
        _mirror_leech(client, nextmsg, isQbit, isLeech, sameDir, bulk)
        return None

    if len(bulk) != 0:
        del bulk[0]

    @new_task
    async def __run_multi():
        if multi <= 1:
            return
        await sleep(5)
        if len(bulk) != 0:
            msg = input_list[:1]
            msg.append(f"{bulk[0]} -i {multi - 1}")
            nextmsg = await sendMessage(message, " ".join(msg))
        else:
            msg = [s.strip() for s in input_list]
            index = msg.index("-i")
            msg[index + 1] = f"{multi - 1}"
            nextmsg = await client.get_messages(
                chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1
            )
            nextmsg = await sendMessage(nextmsg, " ".join(msg))
        nextmsg = await client.get_messages(
            chat_id=message.chat.id, message_ids=nextmsg.id
        )
        if folder_name:
            sameDir["tasks"].add(nextmsg.id)
        nextmsg.from_user = message.from_user
        await sleep(5)
        _mirror_leech(client, nextmsg, isQbit, isLeech, sameDir, bulk)

    __run_multi()

    path = f"/usr/src/app/downloads/{message.id}{folder_name}"

    if len(text) > 1 and text[1].startswith("Tag: "):
        tag, id_ = text[1].split("Tag: ")[1].split()
        message.from_user = await client.get_users(id_)
        with contextlib.suppress(Exception):
            await message.unpin()
    elif sender_chat := message.sender_chat:
        tag = sender_chat.title
    if username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    if link and is_telegram_link(link):
        try:
            reply_to, session = await get_tg_link_content(link)
        except Exception as e:
            await sendMessage(message, f"ERROR: {e}")
            await delete_links(message)
            return None
    elif not link and (reply_to := message.reply_to_message) and reply_to.text:
        reply_text = reply_to.text.split("\n", 1)[0].strip()
        if reply_text and is_telegram_link(reply_text):
            try:
                reply_to, session = await get_tg_link_content(reply_text)
            except Exception as e:
                await sendMessage(message, f"ERROR: {e}")
                await delete_links(message)
                return None

    if reply_to:
        file_ = getattr(reply_to, reply_to.media.value) if reply_to.media else None
        if file_ is None:
            reply_text = reply_to.text.split("\n", 1)[0].strip()
            if (
                is_url(reply_text)
                or is_magnet(reply_text)
                or is_rclone_path(reply_text)
            ):
                link = reply_text
        elif reply_to.document and (
            file_.mime_type == "application/x-bittorrent"
            or file_.file_name.endswith(".torrent")
        ):
            link = await reply_to.download()
            file_ = None

    if (
        not is_url(link)
        and not is_magnet(link)
        and not await aiopath.exists(link)
        and not is_rclone_path(link)
        and file_ is None
    ):
        reply_message = await sendMessage(message, MIRROR_HELP_MESSAGE)
        await deleteMessage(message)
        await one_minute_del(reply_message)
        return None

    error_msg = []
    error_button = None
    if await nsfw_precheck(message):
        error_msg.extend(["NSFW detected"])
    task_utilis_msg, error_button = await task_utils(message)
    if task_utilis_msg:
        error_msg.extend(task_utilis_msg)
    if error_msg:
        final_msg = f"Hey, <b>{tag}</b>!\n"
        for __i, __msg in enumerate(error_msg, 1):
            final_msg += f"\n<blockquote><b>{__i}</b>: {__msg}</blockquote>"
        if error_button is not None:
            error_button = error_button.column(2)
        await delete_links(message)
        force_m = await sendMessage(message, final_msg, error_button)
        await five_minute_del(force_m)
        return None

    if (
        not is_mega_link(link)
        and not isQbit
        and not is_magnet(link)
        and not is_rclone_path(link)
        and not is_gdrive_link(link)
        and not link.endswith(".torrent")
        and file_ is None
    ):
        content_type = await get_content_type(link)
        if content_type is None or re_match(r"text/html|text/plain", content_type):
            process_msg = await sendMessage(
                message, f"<b>Processing:</b> <code>{link}</code>"
            )
            try:
                link = await sync_to_async(direct_link_generator, link)
                if isinstance(link, tuple):
                    link, headers = link
                elif isinstance(link, str):
                    LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith("ERROR:"):
                    await editMessage(process_msg, str(e))
                    await delete_links(message)
                    await one_minute_del(process_msg)
                    return None
            await deleteMessage(process_msg)

    if not isLeech:
        if config_dict["DEFAULT_UPLOAD"] == "rc" and not up or up == "rc":
            up = config_dict["RCLONE_PATH"]
        if not up and config_dict["DEFAULT_UPLOAD"] == "gd":
            up = "gd"
            user_tds = await fetch_user_tds(message.from_user.id)
            if not drive_id and len(user_tds) == 1:
                drive_id, index_link = next(iter(user_tds.values())).values()
            if drive_id and not await sync_to_async(
                GoogleDriveHelper().getFolderData, drive_id
            ):
                return await sendMessage(
                    message, "Google Drive ID validation failed!!"
                )
        if up == "gd" and not config_dict["GDRIVE_ID"] and not drive_id:
            await sendMessage(message, "GDRIVE_ID not Provided!")
            return None
        if not up:
            await sendMessage(message, "No Rclone Destination!")
            return None
        if up not in ["rcl", "gd"]:
            if up.startswith("mrcc:"):
                config_path = f"tanha/{message.from_user.id}.conf"
            else:
                config_path = "rcl.conf"
            if not await aiopath.exists(config_path):
                await sendMessage(
                    message, f"Rclone Config: {config_path} not Exists!"
                )
                return None
        if up != "gd" and not is_rclone_path(up):
            await sendMessage(message, "Wrong Rclone Upload Destination!")
            await delete_links(message)
            return None

    if link == "rcl":
        link = await RcloneList(client, message).get_rclone_path("rcd")
        if not is_rclone_path(link):
            await sendMessage(message, link)
            await delete_links(message)
            return None

    if up == "rcl" and not isLeech:
        up = await RcloneList(client, message).get_rclone_path("rcu")
        if not is_rclone_path(up):
            await sendMessage(message, up)
            await delete_links(message)
            return None

    listener = MirrorLeechListener(
        message,
        compress,
        extract,
        isQbit,
        isLeech,
        tag,
        select,
        seed,
        sameDir,
        rcf,
        up,
        join,
        drive_id=drive_id,
        index_link=index_link,
        attachment=attachment,
        files_utils={"screenshots": sshots, "thumb": thumb},
    )

    if file_ is not None:
        await delete_links(message)
        await TelegramDownloadHelper(listener).add_download(
            reply_to, f"{path}/", name, session
        )
    elif isinstance(link, dict):
        await add_direct_download(link, path, listener, name)
    elif is_rclone_path(link):
        if link.startswith("mrcc:"):
            link = link.split("mrcc:", 1)[1]
            config_path = f"tanha/{message.from_user.id}.conf"
        else:
            config_path = "rcl.conf"
        if not await aiopath.exists(config_path):
            await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
            return None
        await add_rclone_download(link, config_path, f"{path}/", name, listener)
    elif is_gdrive_link(link):
        await delete_links(message)
        await add_gd_download(link, path, listener, name)
    elif is_mega_link(link):
        await delete_links(message)
        await add_mega_download(link, f"{path}/", listener, name)
    elif isQbit:
        await add_qb_torrent(link, path, listener, ratio, seed_time)
        LOGGER.info("Downloading with qbitEngine")
    else:
        ussr = args["-u"]
        pssw = args["-p"]
        if ussr or pssw:
            auth = f"{ussr}:{pssw}"
            headers += (
                f" authorization: Basic {b64encode(auth.encode()).decode('ascii')}"
            )
        await add_aria2c_download(
            link, path, listener, name, headers, ratio, seed_time
        )
    await delete_links(message)
    return None


async def mirror(client, message):
    _mirror_leech(client, message)


async def leech(client, message):
    _mirror_leech(client, message, isLeech=True)


bot.add_handler(
    MessageHandler(
        mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized
    )
)
bot.add_handler(
    MessageHandler(
        leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized
    )
)
