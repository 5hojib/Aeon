#!/usr/bin/env python3
from asyncio import sleep

from bot import LOGGER, get_client, QbTorrents, qb_listener_lock
from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, sync_to_async


def get_download(client, tag):
    try:
        return client.torrents_info(tag=tag)[0]
    except Exception as e:
        LOGGER.error(
            f'{e}: Qbittorrent, while getting torrent info. Tag: {tag}')
        return None


class QbittorrentStatus:

    def __init__(self, listener, seeding=False, queued=False):
        self.__client = get_client()
        self.__listener = listener
        self.upload_details = listener.upload_details
        self.__info = get_download(self.__client, f'{self.__listener.uid}')
        self.queued = queued
        self.seeding = seeding
        self.message = listener.message

    def __update(self):
        new_info = get_download(self.__client, f'{self.__listener.uid}')
        if new_info is not None:
            self.__info = new_info

    def progress(self):
        return f'{round(self.__info.progress*100, 2)}%'

    def processed_bytes(self):
        return get_readable_file_size(self.__info.downloaded)

    def speed(self):
        return f"{get_readable_file_size(self.__info.dlspeed)}/s"

    def name(self):
        if self.__info.state in ["metaDL", "checkingResumeData"]:
            return f"[METADATA]{self.__info.name}"
        else:
            return self.__info.name

    def size(self):
        return get_readable_file_size(self.__info.size)

    def eta(self):
        return get_readable_time(self.__info.eta)

    def status(self):
        self.__update()
        state = self.__info.state
        if state == "queuedDL" or self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        elif state == "queuedUP":
            return MirrorStatus.STATUS_QUEUEUP
        elif state in ["pausedDL", "pausedUP"]:
            return MirrorStatus.STATUS_PAUSED
        elif state in ["checkingUP", "checkingDL"]:
            return MirrorStatus.STATUS_CHECKING
        elif state in ["stalledUP", "uploading"] and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        return self.__info.num_seeds

    def leechers_num(self):
        return self.__info.num_leechs

    def uploaded_bytes(self):
        return get_readable_file_size(self.__info.uploaded)

    def upload_speed(self):
        return f"{get_readable_file_size(self.__info.upspeed)}/s"

    def ratio(self):
        return f"{round(self.__info.ratio, 3)}"

    def seeding_time(self):
        return get_readable_time(self.__info.seeding_time)

    def download(self):
        return self

    def gid(self):
        return self.hash()[:8]

    def hash(self):
        self.__update()
        return self.__info.hash

    def client(self):
        return self.__client

    def listener(self):
        return self.__listener

    async def cancel_download(self):
        self.__update()
        await sync_to_async(self.__client.torrents_pause, torrent_hashes=self.__info.hash)
        if not self.seeding:
            if self.queued:
                LOGGER.info(f'Cancelling QueueDL: {self.name()}')
                msg = 'task have been removed from queue/download'
            else:
                LOGGER.info(f"Cancelling Download: {self.__info.name}")
                msg = 'Download stopped by user!'
            await sleep(0.3)
            await sync_to_async(self.__client.torrents_delete, torrent_hashes=self.__info.hash, delete_files=True)
            await sync_to_async(self.__client.torrents_delete_tags, tags=self.__info.tags)
            async with qb_listener_lock:
                if self.__info.tags in QbTorrents:
                    del QbTorrents[self.__info.tags]
            await self.__listener.onDownloadError(msg)