import telegram
from telegram import raw
from telegram import types
from ..object import Object


class WebPagePreview(Object):
    def __init__(
        self,
        *,
        webpage: "types.WebPage",
        force_large_media: bool = None,
        force_small_media: bool = None,
        invert_media: bool = None
    ):
        super().__init__()

        self.webpage = webpage
        self.force_large_media = force_large_media
        self.force_small_media = force_small_media
        self.invert_media = invert_media

    @staticmethod
    def _parse(web_page_preview: "raw.types.MessageMediaVenue", invert_media: bool = None):
        return WebPagePreview(
            webpage=types.WebPageEmpty._parse(web_page_preview.webpage),
            force_large_media=web_page_preview.force_large_media,
            force_small_media=web_page_preview.force_small_media,
            invert_media=invert_media
        )
