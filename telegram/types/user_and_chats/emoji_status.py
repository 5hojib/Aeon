from datetime import datetime
from typing import Optional

import telegram
from telegram import raw
from telegram import utils
from ..object import Object


class EmojiStatus(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        custom_emoji_id: int,
        until_date: Optional[datetime] = None
    ):
        super().__init__(client)

        self.custom_emoji_id = custom_emoji_id
        self.until_date = until_date

    @staticmethod
    def _parse(client, emoji_status: "raw.base.EmojiStatus") -> Optional["EmojiStatus"]:
        if isinstance(emoji_status, raw.types.EmojiStatus):
            return EmojiStatus(
                client=client,
                custom_emoji_id=emoji_status.document_id
            )

        if isinstance(emoji_status, raw.types.EmojiStatusUntil):
            return EmojiStatus(
                client=client,
                custom_emoji_id=emoji_status.document_id,
                until_date=utils.timestamp_to_datetime(emoji_status.until)
            )

        return None

    def write(self):
        if self.until_date:
            return raw.types.EmojiStatusUntil(
                document_id=self.custom_emoji_id,
                until=utils.datetime_to_timestamp(self.until_date)
            )

        return raw.types.EmojiStatus(
            document_id=self.custom_emoji_id
        )
