#!/usr/bin/env python3
from asyncio import Event, sleep, wait_for, wrap_future
from functools import partial
from re import split as re_split
from time import time

from aiofiles.os import path as aiopath
from aiohttp import ClientSession
from pyrogram.filters import command, regex, user
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from yt_dlp import YoutubeDL

from bot import (DOWNLOAD_DIR, IS_PREMIUM_USER, LOGGER, bot, config_dict, categories_dict,
                 user_data)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            get_readable_time, is_gdrive_link,
                                            is_rclone_path, is_url, new_task,
                                            new_thread, sync_to_async)
from bot.helper.ext_utils.help_messages import YT_HELP_MESSAGE
from bot.helper.jmdkh_utils import none_admin_utils, stop_duplicate_tasks
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (auto_delete_message, anno_checker,
                                                      delete_links,
                                                      editMessage, isAdmin,
                                                      isBot_canDm,
                                                      open_category_btns,
                                                      request_limiter,
                                                      sendLogMessage,
                                                      sendMessage)
from bot.helper.ext_utils.bulk_links import extract_bulk_links


@new_task
async def select_format(client, query, obj):
    data = query.data.split()
    message = query.message
    await query.answer()

    if data[1] == 'dict':
        b_name = data[2]
        await obj.qual_subbuttons(b_name)
    elif data[1] == 'mp3':
        await obj.mp3_subbuttons()
    elif data[1] == 'audio':
        await obj.audio_format()
    elif data[1] == 'aq':
        if data[2] == 'back':
            await obj.audio_format()
        else:
            await obj.audio_quality(data[2])
    elif data[1] == 'back':
        await obj.back_to_main()
    elif data[1] == 'cancel':
        await editMessage(message, 'Task has been cancelled.')
        obj.qual = None
        obj.is_cancelled = True
        obj.event.set()
    else:
        if data[1] == 'sub':
            obj.qual = obj.formats[data[2]][data[3]][1]
        elif '|' in data[1]:
            obj.qual = obj.formats[data[1]]
        else:
            obj.qual = data[1]
        obj.event.set()


