from telegram import raw
from ..object import Object


class ForumTopicCreated(Object):
    def __init__(
        self, *,
        id: int,
        title: str,
        icon_color: int,
        icon_emoji_id: int = None
    ):
        super().__init__()

        self.id = id
        self.title = title
        self.icon_color = icon_color
        self.icon_emoji_id = icon_emoji_id

    @staticmethod
    def _parse(message: "raw.base.Message") -> "ForumTopicCreated":


        return ForumTopicCreated(
            id=getattr(message, "id", None),
            title=getattr(message.action,"title", None),
            icon_color=getattr(message.action,"icon_color", None),
            icon_emoji_id=getattr(message.action,"icon_emoji_id", None)
        )
