import telegram
from telegram import raw
from telegram import types
from ..object import Object
from ... import utils


class Dialog(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        chat: "types.Chat",
        top_message: "types.Message",
        unread_messages_count: int,
        unread_mentions_count: int,
        unread_mark: bool,
        is_pinned: bool
    ):
        super().__init__(client)

        self.chat = chat
        self.top_message = top_message
        self.unread_messages_count = unread_messages_count
        self.unread_mentions_count = unread_mentions_count
        self.unread_mark = unread_mark
        self.is_pinned = is_pinned

    @staticmethod
    def _parse(client, dialog: "raw.types.Dialog", messages, users, chats) -> "Dialog":
        return Dialog(
            chat=types.Chat._parse_dialog(client, dialog.peer, users, chats),
            top_message=messages.get(utils.get_peer_id(dialog.peer)),
            unread_messages_count=dialog.unread_count,
            unread_mentions_count=dialog.unread_mentions_count,
            unread_mark=dialog.unread_mark,
            is_pinned=dialog.pinned,
            client=client
        )
