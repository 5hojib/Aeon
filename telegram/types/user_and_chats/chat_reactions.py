from typing import Optional, List

import telegram
from telegram import raw, types
from ..object import Object


class ChatReactions(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        all_are_enabled: Optional[bool] = None,
        allow_custom_emoji: Optional[bool] = None,
        reactions: Optional[List["types.Reaction"]] = None,
    ):
        super().__init__(client)

        self.all_are_enabled = all_are_enabled
        self.allow_custom_emoji = allow_custom_emoji
        self.reactions = reactions

    @staticmethod
    def _parse(client, chat_reactions: "raw.base.ChatReactions") -> Optional["ChatReactions"]:
        if isinstance(chat_reactions, raw.types.ChatReactionsAll):
            return ChatReactions(
                client=client,
                all_are_enabled=True,
                allow_custom_emoji=chat_reactions.allow_custom
            )

        if isinstance(chat_reactions, raw.types.ChatReactionsSome):
            return ChatReactions(
                client=client,
                reactions=[types.Reaction._parse(client, reaction)
                           for reaction in chat_reactions.reactions]
            )

        return None
