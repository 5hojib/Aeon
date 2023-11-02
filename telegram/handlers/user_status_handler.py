from typing import Callable

from .handler import Handler


class UserStatusHandler(Handler):
    def __init__(self, callback: Callable, filters=None):
        super().__init__(callback, filters)
