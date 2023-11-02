from telegram import raw

from ..object import Object


class LoginUrl(Object):
    def __init__(
        self, *,
        url: str,
        forward_text: str = None,
        bot_username: str = None,
        request_write_access: str = None,
        button_id: int = None
    ):
        super().__init__()

        self.url = url
        self.forward_text = forward_text
        self.bot_username = bot_username
        self.request_write_access = request_write_access
        self.button_id = button_id

    @staticmethod
    def read(b: "raw.types.KeyboardButtonUrlAuth") -> "LoginUrl":
        return LoginUrl(
            url=b.url,
            forward_text=b.fwd_text,
            button_id=b.button_id
        )

    def write(self, text: str, bot: "raw.types.InputUser"):
        return raw.types.InputKeyboardButtonUrlAuth(
            text=text,
            url=self.url,
            bot=bot,
            fwd_text=self.forward_text,
            request_write_access=self.request_write_access
        )
