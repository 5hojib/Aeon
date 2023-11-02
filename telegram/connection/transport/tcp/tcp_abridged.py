import logging
from typing import Optional

from .tcp import TCP

log = logging.getLogger(__name__)


class TCPAbridged(TCP):
    def __init__(self, ipv6: bool, proxy: dict):
        super().__init__(ipv6, proxy)

    async def connect(self, address: tuple):
        await super().connect(address)
        await super().send(b"\xef")

    async def send(self, data: bytes, *args):
        length = len(data) // 4

        await super().send(
            (bytes([length])
             if length <= 126
             else b"\x7f" + length.to_bytes(3, "little"))
            + data
        )

    async def recv(self, length: int = 0) -> Optional[bytes]:
        length = await super().recv(1)

        if length is None:
            return None

        if length == b"\x7f":
            length = await super().recv(3)

            if length is None:
                return None

        return await super().recv(int.from_bytes(length, "little") * 4)
