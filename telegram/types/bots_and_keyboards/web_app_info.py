from ..object import Object


class WebAppInfo(Object):
    def __init__(
        self, *,
        url: str,
    ):
        super().__init__()

        self.url = url
