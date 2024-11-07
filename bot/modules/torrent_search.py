from html import escape
from urllib.parse import quote

from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import LOGGER, bot, xnox_client
from bot.helper.ext_utils.bot_utils import new_task, new_thread, sync_to_async
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.aeon_utils.access_check import token_check
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    delete_links,
    edit_message,
    send_message,
    one_minute_del,
    five_minute_del,
)

PLUGINS = [
    "piratebay",
    "limetorrents",
    "torrentscsv",
    "torlock",
    "eztv",
    "solidtorrents",
    "yts_am",
    "nyaasi",
    "ettv",
    "thepiratebay",
    "magnetdl",
    "uniondht",
    "yts",
]
TELEGRAPH_LIMIT = 300
src_plugins = {
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/piratebay.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/limetorrents.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentscsv.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torlock.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/eztv.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/solidtorrents.py",
    "https://raw.githubusercontent.com/MaurizioRicci/qBittorrent_search_engines/master/yts_am.py",
    "https://raw.githubusercontent.com/MadeOfMagicAndWires/qBit-plugins/master/engines/nyaasi.py",
    "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/ettv.py",
    "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/thepiratebay.py",
    "https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/magnetdl.py",
    "https://raw.githubusercontent.com/msagca/qbittorrent_plugins/main/uniondht.py",
    "https://raw.githubusercontent.com/khensolomon/leyts/master/yts.py",
}


async def initiate_search_tools():
    qb_plugins = await sync_to_async(xnox_client.search_plugins)
    if qb_plugins:
        names = [plugin["name"] for plugin in qb_plugins]
        await sync_to_async(xnox_client.search_uninstall_plugin, names=names)
    await sync_to_async(xnox_client.search_install_plugin, src_plugins)


async def __search(key, site, message, method):
    LOGGER.info(f"PLUGINS Searching: {key} from {site}")
    search = await sync_to_async(
        xnox_client.search_start, pattern=key, plugins=site, category="all"
    )
    search_id = search.id
    while True:
        result_status = await sync_to_async(
            xnox_client.search_status, search_id=search_id
        )
        status = result_status[0].status
        if status != "Running":
            break
    dict_search_results = await sync_to_async(
        xnox_client.search_results, search_id=search_id, limit=TELEGRAPH_LIMIT
    )
    search_results = dict_search_results.results
    total_results = dict_search_results.total
    if total_results == 0:
        await edit_message(
            message, f"No result found for {key}\nTorrent Site:- {site.capitalize()}"
        )
        return
    msg = f"<b>Found {min(total_results, TELEGRAPH_LIMIT)}</b>"
    msg += f" <b>result(s) for {key}\nTorrent Site:- {site.capitalize()}</b>"
    await sync_to_async(xnox_client.search_delete, search_id=search_id)
    link = await __getResult(search_results, key, message)
    buttons = ButtonMaker()
    buttons.url("View", link)
    button = buttons.menu(1)
    await edit_message(message, msg, button)


async def __getResult(search_results, key, message):
    telegraph_content = []
    msg = f"<h4>PLUGINS Search Result(s) For {key}</h4>"
    for index, result in enumerate(search_results, start=1):
        msg += f"<a href='{result.descrLink}'>{escape(result.fileName)}</a><br>"
        msg += f"<b>Size: </b>{get_readable_file_size(result.fileSize)}<br>"
        msg += f"<b>Seeders: </b>{result.nbSeeders} | <b>Leechers: </b>{result.nbLeechers}<br>"
        link = result.fileUrl
        if link.startswith("magnet:"):
            msg += f"<b>Share Magnet to</b> <a href='http://t.me/share/url?url={quote(link)}'>Telegram</a><br><br>"
        else:
            msg += f"<a href='{link}'>Direct Link</a><br><br>"

        if len(msg.encode("utf-8")) > 39000:
            telegraph_content.append(msg)
            msg = ""

        if index == TELEGRAPH_LIMIT:
            break

    if msg != "":
        telegraph_content.append(msg)

    await edit_message(
        message, f"<b>Creating</b> {len(telegraph_content)} <b>Telegraph pages.</b>"
    )
    path = [
        (await telegraph.create_page(title="Torrent Search", content=content))[
            "path"
        ]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await edit_message(
            message,
            f"<b>Editing</b> {len(telegraph_content)} <b>Telegraph pages.</b>",
        )
        await telegraph.edit_telegraph(path, telegraph_content)
    return f"https://telegra.ph/{path[0]}"


async def __plugin_buttons(user_id):
    buttons = ButtonMaker()
    for siteName in PLUGINS:
        buttons.callback(
            siteName.capitalize(), f"torser {user_id} {siteName} plugin"
        )
    buttons.callback("All", f"torser {user_id} all plugin")
    buttons.callback("Cancel", f"torser {user_id} cancel")
    return buttons.menu(2)


@new_thread
async def torrentSearch(_, message):
    user_id = message.from_user.id
    buttons = ButtonMaker()
    key = message.text.split()
    if message.chat.type != message.chat.type.PRIVATE:
        msg, buttons = await token_check(user_id, buttons)
        if msg is not None:
            reply_message = await send_message(message, msg, buttons.menu(1))
            await delete_links(message)
            await five_minute_del(reply_message)
            return
    if len(key) == 1:
        reply_message = await send_message(
            message, "Send a search key along with command"
        )
        await one_minute_del(reply_message)
        await delete_links(message)
        return
    button = await __plugin_buttons(user_id)
    reply_message = await send_message(
        message, "Choose site to search | Plugins:", button
    )
    await five_minute_del(reply_message)
    await delete_links(message)


@new_task
async def torrentSearchUpdate(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)
    key = key[1].strip() if len(key) > 1 else None
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "plugin":
        await query.answer()
        button = await __plugin_buttons(user_id)
        await edit_message(message, "Choose site:", button)
    elif data[2] != "cancel":
        await query.answer()
        site = data[2]
        await edit_message(
            message,
            f"<b>Searching for {key}\nTorrent Site:- {site.capitalize()}</b>",
        )
        await __search(key, site, message, "plugin")
    else:
        await query.answer()
        await edit_message(message, "Search has been canceled!")


bot.add_handler(
    MessageHandler(
        torrentSearch,
        filters=command(BotCommands.SearchCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(torrentSearchUpdate, filters=regex("^torser")))
