from telegram import raw
from .auto_name import AutoName


class MessagesFilter(AutoName):
    """Messages filter enumeration used in :meth:`~telegram.Client.search_messages` and :meth:`~telegram.Client.search_global`"""

    EMPTY = raw.types.InputMessagesFilterEmpty
    "Empty filter (any kind of messages)"

    PHOTO = raw.types.InputMessagesFilterPhotos
    "Photo messages"

    VIDEO = raw.types.InputMessagesFilterVideo
    "Video messages"

    PHOTO_VIDEO = raw.types.InputMessagesFilterPhotoVideo
    "Photo and video messages"

    DOCUMENT = raw.types.InputMessagesFilterDocument
    "Document messages"

    URL = raw.types.InputMessagesFilterUrl
    "Messages containing URLs"

    ANIMATION = raw.types.InputMessagesFilterGif
    "Animation messages"

    VOICE_NOTE = raw.types.InputMessagesFilterVoice
    "Voice note messages"

    VIDEO_NOTE = raw.types.InputMessagesFilterRoundVideo
    "Video note messages"

    AUDIO_VIDEO_NOTE = raw.types.InputMessagesFilterRoundVideo
    "Audio and video note messages"

    AUDIO = raw.types.InputMessagesFilterMusic
    "Audio messages (music)"

    CHAT_PHOTO = raw.types.InputMessagesFilterChatPhotos
    "Chat photo messages"

    PHONE_CALL = raw.types.InputMessagesFilterPhoneCalls
    "Phone call messages"

    MENTION = raw.types.InputMessagesFilterMyMentions
    "Messages containing mentions"

    LOCATION = raw.types.InputMessagesFilterGeo
    "Location messages"

    CONTACT = raw.types.InputMessagesFilterContacts
    "Contact messages"

    PINNED = raw.types.InputMessagesFilterPinned
    "Pinned messages"
