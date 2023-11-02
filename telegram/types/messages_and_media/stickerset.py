from typing import List, Optional, Union

import telegram
from telegram import raw
from telegram.file_id import FileId, FileType, FileUniqueId, FileUniqueType, ThumbnailSource
from ..object import Object


class StickerSet(Object):
    def __init__(
        self,
        *,
        id: int,
        title: str,
        short_name: str,
        count: int,
        masks: bool = None,
        animated: bool = None,
        videos: bool = None,
        emojis: bool = None
    ):
        self.id = id
        self.title = title
        self.short_name = short_name
        self.count = count
        self.masks = masks
        self.animated = animated
        self.videos = videos
        self.emojis = emojis

    @staticmethod
    def _parse(stickerset: "raw.types.StickerSet") -> "StickerSet":

        return StickerSet(
            id=getattr(stickerset,"id", None),
            title=getattr(stickerset,"title", None),
            short_name=getattr(stickerset,"short_name", None),
            count=getattr(stickerset,"count", None),
            masks=getattr(stickerset,"masks", None),
            animated=getattr(stickerset,"animated", None),
            videos=getattr(stickerset,"videos", None),
            emojis=getattr(stickerset,"emojis", None)
        )
