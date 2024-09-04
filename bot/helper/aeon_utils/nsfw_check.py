from re import IGNORECASE, escape, search

nsfw_keywords = [
    "porn",
    "onlyfans",
    "nsfw",
    "Brazzers",
    "adult",
    "xnxx",
    "xvideos",
    "nsfwcherry",
    "hardcore",
    "Pornhub",
    "xvideos2",
    "youporn",
    "pornrip",
    "playboy",
    "hentai",
    "erotica",
    "blowjob",
    "redtube",
    "stripchat",
    "camgirl",
    "nude",
    "fetish",
    "cuckold",
    "orgy",
    "horny",
    "swingers",
]


def is_nsfw(text):
    pattern = (
        r"(?:^|\W|_)(?:"
        + "|".join(escape(keyword) for keyword in nsfw_keywords)
        + r")(?:$|\W|_)"
    )
    return bool(search(pattern, text, flags=IGNORECASE))


def is_nsfw_data(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if any(
                    isinstance(value, str) and is_nsfw(value)
                    for value in item.values()
                ):
                    return True
            elif (
                "name" in item
                and isinstance(item["name"], str)
                and is_nsfw(item["name"])
            ):
                return True
    elif isinstance(data, dict) and "contents" in data:
        for item in data["contents"]:
            if "filename" in item and is_nsfw(item["filename"]):
                return True
    return False


async def nsfw_precheck(message):
    if is_nsfw(message.text):
        return True

    reply_to = message.reply_to_message
    if not reply_to:
        return False

    for attr in ["document", "video"]:
        if hasattr(reply_to, attr) and getattr(reply_to, attr):
            file_name = getattr(reply_to, attr).file_name
            if file_name and is_nsfw(file_name):
                return True

    return any(
        is_nsfw(getattr(reply_to, attr))
        for attr in ["caption", "text"]
        if hasattr(reply_to, attr) and getattr(reply_to, attr)
    )
