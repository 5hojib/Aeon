from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async,
    is_gdrive_link,
    get_readable_file_size,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    delete_links,
    send_message,
    delete_message,
)
from bot.helper.mirror_leech_utils.upload_utils.gdriveTools import GoogleDriveHelper


@new_task
async def countNode(_, message):
    async def format_node_count(name, mime_type, size, files, folders, tag):
        msg = f"{name}\n\n"
        msg += f"<b>• Size: </b>{get_readable_file_size(size)}\n"
        if mime_type == "Folder":
            msg += f"<b>• SubFolders: </b>{folders}\n"
            msg += f"<b>• Files: </b>{files}\n"
        msg += f"<b>• Counted by: </b>{tag}\n"
        msg += f"<b>• User ID: </b><code>{message.from_user.id}</code>\n"
        return msg

    args = message.text.split()
    if username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    link = args[1] if len(args) > 1 else ""
    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        msg = await send_message(message, f"<b>Counting:</b> <code>{link}</code>")
        gd = GoogleDriveHelper()
        name, mime_type, size, files, folders = await sync_to_async(gd.count, link)
        if mime_type is None:
            await send_message(message, name)
            await delete_message(msg)
            return
        msg = await format_node_count(name, mime_type, size, files, folders, tag)
    else:
        msg = "Send a Google Drive link along with the command or reply to a link with the command."
    await send_message(message, msg)
    await delete_links(message)


bot.add_handler(
    MessageHandler(
        countNode,
        filters=command(BotCommands.CountCommand) & CustomFilters.authorized,
    )
)
