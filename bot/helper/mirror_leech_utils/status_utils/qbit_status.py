from asyncio import sleep, gather

from bot import LOGGER, QbTorrents, xnox_client, qb_listener_lock
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_time,
    get_readable_file_size,
)


def get_download(tag, old_info=None):
    try:
        res = xnox_client.torrents_info(tag=tag)[0]
        return res or old_info
    except Exception as e:
        LOGGER.error(f"{e}: Qbittorrent, while getting torrent info. Tag: {tag}")
        return old_info


class QbittorrentStatus:
    def __init__(self, listener, seeding=False, queued=False):
        self.queued = queued
        self.seeding = seeding
        self.listener = listener
        self._info = None
        self.message = listener.message

    def update(self):
        self._info = get_download(f"{self.listener.mid}", self._info)

    def progress(self):
        return f"{round(self._info.progress * 100, 2)}%"

    def processed_bytes(self):
        return get_readable_file_size(self._info.downloaded)

    def speed(self):
        return f"{get_readable_file_size(self._info.dlspeed)}/s"

    def name(self):
        if self._info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.listener.name}"
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._info.size)

    def eta(self):
        return get_readable_time(self._info.eta)

    def status(self):
        self.update()
        state = self._info.state
        if state == "queuedDL" or self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        if state == "queuedUP":
            return MirrorStatus.STATUS_QUEUEUP
        if state in ["pausedDL", "pausedUP"]:
            return MirrorStatus.STATUS_PAUSED
        if state in ["checkingUP", "checkingDL"]:
            return MirrorStatus.STATUS_CHECKING
        if state in ["stalledUP", "uploading"] and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        return MirrorStatus.STATUS_DOWNLOADING_Q

    def seeders_num(self):
        return self._info.num_seeds

    def leechers_num(self):
        return self._info.num_leechs

    def uploaded_bytes(self):
        return get_readable_file_size(self._info.uploaded)

    def seed_speed(self):
        return f"{get_readable_file_size(self._info.upspeed)}/s"

    def ratio(self):
        return f"{round(self._info.ratio, 3)}"

    def seeding_time(self):
        return get_readable_time(self._info.seeding_time)

    def task(self):
        return self

    def gid(self):
        return self.hash()[:12]

    def hash(self):
        return self._info.hash

    async def cancel_task(self):
        self.listener.isCancelled = True
        await sync_to_async(self.update)
        await sync_to_async(
            xnox_client.torrents_pause, torrent_hashes=self._info.hash
        )
        if not self.seeding:
            if self.queued:
                LOGGER.info(f"Cancelling QueueDL: {self.name()}")
                msg = "task have been removed from queue/download"
            else:
                LOGGER.info(f"Cancelling Download: {self._info.name}")
                msg = "Download stopped by user!"
            await sleep(0.3)
            await gather(
                self.listener.onDownloadError(msg),
                sync_to_async(
                    xnox_client.torrents_delete,
                    torrent_hashes=self._info.hash,
                    delete_files=True,
                ),
                sync_to_async(
                    xnox_client.torrents_delete_tags, tags=self._info.tags
                ),
            )
            async with qb_listener_lock:
                if self._info.tags in QbTorrents:
                    del QbTorrents[self._info.tags]
