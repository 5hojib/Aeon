from telegram import raw
from .auto_name import AutoName


class ChatAction(AutoName):
    TYPING = raw.types.SendMessageTypingAction
    UPLOAD_PHOTO = raw.types.SendMessageUploadPhotoAction
    RECORD_VIDEO = raw.types.SendMessageRecordVideoAction
    UPLOAD_VIDEO = raw.types.SendMessageUploadVideoAction
    RECORD_AUDIO = raw.types.SendMessageRecordAudioAction
    UPLOAD_AUDIO = raw.types.SendMessageUploadAudioAction
    UPLOAD_DOCUMENT = raw.types.SendMessageUploadDocumentAction
    FIND_LOCATION = raw.types.SendMessageGeoLocationAction
    RECORD_VIDEO_NOTE = raw.types.SendMessageRecordRoundAction
    UPLOAD_VIDEO_NOTE = raw.types.SendMessageUploadRoundAction
    PLAYING = raw.types.SendMessageGamePlayAction
    CHOOSE_CONTACT = raw.types.SendMessageChooseContactAction
    SPEAKING = raw.types.SpeakingInGroupCallAction
    IMPORT_HISTORY = raw.types.SendMessageHistoryImportAction
    CHOOSE_STICKER = raw.types.SendMessageChooseStickerAction
    CANCEL = raw.types.SendMessageCancelAction
