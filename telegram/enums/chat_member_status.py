from enum import auto
from .auto_name import AutoName


class ChatMemberStatus(AutoName):
    OWNER = auto()
    ADMINISTRATOR = auto()
    MEMBER = auto()
    RESTRICTED = auto()
    LEFT = auto()
    BANNED = auto()
