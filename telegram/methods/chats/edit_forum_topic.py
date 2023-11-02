import telegram
from telegram import raw
from telegram import types
from typing import Union


class EditForumTopic:
    async def edit_forum_topic(
        self: "telegram.Client",
        chat_id: Union[int, str],
        topic_id: int,
        title: str = None,
        icon_emoji_id: int = None
    ) -> bool:
        await self.invoke(
            raw.functions.channels.EditForumTopic(
                channel=await self.resolve_peer(chat_id),
                topic_id=topic_id,
                title=title,
                icon_emoji_id=icon_emoji_id
            )
        )
        return True
