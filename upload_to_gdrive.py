# upload_to_gdrive.py
import os, sys, json, base64
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def normalize_json_string(s: str) -> str:
    """清洗常见粘贴问题：去掉```代码块、首尾引号、花引号；若是base64也尝试解码"""
    if not s:
        return s
    t = s.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    t = (t.replace("“", '"').replace("”", '"')
           .replace("‘", "'").replace("’", "'"))
    # 先试 JSON
    try:
        json.loads(t)
        return t
    except Exception:
        pass
    # 再试 base64
    try:
        tb = base64.b64decode(t, validate=True).decode("utf-8", "replace").strip()
        json.loads(tb)
        return tb
    except Exception:
        return t

def load_service_account_info():
    raw = os.environ.get("DRIVE_CREDENTIALS_JSON", "")
    if raw:
        text = normalize_json_string(raw)
        info = json.loads(text)  # 若失败会抛异常，Actions 会显示行号
        with open("creds.json", "w", encoding="utf-8") as f:
            json.dump(info, f)
        return info
    # 回退：读取已经写入的文件
    with open("creds.json", "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    file_path = os.environ.get("LATEST_CSV")

    if not folder_id:
        print("❌ 缺少环境变量 GDRIVE_FOLDER_ID"); sys.exit(1)
    if not file_path or not os.path.exists(file_path):
        print(f"❌ 找不到要上传的文件：{file_path}"); sys.exit(1)

    # 凭证
    info = load_service_account_info()
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # 先校验文件夹 ID 是否可访问
    try:
        folder_meta = service.files().get(fileId=folder_id, fields="id,name").execute()
        print(f"📁 目标文件夹：{folder_meta.get('name')} (id={folder_meta.get('id')})")
    except HttpError as e:
        print("❌ 无法访问目标文件夹。")
        print("   可能原因：1) GDRIVE_FOLDER_ID 不是纯 ID；2) 服务账号无权限；3) ID 写错。")
        print("   请确认：把服务账号邮箱添加为该文件夹“编辑者”，并只填纯 ID，如：16VD5wA9C...Q49mx")
        raise

    file_name = os.path.basename(file_path)
    print(f"📤 准备上传：{file_name}")

    media = MediaFileUpload(file_path, mimetype="text/csv", resumable=False)  # 非分片上传更稳
    file_metadata = {"name": file_name, "parents": [folder_id]}

    try:
        res = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink,webContentLink"
        ).execute()
    except HttpError as e:
        print("❌ 上传失败（Google Drive 返回错误）：")
        print(e)
        # 常见 404：File not found: <folderId> → 权限或ID错误
        raise

    print("✅ 上传成功：")
    print(f"   • fileId: {res.get('id')}")
    print(f"   • 查看链接: {res.get('webViewLink')}")
    print(f"   • 直接下载: {res.get('webContentLink')}")

if __name__ == "__main__":
    main()
