import asyncio
from time import time
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
        return await sendMessage(message, '<b>Reply to any message to broadcast users in Bot PM.</b>')

    t, s, b, u = 0, 0, 0, 0
    start_time = time()
    status = '''<b>Broadcast Stats :</b>

<b>• Total users:</b> {t}
<b>• Success:</b> {s}
<b>• Blocked or deleted:</b> {b}
<b>• Unsuccessful attempts:</b> {u}'''
    
    updater = time()
    pls_wait = await sendMessage(message, status.format(**locals()))
    
    for uid in (await DbManager().get_pm_uids()):
        try:
            await message.reply_to_message.copy(uid)
            s += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(uid)
            s += 1
        except (UserIsBlocked, InputUserDeactivated):
            await DbManager().rm_pm_user(uid)
            b += 1
        except Exception:
            u += 1
        
        t += 1
        if (time() - updater) > 10:
            await editMessage(pls_wait, status.format(**locals()))
            updater = time()
    
    elapsed_time = get_readable_time(time() - start_time)
    await editMessage(pls_wait, f"{status.format(**locals())}\n\n<b>Elapsed Time:</b> <code>{elapsed_time}</code>")

bot.add_handler(MessageHandler(broadcast, filters=command(BotCommands.BroadcastCommand) & CustomFilters.owner))
