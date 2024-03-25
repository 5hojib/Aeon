YT_HELP_MESSAGE = """
<b>To use the commands, follow this format:</b>
<code>/{cmd} link options</code> or replying to link </b>
<code>/{cmd} options</code>

<b>OPTIONS:</b>
<b>-s:</b> Select quality for specific link or links.

<b>-z password:</b> Create a password-protected zip file.

<b>-n new_name:</b> Rename the file.

<b>-t thumbnail url:</b> Custom thumbnail for each leexh.(raw or tg image url)

<b>-ss value:</b> Generate ss for leech video, max 10 for each leach.

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

<b>-t thumbnail url:</b> Custom thumbnail for each leexh.(raw or tg image url)

<b>-ss value:</b> Generate ss for leech video, max 10 for each leach.

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

<b>main:dump/ubuntu.iso</b> or <b>rcl:</b> Treat a path as an rclone download."""


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
