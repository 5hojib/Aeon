#!/usr/bin/env python3
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from html import escape
from base64 import b64encode
from re import match as re_match
from asyncio import sleep
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from cloudscraper import create_scraper

from bot import bot, LOGGER, config_dict, bot_name, user_data
from bot.helper.ext_utils.bot_utils import is_url, is_magnet, is_mega_link, is_gdrive_link, get_content_type, new_task, sync_to_async, is_rclone_path, is_telegram_link, arg_parser, fetch_user_tds
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.task_manager import task_utils
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_utils.download_utils.mega_download import add_mega_download
from bot.helper.mirror_utils.download_utils.rclone_download import add_rclone_download
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.telegram_download import TelegramDownloadHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, get_tg_link_content, delete_links, deleteMessage, one_minute_del, five_minute_del, isAdmin
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.ext_utils.help_messages import MIRROR_HELP_MESSAGE
from bot.helper.ext_utils.bulk_links import extract_bulk_links
from bot.helper.mirror_utils.download_utils.direct_downloader import add_direct_download

@new_task
async def _mirror_leech(client, message, isQbit=False, isLeech=False, sameDir=None, bulk=[]):
    text = message.text.split('\n')
    input_list = text[0].split(' ')

    arg_base = {'link': '', 
                '-i': 0,
                '-m': '', '-sd': '', '-samedir': '',
                '-d': False, '-seed': False,
                '-j': False, '-join': False,
                '-s': False, '-select': False,
                '-b': False, '-bulk': False,
                '-n': '', '-name': '',
                '-e': False, '-extract': False,
                '-uz': False, '-unzip': False,
                '-z': False, '-zip': False,
                '-up': '', '-upload': '',
                '-rcf': '', 
                '-u': '', '-user': '',
                '-p': '', '-pass': '',
                '-id': '',
                '-index': '',
    }

    args = arg_parser(input_list[1:], arg_base)

    try:
        multi = int(args['-i'])
    except:
        multi = 0
    
    link          = args['link']
    folder_name   = args['-m'] or args['-sd'] or args['-samedir']
    seed          = args['-d'] or args['-seed']
    join          = args['-j'] or args['-join']
    select        = args['-s'] or args['-select']
    isBulk        = args['-b'] or args['-bulk']
    name          = args['-n'] or args['-name']
    extract       = args['-e'] or args['-extract'] or args['-uz'] or args['-unzip'] or 'uz' in input_list[0] or 'unzip' in input_list[0]
    compress      = args['-z'] or args['-zip'] or (not extract and ('z' in input_list[0] or 'zip' in input_list[0]))
    up            = args['-up'] or args['-upload']
    rcf           = args['-rcf']
    drive_id      = args['-id']
    index_link    = args['-index']
    bulk_start    = 0
    bulk_end      = 0
    ratio         = None
    seed_time     = None
    reply_to      = None
    file_         = None
    session       = ''
    
    if not isinstance(seed, bool):
        dargs = seed.split(':')
        ratio = dargs[0] or None
        if len(dargs) == 2:
            seed_time = dargs[1] or None
        seed = True

    if not isinstance(isBulk, bool):
        dargs = isBulk.split(':')
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
        folder_name = f'/{folder_name}'
        if sameDir is None:
            sameDir = {'total': multi, 'tasks': set(), 'name': folder_name}
        sameDir['tasks'].add(message.id)

    if isBulk:
        try:
            bulk = await extract_bulk_links(message, bulk_start, bulk_end)
            if len(bulk) == 0:
                raise ValueError('Bulk Empty!')
        except:
            await sendMessage(message, 'Reply to text file or tg message that have links seperated by new line!')
            return
        b_msg = input_list[:1]
        b_msg.append(f'{bulk[0]} -i {len(bulk)}')
        nextmsg = await sendMessage(message, " ".join(b_msg))
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        nextmsg.from_user = message.from_user
        _mirror_leech(client, nextmsg, isQbit, isLeech, sameDir, bulk)
        return

    if len(bulk) != 0:
        del bulk[0]

    @new_task
    async def __run_multi():
        if multi <= 1:
            return
        await sleep(5)
        if len(bulk) != 0:
            msg = input_list[:1]
            msg.append(f'{bulk[0]} -i {multi - 1}')
            nextmsg = await sendMessage(message, " ".join(msg))
        else:
            msg = [s.strip() for s in input_list]
            index = msg.index('-i')
            msg[index+1] = f"{multi - 1}"
            nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1)
            nextmsg = await sendMessage(nextmsg, " ".join(msg))
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        if folder_name:
            sameDir['tasks'].add(nextmsg.id)
        nextmsg.from_user = message.from_user
        await sleep(5)
        _mirror_leech(client, nextmsg, isQbit, isLeech, sameDir, bulk)

    __run_multi()

    path = f'/usr/src/app/downloads/{message.id}{folder_name}'

    if len(text) > 1 and text[1].startswith('Tag: '):
        tag, id_ = text[1].split('Tag: ')[1].split()
        message.from_user = await client.get_users(id_)
        try:
            await message.unpin()
        except:
            pass
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
            await sendMessage(message, f'ERROR: {e}')
            await delete_links(message)
            return
    elif not link and (reply_to := message.reply_to_message):
        if reply_to.text:
            reply_text = reply_to.text.split('\n', 1)[0].strip()
            if reply_text and is_telegram_link(reply_text):
                try:
                    reply_to, session = await get_tg_link_content(reply_text)
                except Exception as e:
                    await sendMessage(message, f'ERROR: {e}')
                    await delete_links(message)
                    return

    if reply_to:
        file_ = getattr(reply_to, reply_to.media.value) if reply_to.media else None
        if file_ is None:
            reply_text = reply_to.text.split('\n', 1)[0].strip()
            if is_url(reply_text) or is_magnet(reply_text):
                link = reply_text
        elif reply_to.document and (file_.mime_type == 'application/x-bittorrent' or file_.file_name.endswith('.torrent')):
            link = await reply_to.download()
            file_ = None

    if not is_url(link) and not is_magnet(link) and not await aiopath.exists(link) and not is_rclone_path(link) and file_ is None:
        reply_message = await sendMessage(message, MIRROR_HELP_MESSAGE)
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

    if not is_mega_link(link) and not isQbit and not is_magnet(link) and not is_rclone_path(link) \
       and not is_gdrive_link(link) and not link.endswith('.torrent') and file_ is None:
        content_type = await get_content_type(link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            process_msg = await sendMessage(message, f"<b>Processing:</b> <code>{link}</code>")
            try:
                link = await sync_to_async(direct_link_generator, link)
                if not isinstance(link, dict):
                    LOGGER.info(f"Generated link: {link}")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    await editMessage(process_msg, str(e))
                    await delete_links(message)
                    await one_minute_del(process_msg)
                    return
            await deleteMessage(process_msg)

    if not isLeech:
        if config_dict['DEFAULT_UPLOAD'] == 'rc' and not up or up == 'rc':
            up = config_dict['RCLONE_PATH']
        if not up and config_dict['DEFAULT_UPLOAD'] == 'gd':
            up = 'gd'
            user_tds = await fetch_user_tds(message.from_user.id)
            if not drive_id and len(user_tds) == 1:
                drive_id, index_link = next(iter(user_tds.values())).values()
            if drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
                return await sendMessage(message, "Google Drive ID validation failed!!")
        if up == 'gd' and not config_dict['GDRIVE_ID'] and not drive_id:
            await sendMessage(message, 'GDRIVE_ID not Provided!')
            return
        elif not up:
            await sendMessage(message, 'No Rclone Destination!')
            return
        elif up not in ['rcl', 'gd']:
            if up.startswith('mrcc:'):
                config_path = f'tanha/{message.from_user.id}.conf'
            else:
                config_path = 'rcl.conf'
            if not await aiopath.exists(config_path):
                await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
                return
        if up != 'gd' and not is_rclone_path(up):
            await sendMessage(message, 'Wrong Rclone Upload Destination!')
            await delete_links(message)
            return

    if link == 'rcl':
        link = await RcloneList(client, message).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await sendMessage(message, link)
            await delete_links(message)
            return

    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, message).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await sendMessage(message, up)
            await delete_links(message)
            return

    listener = MirrorLeechListener(message, compress, extract, isQbit, isLeech, tag, select, seed, 
                                    sameDir, rcf, up, join, drive_id=drive_id, index_link=index_link, source_url=link)

    if file_ is not None:
        await delete_links(message)
        await TelegramDownloadHelper(listener).add_download(reply_to, f'{path}/', name, session)
    elif isinstance(link, dict):
        await add_direct_download(link, path, listener, name)
    elif is_rclone_path(link):
        if link.startswith('mrcc:'):
            link = link.split('mrcc:', 1)[1]
            config_path = f'tanha/{message.from_user.id}.conf'
        else:
            config_path = 'rcl.conf'
        if not await aiopath.exists(config_path):
            await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
            return
        await add_rclone_download(link, config_path, f'{path}/', name, listener)
    elif is_gdrive_link(link):
        await delete_links(message)
        await add_gd_download(link, path, listener, name)
    elif is_mega_link(link):
        await delete_links(message)
        await add_mega_download(link, f'{path}/', listener, name)
    elif isQbit:
        await add_qb_torrent(link, path, listener, ratio, seed_time)
    else:
        ussr = args['-u'] or args['-user']
        pssw = args['-p'] or args['-pass']
        if ussr or pssw:
            auth = f"{ussr}:{pssw}"
            auth = "Basic " + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        await add_aria2c_download(link, path, listener, name, auth, ratio, seed_time)
    await delete_links(message)


async def mirror(client, message):
    _mirror_leech(client, message)


async def qb_mirror(client, message):
    _mirror_leech(client, message, isQbit=True)


async def leech(client, message):
    _mirror_leech(client, message, isLeech=True)


async def qb_leech(client, message):
    _mirror_leech(client, message, isQbit=True, isLeech=True)


bot.add_handler(MessageHandler(mirror, filters=command(
    BotCommands.MirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_mirror, filters=command(
    BotCommands.QbMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(leech, filters=command(
    BotCommands.LeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_leech, filters=command(
    BotCommands.QbLeechCommand) & CustomFilters.authorized))
