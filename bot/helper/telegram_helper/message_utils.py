from re import match as re_match
from time import time
from asyncio import sleep

from pyrogram import Client, enums
from cachetools import TTLCache
from pyrogram.types import InputMediaPhoto
from pyrogram.errors import FloodWait, MessageEmpty, MessageNotModified

from bot import (
    LOGGER,
    TELEGRAM_API,
    TELEGRAM_HASH,
    Intervals,
    bot,
    user,
    user_data,
    status_dict,
    task_dict_lock,
)
from bot.helper.ext_utils.bot_utils import setInterval
from bot.helper.ext_utils.exceptions import TgLinkException
from bot.helper.ext_utils.status_utils import get_readable_message

session_cache = TTLCache(maxsize=1000, ttl=36000)


async def send_message(
    message, text, buttons=None, block=True, photo=None, MARKDOWN=False
):
    parse_mode = enums.ParseMode.MARKDOWN if MARKDOWN else enums.ParseMode.HTML
    try:
        if isinstance(message, int):
            return await bot.send_message(
                chat_id=message,
                text=text,
                disable_web_page_preview=True,
                disable_notification=True,
                reply_markup=buttons,
                parse_mode=parse_mode,
            )
        if photo:
            return await message.reply_photo(
                photo=photo,
                reply_to_message_id=message.id,
                caption=text,
                reply_markup=buttons,
                disable_notification=True,
                parse_mode=parse_mode,
            )
        return await message.reply(
            text=text,
            quote=True,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons,
            parse_mode=parse_mode,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        if block:
            await sleep(f.value * 1.2)
            return await send_message(message, text, buttons, block, photo, MARKDOWN)
        return str(f)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def edit_message(
    message, text, buttons=None, block=True, photo=None, MARKDOWN=False
):
    parse_mode = enums.ParseMode.MARKDOWN if MARKDOWN else enums.ParseMode.HTML
    try:
        if message.media:
            if photo:
                return await message.edit_media(
                    InputMediaPhoto(photo, text),
                    reply_markup=buttons,
                    parse_mode=parse_mode,
                )
            return await message.edit_caption(
                caption=text, reply_markup=buttons, parse_mode=parse_mode
            )
        await message.edit(
            text=text,
            disable_web_page_preview=True,
            reply_markup=buttons,
            parse_mode=parse_mode,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        if block:
            await sleep(f.value * 1.2)
            return await edit_message(message, text, buttons, block, photo, MARKDOWN)
    except (MessageNotModified, MessageEmpty):
        pass
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendFile(message, file, caption="", buttons=None):
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
        return await sendFile(message, file, caption, buttons)
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
    if reply_to := message.reply_to_message:
        await delete_message(reply_to)
    await delete_message(message)


async def auto_delete_message(cmd_message=None, bot_message=None):
    await sleep(60)
    if cmd_message is not None:
        await delete_message(cmd_message)
    if bot_message is not None:
        await delete_message(bot_message)


async def delete_status():
    async with task_dict_lock:
        for key, data in list(status_dict.items()):
            try:
                await delete_message(data["message"])
                del status_dict[key]
            except Exception as e:
                LOGGER.error(str(e))


async def get_tg_link_message(link, user_id=""):
    message = None
    links = []
    user_s = None

    if user_id:
        if user_id in session_cache:
            user_s = session_cache[user_id]
        else:
            user_dict = user_data.get(user_id, {})
            session_string = user_dict.get("session_string")
            if session_string:
                user_s = Client(
                    f"session_{user_id}",
                    TELEGRAM_API,
                    TELEGRAM_HASH,
                    session_string=session_string,
                    no_updates=True,
                )
                await user_s.start()
                session_cache[user_id] = user_s
            else:
                user_s = user

    if link.startswith("https://t.me/"):
        private = False
        msg = re_match(
            r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9-]+)", link
        )
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9-]+)", link
        )
        if not user:
            raise TgLinkException(
                "USER_SESSION_STRING required for this private link!"
            )

    chat = msg[1]
    msg_id = msg[2]
    if "-" in msg_id:
        start_id, end_id = map(int, msg_id.split("-"))
        msg_id = start_id
        btw = end_id - start_id
        if private:
            link = link.split("&message_id=")[0]
            links.append(f"{link}&message_id={start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}&message_id={start_id}")
        else:
            link = link.rsplit("/", 1)[0]
            links.append(f"{link}/{start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}/{start_id}")
    else:
        msg_id = int(msg_id)

    if chat.isdigit():
        chat = int(chat) if private else int(f"-100{chat}")

    if not private:
        try:
            message = await bot.get_messages(chat_id=chat, message_ids=msg_id)
            if message.empty:
                private = True
        except Exception as e:
            private = True
            if not user_s:
                raise e

    if not private:
        return (links, bot) if links else (message, bot)
    if user_s:
        try:
            user_message = await user_s.get_messages(
                chat_id=chat, message_ids=msg_id
            )
        except Exception as e:
            raise TgLinkException("We don't have access to this chat!") from e
        if not user_message.empty:
            return (links, user_s) if links else (user_message, user_s)
        return None
    raise TgLinkException("Private: Please report!")


