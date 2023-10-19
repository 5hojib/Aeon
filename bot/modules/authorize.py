from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

from bot import user_data, DATABASE_URL, bot
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.bot_utils import update_user_ldata

async def change_authorization(message, is_authorize):
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    else:
        id_ = message.chat.id
    if is_authorize:
        success_message = 'Authorized'
        if id_ in user_data and user_data[id_].get('is_auth'):
            success_message = 'Already authorized!'
        else:
            update_user_ldata(id_, 'is_auth', True)
            if DATABASE_URL:
                await DbManager().update_user_data(id_)
    else:
        success_message = 'Unauthorized'
        if id_ not in user_data or user_data[id_].get('is_auth'):
            update_user_ldata(id_, 'is_auth', False)
            if DATABASE_URL:
                await DbManager().update_user_data(id_)
        else:
            success_message = 'Already unauthorized!'
    await sendMessage(message, success_message)


async def change_sudo(message, is_sudo):
    id_ = ""
    msg = message.text.split()
    if len(msg) > 1:
        id_ = int(msg[1].strip())
    elif reply_to := message.reply_to_message:
        id_ = reply_to.from_user.id
    if is_sudo:
        if id_:
            if id_ in user_data and user_data[id_].get('is_sudo'):
                success_message = 'Already Sudo!'
            else:
                update_user_ldata(id_, 'is_sudo', True)
                if DATABASE_URL:
                    await DbManager().update_user_data(id_)
                success_message = 'Promoted as Sudo'
        else:
            success_message = "Give ID or Reply To message of whom you want to Promote."
    elif id_ and id_ in user_data and user_data[id_].get('is_sudo'):
        update_user_ldata(id_, 'is_sudo', False)
        if DATABASE_URL:
            await DbManager().update_user_data(id_)
        success_message = 'Demoted'
    else:
        success_message = "Give ID or Reply To message of whom you want to remove from Sudo"
    await sendMessage(message, success_message)


async def authorize(client, message):
    await change_authorization(message, True)

async def unauthorize(client, message):
    await change_authorization(message, False)

async def addSudo(client, message):
    await change_sudo(message, True)

async def removeSudo(client, message):
    await change_sudo(message, False)

bot.add_handler(MessageHandler(authorize, filters=command(
    BotCommands.AuthorizeCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(unauthorize, filters=command(
    BotCommands.UnAuthorizeCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(addSudo, filters=command(
    BotCommands.AddSudoCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(removeSudo, filters=command(
    BotCommands.RmSudoCommand) & CustomFilters.sudo))
