from enum import auto

from .auto_name import AutoName


class UserStatus(AutoName):
    """User status enumeration used in :obj:`~telegram.types.User`."""

    ONLINE = auto()
    """User is online"""

    OFFLINE = auto()
    """User is offline"""

    RECENTLY = auto()
    """User was seen recently"""

    LAST_WEEK = auto()
    """User was seen last week"""

    LAST_MONTH = auto()
    """User was seen last month"""

    LONG_AGO = auto()
    """User was seen long ago"""
