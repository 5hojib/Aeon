import telegram
from telegram import raw

from ..object import Object


class ForceReply(Object):
    def __init__(
        self,
        selective: bool = None,
        placeholder: str = None
    ):
        super().__init__()

        self.selective = selective
        self.placeholder = placeholder

    @staticmethod
    def read(b):
        return ForceReply(
            selective=b.selective,
            placeholder=b.placeholder
        )

    async def write(self, _: "telegram.Client"):
        return raw.types.ReplyKeyboardForceReply(
            single_use=True,
            selective=self.selective or None,
            placeholder=self.placeholder or None
        )
