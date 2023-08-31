#!/usr/bin/env python3
from random import choice
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex

from bot import LOGGER, bot, config_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, delete_links, one_minute_del, five_minute_del, isAdmin
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task, get_telegraph_list, checking_access, new_thread


async def list_buttons(user_id, isRecursive=True):
    buttons = ButtonMaker()
    buttons.ibutton("Folders", f"list_types {user_id} folders {isRecursive}")
    buttons.ibutton("Files", f"list_types {user_id} files {isRecursive}")
    buttons.ibutton("Both", f"list_types {user_id} both {isRecursive}")
    buttons.ibutton(f"Recursive: {isRecursive}",
                    f"list_types {user_id} rec {isRecursive}")
    buttons.ibutton("Cancel", f"list_types {user_id} cancel")
    return buttons.build_menu(2)


async def _list_drive(key, message, item_type, isRecursive):
    LOGGER.info(f"listing: {key}")
    gdrive = GoogleDriveHelper()
    telegraph_content, contents_no = await sync_to_async(gdrive.drive_list, key, isRecursive=isRecursive, itemType=item_type)
    if telegraph_content:
        try:
            button = await get_telegraph_list(telegraph_content)
        except Exception as e:
            await editMessage(message, e)
            return
        msg = f'<b>Found {contents_no} result for </b>{key}'
        await editMessage(message, msg, button)
    else:
        await editMessage(message, f'<b>No result found for </b>{key}')


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
        isRecursive = not bool(eval(data[3]))
        buttons = await list_buttons(user_id, isRecursive)
        return await editMessage(message, 'Choose list options:', buttons)
    elif data[2] == 'cancel':
        await query.answer()
        return await editMessage(message, "list has been canceled!")
    await query.answer()
    item_type = data[2]
    isRecursive = eval(data[3])
    await editMessage(message, f'<b>Searching for </b>{key}...')
    await _list_drive(key, message, item_type, isRecursive)

@new_task
async def drive_list(_, message):
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
    buttons = await list_buttons(user_id)
    reply_message = await sendMessage(message, 'Choose list options:', buttons)
    await delete_links(message)
    await five_minute_del(reply_message)

bot.add_handler(MessageHandler(drive_list, filters=command(
    BotCommands.ListCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(
    select_type, filters=regex("^list_types")))
