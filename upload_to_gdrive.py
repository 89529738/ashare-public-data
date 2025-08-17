import os
import mimetypes

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# === 环境变量 ===
FOLDER_ID = os.environ["GDRIVE_FOLDER_ID"]          # 目标 Google Drive 文件夹 ID
CLIENT_ID = os.environ["GDRIVE_CLIENT_ID"]          # OAuth 客户端 ID
CLIENT_SECRET = os.environ["GDRIVE_CLIENT_SECRET"]  # OAuth 客户端密钥
REFRESH_TOKEN = os.environ["GDRIVE_REFRESH_TOKEN"]  # OAuth refresh_token
CSV_PATH = os.environ.get("LATEST_CSV")             # 待上传的 CSV 文件路径（由前一步工作流写入）

if not CSV_PATH or not os.path.exists(CSV_PATH):
    raise SystemExit(f"❌ 目标文件不存在: {CSV_PATH}")


def get_service():
    """用 refresh_token 构建 Google Drive service 客户端"""
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    # 用 refresh_token 换取访问令牌
    creds.refresh(Request())

    # cache_discovery=False 防止某些环境下的缓存警告
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_or_update(service, file_path: str, folder_id: str):
    """如已存在同名文件则更新，否则上传新文件到指定文件夹"""
    fname = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or "text/csv"

    # 先把文件名中的单引号转义，然后再放进 f-string —— 这是修复点
    escaped_name = fname.replace("'", "\\'")
    q = f"name = '{escaped_name}' and '{folder_id}' in parents and trashed = false"

    # 查询是否已有同名文件
    r = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    if r.get("files"):
        # 已存在：走更新
        file_id = r["files"][0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"♻️ 已更新：{fname}  (fileId={file_id})")
    else:
        # 不存在：新建并上传
        meta = {"name": fname, "parents": [folder_id]}
        created = service.files().create(body=meta, media_body=media, fields="id").execute()
        print(f"✅ 已上传：{fname}  (fileId={created['id']})")


def main():
    try:
        print(f"➡️ 准备上传：{CSV_PATH}")
        print(f"➡️ 目标文件夹：{FOLDER_ID}")
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
