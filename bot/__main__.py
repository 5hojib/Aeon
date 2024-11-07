from os import execl as osexecl
from sys import executable
from html import escape
from time import time
from uuid import uuid4
from signal import SIGINT, signal
from asyncio import gather, create_subprocess_exec

from psutil import (
    boot_time,
    cpu_count,
    disk_usage,
    cpu_percent,
    swap_memory,
    virtual_memory,
    net_io_counters,
)
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove
from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import (
    LOGGER,
    Intervals,
    bot,
    scheduler,
    user_data,
    config_dict,
    bot_username,
    bot_start_time,
)

from .modules import (  # noqa: F401
    exec,
    help,
    clone,
    shell,
    ytdlp,
    status,
    gd_count,
    authorize,
    broadcast,
    gd_delete,
    gd_search,
    mediainfo,
    cancel_task,
    bot_settings,
    mirror_leech,
    file_selector,
    torrent_search,
    users_settings,
)
from .helper.ext_utils.bot_utils import (
    cmd_exec,
    new_task,
    sync_to_async,
    create_help_buttons,
)
from .helper.ext_utils.db_handler import Database
from .helper.ext_utils.files_utils import clean_all, exit_clean_up
from .helper.ext_utils.status_utils import get_readable_time, get_readable_file_size
from .helper.telegram_helper.filters import CustomFilters
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.telegram_helper.message_utils import (
    sendFile,
    edit_message,
    send_message,
    delete_message,
    five_minute_del,
)


async def stats(_, message):
    if await aiopath.exists(".git"):
        last_commit = await cmd_exec(
            "git log -1 --date=short --pretty=format:'%cd <b>From</b> %cr'", True
        )
        last_commit = last_commit[0]
    else:
        last_commit = "No UPSTREAM_REPO"
    total, used, free, disk = disk_usage("/")
    swap = swap_memory()
    memory = virtual_memory()
    stats = (
        f"<b>Commit Date:</b> {last_commit}\n\n"
        f"<b>Bot Uptime:</b> {get_readable_time(time() - bot_start_time)}\n"
        f"<b>OS Uptime:</b> {get_readable_time(time() - boot_time())}\n\n"
        f"<b>Total Disk Space:</b> {get_readable_file_size(total)}\n"
        f"<b>Used:</b> {get_readable_file_size(used)} | <b>Free:</b> {get_readable_file_size(free)}\n\n"
        f"<b>Upload:</b> {get_readable_file_size(net_io_counters().bytes_sent)}\n"
        f"<b>Download:</b> {get_readable_file_size(net_io_counters().bytes_recv)}\n\n"
        f"<b>CPU:</b> {cpu_percent(interval=0.5)}%\n"
        f"<b>RAM:</b> {memory.percent}%\n"
        f"<b>DISK:</b> {disk}%\n\n"
        f"<b>Physical Cores:</b> {cpu_count(logical=False)}\n"
        f"<b>Total Cores:</b> {cpu_count(logical=True)}\n\n"
        f"<b>SWAP:</b> {get_readable_file_size(swap.total)} | <b>Used:</b> {swap.percent}%\n"
        f"<b>Memory Total:</b> {get_readable_file_size(memory.total)}\n"
        f"<b>Memory Free:</b> {get_readable_file_size(memory.available)}\n"
        f"<b>Memory Used:</b> {get_readable_file_size(memory.used)}\n"
    )
    await send_message(message, stats)


async def start(client, message):
    if len(message.command) > 1 and message.command[1] == "private":
        await delete_message(message)
    elif len(message.command) > 1 and len(message.command[1]) == 36:
        userid = message.from_user.id
        input_token = message.command[1]
        stored_token = await Database().get_user_token(userid)
        if stored_token is None:
            return await send_message(
                message,
                "<b>This token is not for you!</b>\n\nPlease generate your own.",
            )
        if input_token != stored_token:
            return await send_message(
                message, "Invalid token.\n\nPlease generate a new one."
            )
        if userid not in user_data:
            return await send_message(
                message, "This token is not yours!\n\nKindly generate your own."
            )
        data = user_data[userid]
        if "token" not in data or data["token"] != input_token:
            return await send_message(
                message,
                "<b>This token has already been used!</b>\n\nPlease get a new one.",
            )
        token = str(uuid4())
        token_time = time()
        data["token"] = token
        data["time"] = token_time
        user_data[userid].update(data)
        await Database().update_user_tdata(userid, token, token_time)
        msg = "Your token has been successfully generated!\n\n"
        msg += f'It will be valid for {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]), True)}'
        return await send_message(message, msg)
    elif await CustomFilters.authorized(client, message):
        help_command = f"/{BotCommands.HelpCommand}"
        start_string = f"This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram.\n<b>Type {help_command} to get a list of available commands</b>"
        await send_message(message, start_string)
    else:
        await send_message(message, "You are not a authorized user!")
    await Database().update_pm_users(message.from_user.id)
    return None


