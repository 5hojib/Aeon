from bot import GROUPS_EMAIL

YT_HELP_MESSAGE = """
<b>To use the commands, follow this format:</b>
<code>/{cmd} link options</code> or replying to link </b>
<code>/{cmd} options</code>

<b>OPTIONS:</b>
<blockquote expandable><b>-s:</b> Select quality for specific link or links.
<b>-z password:</b> Create a password-protected zip file.
<b>-n new_name:</b> Rename the file.
<b>-t thumbnail url:</b> Custom thumbnail for each leech(raw or tg image url).
<b>-ss value:</b> Generate ss for leech video, max 10 for each leach.
<b>-id drive_folder_link or drive_id -index https://anything.in/0:</b> Upload to a custom drive.
<b>-opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{{"ffmpeg": ["-threads", "4"]}}|wait_for_video:(5, 100):</b> Set additional options.
<b>-i 10:</b> Process multiple links.
<b>-b:</b> Perform bulk download by replying to a text message or file with links separated with new line.</blockquote>


<b>Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.</b>
"""

MIRROR_HELP_MESSAGE = """
<b>To use the commands, follow this format:</b>
<code>/{cmd} link options</code> or replying to link </b>
<code>/{cmd} options</code>

<b>OPTIONS:</b>
<blockquote expandable><b>-n new name:</b> Rename the file or folder.
<b>-atc attachment url:</b> Custom attachment for each mkv.(raw only)
<b>-t thumbnail url:</b> Custom thumbnail for each leech.(raw or tg image url)
<b>-ss value:</b> Generate ss for leech video, max 10 for each leach.
<b>-z or -z password:</b> Zip the file or folder with or without password.
<b>-e or -e password:</b> Extract the file or folder with or without password.
<b>-up upload destination:</b> Upload the file or folder to a specific destination.
<b>-id drive_folder_link</b> or <b>-id drive_id -index https://anything.in/0:</b>: Upload to a custom Google Drive folder or ID.
<b>-u username -p password:</b> Provide authorization for a direct link.
<b>-s:</b> Select a torrent file.
<b>-h Direct link custom headers:</b> -h <code>/cmd</code> link -h Key: value Key1: value1.
<b>-d ratio:seed_time:</b> Set the seeding ratio and time for a torrent.
<b>-i number of links/files:</b> Process multiple links or files.
<b>-m folder name:</b> Process multiple links or files within the same upload directory.
<b>-b:</b> Perform bulk download by replying to a text message or file with multiple links separated with new line.
<b>-j:</b> Join split files together before extracting or zipping.
<b>-rcf:</b> Set Rclone flags for the command.
<b>main:dump/ubuntu.iso</b> or <b>rcl:</b> Treat a path as an rclone download.</blockquote>
"""

CLONE_HELP_MESSAGE = """
Send Gdrive link or rclone path along with command or by replying to the link/rc_path by command.

<b>Multi links only by replying to first gdlink or rclone_path:</b>
<code>/{cmd}</code> -i 10 (number of links/pathies)

<b>Gdrive:</b>
<code>/{cmd}</code> gdrivelink

<b>Upload Custom Drive:</b> link -id -index
-id <code>drive_folder_link</code> or <code>drive_id</code> -index <code>https://anything.in/0:</code>
drive_id must be a folder ID, and index must be a URL, otherwise it will not accept.

<b>Rclone:</b>
<code>/{cmd}</code> (rcl or rclone_path) -up (rcl or rclone_path) -rcf flagkey:flagvalue|flagkey|flagkey:flagvalue

Note: If -up is not specified, the rclone destination will be the RCLONE_PATH from config.env.
"""

PASSWORD_ERROR_MESSAGE = """
<b>This link requires a password!</b>
- Insert sign <b>::</b> after the link and write the password after the sign.
<b>Example:</b> {}::love you
Note: No spaces between the signs <b>::</b>
For the password, you can use a space!
"""


