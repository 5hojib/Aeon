from typing import Callable

from .handler import Handler


class RawUpdateHandler(Handler):
    def __init__(self, callback: Callable):
        super().__init__(callback)
