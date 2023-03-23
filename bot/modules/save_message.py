from pyrogram.errors import UserIsBlocked
from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import request_limiter


@new_task
async def save_message(client, query):
    if not await CustomFilters.sudo(client, query) and await request_limiter(query=query):
        return
    try:
        button = ButtonMaker()
        button_exist = False
        for _markup in query.message.reply_markup.inline_keyboard:
            if isinstance(_markup, list):
                for another_markup in _markup:
                    if isinstance(another_markup, list):
                        for one_more_markup in another_markup:
                            if one_more_markup and not one_more_markup.callback_data:
                                button_exist = True
                                button.ubutton(one_more_markup.text, one_more_markup.url)
                    elif another_markup and not another_markup.callback_data:
                        button_exist = True
                        button.ubutton(another_markup.text, another_markup.url)
            elif _markup and not _markup.callback_data:
                button_exist = True
                button.ubutton(_markup.text, _markup.url)
        reply_markup = button.build_menu(2) if button_exist else None
        await query.message.copy(query.from_user.id, reply_markup=reply_markup, disable_notification=False)
        await query.answer('Saved Successfully', show_alert=True)
    except UserIsBlocked:
        await query.answer(f'Start @{client.me.username} in private and try again', show_alert=True)
    except Exception as e:
        LOGGER.error(e)
        await query.answer("Something went wrong!", show_alert=True)


bot.add_handler(CallbackQueryHandler(save_message, filters=regex("^save")))