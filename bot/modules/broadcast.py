import asyncio
from time import time

from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.db_handler import Database
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import edit_message, send_message


@new_task
async def broadcast(_, message):
    if not message.reply_to_message:
        await send_message(
            message, "Reply to any message to broadcast messages to users in Bot PM."
        )
        return

    total, successful, blocked, unsuccessful = 0, 0, 0, 0
    start_time = time()
    updater = time()
    broadcast_message = await send_message(message, "Broadcast in progress...")

    for uid in await Database().get_pm_uids():
        try:
            await message.reply_to_message.copy(uid)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(uid)
            successful += 1
        except (UserIsBlocked, InputUserDeactivated):
            await Database().rm_pm_user(uid)
            blocked += 1
        except Exception:
            unsuccessful += 1

        total += 1

        if (time() - updater) > 10:
            status = generate_status(total, successful, blocked, unsuccessful)
            await edit_message(broadcast_message, status)
            updater = time()

    elapsed_time = get_readable_time(time() - start_time, True)
    status = generate_status(total, successful, blocked, unsuccessful, elapsed_time)
    await edit_message(broadcast_message, status)


def generate_status(total, successful, blocked, unsuccessful, elapsed_time=""):
    status = "<b>Broadcast Stats :</b>\n\n"
    status += f"<b>• Total users:</b> {total}\n"
    status += f"<b>• Success:</b> {successful}\n"
    status += f"<b>• Blocked or deleted:</b> {blocked}\n"
    status += f"<b>• Unsuccessful attempts:</b> {unsuccessful}"
    if elapsed_time:
        status += f"\n\n<b>Elapsed Time:</b> {elapsed_time}"
    return status


bot.add_handler(
    MessageHandler(
        broadcast,
        filters=command(BotCommands.BroadcastCommand) & CustomFilters.owner,
    )
)
