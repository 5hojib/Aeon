from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import new_task, sync_to_async
from bot.helper.ext_utils.links_utils import is_gdrive_link
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import send_message, delete_message
from bot.helper.mirror_leech_utils.gdrive_utils.count import gdCount


@new_task
async def countNode(_, message):
    args = message.text.split()
    user = message.from_user or message.sender_chat
    if username := user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    link = args[1] if len(args) > 1 else ""
    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        msg = await send_message(message, f"Counting: <code>{link}</code>")
        name, mime_type, size, files, folders = await sync_to_async(
            gdCount().count, link, user.id
        )
        if mime_type is None:
            await send_message(message, name)
            return
        await delete_message(msg)
        msg = f"<b>Name: </b><code>{name}</code>"
        msg += f"\n\n<b>Size: </b>{get_readable_file_size(size)}"
        msg += f"\n\n<b>Type: </b>{mime_type}"
        if mime_type == "Folder":
            msg += f"\n<b>SubFolders: </b>{folders}"
            msg += f"\n<b>Files: </b>{files}"
        msg += f"\n\n<b>cc: </b>{tag}"
    else:
        msg = "Send Gdrive link along with command or by replying to the link by command"

    await send_message(message, msg)


bot.add_handler(
    MessageHandler(
        countNode,
        filters=command(BotCommands.CountCommand) & CustomFilters.authorized,
    )
)