async def update_status_message(sid, force=False):
    if Intervals["stopAll"]:
        return
    async with task_dict_lock:
        if not status_dict.get(sid):
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
            return
        if not force and time() - status_dict[sid]["time"] < 3:
            return
        status_dict[sid]["time"] = time()
        page_no = status_dict[sid]["page_no"]
        status = status_dict[sid]["status"]
        is_user = status_dict[sid]["is_user"]
        page_step = status_dict[sid]["page_step"]
        text, buttons = await get_readable_message(
            sid, is_user, page_no, status, page_step
        )
        if text is None:
            del status_dict[sid]
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
            return
        if text != status_dict[sid]["message"].text:
            message = await edit_message(
                status_dict[sid]["message"], text, buttons, block=False
            )
            if isinstance(message, str):
                if message.startswith("Telegram says: [400"):
                    del status_dict[sid]
                    if obj := Intervals["status"].get(sid):
                        obj.cancel()
                        del Intervals["status"][sid]
                else:
                    LOGGER.error(
                        f"Status with id: {sid} haven't been updated. Error: {message}"
                    )
                return
            status_dict[sid]["message"].text = text
            status_dict[sid]["time"] = time()


async def sendStatusMessage(msg, user_id=0):
    if Intervals["stopAll"]:
        return
    async with task_dict_lock:
        sid = user_id or msg.chat.id
        is_user = bool(user_id)
        if sid in list(status_dict.keys()):
            page_no = status_dict[sid]["page_no"]
            status = status_dict[sid]["status"]
            page_step = status_dict[sid]["page_step"]
            text, buttons = await get_readable_message(
                sid, is_user, page_no, status, page_step
            )
            if text is None:
                del status_dict[sid]
                if obj := Intervals["status"].get(sid):
                    obj.cancel()
                    del Intervals["status"][sid]
                return
            message = status_dict[sid]["message"]
            await delete_message(message)
            message = await send_message(msg, text, buttons, block=False)
            if isinstance(message, str):
                LOGGER.error(
                    f"Status with id: {sid} haven't been sent. Error: {message}"
                )
                return
            message.text = text
            status_dict[sid].update({"message": message, "time": time()})
        else:
            text, buttons = await get_readable_message(sid, is_user)
            if text is None:
                return
            message = await send_message(msg, text, buttons, block=False)
            if isinstance(message, str):
                LOGGER.error(
                    f"Status with id: {sid} haven't been sent. Error: {message}"
                )
                return
            message.text = text
            status_dict[sid] = {
                "message": message,
                "time": time(),
                "page_no": 1,
                "page_step": 1,
                "status": "All",
                "is_user": is_user,
            }
    if not Intervals["status"].get(sid) and not is_user:
        Intervals["status"][sid] = setInterval(1, update_status_message, sid)
