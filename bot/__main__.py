#!/usr/bin/env python3
import platform
from time import time
from datetime import datetime
from sys import executable
from os import execl as osexecl
from asyncio import create_subprocess_exec, gather
from uuid import uuid4
from base64 import b64decode
from quoters import Quote
from html import escape
from cloudscraper import create_scraper

from requests import get as rget
from pytz import timezone
from bs4 import BeautifulSoup
from signal import signal, SIGINT
from aiofiles.os import path as aiopath, remove as aioremove
from aiofiles import open as aiopen
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, cpu_freq, virtual_memory, net_io_counters, boot_time
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, private, regex
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, config_dict, user_data, botStartTime, LOGGER, Interval, DATABASE_URL, QbInterval, INCOMPLETE_TASK_NOTIFIER, scheduler, bot_name
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.bot_utils import get_progress_bar_string, get_readable_file_size, get_readable_time, cmd_exec, sync_to_async, set_commands, update_user_ldata, new_thread, format_validity_time, new_task
from .helper.ext_utils.db_handler import DbManager
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile, deleteMessage, one_minute_del
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.listeners.aria2_listener import start_aria2_listener
from .modules import authorize, cancel_mirror, mirror_leech, status, torrent_search, torrent_select, ytdlp, rss, shell, eval, users_settings, bot_settings, speedtest, images, mediainfo, broadcast
from .helper.mirror_utils.gdrive_utils import count, delete, list, clone

@new_thread
async def stats(_, message):
    total, used, free, disk = disk_usage('/')
    memory = virtual_memory()
    currentTime = get_readable_time(time() - botStartTime)
    osUptime = get_readable_time(time() - boot_time())
    cpuUsage = cpu_percent(interval=0.5)
    quote = Quote.print().split('―', 1)[0].strip().replace("“", "").replace("”", "")
    limit_mapping = {
        'Torrent':    config_dict.get('TORRENT_LIMIT', '∞'),
        'Gdrive':     config_dict.get('GDRIVE_LIMIT', '∞'),
        'Ytdlp':      config_dict.get('YTDLP_LIMIT', '∞'),
        'Direct':     config_dict.get('DIRECT_LIMIT', '∞'),
        'Leech':      config_dict.get('LEECH_LIMIT', '∞'),
        'Clone':      config_dict.get('CLONE_LIMIT', '∞'),
        'Mega':       config_dict.get('MEGA_LIMIT', '∞'),
        'User tasks': config_dict.get('USER_MAX_TASKS', '∞'),
    }
    system_info = f'<b>{quote}</b>\n\n'\
        f'<code>• Bot uptime :</code> {currentTime}\n'\
        f'<code>• Sys uptime :</code> {osUptime}\n'\
        f'<code>• CPU usage  :</code> {cpuUsage}%\n'\
        f'<code>• RAM usage  :</code> {memory.percent}%\n'\
        f'<code>• Disk usage :</code> {disk}%\n'\
        f'<code>• Disk space :</code> {get_readable_file_size(free)}/{get_readable_file_size(total)}\n\n'
            
    limitations = f'<b>LIMITATIONS</b>\n\n'
    
    for k, v in limit_mapping.items():
        if v == '':
            v = '∞'
        elif k != 'User tasks':
            v = f'{v}GB/Link'
        else:
            v = f'{v} Tasks/user'
        limitations += f'<code>• {k:<11}:</code> {v}\n'

    stats = system_info + limitations
    reply_message = await sendMessage(message, stats, photo='IMAGES')
    await deleteMessage(message)
    await one_minute_del(reply_message)

