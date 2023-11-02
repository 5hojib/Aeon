from telegram import raw, utils
from ..object import Object


class SentWebAppMessage(Object):
    def __init__(
        self, *,
        inline_message_id: str,
    ):
        super().__init__()

        self.inline_message_id = inline_message_id

    @staticmethod
    def _parse(obj: "raw.types.WebViewMessageSent"):
        return SentWebAppMessage(inline_message_id=utils.pack_inline_message_id(obj.msg_id))
