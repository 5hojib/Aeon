from typing import Union, List, Match, Optional

import telegram
from telegram import raw, enums
from telegram import types
from ..object import Object
from ..update import Update
from ... import utils


class CallbackQuery(Object, Update):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        id: str,
        from_user: "types.User",
        chat_instance: str,
        message: "types.Message" = None,
        inline_message_id: str = None,
        data: Union[str, bytes] = None,
        game_short_name: str = None,
        matches: List[Match] = None
    ):
        super().__init__(client)

        self.id = id
        self.from_user = from_user
        self.chat_instance = chat_instance
        self.message = message
        self.inline_message_id = inline_message_id
        self.data = data
        self.game_short_name = game_short_name
        self.matches = matches

    @staticmethod
    async def _parse(client: "telegram.Client", callback_query, users) -> "CallbackQuery":
        message = None
        inline_message_id = None

        if isinstance(callback_query, raw.types.UpdateBotCallbackQuery):
            chat_id = utils.get_peer_id(callback_query.peer)
            message_id = callback_query.msg_id

            message = client.message_cache[(chat_id, message_id)]

            if not message:
                message = await client.get_messages(chat_id, message_id)
        elif isinstance(callback_query, raw.types.UpdateInlineBotCallbackQuery):
            inline_message_id = utils.pack_inline_message_id(callback_query.msg_id)

        try:
            data = callback_query.data.decode()
        except (UnicodeDecodeError, AttributeError):
            data = callback_query.data

        return CallbackQuery(
            id=str(callback_query.query_id),
            from_user=types.User._parse(client, users[callback_query.user_id]),
            message=message,
            inline_message_id=inline_message_id,
            chat_instance=str(callback_query.chat_instance),
            data=data,
            game_short_name=callback_query.game_short_name,
            client=client
        )

    async def answer(self, text: str = None, show_alert: bool = None, url: str = None, cache_time: int = 0):
        return await self._client.answer_callback_query(
            callback_query_id=self.id,
            text=text,
            show_alert=show_alert,
            url=url,
            cache_time=cache_time
        )

    async def edit_message_text(
        self,
        text: str,
        parse_mode: Optional["enums.ParseMode"] = None,
        disable_web_page_preview: bool = None,
        reply_markup: "types.InlineKeyboardMarkup" = None
    ) -> Union["types.Message", bool]:
        if self.inline_message_id is None:
            return await self._client.edit_message_text(
                chat_id=self.message.chat.id,
                message_id=self.message.id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                reply_markup=reply_markup
            )
        else:
            return await self._client.edit_inline_text(
                inline_message_id=self.inline_message_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                reply_markup=reply_markup
            )

    async def edit_message_caption(
        self,
        caption: str,
        parse_mode: Optional["enums.ParseMode"] = None,
        reply_markup: "types.InlineKeyboardMarkup" = None
    ) -> Union["types.Message", bool]:
        return await self.edit_message_text(caption, parse_mode, reply_markup=reply_markup)

    async def edit_message_media(
        self,
        media: "types.InputMedia",
        reply_markup: "types.InlineKeyboardMarkup" = None
    ) -> Union["types.Message", bool]:
        if self.inline_message_id is None:
            return await self._client.edit_message_media(
                chat_id=self.message.chat.id,
                message_id=self.message.id,
                media=media,
                reply_markup=reply_markup
            )
        else:
            return await self._client.edit_inline_media(
                inline_message_id=self.inline_message_id,
                media=media,
                reply_markup=reply_markup
            )

    async def edit_message_reply_markup(
        self,
        reply_markup: "types.InlineKeyboardMarkup" = None
    ) -> Union["types.Message", bool]:
        if self.inline_message_id is None:
            return await self._client.edit_message_reply_markup(
                chat_id=self.message.chat.id,
                message_id=self.message.id,
                reply_markup=reply_markup
            )
        else:
            return await self._client.edit_inline_reply_markup(
                inline_message_id=self.inline_message_id,
                reply_markup=reply_markup
            )
