from telegram import raw, types
from typing import Union
from ..object import Object


class ForumTopic(Object):
    def __init__(
        self,
        *,
        id: int,
        date: int,
        title: str,
        icon_color: int,
        top_message: int,
        read_inbox_max_id: int,
        read_outbox_max_id: int,
        unread_count: int,
        unread_mentions_count: int,
        unread_reactions_count: int,
        from_id: Union["types.PeerChannel", "types.PeerUser"],
        my: bool = None,
        closed: bool = None,
        pinned: bool = None,
        short: bool = None,
        icon_emoji_id: int = None,
    ):
        super().__init__()

        self.id = id
        self.date = date
        self.title = title
        self.icon_color = icon_color
        self.top_message = top_message
        self.read_inbox_max_id = read_inbox_max_id
        self.read_outbox_max_id = read_outbox_max_id
        self.unread_count = unread_count
        self.unread_mentions_count = unread_mentions_count
        self.unread_reactions_count = unread_reactions_count
        self.from_id = from_id
        self.my = my
        self.closed = closed
        self.pinned = pinned
        self.short = short
        self.icon_emoji_id = icon_emoji_id

    @staticmethod
    def _parse(forum_topic: "raw.types.forum_topic") -> "ForumTopic":
        from_id = forum_topic.from_id
        if isinstance(from_id, raw.types.PeerChannel):
            peer = types.PeerChannel._parse(from_id)
        if isinstance(from_id, raw.types.PeerUser):
            peer = types.PeerUser._parse(from_id)

        return ForumTopic(
            id=getattr(forum_topic,"id", None),
            date=getattr(forum_topic,"date", None),
            title=getattr(forum_topic,"title", None),
            icon_color=getattr(forum_topic,"icon_color", None),
            top_message=getattr(forum_topic,"top_message", None),
            read_inbox_max_id=getattr(forum_topic,"read_inbox_max_id", None),
            read_outbox_max_id=getattr(forum_topic,"read_outbox_max_id", None),
            unread_count=getattr(forum_topic,"unread_count", None),
            unread_mentions_count=getattr(forum_topic,"unread_mentions_count", None),
            unread_reactions_count=getattr(forum_topic,"unread_reactions_count", None),
            from_id=peer,
            my=getattr(forum_topic,"my", None),
            closed=getattr(forum_topic,"closed", None),
            pinned=getattr(forum_topic,"pinned", None),
            short=getattr(forum_topic,"short", None),
            icon_emoji_id=getattr(forum_topic,"icon_emoji_id", None),
        )
