from typing import Dict

import telegram
from telegram import raw
from telegram import types
from ..object import Object


class ChatAdminWithInviteLinks(Object):
    def __init__(
        self, *,
        admin: "types.User",
        chat_invite_links_count: int,
        revoked_chat_invite_links_count: int = None
    ):
        super().__init__()

        self.admin = admin
        self.chat_invite_links_count = chat_invite_links_count
        self.revoked_chat_invite_links_count = revoked_chat_invite_links_count

    @staticmethod
    def _parse(
        client: "telegram.Client",
        admin: "raw.types.ChatAdminWithInvites",
        users: Dict[int, "raw.types.User"] = None
    ) -> "ChatAdminWithInviteLinks":
        return ChatAdminWithInviteLinks(
            admin=types.User._parse(client, users[admin.admin_id]),
            chat_invite_links_count=admin.invites_count,
            revoked_chat_invite_links_count=admin.revoked_invites_count
        )
