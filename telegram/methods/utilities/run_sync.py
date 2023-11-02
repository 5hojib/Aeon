from telegram import utils
from typing import Any, Callable, TypeVar

class RunSync:
    Result = TypeVar("Result")

    async def run_sync(self, func: Callable[..., Result], *args: Any, **kwargs: Any) -> Result:
        return await utils.run_sync(func, *args, **kwargs)
