import telegram
from telegram import raw
from telegram import types
from ..object import Object


class WebPage(Object):
    def __init__(
        self,
        *,
        client: "telegram.Client" = None,
        id: str,
        url: str,
        display_url: str,
        type: str = None,
        site_name: str = None,
        title: str = None,
        description: str = None,
        audio: "types.Audio" = None,
        document: "types.Document" = None,
        photo: "types.Photo" = None,
        animation: "types.Animation" = None,
        video: "types.Video" = None,
        embed_url: str = None,
        embed_type: str = None,
        embed_width: int = None,
        embed_height: int = None,
        duration: int = None,
        author: str = None
    ):
        super().__init__(client)

        self.id = id
        self.url = url
        self.display_url = display_url
        self.type = type
        self.site_name = site_name
        self.title = title
        self.description = description
        self.audio = audio
        self.document = document
        self.photo = photo
        self.animation = animation
        self.video = video
        self.embed_url = embed_url
        self.embed_type = embed_type
        self.embed_width = embed_width
        self.embed_height = embed_height
        self.duration = duration
        self.author = author

    @staticmethod
    def _parse(client, webpage: "raw.types.WebPage") -> "WebPage":
        audio = None
        document = None
        photo = None
        animation = None
        video = None

        if isinstance(webpage.photo, raw.types.Photo):
            photo = types.Photo._parse(client, webpage.photo)

        doc = webpage.document

        if isinstance(doc, raw.types.Document):
            attributes = {type(i): i for i in doc.attributes}

            file_name = getattr(
                attributes.get(
                    raw.types.DocumentAttributeFilename, None
                ), "file_name", None
            )

            if raw.types.DocumentAttributeAudio in attributes:
                audio_attributes = attributes[raw.types.DocumentAttributeAudio]
                audio = types.Audio._parse(client, doc, audio_attributes, file_name)

            elif raw.types.DocumentAttributeAnimated in attributes:
                video_attributes = attributes.get(raw.types.DocumentAttributeVideo, None)
                animation = types.Animation._parse(client, doc, video_attributes, file_name)

            elif raw.types.DocumentAttributeVideo in attributes:
                video_attributes = attributes[raw.types.DocumentAttributeVideo]
                video = types.Video._parse(client, doc, video_attributes, file_name)

            else:
                document = types.Document._parse(client, doc, file_name)

        return WebPage(
            id=str(webpage.id),
            url=webpage.url,
            display_url=webpage.display_url,
            type=webpage.type,
            site_name=webpage.site_name,
            title=webpage.title,
            description=webpage.description,
            audio=audio,
            document=document,
            photo=photo,
            animation=animation,
            video=video,
            embed_url=webpage.embed_url,
            embed_type=webpage.embed_type,
            embed_width=webpage.embed_width,
            embed_height=webpage.embed_height,
            duration=webpage.duration,
            author=webpage.author
        )
