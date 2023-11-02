from typing import Union

import telegram
from telegram import raw


class GetChatInviteLinkJoinersCount:
    async def get_chat_invite_link_joiners_count(
        self: "telegram.Client",
        chat_id: Union[int, str],
        invite_link: str
    ) -> int:
        r = await self.invoke(
            raw.functions.messages.GetChatInviteImporters(
                peer=await self.resolve_peer(chat_id),
                link=invite_link,
                limit=1,
                offset_date=0,
                offset_user=raw.types.InputUserEmpty()
            )
        )

        return r.count
