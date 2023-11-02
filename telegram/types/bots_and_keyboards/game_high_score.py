import telegram
from telegram import raw, utils
from telegram import types
from ..object import Object


class GameHighScore(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        user: "types.User",
        score: int,
        position: int = None
    ):
        super().__init__(client)

        self.user = user
        self.score = score
        self.position = position

    @staticmethod
    def _parse(client, game_high_score: raw.types.HighScore, users: dict) -> "GameHighScore":
        users = {i.id: i for i in users}

        return GameHighScore(
            user=types.User._parse(client, users[game_high_score.user_id]),
            score=game_high_score.score,
            position=game_high_score.pos,
            client=client
        )

    @staticmethod
    def _parse_action(client, service: raw.types.MessageService, users: dict):
        return GameHighScore(
            user=types.User._parse(client, users[utils.get_raw_peer_id(service.from_id or service.peer_id)]),
            score=service.action.score,
            client=client
        )
