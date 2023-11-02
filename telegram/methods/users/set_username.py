from typing import Optional

import telegram
from telegram import raw


class SetUsername:
    async def set_username(
        self: "telegram.Client",
        username: Optional[str]
    ) -> bool:
        return bool(
            await self.invoke(
                raw.functions.account.UpdateUsername(
                    username=username or ""
                )
            )
        )
