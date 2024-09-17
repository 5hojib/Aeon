from pyrogram.enums import ChatType
from pyrogram.filters import create

from bot import OWNER_ID, user_data
from bot.helper.aeon_utils.access_check import get_chat_info


class CustomFilters:
    @staticmethod
    async def owner_filter(_, message):
        user = message.from_user or message.sender_chat
        return user.id == OWNER_ID

    owner = create(owner_filter)

    @staticmethod
    async def authorized_user(_, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        chat_id = message.chat.id
        return (
            uid == OWNER_ID
            or (
                uid in user_data
                and (
                    user_data[uid].get("is_auth", False)
                    or user_data[uid].get("is_sudo", False)
                )
            )
            or (chat_id in user_data and user_data[chat_id].get("is_auth", False))
        )

    authorized = create(authorized_user)

    @staticmethod
    async def authorized_usetting(_, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        chat_id = message.chat.id

        if (
            uid == OWNER_ID
            or (
                uid in user_data
                and (
                    user_data[uid].get("is_auth", False)
                    or user_data[uid].get("is_sudo", False)
                )
            )
            or (chat_id in user_data and user_data[chat_id].get("is_auth", False))
        ):
            return True

        if message.chat.type == ChatType.PRIVATE:
            for channel_id, data in user_data.items():
                if data.get("is_auth") and str(channel_id).startswith("-100"):
                    try:
                        if await (await get_chat_info(str(channel_id))).get_member(
                            uid
                        ):
                            return True
                    except Exception:
                        continue

        return False

    authorized_uset = create(authorized_usetting)

    @staticmethod
    async def sudo_user(_, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return uid == OWNER_ID or (
            uid in user_data and user_data[uid].get("is_sudo", False)
        )

    sudo = create(sudo_user)
