from telegram import raw
from ..object import Object


class InputReplyToStory(Object):
    def __init__(
        self, *,
        user_id: "raw.types.InputUser" = None,
        story_id: int = None
    ):
        super().__init__()

        self.user_id = user_id
        self.story_id = story_id

    def write(self):
        return raw.types.InputReplyToStory(
            user_id=self.user_id,
            story_id=self.story_id
        ).write()
