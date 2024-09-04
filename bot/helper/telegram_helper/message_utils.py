from re import match as re_match
from time import time
from random import choice
from asyncio import sleep
from traceback import format_exc

from aiofiles.os import remove as aioremove
from pyrogram.types import InputMediaPhoto
from pyrogram.errors import (
    RPCError,
    FloodWait,
    MediaEmpty,
    MessageEmpty,
    PeerIdInvalid,
    WebpageCurlFailed,
    MessageNotModified,
    ReplyMarkupInvalid,
    UserNotParticipant,
    PhotoInvalidDimensions,
)

from bot import (
    IMAGES,
    LOGGER,
    DELETE_LINKS,
    Interval,
    bot,
    user,
    status_reply_dict,
    download_dict_lock,
    status_reply_dict_lock,
)
from bot.helper.ext_utils.bot_utils import (
    SetInterval,
    sync_to_async,
    download_image_url,
    get_readable_message,
)
from bot.helper.ext_utils.exceptions import TgLinkError
from bot.helper.telegram_helper.button_build import ButtonMaker


async def send_message(message, text, buttons=None, photo=None):
    try:
        if photo:
            try:
                if photo == "Random":
                    photo = choice(IMAGES)
                return await message.reply_photo(
                    photo=photo,
                    reply_to_message_id=message.id,
                    caption=text,
                    reply_markup=buttons,
                    disable_notification=True,
                )
            except IndexError:
                pass
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                des_dir = await download_image_url(photo)
                await send_message(message, text, buttons, des_dir)
                await aioremove(des_dir)
                return None
            except Exception:
                LOGGER.error(format_exc())
        return await message.reply(
            text=text,
            quote=True,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await send_message(message, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await send_message(message, text, None, photo)
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)


async def sendCustomMsg(chat_id, text, buttons=None, photo=None):
    try:
        if photo:
            try:
                if photo == "Random":
                    photo = choice(IMAGES)
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=buttons,
                    disable_notification=True,
                )
            except IndexError:
                pass
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                des_dir = await download_image_url(photo)
                await sendCustomMsg(chat_id, text, buttons, des_dir)
                await aioremove(des_dir)
                return None
            except Exception:
                LOGGER.error(format_exc())
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendCustomMsg(chat_id, text, buttons, photo)
    except ReplyMarkupInvalid:
        return await sendCustomMsg(chat_id, text, None, photo)
    except Exception as e:
        LOGGER.error(format_exc())
        return str(e)


async def chat_info(channel_id):
    if channel_id.startswith("-100"):
        channel_id = int(channel_id)
    elif channel_id.startswith("@"):
        channel_id = channel_id.replace("@", "")
    else:
        return None
    try:
        return await bot.get_chat(channel_id)
    except PeerIdInvalid as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        return None


async def isAdmin(message, user_id=None):
    if message.chat.type == message.chat.type.PRIVATE:
        return None
    if user_id:
        member = await message.chat.get_member(user_id)
    else:
        member = await message.chat.get_member(message.from_user.id)
    return member.status in [member.status.ADMINISTRATOR, member.status.OWNER]


async def sendMultiMessage(chat_ids, text, buttons=None, photo=None):
    msg_dict = {}
    for channel_id in chat_ids.split():
        chat = await chat_info(channel_id)
        try:
            if photo:
                try:
                    if photo == "Random":
                        photo = choice(IMAGES)
                    sent = await bot.send_photo(
                        chat_id=chat.id,
                        photo=photo,
                        caption=text,
                        reply_markup=buttons,
                        disable_notification=True,
                    )
                    msg_dict[chat.id] = sent
                    continue
                except IndexError:
                    pass
                except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                    des_dir = await download_image_url(photo)
                    await sendMultiMessage(chat_ids, text, buttons, des_dir)
                    await aioremove(des_dir)
                    return None
                except Exception as e:
                    LOGGER.error(str(e))
            sent = await bot.send_message(
                chat_id=chat.id,
                text=text,
                disable_web_page_preview=True,
                disable_notification=True,
                reply_markup=buttons,
            )
            msg_dict[chat.id] = sent
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.2)
            return await sendMultiMessage(chat_ids, text, buttons, photo)
        except Exception as e:
            LOGGER.error(str(e))
            return str(e)
    return msg_dict