bset_display_dict = {
    "AS_DOCUMENT": "Default type of Telegram file upload. Default is False, meaning as media.",
    "BASE_URL": "Valid BASE URL where the bot is deployed to use torrent web files selection. Collect it from Heroku.",
    "LEECH_LIMIT": "To limit the Torrent/Direct/ytdlp leech size. The default unit is GB. Int",
    "CLONE_LIMIT": "To limit the size of Google Drive folder/file which you can clone. The default unit is GB. Int",
    "MEGA_LIMIT": "To limit the size of Mega download. The default unit is GB. Int",
    "TORRENT_LIMIT": "To limit the size of torrent download. The default unit is GB. Int",
    "DIRECT_LIMIT": "To limit the size of direct link download. The default unit is GB. Int",
    "YTDLP_LIMIT": "To limit the size of ytdlp download. The default unit is GB. Int",
    "PLAYLIST_LIMIT": "To limit the maximum number of playlists. Int",
    "IMAGES": "Add multiple Telegraph (graph.org) image links, separated by spaces.",
    "USER_MAX_TASKS": "Limit the maximum tasks for users of a group at a time. Use an integer.",
    "GDRIVE_LIMIT": "To limit the size of Google Drive folder/file link for leech, zip, and unzip. The default unit is GB. Int",
    "USER_TASKS_LIMIT": "The maximum limit on tasks for each user. Int",
    "FSUB_IDS": "Fill in the chat_id (-100xxxxxx) of groups/channels you want to force subscribe. Separate them by space. Int\n\nNote: Bot should be added in the filled chat_id as admin.",
    "BOT_TOKEN": "The Telegram Bot Token that you got from @BotFather.",
    "CMD_SUFFIX": "Commands index number. This number will be added at the end of all commands.",
    "DATABASE_URL": "Your Mongo Database URL (Connection string). Follow this Generate Database to generate the database. Data will be saved in the database: auth and sudo users, user settings including thumbnails for each user.\n\n<b>NOTE:</b> You can always edit all settings saved in the database from the official site -> (Browse collections).",
    "DEFAULT_UPLOAD": 'Whether "rc" to upload to RCLONE_PATH or "gd" to upload to GDRIVE_ID. Default is "gd".',
    "LEECH_DUMP_ID": "Chat ID where leeched files would be uploaded. Int. NOTE: Only available for superGroup/channel. Add -100 before the channel/superGroup ID. In short, don't add bot ID or your ID!",
    "MIRROR_LOG_ID": "Chat ID where mirror files would be sent. Int. NOTE: Only available for superGroup/channel. Add -100 before the channel/superGroup ID. In short, don't add bot ID or your ID! For multiple IDs, separate them by space.",
    "EXTENSION_FILTER": "File extensions that won't be uploaded/cloned. Separate them by space.",
    "GDRIVE_ID": "This is the Folder/TeamDrive ID of Google Drive or root to which you want to upload all the mirrors using google-api-python-client.",
    "INDEX_URL": "Refer to https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index.",
    "SHOW_MEDIAINFO": "Add a button to show MediaInfo in leeched files. Bool",
    "TOKEN_TIMEOUT": "Token timeout for each group member in seconds. Int",
    "MEDIA_GROUP": "View uploaded split file parts in media group. Default is False.",
    "MEGA_EMAIL": "Email used to sign in on mega.nz for using a premium account. Str",
    "MEGA_PASSWORD": "Password for mega.nz account. Str",
    "OWNER_ID": "The Telegram User ID (not username) of the owner of the bot.",
    "QUEUE_ALL": "Number of parallel tasks for downloads and uploads. For example, if 20 tasks are added and QUEUE_ALL is 8, then the sum of uploading and downloading tasks is 8 and the rest are in the queue. Int. NOTE: If you want to fill QUEUE_DOWNLOAD or QUEUE_UPLOAD, then the QUEUE_ALL value must be greater than or equal to the largest one and less than or equal to the sum of QUEUE_UPLOAD and QUEUE_DOWNLOAD.",
    "QUEUE_DOWNLOAD": "Number of all parallel downloading tasks. Int",
    "QUEUE_UPLOAD": "Number of all parallel uploading tasks. Int",
    "RCLONE_FLAGS": "key:value|key|key|key:value. Check here all RcloneFlags.",
    "RCLONE_PATH": "Default rclone path to which you want to upload all the mirrors using rclone.",
    "SEARCH_API_LINK": "Search API app link. Get your API from deploying this repository. Supported sites: 1337x, Piratebay, Nyaasi, Torlock, Torrent Galaxy, Zooqle, Kickass, Bitsearch, MagnetDL, Libgen, YTS, Limetorrent, TorrentFunk, Glodls, TorrentProject, and YourBittorrent.",
    "SEARCH_LIMIT": "Search limit for the search API, limit for each site and not overall result limit. Default is zero (default API limit for each site).",
    "STOP_DUPLICATE": "Bot will check file/folder name in Drive in case of uploading to GDRIVE_ID. If it's present in Drive, then downloading or cloning will be stopped. (NOTE: Item will be checked using name and not hash, so this feature is not perfect yet). Default is False.",
    "TELEGRAM_API": "This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.",
    "TELEGRAM_HASH": "This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.",
    "TORRENT_TIMEOUT": "Timeout for dead torrents downloading with qBittorrent and Aria2c in seconds. Int",
    "UPSTREAM_REPO": "Your GitHub repository link. If your repo is private, add https://username:{githubtoken}@github.com/{username}/{reponame} format. Get the token from GitHub settings. So you can update your bot from the filled repository on each restart.",
    "UPSTREAM_BRANCH": "Upstream branch for updates. Default is main.",
    "SET_COMMANDS": "Set bot commands automatically. Bool",
    "USE_SERVICE_ACCOUNTS": "Whether to use Service Accounts or not, with google-api-python-client. For this to work see Using Service Accounts section below. Default is False",
    "USER_SESSION_STRING": "To download/upload from your Telegram account. To generate a session string, use this command <code>python3 generate_string_session.py</code> after mounting the repo folder for sure.\n\n<b>NOTE:</b> You can't use the bot with private messages. Use it with superGroup.",
    "YT_DLP_OPTIONS": 'Default yt-dlp options. Check all possible options HERE or use this script to convert CLI arguments to API options. Format: key:value|key:value|key:value. Add ^ before an integer or float, some numbers must be numeric and some strings. \nExample: "format:bv*+mergeall[vcodec=none]|nocheckcertificate:True".',
}

