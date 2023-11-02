from io import BytesIO
from typing import Any

from ..tl_object import TLObject


class BoolFalse(bytes, TLObject):
    ID = 0xBC799737
    value = False

    @classmethod
    def read(cls, *args: Any) -> bool:
        return cls.value

    def __new__(cls) -> bytes:
        return cls.ID.to_bytes(4, "little")


class BoolTrue(BoolFalse):
    ID = 0x997275B5
    value = True


class Bool(bytes, TLObject):
    @classmethod
    def read(cls, data: BytesIO, *args: Any) -> bool:
        return int.from_bytes(data.read(4), "little") == BoolTrue.ID

    def __new__(cls, value: bool) -> bytes:
        return BoolTrue() if value else BoolFalse()
