from json import loads
from asyncio import sleep, gather
from secrets import token_hex

from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, bot, config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    new_task,
    arg_parser,
    is_share_link,
    sync_to_async,
    fetch_user_tds,
    is_gdrive_link,
    is_rclone_path,
    get_telegraph_list,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkError
from bot.helper.aeon_utils.nsfw_check import nsfw_precheck
from bot.helper.aeon_utils.send_react import send_react
from bot.helper.ext_utils.help_strings import CLONE_HELP_MESSAGE
from bot.helper.ext_utils.task_manager import task_utils, limit_checker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    delete_links,
    edit_message,
    send_message,
    delete_message,
    one_minute_del,
    five_minute_del,
    sendStatusMessage,
)
from bot.helper.mirror_leech_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_leech_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_leech_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_leech_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_leech_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_leech_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)


async def rcloneNode(client, message, link, dst_path, rcf, tag):
    if link == "rcl":
        link = await RcloneList(client, message).get_rclone_path("rcd")
        if not is_rclone_path(link):
            await send_message(message, link)
            return

    if link.startswith("mrcc:"):
        link = link.split("mrcc:", 1)[1]
        config_path = f"tanha/{message.from_user.id}.conf"
    else:
        config_path = "rcl.conf"

    if not await aiopath.exists(config_path):
        await send_message(message, f"Rclone Config: {config_path} not Exists!")
        return

    if dst_path == "rcl" or config_dict["RCLONE_PATH"] == "rcl":
        dst_path = await RcloneList(client, message).get_rclone_path(
            "rcu", config_path
        )
        if not is_rclone_path(dst_path):
            await send_message(message, dst_path)
            return

    dst_path = (dst_path or config_dict["RCLONE_PATH"]).strip("/")
    if not is_rclone_path(dst_path):
        await send_message(message, "Given Wrong RClone Destination!")
        return
    if dst_path.startswith("mrcc:"):
        if config_path != f"tanha/{message.from_user.id}.conf":
            await send_message(
                message, "You should use same rcl.conf to clone between pathies!"
            )
            return
        dst_path = dst_path.lstrip("mrcc:")
    elif config_path != "rcl.conf":
        await send_message(
            message, "You should use same rcl.conf to clone between pathies!"
        )
        return

    remote, src_path = link.split(":", 1)
    src_path = src_path.strip("/")

    cmd = [
        "xone",
        "lsjson",
        "--fast-list",
        "--stat",
        "--no-modtime",
        "--config",
        config_path,
        f"{remote}:{src_path}",
    ]
    res = await cmd_exec(cmd)
    if res[2] != 0:
        if res[2] != -9:
            msg = f"Error: While getting RClone Stats. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}"
            await send_message(message, msg)
        return
    rstat = loads(res[0])
    if rstat["IsDir"]:
        name = src_path.rsplit("/", 1)[-1] if src_path else remote
        dst_path += name if dst_path.endswith(":") else f"/{name}"
        mime_type = "Folder"
    else:
        name = src_path.rsplit("/", 1)[-1]
        mime_type = rstat["MimeType"]

    listener = MirrorLeechListener(message, tag=tag)
    await listener.on_download_start()

    RCTransfer = RcloneTransferHelper(listener, name)
    LOGGER.info(
        f"Clone Started: Name: {name} - Source: {link} - Destination: {dst_path}"
    )
    gid = token_hex(4)
    async with download_dict_lock:
        download_dict[message.id] = RcloneStatus(RCTransfer, message, gid, "cl")
    await sendStatusMessage(message)
    link, destination = await RCTransfer.clone(
        config_path, remote, src_path, dst_path, rcf, mime_type
    )
    if not link:
        return
    LOGGER.info(f"Cloning Done: {name}")
    cmd1 = [
        "xone",
        "lsf",
        "--fast-list",
        "-R",
        "--files-only",
        "--config",
        config_path,
        destination,
    ]
    cmd2 = [
        "xone",
        "lsf",
        "--fast-list",
        "-R",
        "--dirs-only",
        "--config",
        config_path,
        destination,
    ]
    cmd3 = [
        "xone",
        "size",
        "--fast-list",
        "--json",
        "--config",
        config_path,
        destination,
    ]
    res1, res2, res3 = await gather(cmd_exec(cmd1), cmd_exec(cmd2), cmd_exec(cmd3))
    if res1[2] != res2[2] != res3[2] != 0:
        if res1[2] == -9:
            return
        files = None
        folders = None
        size = 0
        LOGGER.error(
            f"Error: While getting RClone Stats. Path: {destination}. Stderr: {res1[1][:4000]}"
        )
    else:
        files = len(res1[0].split("\n"))
        folders = len(res2[0].split("\n"))
        rsize = loads(res3[0])
        size = rsize["bytes"]
    await listener.onUploadComplete(
        link, size, files, folders, mime_type, name, destination
    )