uset_display_dict = {
    "rcc": [
        "RClone is a command-line program to sync files and directories to and from different cloud storage providers like GDrive, OneDrive...",
        "Send rclone.conf. Timeout: 60 sec",
    ],
    "prefix": [
        "Filename Prefix is the front part attached to the filename of the leech files.",
        "Send filename prefix. Timeout: 60 sec",
    ],
    "suffix": [
        "Filename Suffix is the end part attached to the filename of the leech files.",
        "Send filename suffix. Timeout: 60 sec",
    ],
    "remname": [
        "Filename Remname is a combination of regex patterns used for removing or manipulating the filename of the leech files.",
        "Send filename remname. Timeout: 60 sec",
    ],
    "metadata": [
        "Metadata will change MKV video files including all audio, streams, and subtitle titles.",
        "Send metadata title. Timeout: 60 sec",
    ],
    "attachment": [
        "Attachment url, it will added in mkv as thumbnail or cover photo, whetever you say.",
        "Send raw photo url, example from imgbb.com . Timeout: 60 sec",
    ],
    "lcaption": [
        "Leech Caption is the custom caption on the leech files uploaded by the bot.",
        "Send leech caption. You can add HTML tags. Timeout: 60 sec",
    ],
    "ldump": [
        "Leech Files User Dump for personal use as a storage.",
        "Send leech dump channel ID. Timeout: 60 sec",
    ],
    "thumb": [
        "Custom thumbnail to appear on the leeched files uploaded by the bot.",
        "Send a photo to save it as a custom thumbnail. Timeout: 60 sec",
    ],
    "yt_opt": [
        "YT-DLP Options are the custom quality settings for the extraction of videos from yt-dlp supported sites.",
        'Send YT-DLP options. Timeout: 60 sec\nFormat: key:value|key:value|key:value.\nExample: format:bv*+mergeall[vcodec=none]|nocheckcertificate:True\nCheck all yt-dlp API options from this <a href="https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184">file</a> or use this <a href="https://t.me/mltb_official_channel/177">script</a> to convert CLI arguments to API options.',
    ],
    "user_tds": [
        f'UserTD helps to upload files via the bot to your custom drive destination through global SA mail.\n\n<b>SA Mail:</b> {SA if (SA := GROUPS_EMAIL) else "Not Specified"}',
        "Send User TD details for use while mirroring/cloning.\n<b>Format:</b>\nname drive_id/link index (optional)\n\n<b>NOTE:</b>\n1. You must add our SA mail to your drive with write permission.\n2. Names can have spaces.\n3. Drive ID must be valid for acceptance.\n\n<b>Timeout:</b> 60 sec.",
    ],
}
