import hashlib, os, time
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, app
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage


def HumanBytes(size):
    if not size: return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: " ", 1: "K", 2: "M", 3: "G", 4: "T"}
    while size > power:
        size /= power
        n += 1
    return f"{str(round(size, 2))} {Dic_powerN[n]}iB"


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        (f"{str(days)}d, " if days else "")
        + (f"{str(hours)}h, " if hours else "")
        + (f"{str(minutes)}m, " if minutes else "")
        + (f"{str(seconds)}s, " if seconds else "")
        + (f"{str(milliseconds)}ms, " if milliseconds else "")
    )
    return tmp[:-2]


def hash(update, context):
    message = update.effective_message
    mediamessage = message.reply_to_message
    help_msg = "<b>Reply to message including file:</b>"
    help_msg += f"\n<code>/{BotCommands.HashCommand}" + " {message}" + "</code>"
    if not mediamessage: return sendMessage(help_msg, context.bot, update.message)
    media_array = [mediamessage.document, mediamessage.video, mediamessage.audio, mediamessage.document, \
        mediamessage.video, mediamessage.photo, mediamessage.audio, mediamessage.voice, \
        mediamessage.animation, mediamessage.video_note, mediamessage.sticker]
    file = next((i for i in media_array if i is not None), None)
    if not file: return sendMessage(help_msg, context.bot, update.message)
    VtPath = os.path.join("Hasher", str(message.from_user.id))
    if not os.path.exists("Hasher"): os.makedirs("Hasher")
    if not os.path.exists(VtPath): os.makedirs(VtPath)
    sent = sendMessage("Trying to download. Please wait.", context.bot, update.message)
    try:
        filename = os.path.join(VtPath, file.file_name)
        file = app.download_media(message=file, file_name=filename)
    except Exception as e:
        LOGGER.error(e)
        try: os.remove(file)
        except: pass
        file = None
    if not file: return editMessage("Error when downloading. Try again later.", sent)
    hashStartTime = time.time()
    try:
        with open(file, "rb") as f:
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha224 = hashlib.sha224()
            sha256 = hashlib.sha256()
            sha512 = hashlib.sha512()
            sha384 = hashlib.sha384()
            while chunk := f.read(8192):
                md5.update(chunk)
                sha1.update(chunk)
                sha224.update(chunk)
                sha256.update(chunk)
                sha512.update(chunk)
                sha384.update(chunk)
    except Exception as a:
        LOGGER.info(str(a))
        try: os.remove(file)
        except: pass
        return editMessage("Hashing error. Check Logs.", sent)
    finishedText = (
        f"🍆 File: <code>{filename}</code>\n"
        + f"🍓 MD5: <code>{md5.hexdigest()}</code>\n"
    )
    finishedText += f"🍌 SHA1: <code>{sha1.hexdigest()}</code>\n"
    finishedText += f"🍒 SHA224: <code>{sha224.hexdigest()}</code>\n"
    finishedText += f"🍑 SHA256: <code>{sha256.hexdigest()}</code>\n"
    finishedText += f"🥭 SHA512: <code>{sha512.hexdigest()}</code>\n"
    finishedText += f"🍎 SHA384: <code>{sha384.hexdigest()}</code>\n"
    timeTaken = f"🥚 Hash Time: <code>{TimeFormatter((time.time() - hashStartTime) * 1000)}</code>"
    editMessage(f"{timeTaken}\n{finishedText}", sent)
    try: os.remove(file)
    except: pass


hash_handler = CommandHandler(BotCommands.HashCommand, hash,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
dispatcher.add_handler(hash_handler)