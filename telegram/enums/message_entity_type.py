from telegram import raw
from .auto_name import AutoName


class MessageEntityType(AutoName):
    MENTION = raw.types.MessageEntityMention
    HASHTAG = raw.types.MessageEntityHashtag
    CASHTAG = raw.types.MessageEntityCashtag
    BOT_COMMAND = raw.types.MessageEntityBotCommand
    URL = raw.types.MessageEntityUrl
    EMAIL = raw.types.MessageEntityEmail
    PHONE_NUMBER = raw.types.MessageEntityPhone
    BOLD = raw.types.MessageEntityBold
    ITALIC = raw.types.MessageEntityItalic
    UNDERLINE = raw.types.MessageEntityUnderline
    STRIKETHROUGH = raw.types.MessageEntityStrike
    SPOILER = raw.types.MessageEntitySpoiler
    CODE = raw.types.MessageEntityCode
    PRE = raw.types.MessageEntityPre
    BLOCKQUOTE = raw.types.MessageEntityBlockquote
    TEXT_LINK = raw.types.MessageEntityTextUrl
    TEXT_MENTION = raw.types.MessageEntityMentionName
    BANK_CARD = raw.types.MessageEntityBankCard
    CUSTOM_EMOJI = raw.types.MessageEntityCustomEmoji
    UNKNOWN = raw.types.MessageEntityUnknown
