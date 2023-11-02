from datetime import datetime

from telegram import raw, utils
from telegram import types
from ..object import Object


class InviteLinkImporter(Object):
    def __init__(
        self, *,
        date: datetime,
        user: "types.User"
    ):
        super().__init__(None)

        self.date = date
        self.user = user

    @staticmethod
    def _parse(client, invite_importers: "raw.types.messages.ChatInviteImporters"):
        importers = types.List()

        d = {i.id: i for i in invite_importers.users}

        for j in invite_importers.importers:
            importers.append(
                InviteLinkImporter(
                    date=utils.timestamp_to_datetime(j.date),
                    user=types.User._parse(client=None, user=d[j.user_id])
                )
            )

        return importers
