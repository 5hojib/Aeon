from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper

drive_helper = GoogleDriveHelper()

def a(b):
	  return drive_helper.getFilesByFolderId(b)