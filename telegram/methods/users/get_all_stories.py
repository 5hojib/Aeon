import logging
from typing import AsyncGenerator, Optional

import telegram
from telegram import raw
from telegram import types

log = logging.getLogger(__name__)

class GetAllStories:
    async def get_all_stories(
        self: "telegram.Client"
    ) -> Optional[AsyncGenerator["types.Story", None]]:

        rpc = raw.functions.stories.GetAllStories()
        r = await self.invoke(rpc, sleep_threshold=-1)

        for peer_story in r.peer_stories:
            for story in peer_story.stories:
                yield await types.Story._parse(self, story, peer_story.peer)
