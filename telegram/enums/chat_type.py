from enum import auto

from .auto_name import AutoName


class ChatType(AutoName):
    """Chat type enumeration used in :obj:`~telegram.types.Chat`."""

    PRIVATE = auto()
    "Chat is a private chat with a user"

    BOT = auto()
    "Chat is a private chat with a bot"

    GROUP = auto()
    "Chat is a basic group"

    SUPERGROUP = auto()
    "Chat is a supergroup"

    CHANNEL = auto()
    "Chat is a channel"
