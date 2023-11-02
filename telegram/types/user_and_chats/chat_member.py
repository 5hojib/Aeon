from datetime import datetime
from typing import Union, Dict

import telegram
from telegram import raw, types, utils, enums
from ..object import Object


class ChatMember(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        status: "enums.ChatMemberStatus",
        user: "types.User" = None,
        chat: "types.Chat" = None,
        custom_title: str = None,
        until_date: datetime = None,
        joined_date: datetime = None,
        invited_by: "types.User" = None,
        promoted_by: "types.User" = None,
        restricted_by: "types.User" = None,
        is_member: bool = None,
        can_be_edited: bool = None,
        permissions: "types.ChatPermissions" = None,
        privileges: "types.ChatPrivileges" = None
    ):
        super().__init__(client)

        self.status = status
        self.user = user
        self.chat = chat
        self.custom_title = custom_title
        self.until_date = until_date
        self.joined_date = joined_date
        self.invited_by = invited_by
        self.promoted_by = promoted_by
        self.restricted_by = restricted_by
        self.is_member = is_member
        self.can_be_edited = can_be_edited
        self.permissions = permissions
        self.privileges = privileges

    @staticmethod
    def _parse(
        client: "telegram.Client",
        member: Union["raw.base.ChatParticipant", "raw.base.ChannelParticipant"],
        users: Dict[int, "raw.base.User"],
        chats: Dict[int, "raw.base.Chat"]
    ) -> "ChatMember":
        # Chat participants
        if isinstance(member, raw.types.ChatParticipant):
            return ChatMember(
                status=enums.ChatMemberStatus.MEMBER,
                user=types.User._parse(client, users[member.user_id]),
                joined_date=utils.timestamp_to_datetime(member.date),
                invited_by=types.User._parse(client, users[member.inviter_id]),
                client=client
            )
        elif isinstance(member, raw.types.ChatParticipantAdmin):
            return ChatMember(
                status=enums.ChatMemberStatus.ADMINISTRATOR,
                user=types.User._parse(client, users[member.user_id]),
                joined_date=utils.timestamp_to_datetime(member.date),
                invited_by=types.User._parse(client, users[member.inviter_id]),
                client=client
            )
        elif isinstance(member, raw.types.ChatParticipantCreator):
            return ChatMember(
                status=enums.ChatMemberStatus.OWNER,
                user=types.User._parse(client, users[member.user_id]),
                client=client
            )

        # Channel participants
        if isinstance(member, raw.types.ChannelParticipant):
            return ChatMember(
                status=enums.ChatMemberStatus.MEMBER,
                user=types.User._parse(client, users[member.user_id]),
                joined_date=utils.timestamp_to_datetime(member.date),
                client=client
            )
        elif isinstance(member, raw.types.ChannelParticipantAdmin):
            return ChatMember(
                status=enums.ChatMemberStatus.ADMINISTRATOR,
                user=types.User._parse(client, users[member.user_id]),
                joined_date=utils.timestamp_to_datetime(member.date),
                promoted_by=types.User._parse(client, users[member.promoted_by]),
                invited_by=(
                    types.User._parse(client, users[member.inviter_id])
                    if member.inviter_id else None
                ),
                custom_title=member.rank,
                can_be_edited=member.can_edit,
                privileges=types.ChatPrivileges._parse(member.admin_rights),
                client=client
            )
        elif isinstance(member, raw.types.ChannelParticipantBanned):
            peer = member.peer
            peer_id = utils.get_raw_peer_id(peer)

            user = (
                types.User._parse(client, users[peer_id])
                if isinstance(peer, raw.types.PeerUser) else None
            )

            chat = (
                types.Chat._parse_chat(client, chats[peer_id])
                if not isinstance(peer, raw.types.PeerUser) else None
            )

            return ChatMember(
                status=(
                    enums.ChatMemberStatus.BANNED
                    if member.banned_rights.view_messages
                    else enums.ChatMemberStatus.RESTRICTED
                ),
                user=user,
                chat=chat,
                until_date=utils.timestamp_to_datetime(member.banned_rights.until_date),
                joined_date=utils.timestamp_to_datetime(member.date),
                is_member=not member.left,
                restricted_by=types.User._parse(client, users[member.kicked_by]),
                permissions=types.ChatPermissions._parse(member.banned_rights),
                client=client
            )
        elif isinstance(member, raw.types.ChannelParticipantCreator):
            return ChatMember(
                status=enums.ChatMemberStatus.OWNER,
                user=types.User._parse(client, users[member.user_id]),
                custom_title=member.rank,
                privileges=types.ChatPrivileges._parse(member.admin_rights),
                client=client
            )
        elif isinstance(member, raw.types.ChannelParticipantLeft):
            peer = member.peer
            peer_id = utils.get_raw_peer_id(peer)

            user = (
                types.User._parse(client, users[peer_id])
                if isinstance(peer, raw.types.PeerUser) else None
            )

            chat = (
                types.Chat._parse_chat(client, chats[peer_id])
                if not isinstance(peer, raw.types.PeerUser) else None
            )

            return ChatMember(
                status=enums.ChatMemberStatus.LEFT,
                user=user,
                chat=chat,
                client=client
            )
        elif isinstance(member, raw.types.ChannelParticipantSelf):
            return ChatMember(
                status=enums.ChatMemberStatus.MEMBER,
                user=types.User._parse(client, users[member.user_id]),
                joined_date=utils.timestamp_to_datetime(member.date),
                invited_by=types.User._parse(client, users[member.inviter_id]),
                client=client
            )
