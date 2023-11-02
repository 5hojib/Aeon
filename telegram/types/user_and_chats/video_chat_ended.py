from telegram import raw
from ..object import Object


class VideoChatEnded(Object):
    def __init__(
        self, *,
        duration: int
    ):
        super().__init__()

        self.duration = duration

    @staticmethod
    def _parse(action: "raw.types.MessageActionGroupCall") -> "VideoChatEnded":
        return VideoChatEnded(duration=action.duration)