async def gdcloneNode(message, link, listen_up):
    if not is_gdrive_link(link) and is_share_link(link):
        process_msg = await send_message(
            message, f"<b>Processing Link:</b> <code>{link}</code>"
        )
        try:
            link = await sync_to_async(direct_link_generator, link)
            LOGGER.info(f"Generated link: {link}")
            await edit_message(
                process_msg, f"<b>Generated Link:</b> <code>{link}</code>"
            )
        except DirectDownloadLinkError as e:
            LOGGER.error(str(e))
            if str(e).startswith("ERROR:"):
                await edit_message(process_msg, str(e))
                await delete_links(message)
                await one_minute_del(process_msg)
                return
        await delete_message(process_msg)
    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        name, mime_type, size, files, _ = await sync_to_async(gd.count, link)
        if mime_type is None:
            await send_message(message, name)
            return
        if config_dict["STOP_DUPLICATE"]:
            LOGGER.info("Checking File/Folder if already in Drive...")
            telegraph_content, contents_no = await sync_to_async(
                gd.drive_list, name, True, True
            )
            if telegraph_content:
                msg = f"File/Folder is already available in Drive.\nHere are {contents_no} list results:"
                button = await get_telegraph_list(telegraph_content)
                await send_message(message, msg, button)
                return
        listener = MirrorLeechListener(
            message,
            tag=listen_up[0],
            is_clone=True,
            drive_id=listen_up[1],
            index_link=listen_up[2],
        )
        if limit_exceeded := await limit_checker(size, listener):
            await listener.onUploadError(limit_exceeded)
            return
        await listener.on_download_start()
        LOGGER.info(f"Clone Started: Name: {name} - Source: {link}")
        drive = GoogleDriveHelper(name, listener=listener)
        if files <= 20:
            msg = await send_message(message, f"<b>Cloning:</b> <code>{link}</code>")
            link, size, mime_type, files, folders = await sync_to_async(
                drive.clone, link, listener.drive_id
            )
            await delete_message(msg)
        else:
            gid = token_hex(4)
            async with download_dict_lock:
                download_dict[message.id] = GdriveStatus(
                    drive, size, message, gid, "cl"
                )
            await sendStatusMessage(message)
            link, size, mime_type, files, folders = await sync_to_async(
                drive.clone, link, listener.drive_id
            )
        if not link:
            return
        LOGGER.info(f"Cloning Done: {name}")
        await listener.onUploadComplete(link, size, files, folders, mime_type, name)
    else:
        reply_message = await send_message(message, CLONE_HELP_MESSAGE)
        await delete_message(message)
        await one_minute_del(reply_message)


@new_task
async def clone(client, message):
    await send_react(message)
    input_list = message.text.split(" ")
    arg_base = {
        "link": "",
        "-i": "0",
        "-up": "",
        "-rcf": "",
        "-id": "",
        "-index": "",
    }
    args = arg_parser(input_list[1:], arg_base)
    i = args["-i"]
    dst_path = args["-up"]
    rcf = args["-rcf"]
    link = args["link"]
    drive_id = args["-id"]
    index_link = args["-index"]
    multi = int(i) if i.isdigit() else 0

    if username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    if not link and (reply_to := message.reply_to_message):
        link = reply_to.text.split("\n", 1)[0].strip()

    @new_task
    async def __run_multi():
        if multi > 1:
            await sleep(5)
            msg = [s.strip() for s in input_list]
            index = msg.index("-i")
            msg[index + 1] = f"{multi - 1}"
            nextmsg = await client.get_messages(
                chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1
            )
            nextmsg = await send_message(nextmsg, " ".join(msg))
            nextmsg = await client.get_messages(
                chat_id=message.chat.id, message_ids=nextmsg.id
            )
            nextmsg.from_user = message.from_user
            await sleep(5)
            clone(client, nextmsg)

    __run_multi()

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    if len(link) == 0:
        reply_message = await send_message(message, CLONE_HELP_MESSAGE)
        await delete_message(message)
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
        force_m = await send_message(message, final_msg, error_button)
        await five_minute_del(force_m)
        return None

    if is_rclone_path(link):
        if not await aiopath.exists("rcl.conf") and not await aiopath.exists(
            f"tanha/{message.from_user.id}.conf"
        ):
            await send_message(message, "Rclone Config Not exists!")
            return None
        if not config_dict["RCLONE_PATH"] and not dst_path:
            await send_message(message, "Destination not specified!")
            await delete_links(message)
            return None
        await rcloneNode(client, message, link, dst_path, rcf, tag)
    else:
        user_tds = await fetch_user_tds(message.from_user.id)
        if not drive_id and len(user_tds) == 1:
            drive_id, index_link = next(iter(user_tds.values())).values()
        if drive_id and not await sync_to_async(
            GoogleDriveHelper().getFolderData, drive_id
        ):
            return await send_message(message, "Google Drive ID validation failed!!")
        if not config_dict["GDRIVE_ID"] and not drive_id:
            await send_message(message, "GDRIVE_ID not Provided!")
            await delete_links(message)
            return None
        await gdcloneNode(message, link, [tag, drive_id, index_link])
    await delete_links(message)
    return None


bot.add_handler(
    MessageHandler(
        clone, filters=command(BotCommands.CloneCommand) & CustomFilters.authorized
    )
)
