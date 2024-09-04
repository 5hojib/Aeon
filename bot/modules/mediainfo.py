from os import path as ospath
from os import getcwd
from re import search as re_search
from shlex import split as ssplit

import aiohttp
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import mkdir
from aiofiles.os import remove as aioremove
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import edit_message, send_message

section_dict = {"General", "Video", "Audio", "Text", "Menu"}


async def gen_mediainfo(message, link=None, media=None, msg=None):
    temp_send = await send_message(message, "Generating MediaInfo...")
    try:
        path = "Mediainfo/"
        if not await aiopath.isdir(path):
            await mkdir(path)

        if link:
            filename = re_search(".+/(.+)", link).group(1)
            des_path = ospath.join(path, filename)
            headers = {
                "user-agent": "Mozilla/5.0 (Linux; Android 12; 2201116PI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
            }
            async with (
                aiohttp.ClientSession() as session,
                session.get(link, headers=headers) as response,
                aiopen(des_path, "wb") as f,
            ):
                async for chunk in response.content.iter_chunked(10000000):
                    await f.write(chunk)
                    break
        elif media:
            des_path = ospath.join(path, media.file_name)
            if media.file_size <= 50000000:
                await msg.download(ospath.join(getcwd(), des_path))
            else:
                async for chunk in bot.stream_media(media, limit=5):
                    async with aiopen(des_path, "ab") as f:
                        await f.write(chunk)

        stdout, _, _ = await cmd_exec(ssplit(f'mediainfo "{des_path}"'))
        tc = f"<h4>{ospath.basename(des_path)}</h4><br><br>"
        if stdout:
            tc += parseinfo(stdout)

    except Exception as e:
        LOGGER.error(e)
        await edit_message(temp_send, f"MediaInfo stopped due to {e!s}")
    finally:
        await aioremove(des_path)

    link_id = (await telegraph.create_page(title="MediaInfo", content=tc))["path"]
    await temp_send.edit(
        f"<blockquote>MediaInfo generated successfully<a href='https://graph.org/{link_id}'>.</a></blockquote>",
        disable_web_page_preview=False,
    )


def parseinfo(out):
    tc = ""
    trigger = False
    for line in out.split("\n"):
        for section in section_dict:
            if line.startswith(section):
                trigger = True
                if not line.startswith("General"):
                    tc += "</pre><br>"
                tc += f"<h4>{line.replace('Text', 'Subtitle')}</h4>"
                break
        if trigger:
            tc += "<br><pre>"
            trigger = False
        else:
            tc += line + "\n"
    tc += "</pre><br>"
    return tc


async def mediainfo(_, message):
    reply = message.reply_to_message
    help_msg = (
        "<b>By replying to media:</b>"
        f"\n<code>/{BotCommands.MediaInfoCommand} media </code>"
        "\n\n<b>By reply/sending download link:</b>"
        f"\n<code>/{BotCommands.MediaInfoCommand} link </code>"
    )
    if len(message.command) > 1 or (reply and reply.text):
        link = reply.text if reply else message.command[1]
        await gen_mediainfo(message, link)
    elif reply:
        if file := next(
            (i for i in [reply.document, reply.video, reply.audio] if i), None
        ):
            await gen_mediainfo(message, None, file, reply)
        else:
            await send_message(message, help_msg)
    else:
        await send_message(message, help_msg)


bot.add_handler(
    MessageHandler(
        mediainfo,
        filters=command(BotCommands.MediaInfoCommand) & CustomFilters.authorized,
    )
)
