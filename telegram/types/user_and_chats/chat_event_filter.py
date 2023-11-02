from telegram import raw
from ..object import Object


class ChatEventFilter(Object):
    def __init__(
        self, *,
        new_restrictions: bool = False,
        new_privileges: bool = False,
        new_members: bool = False,
        chat_info: bool = False,
        chat_settings: bool = False,
        invite_links: bool = False,
        deleted_messages: bool = False,
        edited_messages: bool = False,
        pinned_messages: bool = False,
        leaving_members: bool = False,
        video_chats: bool = False
    ):
        super().__init__()

        self.new_restrictions = new_restrictions
        self.new_privileges = new_privileges
        self.new_members = new_members
        self.chat_info = chat_info
        self.chat_settings = chat_settings
        self.invite_links = invite_links
        self.deleted_messages = deleted_messages
        self.edited_messages = edited_messages
        self.pinned_messages = pinned_messages
        self.leaving_members = leaving_members
        self.video_chats = video_chats

    def write(self) -> "raw.base.ChannelAdminLogEventsFilter":
        join = False
        leave = False
        invite = False
        ban = False
        unban = False
        kick = False
        unkick = False
        promote = False
        demote = False
        info = False
        settings = False
        pinned = False
        edit = False
        delete = False
        group_call = False
        invites = False

        if self.new_restrictions:
            ban = True
            unban = True
            kick = True
            unkick = True

        if self.new_privileges:
            promote = True
            demote = True

        if self.new_members:
            join = True
            invite = True

        if self.chat_info:
            info = True

        if self.chat_settings:
            settings = True

        if self.invite_links:
            invites = True

        if self.deleted_messages:
            delete = True

        if self.edited_messages:
            edit = True

        if self.pinned_messages:
            pinned = True

        if self.leaving_members:
            leave = True

        if self.video_chats:
            group_call = True

        return raw.types.ChannelAdminLogEventsFilter(
            join=join,
            leave=leave,
            invite=invite,
            ban=ban,
            unban=unban,
            kick=kick,
            unkick=unkick,
            promote=promote,
            demote=demote,
            info=info,
            settings=settings,
            pinned=pinned,
            edit=edit,
            delete=delete,
            group_call=group_call,
            invites=invites
        )
