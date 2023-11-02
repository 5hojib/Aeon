from typing import List, Dict

from telegram import raw, types
from ..object import Object


class VideoChatMembersInvited(Object):
    def __init__(
        self, *,
        users: List["types.User"]
    ):
        super().__init__()

        self.users = users

    @staticmethod
    def _parse(
        client,
        action: "raw.types.MessageActionInviteToGroupCall",
        users: Dict[int, "raw.types.User"]
    ) -> "VideoChatMembersInvited":
        users = [types.User._parse(client, users[i]) for i in action.users]

        return VideoChatMembersInvited(users=users)
