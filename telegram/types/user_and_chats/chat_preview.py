from typing import List

import telegram
from telegram import raw
from telegram import types
from ..object import Object


class ChatPreview(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        title: str,
        type: str,
        members_count: int,
        photo: "types.Photo" = None,
        members: List["types.User"] = None
    ):
        super().__init__(client)

        self.title = title
        self.type = type
        self.members_count = members_count
        self.photo = photo
        self.members = members

    @staticmethod
    def _parse(client, chat_invite: "raw.types.ChatInvite") -> "ChatPreview":
        return ChatPreview(
            title=chat_invite.title,
            type=("group" if not chat_invite.channel else
                  "channel" if chat_invite.broadcast else
                  "supergroup"),
            members_count=chat_invite.participants_count,
            photo=types.Photo._parse(client, chat_invite.photo),
            members=[types.User._parse(client, user) for user in chat_invite.participants] or None,
            client=client
        )
