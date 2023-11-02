from telegram import raw
from ..object import Object


class Username(Object):
    def __init__(
        self, *,
        username: str,
        editable: bool = None,
        active: bool = None
    ):
        super().__init__()

        self.username = username
        self.editable = editable
        self.active = active

    @staticmethod
    def _parse(action: "raw.types.Username") -> "Username":


        return Username(
            username=getattr(action,"username", None),
            editable=getattr(action,"editable", None),
            active=getattr(action,"active", None)
        )
