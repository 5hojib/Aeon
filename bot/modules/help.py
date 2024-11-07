from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import COMMAND_USAGE
from bot.helper.ext_utils.help_messages import (
    YT_HELP_DICT,
    CLONE_HELP_DICT,
    MIRROR_HELP_DICT,
)
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import edit_message, delete_message


async def argUsage(_, query):
    data = query.data.split()
    message = query.message
    if data[1] == "close":
        await delete_message(message)
    elif data[1] == "back":
        if data[2] == "m":
            await edit_message(
                message, COMMAND_USAGE["mirror"][0], COMMAND_USAGE["mirror"][1]
            )
        elif data[2] == "y":
            await edit_message(
                message, COMMAND_USAGE["yt"][0], COMMAND_USAGE["yt"][1]
            )
        elif data[2] == "c":
            await edit_message(
                message, COMMAND_USAGE["clone"][0], COMMAND_USAGE["clone"][1]
            )
    elif data[1] == "mirror":
        buttons = ButtonMaker()
        buttons.callback("Back", "help back m")
        button = buttons.menu()
        await edit_message(message, MIRROR_HELP_DICT[data[2]], button)
    elif data[1] == "yt":
        buttons = ButtonMaker()
        buttons.callback("Back", "help back y")
        button = buttons.menu()
        await edit_message(message, YT_HELP_DICT[data[2]], button)
    elif data[1] == "clone":
        buttons = ButtonMaker()
        buttons.callback("Back", "help back c")
        button = buttons.menu()
        await edit_message(message, CLONE_HELP_DICT[data[2]], button)


bot.add_handler(CallbackQueryHandler(argUsage, filters=regex("^help")))
