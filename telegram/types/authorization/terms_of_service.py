from typing import List

from telegram import raw
from telegram import types
from ..object import Object


class TermsOfService(Object):
    def __init__(self, *, id: str, text: str, entities: List["types.MessageEntity"]):
        super().__init__()

        self.id = id
        self.text = text
        self.entities = entities

    @staticmethod
    def _parse(terms_of_service: "raw.types.help.TermsOfService") -> "TermsOfService":
        return TermsOfService(
            id=terms_of_service.id.data,
            text=terms_of_service.text,
            entities=[
                types.MessageEntity._parse(None, entity, {})
                for entity in terms_of_service.entities
            ] if terms_of_service.entities else None
        )
