from telegram import raw

from ..object import Object


class BotInfo(Object):
    def __init__(self, name: str, about: str, description: str):
        super().__init__()

        self.name = name
        self.about = about
        self.description = description

    
    @staticmethod
    def _parse(bot_info: "raw.types.bots.BotInfo") -> "BotInfo":
        return BotInfo(
            name=getattr(bot_info,"name", None),
            about=getattr(bot_info,"about", None),
            description=getattr(bot_info,"description", None)
        )
