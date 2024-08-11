from bot.helper.ext_utils.bot_utils import (
    MirrorStatus,
    get_readable_time,
    get_readable_file_size,
)


class TelegramStatus:
    def __init__(self, obj, size, message, gid, status):
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.__status = status
        self.message = message

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.processed_bytes)

    def size(self):
        return get_readable_file_size(self.__size)

    def status(self):
        if self.__status == "up":
            if self.__obj.processed_bytes == 0:
                return MirrorStatus.STATUS_PROCESSING
            return MirrorStatus.STATUS_UPLOADING
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        return self.__obj.name

    def progress(self):
        try:
            progress_raw = self.__obj.processed_bytes / self.__size * 100
        except Exception:
            progress_raw = 0
        return f"{round(progress_raw, 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self.__obj.speed)}/s"

    def eta(self):
        try:
            seconds = (self.__size - self.__obj.processed_bytes) / self.__obj.speed
            return get_readable_time(seconds)
        except Exception:
            return "-"

    def gid(self) -> str:
        return self.__gid

    def download(self):
        return self.__obj
