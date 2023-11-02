from typing import Union

import telegram
from telegram import raw, types


class SendInlineBotResult:
    async def send_inline_bot_result(
        self: "telegram.Client",
        chat_id: Union[int, str],
        query_id: int,
        result_id: str,
        disable_notification: bool = None,
        message_thread_id: int = None,
        reply_to_message_id: int = None,
        quote_text: str = None
    ) -> "raw.base.Updates":
        reply_to = None
        if reply_to_message_id or message_thread_id:
            reply_to = types.InputReplyToMessage(reply_to_message_id=reply_to_message_id, message_thread_id=message_thread_id, quote_text=quote_text)

        return await self.invoke(
            raw.functions.messages.SendInlineBotResult(
                peer=await self.resolve_peer(chat_id),
                query_id=query_id,
                id=result_id,
                random_id=self.rnd_id(),
                silent=disable_notification or None,
                reply_to=reply_to
            )
        )
