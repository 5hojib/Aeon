#!/usr/bin/env python3
class style:
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