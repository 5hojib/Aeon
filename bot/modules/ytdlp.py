#!/usr/bin/env python3
from asyncio import sleep
from re import split as re_split

from aiofiles.os import path as aiopath
from aiohttp import ClientSession
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from yt_dlp import YoutubeDL

from bot import DOWNLOAD_DIR, IS_PREMIUM_USER, LOGGER, bot, categories, config_dict, user_data
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_rclone_path, is_url, new_task, sync_to_async
from bot.helper.ext_utils.help_messages import YT_HELP_MESSAGE
from bot.helper.jmdkh_utils import none_admin_utils, stop_duplicate_tasks
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import anno_checker, delete_links, editMessage, isAdmin, open_category_btns, sendDmMessage, sendLogMessage, sendMessage

listener_dict = {}


def extract_info(link):
    with YoutubeDL({'usenetrc': True, 'cookiefile': 'cookies.txt', 'playlist_items': '0'}) as ydl:
        result = ydl.extract_info(link, download=False)
        if result is None:
            raise ValueError('Info result is None')
        return result


async def _mdisk(link, name):
    key = link.split('/')[-1]
    async with ClientSession() as session:
        async with session.get(f'https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={key}') as resp:
            if resp.status == 200:
                resp_json = await resp.json()
                link = resp_json['source']
                if not name:
                    name = resp_json['filename']
            return name, link


async def _auto_cancel(msg, task_id):
    await sleep(120)
    try:
        del listener_dict[task_id]
        await editMessage(msg, 'Timed out! Task has been cancelled.')
    except:
        pass


