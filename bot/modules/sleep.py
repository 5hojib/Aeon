from pyrogram.handlers import MessageHandler
from bot import BASE_URL, alive, bot
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters

async def sleep(update, context):
    if BASE_URL is None:
        await sendMessage('BASE_URL not provided!', context.bot, update.message)
    elif alive.returncode is None:
        alive.kill()
        msg = 'Your bot will sleep in 30 minute maximum.\n\n'
        msg += 'In case changed your mind and want to use the bot again before the sleep then restart the bot.\n\n'
        msg += f'Open this link when you want to wake up the bot {BASE_URL}.'
        await sendMessage(msg, context.bot, update.message)
    else:
        await sendMessage('Ping have been stopped, your bot will sleep in less than 30 min.', context.bot, update.message)

bot.add_handler(MessageHandler('sleep',  CustomFilters.sudo))
