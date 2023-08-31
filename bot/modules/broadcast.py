#!/usr/bin/env python3
from time import time
from asyncio import sleep
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import bot, LOGGER, DATABASE_URL
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import new_task, get_readable_time

@new_task
async def broadcast(_, message):
    if not DATABASE_URL:
        return await sendMessage(message, 'DATABASE_URL not provided!')
    if not message.reply_to_message:
        return await sendMessage(message, '<b>Reply to any Message to Broadcast Users in Bot PM</b>')
    t, s, b, d, u = 0, 0, 0, 0, 0
    start_time = time()
    status = '''<b>Broadcast Stats :</b>
<b>• Total Users:</b> {t}
<b>• Success:</b> {s}
<b>• Blocked Users:</b> {b}
<b>• Deleted Accounts:</b> {d}
<b>• Unsuccess Attempt:</b> {u}'''
    updater = time()
    pls_wait = await sendMessage(message, status.format(**locals()))
    for uid in (await DbManager().get_pm_uids()):
        try:
            await message.reply_to_message.copy(uid)
            s += 1
        except FloodWait as e:
            await sleep(e.value)
            await message.reply_to_message.copy(uid)
            s += 1
        except UserIsBlocked:
            await DbManager().rm_pm_user(uid)
            b += 1
        except InputUserDeactivated:
            await DbManager().rm_pm_user(uid)
            d += 1
        except:
            u += 1
        t += 1
        if (time() - updater) > 10:
            await editMessage(pls_wait, status.format(**locals()))
            updater = time()
    await editMessage(
        pls_wait,
        f"{status.format(**locals())}\n\n<b>Elapsed Time:</b> <code>{get_readable_time(time() - start_time)}</code>",
    )
        
        
bot.add_handler(MessageHandler(broadcast, filters=command(BotCommands.BroadcastCommand) & CustomFilters.owner))