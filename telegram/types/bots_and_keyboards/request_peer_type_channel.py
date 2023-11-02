from ..object import Object


class RequestPeerTypeChannel(Object):
    """Object used to request clients to send a channel identifier.

    Parameters:
        is_creator (``bool``, *optional*):
            If True, show only Channel which user is the owner.

        is_username (``bool``, *optional*):
            If True, show only Channel which has username.
    """ # TODO user_admin_rights, bot_admin_rights

    def __init__(
        self,
        is_creator: bool=None,
        is_username: bool=None
    ):
        super().__init__()

        self.is_creator = is_creator
        self.is_username = is_username
