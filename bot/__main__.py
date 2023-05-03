#!/usr/bin/env python3
from asyncio import create_subprocess_exec, gather
from os import execl as osexecl
from signal import SIGINT, signal
from sys import executable
from time import time
from uuid import uuid4

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from psutil import boot_time, cpu_count, cpu_percent, disk_usage, net_io_counters, swap_memory, virtual_memory
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import DATABASE_URL, INCOMPLETE_TASK_NOTIFIER, LOGGER, STOP_DUPLICATE_TASKS, Interval, QbInterval, bot, user_data, botStartTime, config_dict, scheduler, alive

from bot.helper.listeners.aria2_listener import start_aria2_listener
from .helper.ext_utils.bot_utils import cmd_exec, get_readable_file_size, get_readable_time, set_commands, sync_to_async
from .helper.ext_utils.db_handler import DbManger
from .helper.ext_utils.fs_utils import clean_all, exit_clean_up, start_cleanup
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import editMessage, sendFile, sendMessage
from .modules import anonymous, authorize, bot_settings, cancel_mirror, category_select, clone, eval, gd_count, gd_delete, gd_list, leech_del, mirror_leech, rmdb, rss, save_message, shell, status, torrent_search, torrent_select, users_settings, ytdlp

start_aria2_listener()

async def stats(client, message):
    total, used, free, disk = disk_usage('/')
    memory = virtual_memory()
    currentTime = get_readable_time(time() - botStartTime)
    mem_p = memory.percent
    osUptime = get_readable_time(time() - boot_time())
    cpuUsage = cpu_percent(interval=0.5)
    if await aiopath.exists('.git'):
        commit_id = (await cmd_exec("git log -1 --pretty=format:'%h'", True))[0]
        commit_from = (await cmd_exec("git log -1 --date=short --pretty=format:'%cr'", True))[0]
        commit_date = (await cmd_exec("git log -1 --date=format:'%d %B %Y' --pretty=format:'%ad'", True))[0]
        commit_time = (await cmd_exec("git log -1 --date=format:'%I:%M:%S %p' --pretty=format:'%ad'", True))[0]
        commit_name = (await cmd_exec("git log -1 --pretty=format:'%s%n%b'", True))[0]
    stats = f'<b><u>REPOSITORY INFO</u></b>\n\n' \
            f'<b>• Last commit: </b>{commit_id}\n'\
            f'<b>• Commit date:</b> {commit_date}\n'\
            f'<b>• Commited on: </b>{commit_time}\n'\
            f'<b>• From now: </b>{commit_from}\n'\
            f'<b>• Changelog: </b>{commit_name}\n'\
            f'\n'\
            f'<b><u>SYSTEM INFO</u></b>\n\n'\
            f'<b>• Bot uptime:</b> {currentTime}\n'\
            f'<b>• System uptime:</b> {osUptime}\n'\
            f'<b>• CPU usage:</b> {cpuUsage}%\n'\
            f'<b>• RAM usage:</b> {mem_p}%\n'\
            f'<b>• Disk usage:</b> {disk}%\n'\
            f'<b>• Free disk space:</b> {get_readable_file_size(free)}\n'\
            f'<b>• Total disk space:</b> {get_readable_file_size(total)}\n'
    await sendMessage(message, stats)

async def start(client, message):
    if len(message.command) > 1:
        userid = message.from_user.id
        input_token = message.command[1]
        if userid not in user_data:
            return await sendMessage(message, 'Who are you?')
        data = user_data[userid]
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, 'This is a token already expired')
        data['token'] = str(uuid4())
        data['time'] = time()
        user_data[userid].update(data)
        return await sendMessage(message, f'Token refreshed successfully!\n\n<b>Valid for:</b> {config_dict["TOKEN_TIMEOUT"]}s') 
    elif config_dict['DM_MODE']:
        start_string = f'<b>Welcome, To Era of Luna!</b>\n\nNow I will send your files or links here.\n'
    else:
        start_string = f'<b>Welcome, To Era of Luna!</b>\n\nThis bot can Mirror all your links To Google Drive!\n'
              
    await sendMessage(message, start_string)

