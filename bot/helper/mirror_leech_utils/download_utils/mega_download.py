from asyncio import Event
from secrets import token_hex

from mega import MegaApi, MegaError, MegaRequest, MegaListener, MegaTransfer
from aiofiles.os import makedirs

from bot import (
    LOGGER,
    task_dict,
    config_dict,
    non_queued_dl,
    task_dict_lock,
    queue_dict_lock,
)
from bot.helper.ext_utils.bot_utils import async_to_sync, sync_to_async
from bot.helper.ext_utils.links_utils import get_mega_link_type
from bot.helper.ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
)
from bot.helper.telegram_helper.message_utils import send_message, sendStatusMessage
from bot.helper.mirror_leech_utils.status_utils.mega_status import MegaDownloadStatus
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus


class MegaAppListener(MegaListener):
    NO_ERROR = "no error"
    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN, MegaRequest.TYPE_FETCH_NODES)

    def __init__(self, continue_event: Event, listener):
        super().__init__()
        self.continue_event = continue_event
        self.listener = listener
        self.node = None
        self.public_node = None
        self.is_cancelled = False
        self.error = None
        self._bytes_transferred = 0
        self._speed = 0
        self._name = ""

    @property
    def speed(self):
        return self._speed

    @property
    def downloaded_bytes(self):
        return self._bytes_transferred

    def onRequestFinish(self, api, request, error):
        if str(error).lower() != MegaAppListener.NO_ERROR:
            self.error = error.copy()
            LOGGER.error(f"Mega onRequestFinishError: {self.error}")
            self.continue_event.set()
            return

        request_type = request.getType()
        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode()
            self._name = self.public_node.getName()
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info("Fetching Root Node.")
            self.node = api.getRootNode()
            self._name = self.node.getName()
            LOGGER.info(f"Node Name: {self.node.getName()}")

        if (
            request_type not in MegaAppListener._NO_EVENT_ON
            or self.node
            and "cloud drive" not in self._name.lower()
        ):
            self.continue_event.set()

    def onRequestTemporaryError(self, api, request, error: MegaError):
        LOGGER.error(f"Mega Request error in {error}")
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(
                self.listener.onDownloadError,
                f"RequestTempError: {error.toString()}",
            )
        self.error = error.toString()
        self.continue_event.set()

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self._speed = transfer.getSpeed()
        self._bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (
                transfer.isFolderTransfer() or transfer.getFileName() == self._name
            ):
                async_to_sync(self.listener.on_download_complete)
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
        filen = transfer.getFileName()
        state = transfer.getState()
        errStr = error.toString()
        LOGGER.error(f"Mega download error in file {transfer} {filen}: {error}")
        if state in [1, 4]:
            return

        self.error = errStr
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(
                self.listener.onDownloadError,
                f"TransferTempError: {errStr} ({filen})",
            )
            self.continue_event.set()


class AsyncExecutor:
    def __init__(self):
        self.continue_event = Event()

    async def do(self, function, *args):
        self.continue_event.clear()
        await sync_to_async(function, *args)
        await self.continue_event.wait()


async def add_mega_download(listener, path):
    mega_link = listener.link
    name = listener.name
    listener.name = listener.name
    MEGA_EMAIL = config_dict["MEGA_EMAIL"]
    MEGA_PASSWORD = config_dict["MEGA_PASSWORD"]

    executor = AsyncExecutor()
    api = MegaApi(None, None, None, "aeon")
    folder_api = None

    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)

    if MEGA_EMAIL and MEGA_PASSWORD:
        await executor.do(api.login, MEGA_EMAIL, MEGA_PASSWORD)

    if get_mega_link_type(mega_link) == "file":
        await executor.do(api.getPublicNode, mega_link)
        node = mega_listener.public_node
    else:
        folder_api = MegaApi(None, None, None, "aeon")
        folder_api.addListener(mega_listener)
        await executor.do(folder_api.loginToFolder, mega_link)
        node = await sync_to_async(folder_api.authorizeNode, mega_listener.node)

    if mega_listener.error:
        await send_message(listener.message, str(mega_listener.error))
        await executor.do(api.logout)
        if folder_api:
            await executor.do(folder_api.logout)
        return

    name = name or node.getName()
    msg, button = await stop_duplicate_check(listener)
    if msg:
        await send_message(listener.message, msg, button)
        await executor.do(api.logout)
        if folder_api:
            await executor.do(folder_api.logout)
        return

    gid = token_hex(4)
    size = api.getSize(node)
    added_to_queue, event = await check_running_tasks(listener, "dl")
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, gid, "dl")
        await listener.on_download_start()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with task_dict_lock:
            if listener.mid not in task_dict:
                await executor.do(api.logout)
                if folder_api:
                    await executor.do(folder_api.logout)
                return
        from_queue = True
        LOGGER.info(f"Start Queued Download from Mega: {name}")
    else:
        from_queue = False

    async with task_dict_lock:
        task_dict[listener.mid] = MegaDownloadStatus(
            listener, name, size, gid, mega_listener
        )
    async with queue_dict_lock:
        non_queued_dl.add(listener.mid)

    if from_queue:
        LOGGER.info(f"Start Queued Download from Mega: {name}")
    else:
        await listener.on_download_start()
        await sendStatusMessage(listener.message)
        LOGGER.info(f"Download from Mega: {name}")

    await makedirs(path, exist_ok=True)
    await executor.do(api.startDownload, node, path, name, None, False, None)
    await executor.do(api.logout)
    if folder_api:
        await executor.do(folder_api.logout)
