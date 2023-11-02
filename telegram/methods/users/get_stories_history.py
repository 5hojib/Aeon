import logging
from typing import AsyncGenerator, Optional

import telegram
from telegram import raw
from telegram import types

log = logging.getLogger(__name__)

class GetUserStoriesHistory:
    async def get_stories_history(
        self: "telegram.Client",
        channel_id: int = None,
        limit: int = 0,
        offset_id: int = 0
    ) -> Optional[AsyncGenerator["types.Story", None]]:
        if channel_id:
            peer = await self.resolve_peer(channel_id)
        else:
            peer = await self.resolve_peer("me")

        rpc = raw.functions.stories.GetStoriesArchive(peer=peer, offset_id=offset_id, limit=limit)

        r = await self.invoke(rpc, sleep_threshold=-1)

        for story in r.stories:
            yield await types.Story._parse(self, story, peer)
