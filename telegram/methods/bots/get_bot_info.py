from typing import Union

import telegram
from telegram import raw


class GetBotInfo:
    async def get_bot_info(
        self: "telegram.Client",
        lang_code: str,
        bot: Union[int, str] = None
    ) -> telegram.types.BotInfo:
        peer = None
        if bot:
            peer = await self.resolve_peer(bot)
        r = await self.invoke(raw.functions.bots.GetBotInfo(lang_code=lang_code, bot=peer))
        return telegram.types.BotInfo._parse(r)
