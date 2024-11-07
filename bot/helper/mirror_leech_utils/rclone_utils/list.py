from json import loads
from time import time
from asyncio import Event, gather, wait_for, wrap_future
from functools import partial
from configparser import ConfigParser

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from pyrogram.filters import user, regex
from pyrogram.handlers import CallbackQueryHandler

from bot import LOGGER, config_dict
from bot.helper.ext_utils.bot_utils import (
    cmd_exec,
    new_task,
    new_thread,
    update_user_ldata,
)
from bot.helper.ext_utils.db_handler import Database
from bot.helper.ext_utils.status_utils import (
    get_readable_time,
    get_readable_file_size,
)
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    edit_message,
    send_message,
    delete_message,
)

LIST_LIMIT = 6


@new_task
async def path_updates(_, query, obj):
    await query.answer()
    message = query.message
    data = query.data.split()
    if data[1] == "cancel":
        obj.remote = "Task has been cancelled!"
        obj.path = ""
        obj.listener.isCancelled = True
        obj.event.set()
        await delete_message(message)
        return
    if obj.query_proc:
        return
    obj.query_proc = True
    if data[1] == "pre":
        obj.iter_start -= LIST_LIMIT * obj.page_step
        await obj.get_path_buttons()
    elif data[1] == "nex":
        obj.iter_start += LIST_LIMIT * obj.page_step
        await obj.get_path_buttons()
    elif data[1] == "back":
        if data[2] == "re":
            await obj.list_config()
        else:
            await obj.back_from_path()
    elif data[1] == "re":
        data = query.data.split(maxsplit=2)
        obj.remote = data[2]
        await obj.get_path()
    elif data[1] == "pa":
        index = int(data[3])
        obj.path += (
            f"/{obj.path_list[index]['Path']}"
            if obj.path
            else obj.path_list[index]["Path"]
        )
        if data[2] == "fo":
            await obj.get_path()
        else:
            await delete_message(message)
            obj.event.set()
    elif data[1] == "ps":
        if obj.page_step == int(data[2]):
            return
        obj.page_step = int(data[2])
        await obj.get_path_buttons()
    elif data[1] == "root":
        obj.path = ""
        await obj.get_path()
    elif data[1] == "itype":
        obj.item_type = data[2]
        await obj.get_path()
    elif data[1] == "cur":
        await delete_message(message)
        obj.event.set()
    elif data[1] == "def":
        path = (
            f"{obj.remote}{obj.path}"
            if obj.config_path == "rclone.conf"
            else f"mrcc:{obj.remote}{obj.path}"
        )
        if path != obj.listener.userDict.get("rclone_path"):
            update_user_ldata(obj.listener.userId, "rclone_path", path)
            await obj.get_path_buttons()
            await Database().update_user_data(obj.listener.userId)
    elif data[1] == "owner":
        obj.config_path = "rclone.conf"
        obj.path = ""
        obj.remote = ""
        await obj.list_remotes()
    elif data[1] == "user":
        obj.config_path = obj.user_rcc_path
        obj.path = ""
        obj.remote = ""
        await obj.list_remotes()
    obj.query_proc = False


