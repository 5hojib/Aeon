from telegram import raw
from ..object import Object


class MessageStory(Object):
    def __init__(
        self,
        *,
        from_id: int,
        story_id: int
    ):
        super().__init__()

        self.from_id = from_id
        self.story_id = story_id

    @staticmethod
    def _parse(message_story: "raw.types.MessageMediaStory") -> "MessageStory":
        if isinstance(message_story.peer, raw.types.PeerChannel):
            from_id = message_story.peer.channel_id
        else:
            from_id = message_story.peer.user_id
        return MessageStory(
            from_id=from_id,
            story_id=message_story.id
        )
