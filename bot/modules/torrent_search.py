import contextlib
from html import escape
from urllib.parse import quote

from aiohttp import ClientSession
from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import LOGGER, bot, config_dict, xnox_client
from bot.helper.ext_utils.bot_utils import (
    new_task,
    new_thread,
    sync_to_async,
    checking_access,
    get_readable_file_size,
)
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    isAdmin,
    editMessage,
    sendMessage,
    delete_links,
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
SITES = None
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

    if SEARCH_API_LINK := config_dict["SEARCH_API_LINK"]:
        global SITES
        try:
            async with ClientSession(trust_env=True) as c:
                async with c.get(f"{SEARCH_API_LINK}/api/v1/sites") as res:
                    data = await res.json()
            SITES = {
                str(site): str(site).capitalize() for site in data["supported_sites"]
            }
            SITES["all"] = "All"
        except Exception as e:
            LOGGER.error(
                f"{e} Can't fetching sites from SEARCH_API_LINK make sure use latest version of API"
            )
            SITES = None


async def __search(key, site, message, method):
    if method.startswith("api"):
        SEARCH_API_LINK = config_dict["SEARCH_API_LINK"]
        SEARCH_LIMIT = config_dict["SEARCH_LIMIT"]
        if method == "apisearch":
            LOGGER.info(f"API Searching: {key} from {site}")
            if site == "all":
                api = f"{SEARCH_API_LINK}/api/v1/all/search?query={key}&limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/search?site={site}&query={key}&limit={SEARCH_LIMIT}"
        elif method == "apitrend":
            LOGGER.info(f"API Trending from {site}")
            if site == "all":
                api = f"{SEARCH_API_LINK}/api/v1/all/trending?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/trending?site={site}&limit={SEARCH_LIMIT}"
        elif method == "apirecent":
            LOGGER.info(f"API Recent from {site}")
            if site == "all":
                api = f"{SEARCH_API_LINK}/api/v1/all/recent?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/recent?site={site}&limit={SEARCH_LIMIT}"
        try:
            async with ClientSession(trust_env=True) as c:
                async with c.get(api) as res:
                    search_results = await res.json()
            if "error" in search_results or search_results["total"] == 0:
                await editMessage(
                    message,
                    f"No result found for {key}\nTorrent Site:- {SITES.get(site)}",
                )
                return
            msg = f"<b>Found {min(search_results['total'], TELEGRAPH_LIMIT)}</b>"
            if method == "apitrend":
                msg += (
                    f" <b>trending result(s)\nTorrent Site:- {SITES.get(site)}</b>"
                )
            elif method == "apirecent":
                msg += f" <b>recent result(s)\nTorrent Site:- {SITES.get(site)}</b>"
            else:
                msg += (
                    f" <b>result(s) for {key}\nTorrent Site:- {SITES.get(site)}</b>"
                )
            search_results = search_results["data"]
        except Exception as e:
            await editMessage(message, str(e))
            return
    else:
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
            await editMessage(
                message,
                f"No result found for {key}\nTorrent Site:- {site.capitalize()}",
            )
            return
        msg = f"<b>Found {min(total_results, TELEGRAPH_LIMIT)}</b>"
        msg += f" <b>result(s) for {key}\nTorrent Site:- {site.capitalize()}</b>"
        await sync_to_async(xnox_client.search_delete, search_id=search_id)
    link = await __getResult(search_results, key, message, method)
    buttons = ButtonMaker()
    buttons.url("View", link)
    button = buttons.column(1)
    await editMessage(message, msg, button)