class YtSelection:
    def __init__(self, client, message):
        self.__message = message
        self.__user_id = message.from_user.id
        self.__client = client
        self.__is_m4a = False
        self.__reply_to = None
        self.__time = time()
        self.__timeout = 120
        self.__is_playlist = False
        self.is_cancelled = False
        self.__main_buttons = None
        self.event = Event()
        self.formats = {}
        self.qual = None

    @new_thread
    async def __event_handler(self):
        pfunc = partial(select_format, obj=self)
        handler = self.__client.add_handler(CallbackQueryHandler(
            pfunc, filters=regex('^ytq') & user(self.__user_id)), group=-1)
        try:
            await wait_for(self.event.wait(), timeout=self.__timeout)
        except:
            await editMessage(self.__reply_to, 'Timed Out. Task has been cancelled!')
            self.qual = None
            self.is_cancelled = True
            self.event.set()
        finally:
            self.__client.remove_handler(*handler)

    async def get_quality(self, result):
        future = self.__event_handler()
        buttons = ButtonMaker()
        if 'entries' in result:
            self.__is_playlist = True
            for i in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
                video_format = f'bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]'
                b_data = f'{i}|mp4'
                self.formats[b_data] = video_format
                buttons.ibutton(f'{i}-mp4', f'ytq {b_data}')
                video_format = f'bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]'
                b_data = f'{i}|webm'
                self.formats[b_data] = video_format
                buttons.ibutton(f'{i}-webm', f'ytq {b_data}')
            buttons.ibutton('MP3', 'ytq mp3')
            buttons.ibutton('Audio Formats', 'ytq audio')
            buttons.ibutton('Best Videos', 'ytq bv*+ba/b')
            buttons.ibutton('Best Audios', 'ytq ba/b')
            buttons.ibutton('Cancel', 'ytq cancel', 'footer')
            self.__main_buttons = buttons.build_menu(3)
            msg = f'Choose Playlist Videos Quality:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        else:
            format_dict = result.get('formats')
            if format_dict is not None:
                for item in format_dict:
                    if item.get('tbr'):
                        format_id = item['format_id']

                        if item.get('filesize'):
                            size = item['filesize']
                        elif item.get('filesize_approx'):
                            size = item['filesize_approx']
                        else:
                            size = 0

                        if item.get('video_ext') == 'none' and item.get('acodec') != 'none':
                            if item.get('audio_ext') == 'm4a':
                                self.__is_m4a = True
                            b_name = f"{item['acodec']}-{item['ext']}"
                            v_format = f'ba[format_id={format_id}]'
                        elif item.get('height'):
                            height = item['height']
                            ext = item['ext']
                            fps = item['fps'] if item.get('fps') else ''
                            b_name = f'{height}p{fps}-{ext}'
                            ba_ext = '[ext=m4a]' if self.__is_m4a and ext == 'mp4' else ''
                            v_format = f'bv*[format_id={format_id}]+ba{ba_ext}/b[height=?{height}]'
                        else:
                            continue

                        self.formats.setdefault(b_name, {})[f"{item['tbr']}"] = [
                            size, v_format]

                for b_name, tbr_dict in self.formats.items():
                    if len(tbr_dict) == 1:
                        tbr, v_list = next(iter(tbr_dict.items()))
                        buttonName = f'{b_name} ({get_readable_file_size(v_list[0])})'
                        buttons.ibutton(buttonName, f'ytq sub {b_name} {tbr}')
                    else:
                        buttons.ibutton(b_name, f'ytq dict {b_name}')
            buttons.ibutton('MP3', 'ytq mp3')
            buttons.ibutton('Audio Formats', 'ytq audio')
            buttons.ibutton('Best Video', 'ytq bv*+ba/b')
            buttons.ibutton('Best Audio', 'ytq ba/b')
            buttons.ibutton('Cancel', 'ytq cancel', 'footer')
            self.__main_buttons = buttons.build_menu(2)
            msg = f'Choose Video Quality:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        self.__reply_to = await sendMessage(self.__message, msg, self.__main_buttons)
        await wrap_future(future)
        if not self.is_cancelled:
            await self.__reply_to.delete()
        return self.qual

    async def back_to_main(self):
        if self.__is_playlist:
            msg = f'Choose Playlist Videos Quality:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        else:
            msg = f'Choose Video Quality:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        await editMessage(self.__reply_to, msg, self.__main_buttons)

    async def qual_subbuttons(self, b_name):
        buttons = ButtonMaker()
        tbr_dict = self.formats[b_name]
        for tbr, d_data in tbr_dict.items():
            button_name = f'{tbr}K ({get_readable_file_size(d_data[0])})'
            buttons.ibutton(button_name, f'ytq sub {b_name} {tbr}')
        buttons.ibutton('Back', 'ytq back', 'footer')
        buttons.ibutton('Cancel', 'ytq cancel', 'footer')
        subbuttons = buttons.build_menu(2)
        msg = f'Choose Bit rate for <b>{b_name}</b>:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        await editMessage(self.__reply_to, msg, subbuttons)

    async def mp3_subbuttons(self):
        i = 's' if self.__is_playlist else ''
        buttons = ButtonMaker()
        audio_qualities = [64, 128, 320]
        for q in audio_qualities:
            audio_format = f'ba/b-mp3-{q}'
            buttons.ibutton(f'{q}K-mp3', f'ytq {audio_format}')
        buttons.ibutton('Back', 'ytq back')
        buttons.ibutton('Cancel', 'ytq cancel')
        subbuttons = buttons.build_menu(3)
        msg = f'Choose mp3 Audio{i} Bitrate:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        await editMessage(self.__reply_to, msg, subbuttons)

    async def audio_format(self):
        i = 's' if self.__is_playlist else ''
        buttons = ButtonMaker()
        for frmt in ['aac', 'alac', 'flac', 'm4a', 'opus', 'vorbis', 'wav']:
            audio_format = f'ba/b-{frmt}-'
            buttons.ibutton(frmt, f'ytq aq {audio_format}')
        buttons.ibutton('Back', 'ytq back', 'footer')
        buttons.ibutton('Cancel', 'ytq cancel', 'footer')
        subbuttons = buttons.build_menu(3)
        msg = f'Choose Audio{i} Format:\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        await editMessage(self.__reply_to, msg, subbuttons)

    async def audio_quality(self, format):
        i = 's' if self.__is_playlist else ''
        buttons = ButtonMaker()
        for qual in range(11):
            audio_format = f'{format}{qual}'
            buttons.ibutton(qual, f'ytq {audio_format}')
        buttons.ibutton('Back', 'ytq aq back')
        buttons.ibutton('Cancel', 'ytq aq cancel')
        subbuttons = buttons.build_menu(5)
        msg = f'Choose Audio{i} Qaulity:\n0 is best and 10 is worst\nTimeout: {get_readable_time(self.__timeout-(time()-self.__time))}'
        await editMessage(self.__reply_to, msg, subbuttons)