async def restart(_, message):
    Intervals["stopAll"] = True
    restart_message = await send_message(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if qb := Intervals["qb"]:
        qb.cancel()
    if st := Intervals["status"]:
        for intvl in list(st.values()):
            intvl.cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec(
        "pkill",
        "-9",
        "-f",
        "gunicorn|xria|xnox|xtra|xone",
    )
    proc2 = await create_subprocess_exec("python3", "update.py")
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(_, message):
    start_time = int(round(time() * 1000))
    reply = await send_message(message, "Starting Ping")
    end_time = int(round(time() * 1000))
    await edit_message(reply, f"{end_time - start_time} ms")


@new_task
async def log(_, message):
    buttons = ButtonMaker()
    buttons.callback("Log display", f"aeon {message.from_user.id} logdisplay")
    reply_message = await sendFile(message, "log.txt", buttons=buttons.menu(1))
    await delete_message(message)
    await five_minute_del(reply_message)


help_string = f"""
NOTE: Try each command without any argument to see more detalis.

/{BotCommands.MirrorCommand[0]}: Start mirroring to cloud.
/{BotCommands.YtdlCommand[0]}: Mirror yt-dlp supported link.
/{BotCommands.LeechCommand[0]}: Start leeching to Telegram.
/{BotCommands.YtdlLeechCommand[0]}: Leech yt-dlp supported link.
/{BotCommands.CloneCommand[0]} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.UserSetCommand} [query]: Users settings.
/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand[0]}: Shows a status of all the downloads.
/{BotCommands.StatsCommand[0]}: Show stats of the machine where the bot is hosted in."""


async def bot_help(_, message):
    await send_message(message, help_string)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        cmd = r"""remote_url=$(git config --get remote.origin.url) &&
            if echo "$remote_url" | grep -qE "github\.com[:/](.*)/(.*?)(\.git)?$"; then
                last_commit=$(git log -1 --pretty=format:'%h') &&
                commit_link="https://github.com/5hojib/Aeon/commit/$last_commit" &&
                echo $commit_link;
            else
                echo "Failed to extract repository name and owner name from the remote URL.";
            fi"""

        result = await cmd_exec(cmd, True)

        commit_link = result[0]

        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f'<a href="{commit_link}">Restarted Successfully!</a>',
            )
        except Exception as e:
            print(f"Failed to edit message: {e}")
        await remove(".restartmsg")


@new_task
async def AeonCallback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="This message not your's!", show_alert=True)
    if data[2] == "logdisplay":
        await query.answer()
        async with aiopen("log.txt") as f:
            logFileLines = (await f.read()).splitlines()

        def parseline(line):
            try:
                return "[" + line.split("] [", 1)[1]
            except IndexError:
                return line

        ind, Loglines = 1, ""
        try:
            while len(Loglines) <= 3500:
                Loglines = parseline(logFileLines[-ind]) + "\n" + Loglines
                if ind == len(logFileLines):
                    break
                ind += 1
            startLine = "<pre language='python'>"
            endLine = "</pre>"
            btn = ButtonMaker()
            btn.callback("Close", f"aeon {user_id} close")
            reply_message = await send_message(
                message, startLine + escape(Loglines) + endLine, btn.menu(1)
            )
            await query.edit_message_reply_markup(None)
            await delete_message(message)
            await five_minute_del(reply_message)
        except Exception as err:
            LOGGER.error(f"TG Log Display : {err!s}")
    elif data[2] == "private":
        await query.answer(url=f"https://t.me/{bot_username}?start=private")
        return None
    else:
        await query.answer()
        await delete_message(message)
        return None


async def main():
    await Database().db_load()
    await gather(
        sync_to_async(clean_all),
        torrent_search.initiate_search_tools(),
        restart_notification(),
        telegraph.create_account(),
        sync_to_async(start_aria2_listener, wait=False),
    )
    create_help_buttons()

    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(
        MessageHandler(
            log, filters=command(BotCommands.LogCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo
        )
    )
    bot.add_handler(
        MessageHandler(
            ping, filters=command(BotCommands.PingCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(
        MessageHandler(
            bot_help,
            filters=command(BotCommands.HelpCommand) & CustomFilters.authorized,
        )
    )
    bot.add_handler(
        MessageHandler(
            stats,
            filters=command(BotCommands.StatsCommand) & CustomFilters.authorized,
        )
    )
    bot.add_handler(CallbackQueryHandler(AeonCallback, filters=regex(r"^aeon")))
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)


bot.loop.run_until_complete(main())
bot.loop.run_forever()