async def __getResult(search_results, key, message, method):
    telegraph_content = []
    if method == "apirecent":
        msg = "<h4>API Recent Results</h4>"
    elif method == "apisearch":
        msg = f"<h4>API Search Result(s) For {key}</h4>"
    elif method == "apitrend":
        msg = "<h4>API Trending Results</h4>"
    else:
        msg = f"<h4>PLUGINS Search Result(s) For {key}</h4>"
    for index, result in enumerate(search_results, start=1):
        if method.startswith("api"):
            try:
                if "name" in result:
                    msg += f"<code><a href='{result['url']}'>{escape(result['name'])}</a></code><br>"
                if "torrents" in result:
                    for subres in result["torrents"]:
                        msg += f"<b>Quality: </b>{subres['quality']} | <b>Type: </b>{subres['type']} | "
                        msg += f"<b>Size: </b>{subres['size']}<br>"
                        if "torrent" in subres:
                            msg += (
                                f"<a href='{subres['torrent']}'>Direct Link</a><br>"
                            )
                        elif "magnet" in subres:
                            msg += "<b>Share Magnet to</b> "
                            msg += f"<a href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a><br>"
                    msg += "<br>"
                else:
                    msg += f"<b>Size: </b>{result['size']}<br>"
                    with contextlib.suppress(Exception):
                        msg += f"<b>Seeders: </b>{result['seeders']} | <b>Leechers: </b>{result['leechers']}<br>"
                    if "torrent" in result:
                        msg += (
                            f"<a href='{result['torrent']}'>Direct Link</a><br><br>"
                        )
                    elif "magnet" in result:
                        msg += "<b>Share Magnet to</b> "
                        msg += f"<a href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a><br><br>"
                    else:
                        msg += "<br>"
            except Exception:
                continue
        else:
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

    await editMessage(
        message, f"<b>Creating</b> {len(telegraph_content)} <b>Telegraph pages.</b>"
    )
    path = [
        (await telegraph.create_page(title="Torrent Search", content=content))[
            "path"
        ]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await editMessage(
            message,
            f"<b>Editing</b> {len(telegraph_content)} <b>Telegraph pages.</b>",
        )
        await telegraph.edit_telegraph(path, telegraph_content)
    return f"https://telegra.ph/{path[0]}"


def __api_buttons(user_id, method):
    buttons = ButtonMaker()
    for data, name in SITES.items():
        buttons.callback(name, f"torser {user_id} {data} {method}")
    buttons.callback("Cancel", f"torser {user_id} cancel")
    return buttons.column(2)


async def __plugin_buttons(user_id):
    buttons = ButtonMaker()
    for siteName in PLUGINS:
        buttons.callback(
            siteName.capitalize(), f"torser {user_id} {siteName} plugin"
        )
    buttons.callback("All", f"torser {user_id} all plugin")
    buttons.callback("Cancel", f"torser {user_id} cancel")
    return buttons.column(2)


@new_thread
async def torrentSearch(_, message):
    user_id = message.from_user.id
    buttons = ButtonMaker()
    key = message.text.split()
    if not await isAdmin(message, user_id):
        if message.chat.type != message.chat.type.PRIVATE:
            msg, buttons = await checking_access(user_id, buttons)
            if msg is not None:
                reply_message = await sendMessage(message, msg, buttons.column(1))
                await delete_links(message)
                await five_minute_del(reply_message)
                return
    if len(key) == 1 and SITES is None:
        reply_message = await sendMessage(
            message, "Send a search key along with command"
        )
        await one_minute_del(reply_message)
        await delete_links(message)
        return
    if len(key) == 1:
        buttons.callback("Trending", f"torser {user_id} apitrend")
        buttons.callback("Recent", f"torser {user_id} apirecent")
        buttons.callback("Cancel", f"torser {user_id} cancel")
        button = buttons.column(2)
        reply_message = await sendMessage(
            message, "Send a search key along with command", button
        )
    elif SITES is not None:
        buttons.callback("Api", f"torser {user_id} apisearch")
        buttons.callback("Plugins", f"torser {user_id} plugin")
        buttons.callback("Cancel", f"torser {user_id} cancel")
        button = buttons.column(2)
        reply_message = await sendMessage(message, "Choose tool to search:", button)
    else:
        button = await __plugin_buttons(user_id)
        reply_message = await sendMessage(
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
    elif data[2].startswith("api"):
        await query.answer()
        button = __api_buttons(user_id, data[2])
        await editMessage(message, "Choose site:", button)
    elif data[2] == "plugin":
        await query.answer()
        button = await __plugin_buttons(user_id)
        await editMessage(message, "Choose site:", button)
    elif data[2] != "cancel":
        await query.answer()
        site = data[2]
        method = data[3]
        if method.startswith("api"):
            if key is None:
                if method == "apirecent":
                    endpoint = "Recent"
                elif method == "apitrend":
                    endpoint = "Trending"
                await editMessage(
                    message,
                    f"<b>Listing {endpoint} Items...\nTorrent Site:- {SITES.get(site)}</b>",
                )
            else:
                await editMessage(
                    message,
                    f"<b>Searching for {key}\nTorrent Site:- {SITES.get(site)}</b>",
                )
        else:
            await editMessage(
                message,
                f"<b>Searching for {key}\nTorrent Site:- {site.capitalize()}</b>",
            )
        await __search(key, site, message, method)
    else:
        await query.answer()
        await editMessage(message, "Search has been canceled!")


bot.add_handler(
    MessageHandler(
        torrentSearch,
        filters=command(BotCommands.SearchCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(torrentSearchUpdate, filters=regex("^torser")))
