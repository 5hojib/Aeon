from typing import Optional, List

import telegram
from telegram import raw, types, utils, enums
from .inline_query_result import InlineQueryResult


class InlineQueryResultAnimation(InlineQueryResult):
    def __init__(
        self,
        animation_url: str,
        animation_width: int = 0,
        animation_height: int = 0,
        animation_duration: int = 0,
        thumb_url: str = None,
        thumb_mime_type: str = "image/jpeg",
        id: str = None,
        title: str = None,
        description: str = None,
        caption: str = "",
        parse_mode: Optional["enums.ParseMode"] = None,
        caption_entities: List["types.MessageEntity"] = None,
        reply_markup: "types.InlineKeyboardMarkup" = None,
        input_message_content: "types.InputMessageContent" = None
    ):
        super().__init__("gif", id, input_message_content, reply_markup)

        self.animation_url = animation_url
        self.animation_width = animation_width
        self.animation_height = animation_height
        self.animation_duration = animation_duration
        self.thumb_url = thumb_url
        self.thumb_mime_type = thumb_mime_type
        self.title = title
        self.description = description
        self.caption = caption
        self.parse_mode = parse_mode
        self.caption_entities = caption_entities
        self.reply_markup = reply_markup
        self.input_message_content = input_message_content

    async def write(self, client: "telegram.Client"):
        animation = raw.types.InputWebDocument(
            url=self.animation_url,
            size=0,
            mime_type="image/gif",
            attributes=[
                raw.types.DocumentAttributeVideo(
                    w=self.animation_width,
                    h=self.animation_height,
                    duration=self.animation_duration
                )
            ]
        )

        if self.thumb_url is None:
            thumb = animation
        else:
            thumb = raw.types.InputWebDocument(
                url=self.thumb_url,
                size=0,
                mime_type=self.thumb_mime_type,
                attributes=[]
            )

        message, entities = (await utils.parse_text_entities(
            client, self.caption, self.parse_mode, self.caption_entities
        )).values()

        return raw.types.InputBotInlineResult(
            id=self.id,
            type=self.type,
            title=self.title,
            thumb=thumb,
            content=animation,
            send_message=(
                await self.input_message_content.write(client, self.reply_markup)
                if self.input_message_content
                else raw.types.InputBotInlineMessageMediaAuto(
                    reply_markup=await self.reply_markup.write(client) if self.reply_markup else None,
                    message=message,
                    entities=entities
                )
            )
        )
