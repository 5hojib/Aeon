import telegram
from telegram import raw, types
from .menu_button import MenuButton


class MenuButtonWebApp(MenuButton):
    def __init__(
        self,
        text: str,
        web_app: "types.WebAppInfo"
    ):
        super().__init__("web_app")

        self.text = text
        self.web_app = web_app

    async def write(self, client: "telegram.Client") -> "raw.types.BotMenuButton":
        return raw.types.BotMenuButton(
            text=self.text,
            url=self.web_app.url
        )
