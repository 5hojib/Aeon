section_dict = {"General", "Video", "Audio", "Text", "Image"}


def parseinfo(out):
    tc = ""
    skip = False
    for line in out.split("\n"):
        if line.startswith("Menu"):
            skip = True
        elif any(line.startswith(section) for section in section_dict):
            skip = False
            if not line.startswith("General"):
                tc += "</pre><br>"
            tc += f"<blockquote>{line.replace('Text', 'Subtitle')}</blockquote><pre>"
        if not skip:
            key, sep, value = line.partition(":")
            tc += f"{key.strip():<28}{sep} {value.strip()}\n"
    tc += "</pre><br>"
    return tc
