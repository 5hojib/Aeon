import asyncio
from typing import Union, List, Iterable

import telegram
from telegram import raw
from telegram import types


class GetUsers:
    async def get_users(
        self: "telegram.Client",
        user_ids: Union[int, str, Iterable[Union[int, str]]]
    ) -> Union["types.User", List["types.User"]]:
        is_iterable = not isinstance(user_ids, (int, str))
        user_ids = list(user_ids) if is_iterable else [user_ids]
        user_ids = await asyncio.gather(*[self.resolve_peer(i) for i in user_ids])

        r = await self.invoke(
            raw.functions.users.GetUsers(
                id=user_ids
            )
        )

        users = types.List()

        for i in r:
            users.append(types.User._parse(self, i))

        return users if is_iterable else users[0]
