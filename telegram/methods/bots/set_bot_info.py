from typing import Union

import telegram
from telegram import raw


class SetBotInfo:
    async def set_bot_info(
        self: "telegram.Client",
        lang_code: str,
        bot: Union[int, str] = None,
        name: str = None,
        about: str = None,
        description: str = None
    ) -> bool:
        peer = None
        if bot:
            peer = await self.resolve_peer(bot)
        r = await self.invoke(raw.functions.bots.SetBotInfo(lang_code=lang_code, bot=peer, name=name, about=about, description=description))
        return bool(r)
