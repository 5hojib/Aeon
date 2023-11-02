from datetime import datetime
from typing import Dict
from typing import Optional

import telegram
from telegram import raw, utils
from telegram import types
from ..object import Object


class ChatInviteLink(Object):
    def __init__(
        self, *,
        invite_link: str,
        date: datetime,
        is_primary: bool = None,
        is_revoked: bool = None,
        creator: "types.User" = None,
        name: str = None,
        creates_join_request: bool = None,
        start_date: datetime = None,
        expire_date: datetime = None,
        member_limit: int = None,
        member_count: int = None,
        pending_join_request_count: int = None
    ):
        super().__init__()

        self.invite_link = invite_link
        self.date = date
        self.is_primary = is_primary
        self.is_revoked = is_revoked
        self.creator = creator
        self.name = name
        self.creates_join_request = creates_join_request
        self.start_date = start_date
        self.expire_date = expire_date
        self.member_limit = member_limit
        self.member_count = member_count
        self.pending_join_request_count = pending_join_request_count

    @staticmethod
    def _parse(
        client: "telegram.Client",
        invite: "raw.base.ExportedChatInvite",
        users: Dict[int, "raw.types.User"] = None
    ) -> Optional["ChatInviteLink"]:
        if not isinstance(invite, raw.types.ChatInviteExported):
            return None

        creator = (
            types.User._parse(client, users[invite.admin_id])
            if users is not None
            else None
        )

        return ChatInviteLink(
            invite_link=invite.link,
            date=utils.timestamp_to_datetime(invite.date),
            is_primary=invite.permanent,
            is_revoked=invite.revoked,
            creator=creator,
            name=invite.title,
            creates_join_request=invite.request_needed,
            start_date=utils.timestamp_to_datetime(invite.start_date),
            expire_date=utils.timestamp_to_datetime(invite.expire_date),
            member_limit=invite.usage_limit,
            member_count=invite.usage,
            pending_join_request_count=invite.requested
        )
