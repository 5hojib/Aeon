#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from secrets import token_urlsafe
from asyncio import sleep, gather
from aiofiles.os import path as aiopath
from json import loads

from bot import LOGGER, download_dict, download_dict_lock, config_dict, bot
from bot.helper.ext_utils.task_manager import limit_checker, task_utils
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, sendStatusMessage, delete_links, one_minute_del, five_minute_del, isAdmin
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.ext_utils.bot_utils import is_gdrive_link, new_task, get_readable_file_size, sync_to_async, fetch_user_tds, is_share_link, new_task, is_rclone_path, cmd_exec, get_telegraph_list, arg_parser
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.ext_utils.help_messages import CLONE_HELP_MESSAGE
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.listeners.tasks_listener import MirrorLeechListener


async def rcloneNode(client, message, link, dst_path, rcf, tag):
    if link == 'rcl':
        link = await RcloneList(client, message).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await sendMessage(message, link)
            return

    if link.startswith('mrcc:'):
        link = link.split('mrcc:', 1)[1]
        config_path = f'tanha/{message.from_user.id}.conf'
    else:
        config_path = 'rcl.conf'

    if not await aiopath.exists(config_path):
        await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
        return

    if dst_path == 'rcl' or config_dict['RCLONE_PATH'] == 'rcl':
        dst_path = await RcloneList(client, message).get_rclone_path('rcu', config_path)
        if not is_rclone_path(dst_path):
            await sendMessage(message, dst_path)
            return

    dst_path = (dst_path or config_dict['RCLONE_PATH']).strip('/')
    if not is_rclone_path(dst_path):
        await sendMessage(message, 'Given Wrong RClone Destination!')
        return
    if dst_path.startswith('mrcc:'):
        if config_path != f'tanha/{message.from_user.id}.conf':
            await sendMessage(message, 'You should use same rcl.conf to clone between pathies!')
            return
    elif config_path != 'rcl.conf':
        await sendMessage(message, 'You should use same rcl.conf to clone between pathies!')
        return

    remote, src_path = link.split(':', 1)
    src_path = src_path .strip('/')

    cmd = ['zcl', 'lsjson', '--fast-list', '--stat',
           '--no-modtime', '--config', config_path, f'{remote}:{src_path}']
    res = await cmd_exec(cmd)
    if res[2] != 0:
        if res[2] != -9:
            msg = f'Error: While getting RClone Stats. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}'
            await sendMessage(message, msg)
        return
    rstat = loads(res[0])
    if rstat['IsDir']:
        name = src_path.rsplit('/', 1)[-1] if src_path else remote
        dst_path += name if dst_path.endswith(':') else f'/{name}'
        mime_type = 'Folder'
    else:
        name = src_path.rsplit('/', 1)[-1]
        mime_type = rstat['MimeType']

    listener = MirrorLeechListener(message, tag=tag, source_url=link)
    await listener.onDownloadStart()

    RCTransfer = RcloneTransferHelper(listener, name)
    LOGGER.info(f'Clone Started: Name: {name} - Source: {link} - Destination: {dst_path}')
    gid = token_urlsafe(8)
    async with download_dict_lock:
        download_dict[message.id] = RcloneStatus(
            RCTransfer, message, gid, 'cl', listener.upload_details)
    await sendStatusMessage(message)
    link, destination = await RCTransfer.clone(config_path, remote, src_path, dst_path, rcf, mime_type)
    if not link:
        return
    LOGGER.info(f'Cloning Done: {name}')
    cmd1 = ['zcl', 'lsf', '--fast-list', '-R',
            '--files-only', '--config', config_path, destination]
    cmd2 = ['zcl', 'lsf', '--fast-list', '-R',
            '--dirs-only', '--config', config_path, destination]
    cmd3 = ['zcl', 'size', '--fast-list', '--json',
            '--config', config_path, destination]
    res1, res2, res3 = await gather(cmd_exec(cmd1), cmd_exec(cmd2), cmd_exec(cmd3))
    if res1[2] != res2[2] != res3[2] != 0:
        if res1[2] == -9:
            return
        files = None
        folders = None
        size = 0
        LOGGER.error(f'Error: While getting RClone Stats. Path: {destination}. Stderr: {res1[1][:4000]}')
    else:
        files = len(res1[0].split("\n"))
        folders = len(res2[0].split("\n"))
        rsize = loads(res3[0])
        size = rsize['bytes']
    await listener.onUploadComplete(link, size, files, folders, mime_type, name, destination)


