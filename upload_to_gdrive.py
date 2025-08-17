import os
import mimetypes
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

FOLDER_ID = os.environ["GDRIVE_FOLDER_ID"]
CLIENT_ID = os.environ["GDRIVE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GDRIVE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GDRIVE_REFRESH_TOKEN"]
CSV_PATH = os.environ.get("LATEST_CSV")

if not CSV_PATH or not os.path.exists(CSV_PATH):
    raise SystemExit(f"❌ 目标文件不存在: {CSV_PATH}")

def get_service():
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def upload_or_update(service, file_path, folder_id):
    fname = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or "text/csv"

    q = f"name = '{fname.replace(\"'\", \"\\'\")}' and '{folder_id}' in parents and trashed = false"
    r = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    if r.get("files"):
        file_id = r["files"][0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"♻️ 已更新：{fname}  (fileId={file_id})")
    else:
        meta = {"name": fname, "parents": [folder_id]}
        created = service.files().create(body=meta, media_body=media, fields="id").execute()
        print(f"✅ 已上传：{fname}  (fileId={created['id']})")

def main():
    try:
        print(f"➡️ 准备上传：{CSV_PATH}")
        service = get_service()
        upload_or_update(service, CSV_PATH, FOLDER_ID)
    except HttpError as e:
        print("❌ Google Drive API 错误：", e)
        raise
    except Exception as e:
        print("❌ 运行失败：", e)
        raise

if __name__ == "__main__":
    main()
