from telegram import raw
from typing import List
from ..object import Object

class ExportedStoryLink(Object):
    def __init__(
            self, *,
            link: str
    ):
        super().__init__()

        self.link = link

    @staticmethod
    def _parse(exportedstorylink: "raw.types.ExportedStoryLink") -> "ExportedStoryLink":
        return ExportedStoryLink(
            link=getattr(exportedstorylink,"link", None)
        )
