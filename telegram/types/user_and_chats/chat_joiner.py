from datetime import datetime
from typing import Dict

import telegram
from telegram import raw, types, utils
from ..object import Object


class ChatJoiner(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client",
        user: "types.User",
        date: datetime = None,
        bio: str = None,
        pending: bool = None,
        approved_by: "types.User" = None,
    ):
        super().__init__(client)

        self.user = user
        self.date = date
        self.bio = bio
        self.pending = pending
        self.approved_by = approved_by

    @staticmethod
    def _parse(
        client: "telegram.Client",
        joiner: "raw.base.ChatInviteImporter",
        users: Dict[int, "raw.base.User"],
    ) -> "ChatJoiner":
        return ChatJoiner(
            user=types.User._parse(client, users[joiner.user_id]),
            date=utils.timestamp_to_datetime(joiner.date),
            pending=joiner.requested,
            bio=joiner.about,
            approved_by=(
                types.User._parse(client, users[joiner.approved_by])
                if joiner.approved_by
                else None
            ),
            client=client
        )