async def gdcloneNode(message, link, listen_up):
    if not is_gdrive_link(link) and is_share_link(link):
        process_msg = await sendMessage(message, f"<b>Processing Link:</b> <code>{link}</code>")
        try:
            link = await sync_to_async(direct_link_generator, link)
            LOGGER.info(f"Generated link: {link}")
            await editMessage(process_msg, f"<b>Generated Link:</b> <code>{link}</code>")
        except DirectDownloadLinkException as e:
            LOGGER.error(str(e))
            if str(e).startswith('ERROR:'):
                await editMessage(process_msg, str(e))
                await delete_links(message)
                await one_minute_del(process_msg)
                return
        await deleteMessage(process_msg)
    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        name, mime_type, size, files, _ = await sync_to_async(gd.count, link)
        if mime_type is None:
            await sendMessage(message, name)
            return
        if config_dict['STOP_DUPLICATE']:
            LOGGER.info('Checking File/Folder if already in Drive...')
            telegraph_content, contents_no = await sync_to_async(gd.drive_list, name, True, True)
            if telegraph_content:
                msg = f'File/Folder is already available in Drive.\nHere are {contents_no} list results:'
                button = await get_telegraph_list(telegraph_content)
                await sendMessage(message, msg, button)
                return
        listener = MirrorLeechListener(message, tag=listen_up[0], isClone=True, drive_id=listen_up[1], index_link=listen_up[2], source_url=link)
        if limit_exceeded := await limit_checker(size, listener):
            await listener.onUploadError(limit_exceeded)
            return
        await listener.onDownloadStart()
        LOGGER.info(f'Clone Started: Name: {name} - Source: {link}')
        drive = GoogleDriveHelper(name, listener=listener)
        if files <= 20:
            msg = await sendMessage(message, f"<b>Cloning:</b> <code>{link}</code>")
            link, size, mime_type, files, folders = await sync_to_async(drive.clone, link, listener.drive_id)
            await deleteMessage(msg)
        else:
            gid = token_urlsafe(8)
            async with download_dict_lock:
                download_dict[message.id] = GdriveStatus(
                    drive, size, message, gid, 'cl', listener.upload_details)
            await sendStatusMessage(message)
            link, size, mime_type, files, folders = await sync_to_async(drive.clone, link, listener.drive_id)
        if not link:
            return
        LOGGER.info(f'Cloning Done: {name}')
        await listener.onUploadComplete(link, size, files, folders, mime_type, name)
    else:
        reply_message = await sendMessage(message, CLONE_HELP_MESSAGE)
        await deleteMessage(message)
        await one_minute_del(reply_message)


@new_task
async def clone(client, message):
    input_list = message.text.split(' ')

    arg_base = {'link': '', 
                '-i': 0, 
                '-up': '', '-upload': '',
                '-rcf': '',
                '-id': '',
                '-index': '',
    }

    args = arg_parser(input_list[1:], arg_base)

    try:
        multi = int(args['-i'])
    except:
        multi = 0

    dst_path   = args['-up'] or args['-upload']
    rcf        = args['-rcf']
    link       = args['link']
    drive_id   = args['-id']
    index_link = args['-index']
    
    if username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    if not link and (reply_to := message.reply_to_message):
        link = reply_to.text.split('\n', 1)[0].strip()

    @new_task
    async def __run_multi():
        if multi > 1:
            await sleep(5)
            msg = [s.strip() for s in input_list]
            index = msg.index('-i')
            msg[index+1] = f"{multi - 1}"
            nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1)
            nextmsg = await sendMessage(nextmsg, " ".join(msg))
            nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
            nextmsg.from_user = message.from_user
            await sleep(5)
            clone(client, nextmsg)

    __run_multi()

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    if len(link) == 0:
        reply_message = await sendMessage(message, CLONE_HELP_MESSAGE)
        await deleteMessage(message)
        await one_minute_del(reply_message)
        return

    error_msg = []
    error_button = None
    if not await isAdmin(message):
        task_utilis_msg, error_button = await task_utils(message)
        if task_utilis_msg:
            error_msg.extend(task_utilis_msg)
    if error_msg:
        final_msg = f'Hey, <b>{tag}</b>!\n'
        for __i, __msg in enumerate(error_msg, 1):
            final_msg += f'\n<b>{__i}</b>: {__msg}\n'
        if error_button is not None:
            error_button = error_button.build_menu(2)
        await delete_links(message)
        force_m = await sendMessage(message, final_msg, error_button)
        await five_minute_del(force_m)
        return

    if is_rclone_path(link):
        if not await aiopath.exists('rcl.conf') and not await aiopath.exists(f'tanha/{message.from_user.id}.conf'):
            await sendMessage(message, 'Rclone Config Not exists!')
            return
        if not config_dict['RCLONE_PATH'] and not dst_path:
            await sendMessage(message, 'Destination not specified!')
            await delete_links(message)
            return
        await rcloneNode(client, message, link, dst_path, rcf, tag)
    else:
        user_tds = await fetch_user_tds(message.from_user.id)
        if not drive_id and len(user_tds) == 1:
            drive_id, index_link = next(iter(user_tds.values())).values()
        if drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
            return await sendMessage(message, "Google Drive ID validation failed!!")
        if not config_dict['GDRIVE_ID'] and not drive_id:
            await sendMessage(message, 'GDRIVE_ID not Provided!')
            await delete_links(message)
            return
        await gdcloneNode(message, link, [tag, drive_id, index_link])
    await delete_links(message)
    
bot.add_handler(MessageHandler(clone, filters=command(
    BotCommands.CloneCommand) & CustomFilters.authorized))
