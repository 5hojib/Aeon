from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from bot import LOGGER, bot, config_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, delete_links, one_minute_del, five_minute_del, isAdmin
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, get_telegraph_list, checking_access

async def build_list_buttons(user_id, is_recursive=True):
    buttons = ButtonMaker()
    buttons.ibutton("List Folders", f"list_types {user_id} folders {is_recursive}")
    buttons.ibutton("List Files", f"list_types {user_id} files {is_recursive}")
    buttons.ibutton("List Both", f"list_types {user_id} both {is_recursive}")
    buttons.ibutton(f"Recursive: {is_recursive}", f"list_types {user_id} rec {is_recursive}")
    buttons.ibutton("Cancel", f"list_types {user_id} cancel")
    return buttons.build_menu(2)

@new_task
async def handle_list_types(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == 'rec':
        await query.answer()
        is_recursive = not bool(eval(data[3]))
        buttons = await build_list_buttons(user_id, is_recursive)
        return await editMessage(message, 'Choose list options:', buttons)
    elif data[2] == 'cancel':
        await query.answer()
        return await editMessage(message, "List has been canceled!")
    await query.answer()
    item_type = data[2]
    is_recursive = eval(data[3])
    await editMessage(message, f'<b>Searching for </b>{key}...')
    await list_drive(key, message, item_type, is_recursive)

@new_task
async def list_drive(_, message):
    if len(message.text.split()) == 1:
        reply_message = await sendMessage(message, 'Send a search key along with command')
        await delete_links(message)
        await one_minute_del(reply_message)
        return
    user_id = message.from_user.id
    if not await isAdmin(message, user_id):
        if message.chat.type != message.chat.type.PRIVATE:
            msg, btn = await checking_access(user_id)
            if msg is not None:
                reply_message = await sendMessage(message, msg, btn.build_menu(1))
                await delete_links(message)
                await five_minute_del(reply_message)
                return
    buttons = await build_list_buttons(user_id)
    reply_message = await sendMessage(message, 'Choose list options:', buttons)
    await five_minute_del(reply_message)
    await delete_links(message)

async def _list_drive(key, message, item_type, is_recursive):
    LOGGER.info(f"Listing: {key}")
    gdrive = GoogleDriveHelper()
    telegraph_content, contents_no = await sync_to_async(gdrive.drive_list, key, isRecursive=is_recursive, itemType=item_type)
    if telegraph_content:
        try:
            button = await get_telegraph_list(telegraph_content)
        except Exception as e:
            await editMessage(message, e)
            return
        msg = f'<b>Found {contents_no} results for </b>{key}'
        await editMessage(message, msg, button)
    else:
        await editMessage(message, f'<b>No results found for </b>{key}')

@new_task
async def select_type(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == 'rec':
        await query.answer()
        is_recursive = not bool(eval(data[3]))
        buttons = await build_list_buttons(user_id, is_recursive)
        return await editMessage(message, 'Choose list options:', buttons)
    elif data[2] == 'cancel':
        await query.answer()
        return await editMessage(message, "List has been canceled!")
    await query.answer()
    item_type = data[2]
    is_recursive = eval(data[3])
    await editMessage(message, f'<b>Searching for </b>{key}...')
    await _list_drive(key, message, item_type, is_recursive)

bot.add_handler(MessageHandler(list_drive, filters=command(
    BotCommands.ListCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(
    handle_list_types, filters=regex("^list_types")))
