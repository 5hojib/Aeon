#!/usr/bin/env python3
class style:
    LINKS_START = """<b>Task Started</b>

<b>• Mode:</b> {Mode}
<b>• By:</b> {Tag}\n\n"""

    ST_MSG = '''This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram.
<b>Type {help_command} to get a list of available commands</b>'''
    ST_BOTPM = '''Now, This bot will send all your files and links here. Start Using ...'''
    ST_UNAUTH = '''You Are not authorized user!'''
    # ---------------------

    # async def restart(client, message): ---> __main__.py
    RESTARTING = 'Restarting...'
    # ---------------------

    # async def restart_notification(): ---> __main__.py
    RESTART_SUCCESS = '''Restarted Successfully!

<b>Date:</b> {date}
<b>Time:</b> {time}'''
    RESTARTED = '''Bot Restarted!'''
    # ---------------------

    # async def ping(client, message): ---> __main__.py
    PING = 'Starting Ping...'
    PING_VALUE = '{value} ms'
    # ---------------------

    # async def __msg_to_reply(self): ---> pyrogramEngine.py
    L_PM_START =          "<b>Task started</b>"
    L_LOG_START =         "<b>Task started</b>\n\n<b>• User:</b> {mention}\n<b>• ID:</b> <code>{uid}</code>"

    # async def onUploadComplete(): ---> tasks_listener.py
    NAME =                '{Name}\n\n'
    SIZE =                '<b>• Size: </b>{Size}\n'
    ELAPSE =              '<b>• Elapsed: </b>{Time}\n'
    MODE =                '<b>• Mode: </b>{Mode}\n'

    # ----- LEECH -------
    L_TOTAL_FILES =       '<b>• Total files: </b>{Files}\n'
    L_CORRUPTED_FILES =   '<b>• Corrupted files: </b>{Corrupt}\n'
    L_CC =                '<b>• Leeched by: </b>{Tag}\n\n'
    PM_BOT_MSG =          '<b>Files are send above</b>'
    L_BOT_MSG =           '<b>Files has been sent to your inbox</b>'
    L_LL_MSG =            '<b>Files are sent. Access via links</b>'
    
    # ----- MIRROR -------
    M_TYPE =              '<b>• Type: </b>{Mimetype}\n'
    M_SUBFOLD =           '<b>• SubFolders: </b>{Folder}\n'
    TOTAL_FILES =         '<b>• Files: </b>{Files}\n'
    RCPATH =              '<b>• Path: </b><code>{RCpath}</code>\n'
    M_CC =                '<b>• Uploaded by: {Tag}\n\n'
    M_BOT_MSG =           '<b>Links has been sent to your inbox</b>'
    
    # ----- BUTTONS -------
    CLOUD_LINK     =  'Cloud Link'
    RCLONE_LINK    =  'Rclone Link'
    SOURCE_URL     =  'Source Link'
    INDEX_LINK     =  'Index Link'
    VIEW_LINK      =  'View Link'
    CHECK_PM       =  'View in inbox'
    MEDIAINFO_LINK =  'Media Info'
    # ---------------------

    #STOP_DUPLICATE_MSG: ---> clone.py, aria2_listener.py, task_manager.py
    STOP_DUPLICATE = 'File/Folder is already available in Drive.\nHere are {content} list results:'
    # ---------------------

    # async def countNode(_, message): ----> gd_count.py
    COUNT_MSG    =  '<b>Counting:</b> <code>{LINK}</code>'
    COUNT_NAME   =  '{COUNT_NAME}\n\n'
    COUNT_SIZE   =  '<b>• Size: </b>{COUNT_SIZE}\n'
    COUNT_TYPE   =  '<b>• Type: </b>{COUNT_TYPE}\n'
    COUNT_SUB    =  '<b>• SubFolders: </b>{COUNT_SUB}\n'
    COUNT_FILE   =  '<b>• Files: </b>{COUNT_FILE}\n'
    COUNT_CC     =  '<b>• Counted by: </b>{COUNT_CC}\n'
    # ---------------------

    # LIST ---> gd_list.py
    LIST_SEARCHING  =  '<b>Searching for </b>{NAME}'
    LIST_FOUND      =  '<b>Found {NO} result for </b>{NAME}'
    LIST_NOT_FOUND  =  '<b>No result found for </b>{NAME}'
    # ---------------------

    # USER Setting --> user_setting.py 
    USER_SETTING = '<b>User Settings for {NAME}</b>'

    UNIVERSAL = '''<b>Universal Settings for {NAME}</b>

<b>• YT-DLP Options:</b> <b><code>{YT}</code></b>
<b>• User Bot PM:</b> <code>{BOT_PM}</code>
<b>• Prefix:</b> <code>{MPREFIX}</code>
<b>• Suffix:</b> <code>{MSUFFIX}</code>
<b>• Remname:</b> <code>{MREMNAME}</code>'''

    MIRROR = '''<b>Mirror Settings for {NAME}</b>

<b>• Rclone Config:</b> {RCLONE}
<b>• User TD Mode:</b> {UTD}'''

    LEECH = '''<b>Leech Settings for {NAME}</b>

<b>• Leech Type:</b> {LTYPE}
<b>• Custom Thumbnail:</b> {THUMB}
<b>• Leech Split Size:</b> <code>{SPLIT_SIZE}</code>
<b>• Equal Splits:</b> {EQUAL_SPLIT}
<b>• Media Group:</b> {MEDIA_GROUP}
<b>• Leech Caption:</b> <code>{LCAPTION}</code>
<b>• Leech Dump:</b> <code>{LDUMP}</code>
<b>• MediaInfo Mode:</b> <code>{MEDIAINFO}</code>'''