@new_task
async def _ytdl(client, message, isZip=False, isLeech=False, sameDir={}):
    mssg = message.text
    user_id = message.from_user.id
    msg_id = message.id
    qual = ''
    select = False
    multi = 0
    link = ''
    folder_name = ''

    args = mssg.split(maxsplit=3)
    args.pop(0)
    raw_url = None
    drive_id = None
    index_link = None
    if len(args) > 0:
        index = 1
        for x in args:
            x = x.strip()
            if x == 's':
                select = True
                index += 1
            elif x.strip().isdigit():
                multi = int(x)
                mi = index
            elif x.startswith('m:'):
                marg = x.split('m:', 1)
                if len(marg) > 1:
                    folder_name = f"/{marg[1]}"
                    if not sameDir:
                        sameDir = set()
                    sameDir.add(message.id)
            else:
                break
        if multi == 0:
            args = mssg.split(maxsplit=index)
            if len(args) > index:
                x = args[index].strip()
                if not x.startswith(('n:', 'pswd:', 'up:', 'rcf:', 'opt:', 'id:', 'index:')):
                    link = re_split(r' opt: | pswd: | n: | rcf: | up: | id: | index: ', x)[
                        0].strip()

    @new_task
    async def __run_multi():
        if multi <= 1:
            return
        await sleep(4)
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1)
        ymsg = mssg.split(maxsplit=mi+1)
        ymsg[mi] = f"{multi - 1}"
        nextmsg = await sendMessage(nextmsg, " ".join(ymsg))
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        if len(folder_name) > 0:
            sameDir.add(nextmsg.id)
        nextmsg.from_user = message.from_user
        if message.sender_chat:
            nextmsg.sender_chat = message.sender_chat
        await sleep(4)
        _ytdl(client, nextmsg, isZip, isLeech, sameDir)

    path = f'{DOWNLOAD_DIR}{message.id}{folder_name}'

    name = mssg.split(' n: ', 1)
    name = re_split(' pswd: | opt: | up: | rcf: | index: | id: ', name[1])[
        0].strip() if len(name) > 1 else ''

    pswd = mssg.split(' pswd: ', 1)
    pswd = re_split(' n: | opt: | up: | rcf: | index: | id: ', pswd[1])[
        0] if len(pswd) > 1 else None

    opt = mssg.split(' opt: ', 1)
    opt = re_split(' n: | pswd: | up: | rcf: | index: | id: ', opt[1])[
        0].strip() if len(opt) > 1 else ''

    rcf = mssg.split(' rcf: ', 1)
    rcf = re_split(' n: | pswd: | up: | opt: | index: | id: ', rcf[1])[
        0].strip() if len(rcf) > 1 else None

    up = mssg.split(' up: ', 1)
    up = re_split(' n: | pswd: | rcf: | opt: ', up[1])[
        0].strip() if len(up) > 1 else None

    drive_id = mssg.split(' id: ', 1)
    drive_id = re_split(' n: | pswd: | rcf: | opt: | index: ', drive_id[1])[
        0].strip() if len(drive_id) > 1 else None
    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    index_link = mssg.split(' index: ', 1)
    index_link = re_split(' n: | pswd: | rcf: | opt: | id: ', index_link[1])[
        0].strip() if len(index_link) > 1 else None
    if index_link and not index_link.startswith(('http://', 'https://')):
        index_link = None
    if index_link and not index_link.endswith('/'):
        index_link += '/'

    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    if reply_to := message.reply_to_message:
        if len(link) == 0:
            link = reply_to.text.split('\n', 1)[0].strip()
        if sender_chat := reply_to.sender_chat:
            tag = sender_chat.title
        elif not reply_to.from_user.is_bot:
            if username := reply_to.from_user.username:
                tag = f"@{username}"
            else:
                tag = reply_to.from_user.mention

    if not is_url(link):
        await sendMessage(message, YT_HELP_MESSAGE.format_map({'cmd': message.command[0], 'fmg': '{"ffmpeg": ["-threads", "4"]}'}))

        await delete_links(message)
        return
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        await delete_links(message)
        return
    user_id = message.from_user.id
    if not await isAdmin(message):
        raw_url = await stop_duplicate_tasks(message, link)
        if raw_url == 'duplicate_tasks':
            await delete_links(message)
            return
        if await none_admin_utils(message, tag, isLeech):
            return
    if (dmMode := config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
        if isLeech and IS_PREMIUM_USER and not config_dict['DUMP_CHAT']:
            await delete_links(message)
            return await sendMessage(message, 'DM_MODE and User Session need DUMP_CHAT')
        dmMessage = await sendDmMessage(message, dmMode, isLeech)
        if dmMessage == 'BotNotStarted':
            await delete_links(message)
            return
    else:
        dmMessage = None
    logMessage = await sendLogMessage(message, link, tag)

    if not isLeech:
        if config_dict['DEFAULT_UPLOAD'] == 'rc' and up is None or up == 'rc':
            up = config_dict['RCLONE_PATH']
        if up is None and config_dict['DEFAULT_UPLOAD'] == 'gd':
            up = 'gd'
            if not drive_id and len(categories) > 1:
                drive_id, index_link = await open_category_btns(message)
            if drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
                return await sendMessage(message, "Google Drive id validation failed!!")
        if up == 'gd' and not config_dict['GDRIVE_ID'] and not drive_id:
            await sendMessage(message, 'GDRIVE_ID not Provided!')
            return
        elif not up:
            await sendMessage(message, 'No Rclone Destination!')
            return
        elif up not in ['rcl', 'gd']:
            if up.startswith('mrcc:'):
                config_path = f'rclone/{message.from_user.id}.conf'
            else:
                config_path = 'rclone.conf'
            if not await aiopath.exists(config_path):
                await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
                return

    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, message).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await sendMessage(message, up)
            return

    listener = MirrorLeechListener(message, isZip, isLeech=isLeech, pswd=pswd,
                                   tag=tag, sameDir=sameDir, rcFlags=rcf, upPath=up,
                                   raw_url=raw_url, drive_id=drive_id,
                                   index_link=index_link, dmMessage=dmMessage, logMessage=logMessage)
    if 'mdisk.me' in link:
        name, link = await _mdisk(link, name)
    try:
        result = await sync_to_async(extract_info, link)
    except Exception as e:
        msg = str(e).replace('<', ' ').replace('>', ' ')
        await sendMessage(message, f"{tag} {msg}")
        __run_multi()
        return

    __run_multi()

    if not select:
        user_dict = user_data.get(user_id, {})
        if 'format:' in opt:
            opts = opt.split('|')
            for f in opts:
                if f.startswith('format:'):
                    qual = f.split('format:', 1)[1]
                    break
        elif user_dict.get('yt_ql'):
            qual = user_dict['yt_ql']
        else:
            qual = config_dict.get('YT_DLP_QUALITY')

    if qual:
        playlist = 'entries' in result
        LOGGER.info(f"Downloading with YT-DLP: {link} added by : {user_id}")
        ydl = YoutubeDLHelper(listener)
        await ydl.add_download(link, path, name, qual, playlist, opt)
    else:
        buttons = ButtonMaker()
        best_video = "bv*+ba/b"
        best_audio = "ba/b"
        formats_dict = {}
        if 'entries' in result:
            for i in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
                video_format = f"bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]"
                b_data = f"{i}|mp4"
                formats_dict[b_data] = video_format
                buttons.ibutton(f"{i}-mp4", f"qu {msg_id} {b_data} t")
                video_format = f"bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]"
                b_data = f"{i}|webm"
                formats_dict[b_data] = video_format
                buttons.ibutton(f"{i}-webm", f"qu {msg_id} {b_data} t")
            buttons.ibutton("MP3", f"qu {msg_id} mp3 t")
            buttons.ibutton("Best Videos", f"qu {msg_id} {best_video} t")
            buttons.ibutton("Best Audios", f"qu {msg_id} {best_audio} t")
            buttons.ibutton("Cancel", f"qu {msg_id} cancel")
            mbuttons = buttons.build_menu(3)
            bmsg = await sendMessage(message, 'Choose Playlist Videos Quality:', mbuttons)
        else:
            formats = result.get('formats')
            is_m4a = False
            if formats is not None:
                for frmt in formats:
                    if frmt.get('tbr'):

                        format_id = frmt['format_id']

                        if frmt.get('filesize'):
                            size = frmt['filesize']
                        elif frmt.get('filesize_approx'):
                            size = frmt['filesize_approx']
                        else:
                            size = 0

                        if frmt.get('video_ext') == 'none' and frmt.get('acodec') != 'none':
                            if frmt.get('audio_ext') == 'm4a':
                                is_m4a = True
                            b_name = f"{frmt['acodec']}-{frmt['ext']}"
                            v_format = f"ba[format_id={format_id}]"
                        elif frmt.get('height'):
                            height = frmt['height']
                            ext = frmt['ext']
                            fps = frmt['fps'] if frmt.get('fps') else ''
                            b_name = f"{height}p{fps}-{ext}"
                            ba_ext = '[ext=m4a]' if is_m4a and ext == 'mp4' else ''
                            v_format = f"bv*[format_id={format_id}]+ba{ba_ext}/b[height=?{height}]"
                        else:
                            continue

                        formats_dict.setdefault(b_name, {})[str(frmt['tbr'])] = [
                            size, v_format]

                for b_name, tbr_dict in formats_dict.items():
                    if len(tbr_dict) == 1:
                        tbr, v_list = next(iter(tbr_dict.items()))
                        buttonName = f"{b_name} ({get_readable_file_size(v_list[0])})"
                        buttons.ibutton(
                            buttonName, f"qu {msg_id} {b_name}|{tbr}")
                    else:
                        buttons.ibutton(b_name, f"qu {msg_id} dict {b_name}")
            buttons.ibutton("MP3", f"qu {msg_id} mp3")
            buttons.ibutton("Best Video", f"qu {msg_id} {best_video}")
            buttons.ibutton("Best Audio", f"qu {msg_id} {best_audio}")
            buttons.ibutton("Cancel", f"qu {msg_id} cancel")
            mbuttons = buttons.build_menu(2)
            bmsg = await sendMessage(message, 'Choose Video Quality:', mbuttons)

        listener_dict[msg_id] = [listener, user_id, link,
                                 name, mbuttons, opt, formats_dict, path]
        await _auto_cancel(bmsg, msg_id)


