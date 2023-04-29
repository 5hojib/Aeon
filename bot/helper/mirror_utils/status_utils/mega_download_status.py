#!/usr/bin/env python3
from mega import MegaApi

from bot.helper.ext_utils.bot_utils import (MirrorStatus,
                                            get_readable_file_size,
                                            get_readable_time)

engine_ = "MegaSDK"


class MegaDownloadStatus:

    def __init__(self, name, size, gid, obj, message, extra_details):
        self.__obj = obj
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.message = message
        self.extra_details = extra_details
        self.engine = engine_

    def name(self):
        return self.__name

    def progress_raw(self):
        try:
            return round(self.__obj.downloaded_bytes / self.__size * 100, 2)
        except:
            return 0.0

    def progress(self):
        return f"{self.progress_raw()}%"

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.downloaded_bytes)

    def eta(self):
        try:
            seconds = (self.__size - self.__obj.downloaded_bytes) / \
                self.__obj.speed
            return get_readable_time(seconds)
        except ZeroDivisionError:
            return '-'

    def size(self):
        return get_readable_file_size(self.__size)

    def speed(self):
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def gid(self):
        return self.__gid

    def download(self):
        return self.__obj