async def restart(client, message):
    restart_message = await sendMessage(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg|rclone')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(client, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, "Starting Ping")
    end_time = int(round(time() * 1000))
    await editMessage(reply, f'{end_time - start_time} ms')


async def log(client, message):
    await sendFile(message, 'log.txt')

help_string = f'''
NOTE: Try each command without any argument to see more detalis.
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to Google Drive.
/{BotCommands.ZipMirrorCommand[0]} or /{BotCommands.ZipMirrorCommand[1]}: Start mirroring and upload the file/folder compressed with zip extension.
/{BotCommands.UnzipMirrorCommand[0]} or /{BotCommands.UnzipMirrorCommand[1]}: Start mirroring and upload the file/folder extracted from any archive extension.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Google Drive using qBittorrent.
/{BotCommands.QbZipMirrorCommand[0]} or /{BotCommands.QbZipMirrorCommand[1]}: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension.
/{BotCommands.QbUnzipMirrorCommand[0]} or /{BotCommands.QbUnzipMirrorCommand[1]}: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.
/{BotCommands.YtdlZipCommand[0]} or /{BotCommands.YtdlZipCommand[1]}: Mirror yt-dlp supported link as zip.
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.
/{BotCommands.ZipLeechCommand[0]} or /{BotCommands.ZipLeechCommand[1]}: Start leeching and upload the file/folder compressed with zip extension.
/{BotCommands.UnzipLeechCommand[0]} or /{BotCommands.UnzipLeechCommand[1]}: Start leeching and upload the file/folder extracted from any archive extension.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.
/{BotCommands.QbZipLeechCommand[0]} or /{BotCommands.QbZipLeechCommand[1]}: Start leeching using qBittorrent and upload the file/folder compressed with zip extension.
/{BotCommands.QbUnzipLeechCommand[0]} or /{BotCommands.QbUnzipLeechCommand[1]}: Start leeching using qBittorrent and upload the file/folder extracted from any archive extension.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.
/{BotCommands.YtdlZipLeechCommand[0]} or /{BotCommands.YtdlZipLeechCommand[1]}: Leech yt-dlp supported link as zip.
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).
/leech{BotCommands.DeleteCommand} [telegram_link]: Delete replies from telegram (Only Owner & Sudo).
/{BotCommands.UserSetCommand} [query]: Users settings.
/{BotCommands.BotSetCommand} [query]: Bot settings.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CategorySelect}: Change upload category for Google Drive.
/{BotCommands.CancelMirror}: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand[0]} : Cancel all tasks which added by you {BotCommands.CancelAllCommand[1]} to in bots.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]}: Shows a status of all the downloads.
/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.
/{BotCommands.PingCommand[0]} or /{BotCommands.PingCommand[1]}: Check how long it takes to Ping the Bot (Only Owner & Sudo).
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).
/{BotCommands.RestartCommand[0]}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.RestartCommand[1]}: Restart all bots and update the bot (Only Owner & Sudo)..
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).
/{BotCommands.ShellCommand}: Run shell commands (Only Owner).
/{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
/{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
/{BotCommands.RssCommand}: RSS Menu.
'''


async def bot_help(client, message):
    await sendMessage(message, help_string)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith('Restarted Successfully!'):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
                await bot.send_message(chat_id, msg, disable_web_page_preview=True, reply_to_message_id=msg_id)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                       disable_notification=True)
        except Exception as e:
            LOGGER.error(e)

    if DATABASE_URL:
        if INCOMPLETE_TASK_NOTIFIER and (notifier_dict := await DbManger().get_incomplete_tasks()):
            for cid, data in notifier_dict.items():
                msg = 'Restarted Successfully!' if cid == chat_id else 'Bot Restarted!'
                for tag, links in data.items():
                    msg += f"\n\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)

        if STOP_DUPLICATE_TASKS:
            await DbManger().clear_download_links()

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
        except:
            pass
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), set_commands(bot))

    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand)))
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
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()