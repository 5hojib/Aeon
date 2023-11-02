import telegram
from telegram import raw
from telegram import types
from ..object import Object


class WebPageEmpty(Object):
    def __init__(
        self,
        *,
        id: str,
        url: str
    ):
        super().__init__()

        self.id = id
        self.url = url

    @staticmethod
    def _parse(webpage: "raw.types.WebPageEmpty") -> "WebPageEmpty":

        return WebPageEmpty(
            id=str(webpage.id),
            url=webpage.url
        )