async def _qual_subbuttons(task_id, b_name, msg):
    buttons = ButtonMaker()
    tbr_dict = listener_dict[task_id][6][b_name]
    for tbr, d_data in tbr_dict.items():
        button_name = f"{tbr}K ({get_readable_file_size(d_data[0])})"
        buttons.ibutton(button_name, f"qu {task_id} {b_name}|{tbr}")
    buttons.ibutton("Back", f"qu {task_id} back")
    buttons.ibutton("Cancel", f"qu {task_id} cancel")
    subbuttons = buttons.build_menu(2)
    await editMessage(msg, f"Choose Bit rate for <b>{b_name}</b>:", subbuttons)


async def _mp3_subbuttons(task_id, msg, playlist=False):
    buttons = ButtonMaker()
    audio_qualities = [64, 128, 320]
    for q in audio_qualities:
        if playlist:
            i = 's'
            audio_format = f"ba/b-{q} t"
        else:
            i = ''
            audio_format = f"ba/b-{q}"
        buttons.ibutton(f"{q}K-mp3", f"qu {task_id} {audio_format}")
    buttons.ibutton("Back", f"qu {task_id} back")
    buttons.ibutton("Cancel", f"qu {task_id} cancel")
    subbuttons = buttons.build_menu(2)
    await editMessage(msg, f"Choose Audio{i} Bitrate:", subbuttons)


