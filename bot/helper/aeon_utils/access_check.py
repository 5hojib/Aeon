from re import IGNORECASE, escape, search
from time import time
from uuid import uuid4

from pyrogram.errors import RPCError, PeerIdInvalid, UserNotParticipant

from bot import (
    LOGGER,
    OWNER_ID,
    bot,
    user_data,
    config_dict,
    bot_username,
)
from bot.helper.ext_utils.db_handler import Database
from bot.helper.aeon_utils.shorteners import short
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.ext_utils.help_messages import nsfw_keywords
from bot.helper.telegram_helper.button_build import ButtonMaker


async def error_check(message):
    msg, button = [], None
    user_id = message.from_user.id
    token_timeout = config_dict["TOKEN_TIMEOUT"]

    if message.chat.type != message.chat.type.BOT:
        if FSUB_IDS := config_dict["FSUB_IDS"]:
            join_button = {}
            for channel_id in FSUB_IDS.split():
                chat = await get_chat_info(int(channel_id))
                if not chat:
                    continue

                try:
                    await chat.get_member(message.from_user.id)
                except UserNotParticipant:
                    invite_link = (
                        f"https://t.me/{chat.username}"
                        if chat.username
                        else chat.invite_link
                    )
                    join_button[chat.title] = invite_link
                except RPCError as e:
                    LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
                except Exception as e:
                    LOGGER.error(f"{e} for {channel_id}")

            if join_button:
                button = button or ButtonMaker()
                for title, link in join_button.items():
                    button.url(f"Join {title}", link, "footer")
                msg.append("You haven't joined our channel/group yet!")

        if not token_timeout or user_id in {
            OWNER_ID,
            user_data.get(user_id, {}).get("is_sudo"),
        }:
            try:
                temp_msg = await message._client.send_message(
                    chat_id=user_id, text="<b>Checking Access...</b>"
                )
                await temp_msg.delete()
            except Exception:
                button = button or ButtonMaker()
                button.callback("Start", f"aeon {user_id} private", "header")
                msg.append("You haven't initiated the bot in a private message!")

    if user_id not in {
        OWNER_ID,
        1781717085,
        user_data.get(user_id, {}).get("is_sudo"),
    }:
        token_msg, button = await token_check(user_id, button)
        if token_msg:
            msg.append(token_msg)

    if await nsfw_precheck(message):
        msg.append("NSFW detected")

    if msg:
        username = message.from_user.username
        tag = f"@{username}" if username else message.from_user.mention
        final_msg = f"Hey, <b>{tag}</b>!\n"
        for i, m in enumerate(msg, 1):
            final_msg += f"\n<blockquote><b>{i}</b>: {m}</blockquote>"

        if button:
            button = button.menu(2)
        return final_msg, button

    return None, None


async def get_chat_info(channel_id):
    try:
        return await bot.get_chat(channel_id)
    except PeerIdInvalid as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        return None


def is_nsfw(text):
    pattern = (
        r"(?:^|\W|_)(?:"
        + "|".join(escape(keyword) for keyword in nsfw_keywords)
        + r")(?:$|\W|_)"
    )
    return bool(search(pattern, text, flags=IGNORECASE))


def is_nsfw_data(data):
    if isinstance(data, list):
        return any(
            is_nsfw(item.get("name", ""))
            if isinstance(item, dict)
            else is_nsfw(item)
            for item in data
        )
    if isinstance(data, dict):
        return any(is_nsfw(item["filename"]) for item in data.get("contents", []))
    return False


async def nsfw_precheck(message):
    if is_nsfw(message.text):
        return True

    reply_to = message.reply_to_message
    if not reply_to:
        return False

    for attr in ["document", "video"]:
        if hasattr(reply_to, attr) and getattr(reply_to, attr):
            file_name = getattr(reply_to, attr).file_name
            if file_name and is_nsfw(file_name):
                return True

    return any(
        is_nsfw(getattr(reply_to, attr))
        for attr in ["caption", "text"]
        if hasattr(reply_to, attr) and getattr(reply_to, attr)
    )


async def check_is_paid(chat, uid):
    try:
        await chat.get_member(uid)
        return True
    except UserNotParticipant:
        return False
    except Exception as e:
        LOGGER.error(f"{e} for {chat.id}")
        return False


async def is_paid(user_id):
    if chat := await get_chat_info(int(config_dict["PAID_CHAT_ID"])):
        return await check_is_paid(chat, user_id)
    return True


async def token_check(user_id, button=None):
    token_timeout = config_dict["TOKEN_TIMEOUT"]
    if not token_timeout or user_id == OWNER_ID:
        return None, button
    if config_dict["PAID_CHAT_ID"] and await is_paid(user_id):
        return None, button

    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    data["time"] = await Database().get_token_expiry(user_id)
    expire = data.get("time")
    isExpired = expire is None or (time() - expire) > token_timeout
    if isExpired:
        token = data["token"] if expire is None and "token" in data else str(uuid4())
        if expire is not None:
            del data["time"]
        data["token"] = token
        await Database().update_user_token(user_id, token)
        user_data[user_id] = data

        time_str = get_readable_time(token_timeout, True)
        button = button or ButtonMaker()
        short_link = await short(f"https://telegram.me/{bot_username}?start={token}")
        button.url("Collect token", short_link)
        msg = "Your token has expired, please collect a new token"
        if config_dict["PAID_CHAT_ID"] and config_dict["PAID_CHAT_LINK"]:
            msg += " or subscribe to the paid channel for no token."
            button.url("Subscribe", config_dict["PAID_CHAT_LINK"])

        return (msg + f"\n<b>It will expire after {time_str}</b>!"), button

    return None, button
