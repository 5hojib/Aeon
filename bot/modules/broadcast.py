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

    total, successful, blocked, unsuccessful = 0, 0, 0, 0
    start_time = time()
    status = '<b>Broadcast Stats :</b>\n\n'
    status += f'<b>• Total users:</b> {total}\n'
    status += f'<b>• Success:</b> {successful}\n'
    status += f'<b>• Blocked or deleted:</b> {blocked}\n'
    status += f'<b>• Unsuccessful attempts:</b> {unsuccessful}'
    updater = time()
    broadcast_message = await sendMessage(message, status.format(**locals()))
    
    for uid in (await DbManager().get_pm_uids()):
        try:
            await message.reply_to_message.copy(uid)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(uid)
            successful += 1
        except (UserIsBlocked, InputUserDeactivated):
            await DbManager().rm_pm_user(uid)
            blocked += 1
        except Exception:
            unsuccessful += 1
        total += 1
        if (time() - updater) > 10:
            await editMessage(broadcast_message, status.format(**locals()))
            updater = time()
    
    elapsed_time = get_readable_time(time() - start_time)
    await editMessage(broadcast_message, f"{status.format(**locals())}\n\n<b>Elapsed Time:</b> {elapsed_time}")

bot.add_handler(MessageHandler(broadcast, filters=command(BotCommands.BroadcastCommand) & CustomFilters.owner))