def extract_info(link, options):
    with YoutubeDL(options) as ydl:
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


@new_task
async def _ytdl(client, message, isZip=False, isLeech=False, sameDir=None, bulk=[]):
    mssg = message.text
    qual = ''
    select = False
    multi = 0
    link = ''
    folder_name = ''
    bulk_start = 0
    bulk_end = 0
    is_bulk = False
    index = 1

    args = mssg.split(maxsplit=4)
    args.pop(0)
    raw_url = None
    drive_id = None
    index_link = None
    if len(args) > 0:
        for x in args:
            x = x.strip()
            if x == 's':
                select = True
                index += 1
            elif x.strip().isdigit():
                multi = int(x)
                mi = index
                index += 1
            elif x.startswith('m:'):
                marg = x.split('m:', 1)
                index += 1
                if len(marg) > 1:
                    folder_name = f'/{marg[1]}'
            elif x == 'b':
                is_bulk = True
                bi = index
                index += 1
            elif x.startswith('b:'):
                is_bulk = True
                bi = index
                index += 1
                dargs = x.split(':')
                bulk_start = dargs[1] or 0
                if len(dargs) == 3:
                    bulk_end = dargs[2] or 0
            else:
                break
        if multi == 0 or len(bulk) != 0:
            args = mssg.split(maxsplit=index)
            if len(args) > index:
                x = args[index].strip()
                if not x.startswith(('n:', 'pswd:', 'up:', 'rcf:', 'opt:', 'id:', 'index:')):
                    link = re_split(r' opt: | pswd: | n: | rcf: | up: | id: | index: ', x)[
                        0].strip()

        if len(folder_name) > 0 and not is_bulk:
            if sameDir is None:
                sameDir = {'total': multi, 'tasks': set()}
            sameDir['tasks'].add(message.id)
  
    if is_bulk:
        bulk = await extract_bulk_links(message, bulk_start, bulk_end)
        if len(bulk) == 0:
            await sendMessage(message, 'Reply to text file or to tg message that have links seperated by new line!')
            return
        b_msg = mssg.split(maxsplit=index)
        b_msg[bi] = f'{len(bulk)}'
        b_msg.insert(index, bulk[0])
        nextmsg = await sendMessage(message, " ".join(b_msg))
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        nextmsg.from_user = message.from_user
        _ytdl(client, nextmsg, isZip, isLeech, sameDir, bulk)
        return

    if len(bulk) != 0:
        del bulk[0]

    @new_task
    async def __run_multi():
        if multi <= 1:
            return
        await sleep(1)
        ymsg = mssg.split(maxsplit=index)
        ymsg[mi] = f'{multi - 1}'
        if len(bulk) != 0:
            ymsg[index] = bulk[0]
            nextmsg = await sendMessage(message, " ".join(ymsg))
        else:
            nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1)
            nextmsg = await sendMessage(nextmsg, ' '.join(ymsg))
            nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        if len(folder_name) > 0:
            sameDir['tasks'].add(nextmsg.id)
        nextmsg.from_user = message.from_user
        if message.sender_chat:
            nextmsg.sender_chat = message.sender_chat
        await sleep(1)
        _ytdl(client, nextmsg, isZip, isLeech, sameDir, bulk)

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
    up = re_split(' n: | pswd: | rcf: | opt: | index: | id: ', up[1])[
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

    opt = opt or config_dict['YT_DLP_OPTIONS']

    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f'@{username}'
    else:
        tag = message.from_user.mention

    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.split('\n', 1)[0].strip()

    if not is_url(link):
        reply_message = await sendMessage(message, YT_HELP_MESSAGE.format_map({'cmd': message.command[0], 'fmg': '{"ffmpeg": ["-threads", "4"]}'}))
        await auto_delete_message(message, reply_message)
        await delete_links(message)
        return
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        await delete_links(message)
        return
    user_id = message.from_user.id
    error_msg = []
    error_button = None
    if not await isAdmin(message):
        if await request_limiter(message):
            await delete_links(message)
            return
        raw_url = await stop_duplicate_tasks(message, link)
        if raw_url == 'duplicate_tasks':
            await delete_links(message)
            return
        none_admin_msg, error_button = await none_admin_utils(message, isLeech)
        if none_admin_msg:
            error_msg.extend(none_admin_msg)
    if (dmMode := config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
        if isLeech and IS_PREMIUM_USER and not config_dict['DUMP_CHAT_ID']:
            error_msg.append('DM_MODE and User Session need DUMP_CHAT_ID')
        dmMessage, error_button = await isBot_canDm(message, dmMode, isLeech, error_button)
        if dmMessage is not None and dmMessage != 'BotStarted':
            error_msg.append(dmMessage)
    else:
        dmMessage = None
    if error_msg:
        final_msg = f'Hey, <b>{tag}</b>,\n'
        for __i, __msg in enumerate(error_msg, 1):
            final_msg += f'\n<b>{__i}</b>: {__msg}\n'
        if error_button is not None:
            error_button = error_button.build_menu(2)
        await delete_links(message)
        await sendMessage(message, final_msg, error_button)
        return
    logMessage = await sendLogMessage(message, link, tag)

    if not isLeech:
        if config_dict['DEFAULT_UPLOAD'] == 'rc' and up is None or up == 'rc':
            up = config_dict['RCLONE_PATH']
        if up is None and config_dict['DEFAULT_UPLOAD'] == 'gd':
            up = 'gd'
            if not drive_id and len(categories_dict) > 1:
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
                await sendMessage(message, f'Rclone Config: {config_path} not Exists!')
                return
        if up != 'gd' and not is_rclone_path(up):
            await sendMessage(message, 'Wrong Rclone Upload Destination!')
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

    options = {'usenetrc': True, 'cookiefile': 'cookies.txt'}
    if opt:
        yt_opt = opt.split('|')
        for ytopt in yt_opt:
            key, value = map(str.strip, ytopt.split(':', 1))
            if value.startswith('^'):
                if '.' in value or value == '^inf':
                    value = float(value.split('^')[1])
                else:
                    value = int(value.split('^')[1])
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.startswith(('{', '[', '(')) and value.endswith(('}', ']', ')')):
                value = eval(value)
            options[key] = value

        options['playlist_items'] = '0'

    try:
        result = await sync_to_async(extract_info, link, options)
    except Exception as e:
        msg = str(e).replace('<', ' ').replace('>', ' ')
        await sendMessage(message, f'{tag} {msg}')
        __run_multi()
        return

    __run_multi()

    if not select:
        user_dict = user_data.get(user_id, {})
        if 'format' in options:
            qual = options['format']
        elif user_dict.get('yt_opt'):
            qual = user_dict['yt_opt']

    if not qual:
        qual = await YtSelection(client, message).get_quality(result)
        if qual is None:
            return
    LOGGER.info(f"Downloading with YT-DLP: {link} added by : {user_id}")
    playlist = 'entries' in result
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
