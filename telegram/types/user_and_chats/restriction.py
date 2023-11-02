from telegram import raw
from ..object import Object


class Restriction(Object):
    def __init__(self, *, platform: str, reason: str, text: str):
        super().__init__(None)

        self.platform = platform
        self.reason = reason
        self.text = text

    @staticmethod
    def _parse(restriction: "raw.types.RestrictionReason") -> "Restriction":
        return Restriction(
            platform=restriction.platform,
            reason=restriction.reason,
            text=restriction.text
        )
