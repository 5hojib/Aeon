from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper

drive_helper = GoogleDriveHelper()
files_in_folder = drive_helper.__getFilesByFolderId(folder_id)

def a(b):
	  return drive_helper.__getFilesByFolderId(b)