@new_task
async def select_format(client, query):
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    task_id = int(data[1])
    try:
        task_info = listener_dict[task_id]
    except:
        await editMessage(message, "This is an old task")
        return
    uid = task_info[1]
    if user_id != uid and not await CustomFilters.sudo(client, query):
        await query.answer(text="This task is not for you!", show_alert=True)
        return
    elif data[2] == "dict":
        await query.answer()
        b_name = data[3]
        await _qual_subbuttons(task_id, b_name, message)
        return
    elif data[2] == "back":
        await query.answer()
        await editMessage(message, 'Choose Video Quality:', task_info[4])
        return
    elif data[2] == "mp3":
        await query.answer()
        playlist = len(data) == 4
        await _mp3_subbuttons(task_id, message, playlist)
        return
    elif data[2] == "cancel":
        await query.answer()
        await editMessage(message, 'Task has been cancelled.')
        del listener_dict[task_id]
    else:
        await query.answer()
        listener = task_info[0]
        link = task_info[2]
        name = task_info[3]
        opt = task_info[5]
        qual = data[2]
        path = task_info[7]
        if len(data) == 4:
            playlist = True
            if '|' in qual:
                qual = task_info[6][qual]
        else:
            playlist = False
            if '|' in qual:
                b_name, tbr = qual.split('|')
                qual = task_info[6][b_name][tbr][1]
        LOGGER.info(f"Downloading with YT-DLP: {link} added by : {user_id}")
        await message.delete()
        del listener_dict[task_id]
        ydl = YoutubeDLHelper(listener)
        await ydl.add_download(link, path, name, qual, playlist, opt)


async def ytdl(client, message):
    _ytdl(client, message)


async def ytdlZip(client, message):
    _ytdl(client, message, True)


async def ytdlleech(client, message):
    _ytdl(client, message, isLeech=True)


async def ytdlZipleech(client, message):
    _ytdl(client, message, True, True)

bot.add_handler(MessageHandler(ytdl, filters=command(
    BotCommands.YtdlCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlZip, filters=command(
    BotCommands.YtdlZipCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlleech, filters=command(
    BotCommands.YtdlLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlZipleech, filters=command(
    BotCommands.YtdlZipLeechCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(select_format, filters=regex("^qu")))