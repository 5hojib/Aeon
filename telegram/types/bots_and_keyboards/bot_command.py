from telegram import raw

from ..object import Object


class BotCommand(Object):
    """A bot command with the standard slash "/" prefix.

    Parameters:
        command (``str``):
            Text of the command; 1-32 characters.
            Can contain only lowercase English letters, digits and underscores.

        description (``str``):
            Description of the command; 1-256 characters.
    """

    def __init__(self, command: str, description: str):
        super().__init__()

        self.command = command
        self.description = description

    def write(self) -> "raw.types.BotCommand":
        return raw.types.BotCommand(
            command=self.command,
            description=self.description,
        )

    @staticmethod
    def read(c: "raw.types.BotCommand") -> "BotCommand":
        return BotCommand(
            command=c.command,
            description=c.description
        )
