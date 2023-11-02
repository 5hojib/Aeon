from telegram import raw
from ..object import Object


class ForumTopicEdited(Object):
    def __init__(
        self, *,
        title: str = None,
        icon_color: int = None,
        icon_emoji_id: str = None
    ):
        super().__init__()

        self.title = title
        self.icon_color = icon_color
        self.icon_emoji_id = icon_emoji_id

    @staticmethod
    def _parse(action: "raw.types.MessageActionTopicEdit") -> "ForumTopicEdited":


        return ForumTopicEdited(
            title=getattr(action,"title", None),
            icon_color=getattr(action,"icon_color", None),
            icon_emoji_id=getattr(action,"icon_emoji_id", None)
        )