async def edit_message(message, text, buttons=None, photo=None):
    try:
        if message.media:
            if photo:
                return await message.edit_media(
                    InputMediaPhoto(photo, text), reply_markup=buttons
                )
            return await message.edit_caption(caption=text, reply_markup=buttons)
        await message.edit(
            text=text, disable_web_page_preview=True, reply_markup=buttons
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await edit_message(message, text, buttons, photo)
    except (MessageNotModified, MessageEmpty):
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendFile(message, file, caption=None, buttons=None):
    try:
        return await message.reply_document(
            document=file,
            quote=True,
            caption=caption,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendFile(message, file, caption)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def delete_message(message):
    try:
        await message.delete()
    except Exception as e:
        LOGGER.error(str(e))


async def one_minute_del(message):
    await sleep(60)
    await delete_message(message)


async def five_minute_del(message):
    await sleep(300)
    await delete_message(message)


async def delete_links(message):
    if DELETE_LINKS:
        if reply_to := message.reply_to_message:
            await delete_message(reply_to)
        await delete_message(message)


async def delete_all_messages():
    async with status_reply_dict_lock:
        try:
            for key, data in list(status_reply_dict.items()):
                del status_reply_dict[key]
                await delete_message(data[0])
        except Exception as e:
            LOGGER.error(str(e))


async def get_tg_link_content(link):
    message = None
    if link.startswith("https://t.me/"):
        private = False
        msg = re_match(
            r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9]+)", link
        )
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9]+)", link
        )
        if not user:
            raise TgLinkError("USER_SESSION_STRING required for this private link!")

    chat = msg.group(1)
    msg_id = int(msg.group(2))
    if chat.isdigit():
        chat = int(chat) if private else int(f"-100{chat}")

    if not private:
        try:
            message = await bot.get_messages(chat_id=chat, message_ids=msg_id)
            if message.empty:
                private = True
        except Exception as e:
            private = True
            if not user:
                raise e

    if private and user:
        try:
            user_message = await user.get_messages(chat_id=chat, message_ids=msg_id)
        except Exception as e:
            raise TgLinkError(
                f"You don't have access to this chat!. ERROR: {e}"
            ) from e
        if not user_message.empty:
            return user_message, "user"
        raise TgLinkError("Private: Please report!")
    if not private:
        return message, "bot"
    raise TgLinkError("Bot can't download from GROUPS without joining!")


async def update_all_messages(force=False):
    async with status_reply_dict_lock:
        if (
            not status_reply_dict
            or not Interval
            or (not force and time() - next(iter(status_reply_dict.values()))[1] < 3)
        ):
            return
        for chat_id in list(status_reply_dict.keys()):
            status_reply_dict[chat_id][1] = time()
    async with download_dict_lock:
        msg, buttons = await sync_to_async(get_readable_message)
    if msg is None:
        return
    async with status_reply_dict_lock:
        for chat_id in list(status_reply_dict.keys()):
            if (
                status_reply_dict[chat_id]
                and msg != status_reply_dict[chat_id][0].text
            ):
                rmsg = await edit_message(
                    status_reply_dict[chat_id][0], msg, buttons
                )
                if isinstance(rmsg, str) and rmsg.startswith("Telegram says: [400"):
                    del status_reply_dict[chat_id]
                    continue
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()


async def sendStatusMessage(msg):
    async with download_dict_lock:
        progress, buttons = await sync_to_async(get_readable_message)
    if progress is None:
        return
    async with status_reply_dict_lock:
        chat_id = msg.chat.id
        if chat_id in list(status_reply_dict.keys()):
            message = status_reply_dict[chat_id][0]
            await delete_message(message)
            del status_reply_dict[chat_id]
        message = await send_message(msg, progress, buttons)
        message.text = progress
        status_reply_dict[chat_id] = [message, time()]
        if not Interval:
            Interval.append(SetInterval(1, update_all_messages))


async def forcesub(message, ids, button=None):
    join_button = {}
    _msg = ""
    for channel_id in ids.split():
        chat = await chat_info(channel_id)
        try:
            await chat.get_member(message.from_user.id)
        except UserNotParticipant:
            if username := chat.username:
                invite_link = f"https://t.me/{username}"
            else:
                invite_link = chat.invite_link
            join_button[chat.title] = invite_link
        except RPCError as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        except Exception as e:
            LOGGER.error(f"{e} for {channel_id}")
    if join_button:
        if button is None:
            button = ButtonMaker()
        _msg = "You haven't joined our channel/group yet!"
        for key, value in join_button.items():
            button.url(f"Join {key}", value, "footer")
    return _msg, button


async def user_info(client, userId):
    return await client.get_users(userId)


async def BotPm_check(message, button=None):
    user_id = message.from_user.id
    try:
        temp_msg = await message._client.send_message(
            chat_id=message.from_user.id, text="<b>Checking Access...</b>"
        )
        await temp_msg.delete()
        return None, button
    except Exception:
        if button is None:
            button = ButtonMaker()
        _msg = "You haven't initiated the bot in a private message!"
        button.callback("Start", f"aeon {user_id} private", "header")
        return _msg, button
