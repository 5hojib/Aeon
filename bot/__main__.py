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

from bot import DATABASE_URL, INCOMPLETE_TASK_NOTIFIER, LOGGER, STOP_DUPLICATE_TASKS, Interval, QbInterval, bot, user_data, botStartTime, config_dict, scheduler

from bot.helper.listeners.aria2_listener import start_aria2_listener
from .helper.ext_utils.bot_utils import cmd_exec, get_readable_file_size, get_readable_time, set_commands, sync_to_async, format_validity_time
from .helper.ext_utils.db_handler import DbManger
from .helper.ext_utils.fs_utils import clean_all, exit_clean_up, start_cleanup
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import editMessage, sendFile, sendMessage, auto_delete_message
from .modules import anonymous, authorize, bot_settings, cancel_mirror, category_select, clone, eval, gd_count, gd_delete, gd_list, leech_del, mirror_leech, rmdb, rss, save_message, shell, status, torrent_search, torrent_select, users_settings, ytdlp, index_scrape

async def stats(_, message):
    total, used, free, disk = disk_usage('/')
    memory = virtual_memory()
    currentTime = get_readable_time(time() - botStartTime)
    mem_p = memory.percent
    osUptime = get_readable_time(time() - boot_time())
    cpuUsage = cpu_percent(interval=0.5)
    if await aiopath.exists('.git'):
        command = '''
                    remote_url=$(git config --get remote.origin.url) &&
                    if echo "$remote_url" | grep -qE "github\.com[:/](.*)/(.*?)(\.git)?$"; then
                        owner_name=$(echo "$remote_url" | awk -F/ '{ print $(NF-1) }') &&
                        repo_name=$(echo "$remote_url" | awk -F/ '{ print $NF }' | sed 's/\.git$//') &&
                        last_commit=$(git log -1 --pretty=format:'%h') &&
                        commit_link="https://github.com/$owner_name/$repo_name/commit/$last_commit" &&
                        echo $commit_link;
                    else
                        echo "Failed to extract repository name and owner name from the remote URL.";
                    fi
                '''
        commit_link = (await cmd_exec(command, True))[0]
        commit_id = (await cmd_exec("git log -1 --pretty=format:'%h'", True))[0]
        commit_from = (await cmd_exec("git log -1 --date=short --pretty=format:'%cr'", True))[0]
        commit_date = (await cmd_exec("git log -1 --date=format:'%d %B %Y' --pretty=format:'%ad'", True))[0]
        commit_time = (await cmd_exec("git log -1 --date=format:'%I:%M:%S %p' --pretty=format:'%ad'", True))[0]
        commit_name = (await cmd_exec("git log -1 --pretty=format:'%s'", True))[0]
        
        commit_html_link = f'<a href="{commit_link}">{commit_id}</a>'
        
        stats = f'<b>REPOSITORY INFO</b>\n\n' \
            f"<code>• Last commit: </code>{commit_html_link}\n"\
            f'<code>• Commit date: </code>{commit_date}\n'\
            f'<code>• Commited on: </code>{commit_time}\n'\
            f'<code>• From now   : </code>{commit_from}\n'\
            f"<code>• What's new : </code>{commit_name}\n"\
            f'\n'\
            f'<b>SYSTEM INFO</b>\n\n'\
            f'<code>• Bot uptime :</code> {currentTime}\n'\
            f'<code>• Sys uptime :</code> {osUptime}\n'\
            f'<code>• CPU usage  :</code> {cpuUsage}%\n'\
            f'<code>• RAM usage  :</code> {mem_p}%\n'\
            f'<code>• Disk usage :</code> {disk}%\n'\
            f'<code>• Disk space :</code> {get_readable_file_size(free)}/{get_readable_file_size(total)}\n\n'\
            
        if config_dict['SHOW_LIMITS']:
        
            DIRECT_LIMIT = config_dict['DIRECT_LIMIT']
            YTDLP_LIMIT = config_dict['YTDLP_LIMIT']
            GDRIVE_LIMIT = config_dict['GDRIVE_LIMIT']
            TORRENT_LIMIT = config_dict['TORRENT_LIMIT']
            CLONE_LIMIT = config_dict['CLONE_LIMIT']
            MEGA_LIMIT = config_dict['MEGA_LIMIT']
            LEECH_LIMIT = config_dict['LEECH_LIMIT']
            USER_MAX_TASKS = config_dict['USER_MAX_TASKS']
        
            torrent_limit = '∞' if TORRENT_LIMIT == '' else f'{TORRENT_LIMIT}GB/Link'
            clone_limit = '∞' if CLONE_LIMIT == '' else f'{CLONE_LIMIT}GB/Link'
            gdrive_limit = '∞' if GDRIVE_LIMIT == '' else f'{GDRIVE_LIMIT}GB/Link'
            mega_limit = '∞' if MEGA_LIMIT == '' else f'{MEGA_LIMIT}GB/Link'
            leech_limit = '∞' if LEECH_LIMIT == '' else f'{LEECH_LIMIT}GB/Link'
            user_task = '∞' if USER_MAX_TASKS == '' else f'{USER_MAX_TASKS} Tasks/user'
            ytdlp_limit = '∞' if YTDLP_LIMIT == '' else f'{YTDLP_LIMIT}GB/Link'
            direct_limit = '∞' if DIRECT_LIMIT == '' else f'{DIRECT_LIMIT}GB/Link'
            stats += f'<b>LIMITATIONS</b>\n\n'\
                f'<code>• Torrent    :</code> {torrent_limit}\n'\
                f'<code>• Gdrive     :</code> {gdrive_limit}\n'\
                f'<code>• Ytdlp      :</code> {ytdlp_limit}\n'\
                f'<code>• Direct     :</code> {direct_limit}\n'\
                f'<code>• Leech      :</code> {leech_limit}\n'\
                f'<code>• Clone      :</code> {clone_limit}\n'\
                f'<code>• Mega       :</code> {mega_limit}\n'\
                f'<code>• User tasks :</code> {user_task}\n\n'
    await sendMessage(message, stats)

async def start(_, message):
    token_timeout = config_dict['TOKEN_TIMEOUT']
    if len(message.command) > 1:
        userid = message.from_user.id
        input_token = message.command[1]
        if userid not in user_data:
            return await sendMessage(message, "You do not own this token.")
        data = user_data[userid]
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, 'This token has already expired')
        data['token'] = str(uuid4())
        data['time'] = time()
        user_data[userid].update(data)
        time_str = format_validity_time(token_timeout)
        return await sendMessage(message, f'Congratulations on acquiring a new token!\n\n<b>It will expire after {time_str}</b>') 
    elif config_dict['DM_MODE']:
        start_string = f'<b>Welcome to the Era of Luna!</b>\n\nYour files or links will be sent to you here.\n'
    else:
        start_string = f'<b>Welcome to the Era of Luna!</b>\n\nThis bot can upload all your links or Telegram files to Google Drive, Telegram, or Rclone destination!\n'
              
    await sendMessage(message, start_string)

async def restart(_, message):
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


async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, "Starting Ping")
    end_time = int(round(time() * 1000))
    await editMessage(reply, f'{end_time - start_time} ms')


async def log(_, message):
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


async def bot_help(_, message):
    reply_message = await sendMessage(message, help_string)
    await auto_delete_message(message, reply_message)


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
    await sync_to_async(start_aria2_listener, wait=False)
    
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