#!/usr/bin/env python3

YT_HELP_MESSAGE = """
<b>To use the commands, follow this format:</b>
<code>/{cmd} link options</code> or replying to link </b>
<code>/{cmd} options</code>

<b>OPTIONS:</b>
<b>-s:</b> Select quality for specific link or links.

<b>-z password:</b> Create a password-protected zip file.

<b>-n new_name:</b> Rename the file.

<b>-id drive_folder_link or drive_id -index https://anything.in/0:</b> Upload to a custom drive.

<b>-opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{{"ffmpeg": ["-threads", "4"]}}|wait_for_video:(5, 100):</b> Set additional options.

<b>-i 10:</b> Process multiple links.

<b>-b:</b> Perform bulk download by replying to a text message or file with links separated with new line.


<b>Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.</b>
"""

MIRROR_HELP_MESSAGE = """
<b>To use the commands, follow this format:</b>
<code>/{cmd} link options</code> or replying to link </b>
<code>/{cmd} options</code>

<b>OPTIONS:</b>
<b>-n new name:</b> Rename the file or folder.

<b>-z or -z password:</b> Zip the file or folder with or without password.

<b>-e or -e password:</b> Extract the file or folder with or without password.

<b>-up upload destination:</b> Upload the file or folder to a specific destination.

<b>-id drive_folder_link</b> or <b>-id drive_id -index https://anything.in/0:</b>: Upload to a custom Google Drive folder or ID.

<b>-u username -p password:</b> Provide authorization for a direct link.

<b>-s:</b> Select a torrent file.

<b>-h Direct link custom headers:</b> -h
<code>/cmd</code> link -h Key: value Key1: value1.

<b>-d ratio:seed_time:</b> Set the seeding ratio and time for a torrent.

<b>-i number of links/files:</b> Process multiple links or files.

<b>-m folder name:</b> Process multiple links or files within the same upload directory.

<b>-b:</b> Perform bulk download by replying to a text message or file with multiple links separated with new line.

<b>-j:</b> Join split files together before extracting or zipping.

<b>-rcf:</b> Set Rclone flags for the command.

<b>main:dump/ubuntu.iso</b> or <b>rcl:</b> Treat a path as an rclone download.


<b>Note:</b>
<b>Commands starting with qb are specifically for torrents.</b>
Some commands may require additional user access or settings.
"""

RSS_HELP_MESSAGE = """
Use this format to add feed URL:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command + any arg
-inf: For included words filter.
-exf: For excluded words filter.

Example: Title <code>https://www.rss-url.com</code> inf: 1080 or 720 or 144p|mkv or mp4|hevc exf: flv or web|xxx opt: up: mrcc:remote:path/subdir rcf: --buffer-size:8M|key|key:value
This filter will parse links that have titles containing "(1080 or 720 or 144p) and (mkv or mp4) and hevc" and don't contain (flv or web) and xxx words. You can add whatever you want.

Another example: inf: 1080 or 720p|.web. or .webrip.|hevc or x264
This will parse titles that contain (1080 or 720p) and (.web. or .webrip.) and (hevc or x264). 
Note: I added spaces before and after "1080" to avoid wrong matching. If there is a number like "10805695" in the title, it won't match "1080" without spaces after it.

<b>Filter Notes:</b>
1. | means "and."
2. Add "or" between similar keys. For example, you can add it between qualities or between extensions. Avoid filters like "f: 1080|mp4 or 720|web" because this will parse "1080" and (mp4 or 720) and web, instead of (1080 and mp4) or (720 and web).
3. You can add "or" and "|" as much as you want.
4. Check the title for static special characters before or after the qualities, extensions, or other elements, and use them in the filter to avoid wrong matches.

<b>Timeout:</b> 60 sec.

<b>Please apply the same formatting to this message:</b>
"""

