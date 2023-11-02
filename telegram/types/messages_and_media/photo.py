from datetime import datetime
from typing import List

import telegram
from telegram import raw, utils
from telegram import types
from telegram.file_id import FileId, FileType, FileUniqueId, FileUniqueType, ThumbnailSource
from ..object import Object


class Photo(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        file_id: str,
        file_unique_id: str,
        width: int,
        height: int,
        file_size: int,
        date: datetime,
        ttl_seconds: int = None,
        thumbs: List["types.Thumbnail"] = None
    ):
        super().__init__(client)

        self.file_id = file_id
        self.file_unique_id = file_unique_id
        self.width = width
        self.height = height
        self.file_size = file_size
        self.date = date
        self.ttl_seconds = ttl_seconds
        self.thumbs = thumbs

    @staticmethod
    def _parse(client, photo: "raw.types.Photo", ttl_seconds: int = None) -> "Photo":
        if isinstance(photo, raw.types.Photo):
            photos: List[raw.types.PhotoSize] = []

            for p in photo.sizes:
                if isinstance(p, raw.types.PhotoSize):
                    photos.append(p)

                if isinstance(p, raw.types.PhotoSizeProgressive):
                    photos.append(
                        raw.types.PhotoSize(
                            type=p.type,
                            w=p.w,
                            h=p.h,
                            size=max(p.sizes)
                        )
                    )

            photos.sort(key=lambda p: p.size)

            main = photos[-1]

            return Photo(
                file_id=FileId(
                    file_type=FileType.PHOTO,
                    dc_id=photo.dc_id,
                    media_id=photo.id,
                    access_hash=photo.access_hash,
                    file_reference=photo.file_reference,
                    thumbnail_source=ThumbnailSource.THUMBNAIL,
                    thumbnail_file_type=FileType.PHOTO,
                    thumbnail_size=main.type,
                    volume_id=0,
                    local_id=0
                ).encode(),
                file_unique_id=FileUniqueId(
                    file_unique_type=FileUniqueType.DOCUMENT,
                    media_id=photo.id
                ).encode(),
                width=main.w,
                height=main.h,
                file_size=main.size,
                date=utils.timestamp_to_datetime(photo.date),
                ttl_seconds=ttl_seconds,
                thumbs=types.Thumbnail._parse(client, photo),
                client=client
            )
