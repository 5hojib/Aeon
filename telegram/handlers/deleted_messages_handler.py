from typing import List, Callable

import telegram
from telegram.filters import Filter
from telegram.types import Message
from .handler import Handler


class DeletedMessagesHandler(Handler):
    def __init__(self, callback: Callable, filters: Filter = None):
        super().__init__(callback, filters)

    async def check(self, client: "telegram.Client", messages: List[Message]):
        for message in messages:
            if await super().check(client, message):
                return True
        else:
            return False
