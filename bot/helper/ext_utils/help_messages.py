#!/usr/bin/env python3

YT_HELP_MESSAGE = """
<a href='https://telegra.ph/Mirror-Leech-YtDl-04-08'>Click here</a>
"""

MIRROR_HELP_MESSAGE = """
<a href='https://telegra.ph/Mirror-Leech-YtDl-04-08'>Click here</a>
"""

CLONE_HELP_MESSAGE = """Send Gdrive|Gdot|Filepress|Filebee|Appdrive|Gdflix link or rclone path along with command or by replying to the link/rc_path by command
<b>Multi links only by replying to first gdlink or rclone_path:</b>
<code>/{cmd}</code> 10(number of links/pathies)
<b>Gdrive:</b>
<code>/{cmd}</code> gdrivelink
<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>id:</b> <code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b> <code>https://anything.in/0:</code> link or by replying to link
drive_id must be folder id and index must be url else it will not accept
<b>Rclone:</b>
<code>/{cmd}</code> rcl or rclone_path up: rcl or rclone_path rcf: flagkey:flagvalue|flagkey|flagkey:flagvalue
Notes:
if up: not specified then rclone destination will be the RCLONE_PATH from config.env
"""

RSS_HELP_MESSAGE = """
Use this format to add feed url:
Title1 link (required)
Title2 link c: cmd inf: xx exf: xx opt: options like(up, rcf, pswd) (optional)
Title3 link c: cmd d:ratio:time opt: up: gd

c: command + any mirror option before link like seed option.
opt: any option after link like up, rcf and pswd(zip).
inf: For included words filter.
exf: For excluded words filter.

Example: Title https://www.rss-url.com inf: 1080 or 720 or 144p|mkv or mp4|hevc exf: flv or web|xxx opt: up: mrcc:remote:path/subdir rcf: --buffer-size:8M|key|key:value
This filter will parse links that it's titles contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't conyain (flv or web) and xxx` words. You can add whatever you want.

Another example: inf:  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
3. You can add `or` and `|` as much as you want."
4. Take look on title if it has static special character after or before the qualities or extensions or whatever and use them in filter to avoid wrong match.
Timeout: 60 sec.
"""