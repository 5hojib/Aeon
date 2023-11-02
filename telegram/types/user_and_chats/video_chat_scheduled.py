from datetime import datetime

from telegram import raw, utils
from ..object import Object


class VideoChatScheduled(Object):
    def __init__(
        self, *,
        start_date: datetime
    ):
        super().__init__()

        self.start_date = start_date

    @staticmethod
    def _parse(action: "raw.types.MessageActionGroupCallScheduled") -> "VideoChatScheduled":
        return VideoChatScheduled(start_date=utils.timestamp_to_datetime(action.schedule_date))
