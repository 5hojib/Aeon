import logging
import time

log = logging.getLogger(__name__)


class MsgId:
    last_time = 0
    offset = 0

    def __new__(cls) -> int:
        now = int(time.time())
        cls.offset = (cls.offset + 4) if now == cls.last_time else 0
        msg_id = (now * 2 ** 32) + cls.offset
        cls.last_time = now

        return msg_id