@new_thread
async def start(_, message):
    buttons = ButtonMaker()
    reply_markup = buttons.build_menu(2)
    if len(message.command) > 1 and message.command[1] == "wzmlx":
        await deleteMessage(message)
    elif len(message.command) > 1 and len(message.command[1]) == 36:
        userid = message.from_user.id
        input_token = message.command[1]
        if DATABASE_URL:
            stored_token = await DbManager().get_user_token(userid)
            if stored_token is None:
                return await sendMessage(message, '<b>This token is not for you!</b>\n\nPlease generate your own.')
            if input_token != stored_token:
                return await sendMessage(message, 'Invalid token.\n\nPlease generate a new one.')
        if userid not in user_data:
            return await sendMessage(message, 'This token is not yours!\n\nKindly generate your own.')
        data = user_data[userid]
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, '<b>This token has already been used!</b>\n\nPlease get a new one.')
        token = str(uuid4())
        token_time = time()
        data['token'] = token
        data['time'] = token_time
        user_data[userid].update(data)
        if DATABASE_URL:
            await DbManager().update_user_tdata(userid, token, token_time)
        msg = 'Your token has been successfully generated!\n\n'
        msg += f'It will be valid for {format_validity_time(int(config_dict["TOKEN_TIMEOUT"]))}'
        return await sendMessage(message, msg)
    elif await CustomFilters.authorized(client, message):
        help_command = f"/{BotCommands.HelpCommand}"
        start_string = f'This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram.\n<b>Type {help_command} to get a list of available commands</b>'
        await sendMessage(message, start_string, photo='IMAGES')
    elif config_dict['BOT_PM']:
        await sendMessage(message, 'Now, This bot will send all your files and links here. Start Using ...', photo='IMAGES')
    else:
        await sendMessage(message, 'You Are not authorized user!', photo='IMAGES')
    await DbManager().update_pm_users(message.from_user.id)


async def restart(client, message):
    restart_message = await sendMessage(message, 'Restarting...')
    if scheduler.running:
        scheduler.shutdown(wait=False)
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', '-e', 'gunicorn|buffet|openstack|render|zcl')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, 'Starting ping...')
    end_time = int(round(time() * 1000))
    value=(end_time - start_time)
    await editMessage(reply, f'{value} ms.')


@new_task
async def wzmlxcb(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="This message not your's!", show_alert=True)
    elif data[2] == "logdisplay":
        await query.answer()
        async with aiopen('log.txt', 'r') as f:
            logFileLines = (await f.read()).splitlines()
        def parseline(line):
            try:
                return "[" + line.split('] [', 1)[1]
            except IndexError:
                return line
        ind, Loglines = 1, ''
        try:
            while len(Loglines) <= 3500:
                Loglines = parseline(logFileLines[-ind]) + '\n' + Loglines
                if ind == len(logFileLines): 
                    break
                ind += 1
            startLine = f"<b>Showing Last {ind} Lines from log.txt:</b> \n\n----------<b>START LOG</b>----------\n\n"
            endLine = "\n----------<b>END LOG</b>----------"
            btn = ButtonMaker()
            btn.ibutton('Close', f'wzmlx {user_id} close')
            reply_message = await sendMessage(message, startLine + escape(Loglines) + endLine, btn.build_menu(1))
            await query.edit_message_reply_markup(None)
            await deleteMessage(message)
            await one_minute_del(reply_message)
        except Exception as err:
            LOGGER.error(f"TG Log Display : {str(err)}")
    elif data[2] == "webpaste":
        await query.answer()
        async with aiopen('log.txt', 'r') as f:
            logFile = await f.read()
        cget = create_scraper().request
        resp = cget('POST', 'http://stashbin.xyz/api/document', data={'content': logFile}).json()
        if resp['ok']:
            btn = ButtonMaker()
            btn.ubutton('Web Paste', f"http://stashbin.xyz/{resp['data']['key']}")
            await query.edit_message_reply_markup(btn.build_menu(1))
    elif data[2] == "botpm":
        await query.answer(url=f"https://t.me/{bot_name}?start=wzmlx")
    else:
        await query.answer()
        await deleteMessage(message)
    
@new_task
async def log(_, message):
    buttons = ButtonMaker()
    buttons.ibutton('Log Display', f'wzmlx {message.from_user.id} logdisplay')
    buttons.ibutton('Web Paste', f'wzmlx {message.from_user.id} webpaste')
    reply_message = await sendFile(message, 'log.txt', buttons=buttons.build_menu(1))
    await deleteMessage(message)
    await one_minute_del(reply_message)

