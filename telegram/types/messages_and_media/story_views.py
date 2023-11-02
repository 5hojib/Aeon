from telegram import raw
from typing import List
from ..object import Object

class StoryViews(Object):
    def __init__(
            self, *,
            view_count: int,
            recent_viewers: List[int] = None
    ):
        super().__init__()

        self.view_count = view_count
        self.recent_viewers = recent_viewers

    @staticmethod
    def _parse(storyviews: "raw.types.StoryViews") -> "StoryViews":
        return StoryViews(
            view_count=getattr(storyviews,"view_count", None),
            recent_viewers=getattr(storyviews,"recent_viewers", None)
        )