class RcloneList:
    def __init__(self, listener):
        self._rc_user = False
        self._rc_owner = False
        self._sections = []
        self._reply_to = None
        self._time = time()
        self._timeout = 240
        self.listener = listener
        self.remote = ""
        self.query_proc = False
        self.item_type = "--dirs-only"
        self.event = Event()
        self.user_rcc_path = f"rclone/{self.listener.userId}.conf"
        self.config_path = ""
        self.path = ""
        self.list_status = ""
        self.path_list = []
        self.iter_start = 0
        self.page_step = 1

    @new_thread
    async def _event_handler(self):
        pfunc = partial(path_updates, obj=self)
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc, filters=regex("^rcq") & user(self.listener.userId)
            ),
            group=-1,
        )
        try:
            await wait_for(self.event.wait(), timeout=self._timeout)
        except Exception:
            self.path = ""
            self.remote = "Timed Out. Task has been cancelled!"
            self.listener.isCancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    async def _send_list_message(self, msg, button):
        if not self.listener.isCancelled:
            if self._reply_to is None:
                self._reply_to = await send_message(
                    self.listener.message, msg, button
                )
            else:
                await edit_message(self._reply_to, msg, button)

    async def get_path_buttons(self):
        items_no = len(self.path_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start / LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker()
        for index, idict in enumerate(
            self.path_list[self.iter_start : LIST_LIMIT + self.iter_start]
        ):
            orig_index = index + self.iter_start
            if idict["IsDir"]:
                ptype = "fo"
                name = idict["Path"]
            else:
                ptype = "fi"
                name = f"[{get_readable_file_size(idict['Size'])}] {idict['Path']}"
            buttons.callback(name, f"rcq pa {ptype} {orig_index}")
        if items_no > LIST_LIMIT:
            for i in [1, 2, 4, 6, 10, 30, 50, 100]:
                buttons.callback(i, f"rcq ps {i}", position="header")
            buttons.callback("Previous", "rcq pre", position="footer")
            buttons.callback("Next", "rcq nex", position="footer")
        if self.list_status == "rcd":
            if self.item_type == "--dirs-only":
                buttons.callback(
                    "Files", "rcq itype --files-only", position="footer"
                )
            else:
                buttons.callback(
                    "Folders", "rcq itype --dirs-only", position="footer"
                )
        if self.list_status == "rcu" or len(self.path_list) > 0:
            buttons.callback("Choose Current Path", "rcq cur", position="footer")
        if self.list_status == "rcu":
            buttons.callback("Set as Default Path", "rcq def", position="footer")
        if self.path or len(self._sections) > 1 or self._rc_user and self._rc_owner:
            buttons.callback("Back", "rcq back pa", position="footer")
        if self.path:
            buttons.callback("Back To Root", "rcq root", position="footer")
        buttons.callback("Cancel", "rcq cancel", position="footer")
        button = buttons.menu(f_cols=2)
        msg = "Choose Path:" + (
            "\nTransfer Type: <i>Download</i>"
            if self.list_status == "rcd"
            else "\nTransfer Type: <i>Upload</i>"
        )
        if self.list_status == "rcu":
            default_path = config_dict["RCLONE_PATH"]
            msg += f"\nDefault Rclone Path: {default_path}" if default_path else ""
        msg += f"\n\nItems: {items_no}"
        if items_no > LIST_LIMIT:
            msg += f" | Page: {int(page)}/{pages} | Page Step: {self.page_step}"
        msg += f"\n\nItem Type: {self.item_type}\nConfig Path: {self.config_path}"
        msg += f"\nCurrent Path: <code>{self.remote}{self.path}</code>"
        msg += (
            f"\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
        )
        await self._send_list_message(msg, button)

    async def get_path(self, itype=""):
        if itype:
            self.item_type == itype
        elif self.list_status == "rcu":
            self.item_type == "--dirs-only"
        cmd = [
            "xone",
            "lsjson",
            self.item_type,
            "--fast-list",
            "--no-mimetype",
            "--no-modtime",
            "--config",
            self.config_path,
            f"{self.remote}{self.path}",
        ]
        if self.listener.isCancelled:
            return None
        res, err, code = await cmd_exec(cmd)
        if code not in [0, -9]:
            if not err:
                err = "Use <code>/shell cat rlog.txt</code> to see more information"
            LOGGER.error(
                f"While rclone listing. Path: {self.remote}{self.path}. Stderr: {err}"
            )
            self.remote = err[:4000]
            self.path = ""
            self.event.set()
            return None
        result = loads(res)
        if (
            len(result) == 0
            and itype != self.item_type
            and self.list_status == "rcd"
        ):
            itype = (
                "--dirs-only" if self.item_type == "--files-only" else "--files-only"
            )
            self.item_type = itype
            return await self.get_path(itype)
        self.path_list = sorted(result, key=lambda x: x["Path"])
        self.iter_start = 0
        await self.get_path_buttons()
        return None

    async def list_remotes(self):
        config = ConfigParser()
        async with aiopen(self.config_path) as f:
            contents = await f.read()
            config.read_string(contents)
        if config.has_section("combine"):
            config.remove_section("combine")
        self._sections = config.sections()
        if len(self._sections) == 1:
            self.remote = f"{self._sections[0]}:"
            await self.get_path()
        else:
            msg = "Choose Rclone remote:" + (
                "\nTransfer Type: <i>Download</i>"
                if self.list_status == "rcd"
                else "\nTransfer Type: <i>Upload</i>"
            )
            msg += f"\nConfig Path: {self.config_path}"
            msg += f"\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
            buttons = ButtonMaker()
            for remote in self._sections:
                buttons.callback(remote, f"rcq re {remote}:")
            if self._rc_user and self._rc_owner:
                buttons.callback("Back", "rcq back re", position="footer")
            buttons.callback("Cancel", "rcq cancel", position="footer")
            button = buttons.menu(2)
            await self._send_list_message(msg, button)

    async def list_config(self):
        if self._rc_user and self._rc_owner:
            msg = "Choose Rclone config:" + (
                "\nTransfer Type: Download"
                if self.list_status == "rcd"
                else "\nTransfer Type: Upload"
            )
            msg += f"\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}"
            buttons = ButtonMaker()
            buttons.callback("Owner Config", "rcq owner")
            buttons.callback("My Config", "rcq user")
            buttons.callback("Cancel", "rcq cancel")
            button = buttons.menu(2)
            await self._send_list_message(msg, button)
        else:
            self.config_path = (
                "rclone.conf" if self._rc_owner else self.user_rcc_path
            )
            await self.list_remotes()

    async def back_from_path(self):
        if self.path:
            path = self.path.rsplit("/", 1)
            self.path = path[0] if len(path) > 1 else ""
            await self.get_path()
        elif len(self._sections) > 1:
            await self.list_remotes()
        else:
            await self.list_config()

    async def get_rclone_path(self, status, config_path=None):
        self.list_status = status
        future = self._event_handler()
        if config_path is None:
            self._rc_user, self._rc_owner = await gather(
                aiopath.exists(self.user_rcc_path), aiopath.exists("rclone.conf")
            )
            if not self._rc_owner and not self._rc_user:
                self.event.set()
                return "Rclone Config not Exists!"
            await self.list_config()
        else:
            self.config_path = config_path
            await self.list_remotes()
        await wrap_future(future)
        await delete_message(self._reply_to)
        if self.config_path != "rclone.conf" and not self.listener.isCancelled:
            return f"mrcc:{self.remote}{self.path}"
        return f"{self.remote}{self.path}"
