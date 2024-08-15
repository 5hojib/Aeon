from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import new_task, sync_to_async, is_gdrive_link
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    sendMessage,
    deleteMessage,
    one_minute_del,
)
from bot.helper.mirror_leech_utils.upload_utils.gdriveTools import GoogleDriveHelper


async def delete_file(link):
    try:
        LOGGER.info(link)
        drive = GoogleDriveHelper()
        return await sync_to_async(drive.deletefile, link)
    except Exception as e:
        LOGGER.error(f"Error deleting Google Drive file: {e!s}")
        return f"An error occurred: {e!s}"


@new_task
async def deletefile(_, message):
    args = message.text.split()
    if len(args) > 1:
        link = args[1]
    elif reply_to := message.reply_to_message:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ""

    if is_gdrive_link(link):
        msg = await delete_file(link)
    else:
        msg = "Send a Google Drive link along with the command or reply to the link with the command."

    reply_message = await sendMessage(message, msg)
    await deleteMessage(message)
    await one_minute_del(reply_message)


bot.add_handler(
    MessageHandler(
        deletefile,
        filters=command(BotCommands.DeleteCommand) & CustomFilters.authorized,
    )
)