CLONE_HELP_MESSAGE = """
Send Gdrive|Gdot|Filepress|Filebee|Appdrive|Gdflix link or rclone path along with command or by replying to the link/rc_path by command.

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


default_desp = {'AS_DOCUMENT': 'Default type of Telegram file upload. Default is False mean as media.',
                'AUTHORIZED_CHATS': 'Fill user_id and chat_id of groups/users you want to authorize. Separate them by space.',
                'BASE_URL': 'Valid BASE URL where the bot is deployed to use torrent web files selection. Format of URL should be http://myip, where myip is the IP/Domain(public) of your bot or if you have chosen port other than 80 so write it in this format http://myip:port (http and not https). Str',
                'BASE_URL_PORT': 'Which is the BASE_URL Port. Default is 80. Int',
                'STORAGE_THRESHOLD': 'To leave specific storage free and any download will lead to leave free storage less than this value will be cancelled the default unit is GB. Int',
                'LEECH_LIMIT':  'To limit the Torrent/Direct/ytdlp leech size. the default unit is GB. Int',
                'CLONE_LIMIT': 'To limit the size of Google Drive folder/file which you can clone. the default unit is GB. Int',
                'MEGA_LIMIT': 'To limit the size of Mega download. the default unit is GB. Int',
                'TORRENT_LIMIT': 'To limit the size of torrent download. the default unit is GB. Int',
                'DIRECT_LIMIT': 'To limit the size of direct link download. the default unit is GB. Int',
                'YTDLP_LIMIT': 'To limit the size of ytdlp download. the default unit is GB. Int',
                'PLAYLIST_LIMIT': 'To limit Maximum Playlist Number. Int',
                'IMAGES': 'Add multiple telgraph(graph.org) image links that are seperated by spaces.',
                'IMG_SEARCH': 'Put Keyword to Download Images. Sperarte each name by , like anime, iron man, god of war',
                'IMG_PAGE': 'Set the page value for downloading a image. Each page have approx 70 images. Deafult is 1. Int',
                'USER_MAX_TASKS': 'Limit the Maximum task for users of group at a time. use the Int',
                'GDRIVE_LIMIT': 'To limit the size of Google Drive folder/file link for leech, Zip, Unzip. the default unit is GB. Int',
                'USER_TASKS_LIMIT': 'The maximum limit on every users for all tasks. Int',
                'FSUB_IDS': 'Fill chat_id(-100xxxxxx) of groups/channel you want to force subscribe. Separate them by space. Int\n\nNote: Bot should be added in the filled chat_id as admin',
                'BOT_TOKEN': 'The Telegram Bot Token that you got from @BotFather',
                'CMD_SUFFIX': 'commands index number. This number will added at the end all commands.',
                'DATABASE_URL': "Your Mongo Database URL (Connection string). Follow this Generate Database to generate database. Data will be saved in Database: auth and sudo users, users settings including thumbnails for each user, rss data and incomplete tasks.\n\n <b>NOTE:</b> You can always edit all settings that saved in database from the official site -> (Browse collections)",
                'DEFAULT_UPLOAD': 'Whether rc to upload to RCLONE_PATH or gd to upload to GDRIVE_ID. Default is gd.',
                'LEECH_DUMP_ID': "Chat ID to where leeched files would be uploaded. Int. NOTE: Only available for superGroup/channel. Add -100 before channel/superGroup id. In short don't add bot id or your id!",
                'MIRROR_LOG_ID': "Chat ID to where Mirror files would be Send. Int. NOTE: Only available for superGroup/channel. Add -100 before channel/superGroup id. In short don't add bot id or your id!. For Multiple id Separate them by space.",
                'EQUAL_SPLITS': 'Split files larger than LEECH_SPLIT_SIZE into equal parts size (Not working with zip cmd). Default is False.',
                'EXTENSION_FILTER': "File extensions that won't upload/clone. Separate them by space.",
                'GDRIVE_ID': 'This is the Folder/TeamDrive ID of the Google Drive OR root to which you want to upload all the mirrors using google-api-python-client.',
                'INCOMPLETE_TASK_NOTIFIER': 'Get incomplete task messages after restart. Require database and superGroup. Default is False',
                'INDEX_URL': 'Refer to https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index.',
                'SHOW_MEDIAINFO': 'Add Button to Show MediaInfo in Leeched file. Bool',
                'TOKEN_TIMEOUT': 'Token timeout for each group member in sec. Int',
                'LEECH_SPLIT_SIZE': 'Size of split in bytes. Default is 2GB. Default is 4GB if your account is premium.',
                'MEDIA_GROUP': 'View Uploaded splitted file parts in media group. Default is False.',
                'MEGA_EMAIL': 'E-Mail used to sign-in on mega.nz for using premium account. Str',
                'MEGA_PASSWORD': 'Password for mega.nz account. Str',
                'OWNER_ID': 'The Telegram User ID (not username) of the Owner of the bot.',
                'QUEUE_ALL': 'Number of parallel tasks of downloads and uploads. For example if 20 task added and QUEUE_ALL is 8, then the summation of uploading and downloading tasks are 8 and the rest in queue. Int. NOTE: if you want to fill QUEUE_DOWNLOAD or QUEUE_UPLOAD, then QUEUE_ALL value must be greater than or equal to the greatest one and less than or equal to summation of QUEUE_UPLOAD and QUEUE_DOWNLOAD',
                'QUEUE_DOWNLOAD': 'Number of all parallel downloading tasks. Int',
                'QUEUE_UPLOAD': 'Number of all parallel uploading tasks. Int',
                'RCLONE_FLAGS': 'key:value|key|key|key:value . Check here all RcloneFlags.',
                'RCLONE_PATH': "Default rclone path to which you want to upload all the mirrors using rclone.",
                'RCLONE_SERVE_URL': 'Valid URL where the bot is deployed to use rclone serve. Format of URL should be http://myip, where myip is the IP/Domain(public) of your bot or if you have chosen port other than 80 so write it in this format http://myip:port (http and not https)',
                'RCLONE_SERVE_USER': 'Username for rclone serve authentication.',
                'RCLONE_SERVE_PASS': 'Password for rclone serve authentication.',
                'RCLONE_SERVE_PORT': 'Which is the RCLONE_SERVE_URL Port. Default is 8080.',
                'RSS_CHAT_ID': 'Chat ID where rss links will be sent. If you want message to be sent to the channel then add channel id. Add -100 before channel id. Int',
                'RSS_DELAY': 'Time in seconds for rss refresh interval. Recommended 900 second at least. Default is 900 in sec. Int',
                'SEARCH_API_LINK': 'Search api app link. Get your api from deploying this repository. Supported Sites: 1337x, Piratebay, Nyaasi, Torlock, Torrent Galaxy, Zooqle, Kickass, Bitsearch, MagnetDL, Libgen, YTS, Limetorrent, TorrentFunk, Glodls, TorrentProject and YourBittorrent',
                'SEARCH_LIMIT': 'Search limit for search api, limit for each site and not overall result limit. Default is zero (Default api limit for each site).',
                'SEARCH_PLUGINS': 'List of qBittorrent search plugins (github raw links). I have added some plugins, you can remove/add plugins as you want.',
                'STOP_DUPLICATE': "Bot will check file/folder name in Drive incase uploading to GDRIVE_ID. If it's present in Drive then downloading or cloning will be stopped. (NOTE: Item will be checked using name and not hash, so this feature is not perfect yet). Default is False",
                'SUDO_USERS': 'Fill user_id of users whom you want to give sudo permission. Separate them by space. Int',
                'TELEGRAM_API': 'This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.',
                'TELEGRAM_HASH': 'This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.',
                'TORRENT_TIMEOUT': 'Timeout of dead torrents downloading with qBittorrent and Aria2c in seconds. Int',
                'UPSTREAM_REPO': "Your github repository link, if your repo is private add https://username:{githubtoken}@github.com/{username}/{reponame} format. Get token from Github settings. So you can update your bot from filled repository on each restart.",
                'UPSTREAM_BRANCH': 'Upstream branch for update. Default is master.',
                'SET_COMMANDS': 'Set bot command automatically. Bool',
                'UPTOBOX_TOKEN': 'Uptobox token to mirror uptobox links. Get it from <a href="https://uptobox.com/my_account">Uptobox Premium Account</a>.',
                'USER_SESSION_STRING': "To download/upload from your telegram account and to send rss. To generate session string use this command <code>python3 generate_string_session.py</code> after mounting repo folder for sure.\n\n<b>NOTE:</b> You can't use bot with private message. Use it with superGroup.",
                'USE_SERVICE_ACCOUNTS': 'Whether to use Service Accounts or not, with google-api-python-client. For this to work see Using Service Accounts section below. Default is False',
                'WEB_PINCODE': ' Whether to ask for pincode before selecting files from torrent in web or not. Default is False. Bool.',
                'YT_DLP_OPTIONS': 'Default yt-dlp options. Check all possible options HERE or use this script to convert cli arguments to api options. Format: key:value|key:value|key:value. Add ^ before integer or float, some numbers must be numeric and some string. \nExample: "format:bv*+mergeall[vcodec=none]|nocheckcertificate:True"'
                }
