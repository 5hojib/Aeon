from telegram import raw
from ..object import Object


class ChatPrivileges(Object):
    def __init__(
        self,
        *,
        can_manage_chat: bool = True,
        can_delete_messages: bool = False,
        can_manage_video_chats: bool = False,
        can_restrict_members: bool = False,
        can_promote_members: bool = False,
        can_change_info: bool = False,
        can_post_messages: bool = False,
        can_edit_messages: bool = False,
        can_invite_users: bool = False,
        can_pin_messages: bool = False,
        can_manage_topics: bool = False,
        is_anonymous: bool = False
    ):
        super().__init__(None)

        self.can_manage_chat: bool = can_manage_chat
        self.can_delete_messages: bool = can_delete_messages
        self.can_manage_video_chats: bool = can_manage_video_chats
        self.can_restrict_members: bool = can_restrict_members
        self.can_promote_members: bool = can_promote_members
        self.can_change_info: bool = can_change_info
        self.can_post_messages: bool = can_post_messages
        self.can_edit_messages: bool = can_edit_messages
        self.can_invite_users: bool = can_invite_users
        self.can_pin_messages: bool = can_pin_messages
        self.can_manage_topics: bool = can_manage_topics
        self.is_anonymous: bool = is_anonymous

    @staticmethod
    def _parse(admin_rights: "raw.base.ChatAdminRights") -> "ChatPrivileges":
        return ChatPrivileges(
            can_manage_chat=admin_rights.other,
            can_delete_messages=admin_rights.delete_messages,
            can_manage_video_chats=admin_rights.manage_call,
            can_restrict_members=admin_rights.ban_users,
            can_promote_members=admin_rights.add_admins,
            can_change_info=admin_rights.change_info,
            can_post_messages=admin_rights.post_messages,
            can_edit_messages=admin_rights.edit_messages,
            can_invite_users=admin_rights.invite_users,
            can_pin_messages=admin_rights.pin_messages,
            can_manage_topics=admin_rights.manage_topics,
            is_anonymous=admin_rights.anonymous
        )
