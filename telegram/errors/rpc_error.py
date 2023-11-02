import re
from datetime import datetime
from importlib import import_module
from typing import Type, Union

from telegram import raw
from telegram.raw.core import TLObject
from .exceptions.all import exceptions


class RPCError(Exception):
    ID = None
    CODE = None
    NAME = None
    MESSAGE = "{value}"

    def __init__(
        self,
        value: Union[int, str, raw.types.RpcError] = None,
        rpc_name: str = None,
        is_unknown: bool = False,
        is_signed: bool = False
    ):
        super().__init__("Telegram says: [{}{} {}] - {} {}".format(
            "-" if is_signed else "",
            self.CODE,
            self.ID or self.NAME,
            self.MESSAGE.format(value=value),
            f'(caused by "{rpc_name}")' if rpc_name else ""
        ))

        try:
            self.value = int(value)
        except (ValueError, TypeError):
            self.value = value

        if is_unknown:
            with open("unknown_errors.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}\t{value}\t{rpc_name}\n")

    @staticmethod
    def raise_it(rpc_error: "raw.types.RpcError", rpc_type: Type[TLObject]):
        error_code = rpc_error.error_code
        is_signed = error_code < 0
        error_message = rpc_error.error_message
        rpc_name = ".".join(rpc_type.QUALNAME.split(".")[1:])

        if is_signed:
            error_code = -error_code

        if error_code not in exceptions:
            raise UnknownError(
                value=f"[{error_code} {error_message}]",
                rpc_name=rpc_name,
                is_unknown=True,
                is_signed=is_signed
            )

        error_id = re.sub(r"_\d+", "_X", error_message)

        if error_id not in exceptions[error_code]:
            raise getattr(
                import_module("telegram.errors"),
                exceptions[error_code]["_"]
            )(value=f"[{error_code} {error_message}]",
              rpc_name=rpc_name,
              is_unknown=True,
              is_signed=is_signed)

        value = re.search(r"_(\d+)", error_message)
        value = value.group(1) if value is not None else value

        raise getattr(
            import_module("telegram.errors"),
            exceptions[error_code][error_id]
        )(value=value,
          rpc_name=rpc_name,
          is_unknown=False,
          is_signed=is_signed)


class UnknownError(RPCError):
    CODE = 520
    """:obj:`int`: Error code"""
    NAME = "Unknown error"
