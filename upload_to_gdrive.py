# upload_to_gdrive.py
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LoadCredentialsFile("creds.json")
if gauth.credentials is None:
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:
    gauth.Refresh()
else:
    gauth.Authorize()
gauth.SaveCredentialsFile("creds.json")

drive = GoogleDrive(gauth)
file_path = os.environ["LATEST_CSV"]
file_name = os.path.basename(file_path)

f = drive.CreateFile({
    'title': file_name,
    'parents': [{'id': os.environ["GDRIVE_FOLDER_ID"]}]
})
f.SetContentFile(file_path)
f.Upload()
print(f"Uploaded {file_name} to Google Drive.")
