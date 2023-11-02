from typing import Optional

import telegram
from telegram import enums
from .html import HTML
from .markdown import Markdown


class Parser:
    def __init__(self, client: Optional["telegram.Client"]):
        self.client = client
        self.html = HTML(client)
        self.markdown = Markdown(client)

    async def parse(self, text: str, mode: Optional[enums.ParseMode] = None):
        text = str(text if text else "").strip()

        if mode is None:
            if self.client:
                mode = self.client.parse_mode
            else:
                mode = enums.ParseMode.DEFAULT

        if mode == enums.ParseMode.DEFAULT:
            return await self.markdown.parse(text)

        if mode == enums.ParseMode.MARKDOWN:
            return await self.markdown.parse(text, True)

        if mode == enums.ParseMode.HTML:
            return await self.html.parse(text)

        if mode == enums.ParseMode.DISABLED:
            return {"message": text, "entities": None}

        raise ValueError(f'Invalid parse mode "{mode}"')

    @staticmethod
    def unparse(text: str, entities: list, is_html: bool):
        if is_html:
            return HTML.unparse(text, entities)
        else:
            return Markdown.unparse(text, entities)
