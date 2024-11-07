from bot.helper.ext_utils.status_utils import MirrorStatus


class RcloneStatus:
    def __init__(self, listener, obj, gid, status):
        self._obj = obj
        self._gid = gid
        self._status = status
        self.listener = listener
        self.message = listener.message

    def gid(self):
        return self._gid

    def progress(self):
        return self._obj.percentage

    def speed(self):
        return self._obj.speed

    def name(self):
        return self.listener.name

    def size(self):
        return self._obj.size

    def eta(self):
        return self._obj.eta

    def status(self):
        if self._status == "dl":
            return MirrorStatus.STATUS_DOWNLOADING_RC
        if self._status == "up":
            return MirrorStatus.STATUS_UPLOADING_RC
        return MirrorStatus.STATUS_CLONING_RC

    def processed_bytes(self):
        return self._obj.transferred_size

    def task(self):
        return self._obj
