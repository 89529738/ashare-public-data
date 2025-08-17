import os
import mimetypes
from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# === 必填：来自 GitHub Secrets / 运行环境 ===
FOLDER_ID = os.environ["GDRIVE_FOLDER_ID"]           # 目标文件夹 ID
CLIENT_ID = os.environ["GDRIVE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GDRIVE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GDRIVE_REFRESH_TOKEN"]
CSV_PATH = os.environ.get("LATEST_CSV")               # 源 CSV 文件（通常是 *_latest.csv）
DATE_TAG = os.environ.get("DATE_TAG")                 # 期待的日期标签（如 20250817）


def _today_cn_yyyymmdd() -> str:
    """默认使用北京时间（UTC+8）的当天日期。"""
    # GitHub runner 是 UTC，用 +8小时得到北京时间
    dt = datetime.utcnow() + timedelta(hours=8)
    return dt.strftime("%Y%m%d")


def _build_target_name(src_path: str, date_tag: str) -> str:
    """
    把 *_latest.csv 改成 *_YYYYMMDD.csv；
    若源文件名里没有 _latest，也会按 <name>_YYYYMMDD.csv 命名。
    """
    base = os.path.basename(src_path)
    stem, ext = os.path.splitext(base)
    if not ext:
        ext = ".csv"  # 兜底

    # 去掉 _latest
    stem_no_latest = stem.replace("_latest", "")
    # 拼成带日期的新名字
    return f"{stem_no_latest}_{date_tag}{ext}"


def _get_service():
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


def upload_or_update(service, file_path: str, folder_id: str, target_name: str):
    mime_type = mimetypes.guess_type(file_path)[0] or "text/csv"

    # Drive 查询：同名 + 同父文件夹
    safe_name = target_name.replace("'", "\\'")
    q = f"name = '{safe_name}' and '{folder_id}' in parents and trashed = false"

    r = service.files().list(
        q=q, spaces="drive", fields="files(id,name)", pageSize=1
    ).execute()

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    if r.get("files"):
        file_id = r["files"][0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"♻️ 已更新：{target_name}  (fileId={file_id})")
    else:
        meta = {"name": target_name, "parents": [folder_id]}
        created = service.files().create(body=meta, media_body=media, fields="id").execute()
        print(f"✅ 已上传：{target_name}  (fileId={created['id']})")


def main():
    if not CSV_PATH or not os.path.exists(CSV_PATH):
        raise SystemExit(f"❌ 目标文件不存在: {CSV_PATH}")

    # 准备日期标签
    date_tag = DATE_TAG or _today_cn_yyyymmdd()
    target_name = _build_target_name(CSV_PATH, date_tag)

    try:
        print(f"➡️ 源文件：{CSV_PATH}")
        print(f"➡️ 目标名：{target_name}")
        service = _get_service()
        upload_or_update(service, CSV_PATH, FOLDER_ID, target_name)
    except HttpError as e:
        print("❌ Google Drive API 错误：", e)
        raise
    except Exception as e:
        print("❌ 运行失败：", e)
        raise


if __name__ == "__main__":
    main()
