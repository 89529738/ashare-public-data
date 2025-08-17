import os, json, sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

# 凭证：由 workflow 写入到 creds.json
if not os.path.exists("creds.json"):
    fail("creds.json 不存在（请检查 DRIVE_CREDENTIALS_JSON Secret 是否已写入）。")

with open("creds.json", "r", encoding="utf-8") as f:
    info = json.load(f)

SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(info, scopes=SCOPES)
service = build("drive", "v3", credentials=creds, cache_discovery=False)

folder_id = os.environ.get("GDRIVE_FOLDER_ID")
file_path = os.environ.get("LATEST_CSV")

if not folder_id:
    fail("环境变量 GDRIVE_FOLDER_ID 为空。")
if not file_path:
    fail("环境变量 LATEST_CSV 为空（没找到匹配的 CSV）。")
if not os.path.exists(file_path):
    fail(f"文件不存在：{file_path}")

file_name = os.path.basename(file_path)
print(f"📤 准备上传：{file_name}")

file_metadata = {"name": file_name, "parents": [folder_id]}
media = MediaFileUpload(file_path, mimetype="text/csv", resumable=True)

uploaded = service.files().create(
    body=file_metadata,
    media_body=media,
    fields="id,webViewLink,webContentLink"
).execute()

print("✅ 上传成功")
print(f"   • fileId: {uploaded.get('id')}")
print(f"   • 查看链接: {uploaded.get('webViewLink')}")
print(f"   • 直接下载: {uploaded.get('webContentLink')}")