async def search_images():
    if not config_dict['IMG_SEARCH']:
        return
    try:
        query_list = config_dict['IMG_SEARCH']
        total_pages = config_dict['IMG_PAGE']
        base_url = "https://www.wallpaperflare.com/search"

        for query in query_list:
            query = query.strip().replace(" ", "+")
            for page in range(1, total_pages + 1):
                url = f"{base_url}?wallpaper={query}&width=1280&height=720&page={page}"
                r = rget(url)
                soup = BeautifulSoup(r.text, "html.parser")
                images = soup.select('img[data-src^="https://c4.wallpaperflare.com/wallpaper"]')
                for img in images:
                    img_url = img['data-src']
                    if img_url not in config_dict['IMAGES']:
                        config_dict['IMAGES'].append(img_url)
            if DATABASE_URL:
                await DbManager().update_config({'IMAGES': config_dict['IMAGES']})
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")


help_string = f'''
NOTE: Try each command without any arguments to see more details.
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Starts mirroring to Google Drive.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Starts mirroring to Google Drive using qBittorrent.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirrors links supported by yt-dlp.
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Starts leeching to Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Starts leeching using qBittorrent.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leeches links supported by yt-dlp.
/{BotCommands.CloneCommand} [drive_url]: Copies files/folders to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Counts files/folders in Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Deletes files/folders from Google Drive (Only Owner & Sudo).
/{BotCommands.UserSetCommand} [query]: User settings.
/{BotCommands.BotSetCommand} [query]: Bot settings.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CancelMirror}: Cancels task by gid or reply.
/{BotCommands.CancelAllCommand} [query]: Cancels all [status] tasks.
/{BotCommands.ListCommand} [query]: Searches in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Searches for torrents with API.
/{BotCommands.StatusCommand}: Shows status of all downloads.
/{BotCommands.StatsCommand}: Shows stats of the machine hosting the bot.
/{BotCommands.PingCommand}: Checks how long it takes to ping the bot (Only Owner & Sudo).
/{BotCommands.AuthorizeCommand}: Authorizes a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorizes a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UsersCommand}: Shows user settings (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Adds sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Removes sudo users (Only Owner).
/{BotCommands.RestartCommand}: Restarts and updates the bot (Only Owner & Sudo).
/{BotCommands.LogCommand}: Gets a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).
/{BotCommands.ShellCommand}: Runs shell commands (Only Owner).
/{BotCommands.EvalCommand}: Runs Python code line or lines (Only Owner).
/{BotCommands.ExecCommand}: Runs commands in Exec (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clears {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
/{BotCommands.RssCommand}: RSS Menu.
'''

@new_task
async def bot_help(client, message):
    reply_message = await sendMessage(message, help_string)
    await deleteMessage(message)
    await one_minute_del(reply_message)


async def restart_notification():
    now = datetime.now(timezone('Asia/Dhaka'))
    date = now.strftime('%d/%m/%y')
    time = now.strftime('%I:%M:%S %p')
    rmsg = f'Restarted Successfully!\n\n<b>Date:</b> {date}\n<b>Time:</b> {time}'
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith(rmsg):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True, disable_notification=True)
        except Exception as e:
            LOGGER.error(e)

    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManager().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = rmsg if cid == chat_id else 'Bot restarted!'
                for tag, links in data.items():
                    msg += f"\n\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=rmsg)
        except:
            pass
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), search_images(), set_commands(bot))
    await sync_to_async(start_aria2_listener, wait=False)
    
    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand) & private))
    #bot.add_handler(CallbackQueryHandler(token_callback, filters=regex(r'^pass')))
    bot.add_handler(MessageHandler(log, filters=command(
        BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(
        BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(
        BotCommands.PingCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(bot_help, filters=command(
        BotCommands.HelpCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(stats, filters=command(
        BotCommands.StatsCommand) & CustomFilters.authorized))
    bot.add_handler(CallbackQueryHandler(wzmlxcb, filters=regex(r'^wzmlx')))
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()